"""
Tests for Django management commands.
"""
import pytest
from io import StringIO
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.tenants.models import Organization


@pytest.mark.django_db
class TestSetCustomPromptCommand:
    """Test the set_custom_prompt management command."""
    
    def test_set_custom_prompt_from_text(self):
        """Test setting custom prompt from text."""
        # Create test organization
        org = Organization.objects.create(
            name="Test Org",
            slug="test-org",
            tenant_id="test-tenant-123"
        )
        
        custom_prompt = "You are a specialized assistant for {organization_name}.\n\nContext:\n{context}\n\nQuestion:\n{question}\n\nSources:\n{sources}"
        
        # Call command
        call_command(
            'set_custom_prompt',
            'test-tenant-123',
            '--prompt-text', custom_prompt,
            '--validate'
        )
        
        # Verify prompt was set
        org.refresh_from_db()
        assert org.custom_prompt == custom_prompt
    
    def test_set_custom_prompt_from_file(self, tmp_path):
        """Test setting custom prompt from file."""
        # Create test organization
        org = Organization.objects.create(
            name="Test Org",
            slug="test-org",
            tenant_id="test-tenant-123"
        )
        
        custom_prompt = "You are a specialized assistant for {organization_name}.\n\nContext:\n{context}\n\nQuestion:\n{question}\n\nSources:\n{sources}"
        
        # Create temporary file
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text(custom_prompt)
        
        # Call command
        call_command(
            'set_custom_prompt',
            'test-tenant-123',
            '--prompt-file', str(prompt_file),
            '--validate'
        )
        
        # Verify prompt was set
        org.refresh_from_db()
        assert org.custom_prompt == custom_prompt
    
    def test_set_custom_prompt_clear(self):
        """Test clearing custom prompt."""
        # Create test organization with custom prompt
        org = Organization.objects.create(
            name="Test Org",
            slug="test-org",
            tenant_id="test-tenant-123",
            custom_prompt="Some custom prompt"
        )
        
        # Call command to clear
        call_command('set_custom_prompt', 'test-tenant-123', '--clear')
        
        # Verify prompt was cleared
        org.refresh_from_db()
        assert org.custom_prompt == ""
    
    def test_set_custom_prompt_nonexistent_organization(self):
        """Test setting custom prompt for non-existent organization."""
        with pytest.raises(CommandError, match="Organization with tenant_id"):
            call_command(
                'set_custom_prompt',
                'nonexistent-tenant',
                '--prompt-text', 'Some prompt'
            )
    
    def test_set_custom_prompt_validation_failure(self):
        """Test setting custom prompt with validation failure."""
        # Create test organization
        org = Organization.objects.create(
            name="Test Org",
            slug="test-org",
            tenant_id="test-tenant-123"
        )
        
        invalid_prompt = "This prompt is missing required placeholders"
        
        with pytest.raises(CommandError, match="Prompt template validation failed"):
            call_command(
                'set_custom_prompt',
                'test-tenant-123',
                '--prompt-text', invalid_prompt,
                '--validate'
            )
    
    def test_set_custom_prompt_missing_arguments(self):
        """Test setting custom prompt with missing arguments."""
        # Create test organization first
        org = Organization.objects.create(
            name="Test Org",
            slug="test-org",
            tenant_id="test-tenant-123"
        )
        
        with pytest.raises(CommandError, match="You must provide either"):
            call_command('set_custom_prompt', 'test-tenant-123')
    
    def test_set_custom_prompt_conflicting_arguments(self):
        """Test setting custom prompt with conflicting arguments."""
        # Create test organization first
        org = Organization.objects.create(
            name="Test Org",
            slug="test-org",
            tenant_id="test-tenant-123"
        )
        
        with pytest.raises(CommandError, match="You cannot provide both"):
            call_command(
                'set_custom_prompt',
                'test-tenant-123',
                '--prompt-text', 'Some prompt',
                '--prompt-file', 'some_file.txt'
            )
    
    def test_set_custom_prompt_file_not_found(self):
        """Test setting custom prompt with non-existent file."""
        # Create test organization first
        org = Organization.objects.create(
            name="Test Org",
            slug="test-org",
            tenant_id="test-tenant-123"
        )
        
        with pytest.raises(CommandError, match="File.*not found"):
            call_command(
                'set_custom_prompt',
                'test-tenant-123',
                '--prompt-file', 'nonexistent_file.txt'
            )
    
    def test_set_custom_prompt_without_validation(self):
        """Test setting custom prompt without validation."""
        # Create test organization
        org = Organization.objects.create(
            name="Test Org",
            slug="test-org",
            tenant_id="test-tenant-123"
        )
        
        # This prompt would fail validation but should work without --validate
        invalid_prompt = "This prompt is missing required placeholders"
        
        # Should not raise error
        call_command(
            'set_custom_prompt',
            'test-tenant-123',
            '--prompt-text', invalid_prompt
        )
        
        # Verify prompt was set despite being invalid
        org.refresh_from_db()
        assert org.custom_prompt == invalid_prompt
    
    def test_set_custom_prompt_output(self, capsys):
        """Test set custom prompt command output."""
        # Create test organization
        org = Organization.objects.create(
            name="Test Org",
            slug="test-org",
            tenant_id="test-tenant-123"
        )
        
        custom_prompt = "You are a specialized assistant for {organization_name}.\n\nContext:\n{context}\n\nQuestion:\n{question}\n\nSources:\n{sources}"
        
        # Call command
        call_command(
            'set_custom_prompt',
            'test-tenant-123',
            '--prompt-text', custom_prompt,
            '--validate'
        )
        
        # Check output
        captured = capsys.readouterr()
        assert "Successfully set custom prompt" in captured.out
        assert "Test Org" in captured.out
        assert "Prompt preview:" in captured.out
