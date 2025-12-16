"""
Configuration management for IntroChat Lambda functions

Loads from AWS Secrets Manager via CONFIG_SECRET environment variable.
The secret should contain a JSON object with all configuration.
"""

import os
import json
import logging
from typing import Any

import boto3

LOG = logging.getLogger(__name__)

def _load_secrets() -> dict[str, Any]:
    """Load configuration from AWS Secrets Manager."""
    secret_arn = os.environ.get("CONFIG_SECRET")
    if not secret_arn:
        raise ValueError("Missing CONFIG_SECRET environment variable")
    
    try:
        client = boto3.client("secretsmanager", region_name="eu-west-1")
        response = client.get_secret_value(SecretId=secret_arn)
        
        if "SecretString" in response:
            secret = json.loads(response["SecretString"])
            LOG.info("Loaded configuration from Secrets Manager")
            return secret
        else:
            raise ValueError("Secret does not contain SecretString")
    except Exception as e:
        LOG.error(f"Failed to load secrets: {e}")
        raise

# Load secrets once at module import time
_secrets = _load_secrets()


# ──── SLACK CONFIGURATION ────────────────────────────────────────────────
slack_cfg: dict[str, str] = {
    "bot_token": _secrets.get("slack_bot_token", ""),
    "signing_secret": _secrets.get("slack_signing_secret", ""),
    "trigger_channel_id": _secrets.get("slack_trigger_channel", "C12345678"),
}

# ──── AZURE AD CONFIGURATION (Coffee Intro) ──────────────────────────────
azure_cfg: dict[str, str] = {
    "tenant_id": _secrets.get("azure_tenant_id", ""),
    "client_id": _secrets.get("azure_client_id", ""),
    "client_secret": _secrets.get("azure_client_secret", ""),
    "group_id": _secrets.get("azure_group_id", ""),
}

# ──── AZURE AD CONFIGURATION (Buddy Intro) ───────────────────────────────
# Falls back to coffee intro credentials if buddy-specific ones not provided
buddy_azure_cfg: dict[str, str] = {
    "tenant_id": _secrets.get("buddy_azure_tenant_id", azure_cfg["tenant_id"]),
    "client_id": _secrets.get("buddy_azure_client_id", azure_cfg["client_id"]),
    "client_secret": _secrets.get("buddy_azure_client_secret", azure_cfg["client_secret"]),
    "group_id": _secrets.get("buddy_azure_group_id", ""),
}

# ──── GOOGLE CONFIGURATION ───────────────────────────────────────────────
google_sa_key_json = _secrets.get("google_service_account_key", "{}")
try:
    google_sa_key: dict[str, Any] = json.loads(google_sa_key_json)
except json.JSONDecodeError:
    LOG.error("Failed to parse google_service_account_key as JSON")
    google_sa_key = {}

google_delegated_user: str = _secrets.get("google_delegated_user", "")
google_calendar_id: str = _secrets.get("google_calendar_id", "")

# ──── DYNAMODB CONFIGURATION ─────────────────────────────────────────────
dynamodb_table_name: str = _secrets.get("dynamodb_table_name", "")
buddy_dynamodb_table_name: str = _secrets.get("buddy_dynamodb_table_name", "")

# ──── MEETING TEMPLATES (Coffee Intro) ───────────────────────────────────
meeting_title_template: str = _secrets.get(
    "meeting_title_template",
    "☕️ Coffee: {person1} & {person2}"
)

meeting_description_template: str = _secrets.get(
    "meeting_description_template",
    "Intro meeting between {person1} and {person2}"
)

# ──── MEETING TEMPLATES (Buddy Intro) ────────────────────────────────────
buddy_meeting_title_template: str = _secrets.get(
    "buddy_meeting_title_template",
    "🤝 Buddy: {person1} & {person2}"
)

buddy_meeting_description_template: str = _secrets.get(
    "buddy_meeting_description_template",
    "Buddy meeting between {person1} and {person2}"
)
