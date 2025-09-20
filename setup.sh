#!/bin/bash

# KnowledgeInjester Setup Script
# This script helps set up the KnowledgeInjester project

set -e

echo "🚀 Setting up KnowledgeInjester..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.10+ and try again."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python $PYTHON_VERSION is installed, but Python $REQUIRED_VERSION+ is required."
    exit 1
fi

echo "✅ Python $PYTHON_VERSION detected"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file from template..."
    cp env.example .env
    echo "📝 Please edit .env file with your configuration before continuing"
    echo "   - Set your database credentials"
    echo "   - Set your OpenAI API key"
    echo "   - Set your Supabase credentials"
    echo ""
    read -p "Press Enter after you've configured .env file..."
else
    echo "✅ .env file already exists"
fi

# Check if PostgreSQL is running
echo "🐘 Checking PostgreSQL connection..."
if ! python3 -c "import psycopg2; psycopg2.connect('postgresql://postgres:password@localhost:5432/postgres')" 2>/dev/null; then
    echo "⚠️  PostgreSQL connection failed. Please ensure PostgreSQL is running and configured."
    echo "   You can start PostgreSQL with: sudo systemctl start postgresql"
    echo "   Or use Docker: docker run --name postgres-pgvector -e POSTGRES_PASSWORD=password -e POSTGRES_DB=knowledgeinjester -p 5432:5432 -d pgvector/pgvector:pg15"
fi

# Run migrations
echo "🗄️ Running database migrations..."
python manage.py migrate

# Create superuser (optional)
echo ""
read -p "Would you like to create a superuser? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python manage.py createsuperuser
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Start the development server: python manage.py runserver"
echo "2. Open http://localhost:8000/docs to view the API documentation"
echo "3. Open http://localhost:8000/admin to access the Django admin (if you created a superuser)"
echo ""
echo "For more information, see the README.md file."
