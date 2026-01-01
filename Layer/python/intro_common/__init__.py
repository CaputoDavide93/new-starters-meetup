"""
IntroChat Common Package - Shared utilities for Lambda functions

Contains:
- config: Configuration management (environment-based)
- azure_sync: Azure AD group synchronization
- calendar_utils: Google Calendar integration
- dynamo_utils: DynamoDB utilities

Note: This package is deployed as 'intro_common' in the Lambda Layer.
"""

__version__ = "3.13.0"
__all__ = [
    "config",
    "azure_sync",
    "calendar_utils",
    "dynamo_utils",
]
