"""
Azure AD synchronization utilities

Syncs Azure AD group members to DynamoDB table for intro matching.
"""

import logging
import json
import requests
from azure.identity import ClientSecretCredential
import boto3

LOG = logging.getLogger(__name__)

def sync_azure_group(
    tenant_id: str,
    client_id: str,
    client_secret: str,
    group_id: str,
    dynamodb_table_name: str,
) -> None:
    """
    Sync Azure AD group members to DynamoDB table.
    
    Args:
        tenant_id: Azure tenant ID
        client_id: Azure app client ID
        client_secret: Azure app client secret
        group_id: Azure group ID to sync
        dynamodb_table_name: DynamoDB table to update
    """
    try:
        # Authenticate with Azure AD
        credentials = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )
        
        # Get access token for Microsoft Graph API
        token = credentials.get_token("https://graph.microsoft.com/.default")
        
        # Use Microsoft Graph API to get group members
        headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json",
        }
        
        # Get group members via Microsoft Graph
        url = f"https://graph.microsoft.com/v1.0/groups/{group_id}/members?$select=mail,userPrincipalName"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        emails = []
        
        for member in data.get("value", []):
            # Prefer mail, fall back to userPrincipalName
            email = member.get("mail") or member.get("userPrincipalName")
            if email:
                emails.append(email)
        
        LOG.info(f"Synced {len(emails)} members from Azure AD group {group_id}")
        
        # Update DynamoDB table
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(dynamodb_table_name)
        
        # Store members list with 'email' as partition key (table schema requirement)
        table.put_item(
            Item={
                "email": "members",
                "active": True,
                "member_list": emails,
            }
        )
        
        LOG.info(f"Updated DynamoDB table {dynamodb_table_name} with {len(emails)} members")
        
    except Exception as e:
        LOG.error(f"Failed to sync Azure AD group: {e}", exc_info=True)
        raise
