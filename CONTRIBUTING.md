# 🤝 Contributing to NewStarters MeetUp

First off, thank you for considering contributing to NewStarters MeetUp! 🎉

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)

## 📜 Code of Conduct

This project follows a simple code of conduct:

- **Be respectful**: Treat everyone with respect
- **Be inclusive**: Welcome newcomers and help them learn
- **Be constructive**: Focus on what's best for the community
- **Be patient**: Remember everyone was new once

## 🚀 Getting Started

### Prerequisites

- Python 3.13+
- Docker (for building Lambda layers)
- AWS CLI configured
- Git

### Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/NewStarters_MeetUp.git
cd NewStarters_MeetUp
git remote add upstream https://github.com/MITT/NewStarters_MeetUp.git
```

## 💻 Development Setup

### 1. Create Virtual Environment

```bash
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r layer/requirements.txt
pip install -r requirements-dev.txt  # If available
```

### 3. Set Up Pre-commit Hooks (Recommended)

```bash
pip install pre-commit
pre-commit install
```

### 4. Configure Local Testing

Create a `secrets.local.json` for local testing (never commit this!):

```json
{
  "slack_bot_token": "xoxb-test-token",
  "slack_signing_secret": "test-secret",
  "...": "..."
}
```

## 🎯 How to Contribute

### 🐛 Reporting Bugs

1. Check existing issues first
2. Use the bug report template
3. Include:
   - Python version
   - AWS Lambda runtime version
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant logs (redact sensitive data!)

### 💡 Suggesting Features

1. Check existing feature requests
2. Open an issue with the feature request template
3. Describe:
   - Use case and motivation
   - Proposed solution
   - Alternatives considered

### 🔧 Code Contributions

1. **Find an issue** to work on, or create one
2. **Comment** on the issue to let others know you're working on it
3. **Fork** the repository
4. **Create a branch**: `git checkout -b feature/your-feature-name`
5. **Make changes** following our coding standards
6. **Test** your changes
7. **Commit** with clear messages
8. **Push** and create a Pull Request

## 📤 Pull Request Process

### Before Submitting

- [ ] Code follows the style guidelines
- [ ] Tests pass locally
- [ ] Documentation is updated
- [ ] No secrets or sensitive data included
- [ ] Commit messages are clear and descriptive

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
Describe how you tested the changes

## Checklist
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review
- [ ] I have added tests (if applicable)
- [ ] I have updated documentation (if applicable)
```

### Review Process

1. Maintainers will review your PR
2. Address any feedback
3. Once approved, a maintainer will merge

## 📏 Coding Standards

### Python Style

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use type hints (Python 3.13+ style)
- Maximum line length: 100 characters
- Use f-strings for formatting

### Example

```python
def get_user_by_email(email: str, table_name: str) -> dict | None:
    """
    Retrieve user from DynamoDB by email.
    
    Args:
        email: User's email address (lowercase)
        table_name: DynamoDB table name
        
    Returns:
        User dict or None if not found
    """
    try:
        response = table.get_item(Key={"email": email.lower()})
        return response.get("Item")
    except Exception as e:
        LOG.error(f"Failed to get user {email}: {e}")
        return None
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Functions | snake_case | `get_calendar_service` |
| Variables | snake_case | `user_email` |
| Constants | UPPER_SNAKE | `MAX_RETRIES` |
| Classes | PascalCase | `CalendarEvent` |
| Files | snake_case | `calendar_utils.py` |

### Imports

```python
# Standard library
import json
import logging
from datetime import datetime

# Third-party
import boto3
from slack_sdk import WebClient

# Local
from intro_common.config import slack_cfg
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_calendar_utils.py
```

### Writing Tests

```python
import pytest
from intro_common.dynamo_utils import get_display_name

def test_get_display_name_from_email():
    """Test email-derived name formatting."""
    result = get_display_name("john.doe@example.com", "test-table")
    assert result == "John Doe"

def test_get_display_name_with_underscores():
    """Test underscore handling in email names."""
    result = get_display_name("john_doe@example.com", "test-table")
    assert result == "John Doe"
```

## 📚 Documentation

### Code Documentation

- All functions should have docstrings
- Use Google-style docstrings
- Include type hints

### README Updates

- Update README.md for new features
- Add examples for new functionality
- Keep the architecture diagram current

### Changelog

When contributing, add an entry to CHANGELOG.md:

```markdown
## [Unreleased]

### Added
- New feature description (#PR_NUMBER)

### Fixed
- Bug fix description (#PR_NUMBER)

### Changed
- Change description (#PR_NUMBER)
```

## 🏗️ Project Structure

```
src/
├── common/           # Shared utilities (synced to layer)
│   ├── config.py     # Configuration loading
│   ├── azure_sync.py # Azure AD integration
│   ├── calendar_utils.py # Google Calendar
│   └── dynamo_utils.py   # DynamoDB operations
├── ui_lambda/        # Slack UI handler
│   └── ui_entry.py
└── worker_lambda/    # Background worker
    └── worker_entry.py
```

### Key Files

| File | Purpose |
|------|---------|
| `src/common/config.py` | Secrets Manager integration |
| `src/ui_lambda/ui_entry.py` | Slack slash command handler |
| `src/worker_lambda/worker_entry.py` | Meeting booking logic |
| `scripts/build.sh` | Build deployment packages |

## ❓ Questions?

- Open a [GitHub Discussion](https://github.com/MITT/NewStarters_MeetUp/discussions)
- Email the maintainer: CaputoDav93@Gmail.com

---

Thank you for contributing! 🙏
