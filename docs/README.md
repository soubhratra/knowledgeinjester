# KnowledgeInjester Documentation

This directory contains detailed documentation for the KnowledgeInjester project.

## Security Implementation

### Core Security Documentation
- **[SECURITY_UPGRADE.md](SECURITY_UPGRADE.md)** - Complete technical specification of the security upgrade (Phase 0 & Phase 1)
- **[SECURITY_UPGRADE_SUMMARY.md](SECURITY_UPGRADE_SUMMARY.md)** - Executive summary of security changes
- **[MIGRATION_CHECKLIST.md](MIGRATION_CHECKLIST.md)** - Step-by-step migration guide for deploying security updates

### Testing & Fixes
- **[SECURITY_TEST_FIX_SUMMARY.md](SECURITY_TEST_FIX_SUMMARY.md)** - Summary of test issues and fixes
- **[TEST_RESULTS_SUMMARY.md](TEST_RESULTS_SUMMARY.md)** - Comprehensive test results documentation

### Local Development
- **[LOCALHOST_TESTING_GUIDE.md](LOCALHOST_TESTING_GUIDE.md)** - Guide for testing with localhost origins (HTTP exception for development)
- **[HOW_TO_USE_JWT_IN_SWAGGER.md](HOW_TO_USE_JWT_IN_SWAGGER.md)** - Detailed guide for passing JWT tokens in Swagger UI testing
- **[SWAGGER_UI_UPDATE.md](SWAGGER_UI_UPDATE.md)** - Updates to Swagger UI for request body visibility

## Feature Documentation

- **[CUSTOM_PROMPTS.md](CUSTOM_PROMPTS.md)** - Guide for setting up organization-specific AI prompts
- **[TESTING.md](TESTING.md)** - Testing guidelines and test suite documentation
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Overall implementation summary

## Development History

- **[CONVERSATION_HISTORY.md](CONVERSATION_HISTORY.md)** - Detailed conversation history of the implementation

## Quick Links

### Security Features
- **JWT Token Authentication** - See [SECURITY_UPGRADE.md](SECURITY_UPGRADE.md#phase-1-jwt-tokens)
- **Site-Key Based Access** - See [SECURITY_UPGRADE.md](SECURITY_UPGRADE.md#phase-0-site-key-origin)
- **Origin Validation** - See [SECURITY_UPGRADE.md](SECURITY_UPGRADE.md#origin-validation)
- **Conversation Tracking** - See [SECURITY_UPGRADE.md](SECURITY_UPGRADE.md#conversation-model)

### Testing
- **Running Tests** - See [TESTING.md](TESTING.md)
- **Security Tests** - See [SECURITY_TEST_FIX_SUMMARY.md](SECURITY_TEST_FIX_SUMMARY.md)
- **Local Testing with Swagger** - See [HOW_TO_USE_JWT_IN_SWAGGER.md](HOW_TO_USE_JWT_IN_SWAGGER.md)

### Deployment
- **Migration Steps** - See [MIGRATION_CHECKLIST.md](MIGRATION_CHECKLIST.md)
- **Production Configuration** - See [SECURITY_UPGRADE.md](SECURITY_UPGRADE.md#production-deployment)

## Getting Started

1. Start with [SECURITY_UPGRADE_SUMMARY.md](SECURITY_UPGRADE_SUMMARY.md) for a high-level overview
2. Follow [LOCALHOST_TESTING_GUIDE.md](LOCALHOST_TESTING_GUIDE.md) to test locally
3. Use [HOW_TO_USE_JWT_IN_SWAGGER.md](HOW_TO_USE_JWT_IN_SWAGGER.md) for API testing
4. Review [MIGRATION_CHECKLIST.md](MIGRATION_CHECKLIST.md) before deploying

## API Documentation

For interactive API documentation, visit:
- **Swagger UI**: http://localhost:8000/api/docs
- **Main README**: [../README.md](../README.md)

