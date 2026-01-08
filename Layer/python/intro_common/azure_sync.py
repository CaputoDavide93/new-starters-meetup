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
) -> int:
    """
    Sync Azure AD group members to DynamoDB table.
    
    Args:
        tenant_id: Azure tenant ID
        client_id: Azure app client ID
        client_secret: Azure app client secret
        group_id: Azure group ID to sync
        dynamodb_table_name: DynamoDB table to update
        
    Returns:
        Number of departed users removed from DB
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
        
        # Get group members via Microsoft Graph (with pagination for large groups)
        # Include displayName for user records
        url = f"https://graph.microsoft.com/v1.0/groups/{group_id}/members?$select=mail,userPrincipalName,displayName&$top=999"
        members_data = []  # Store email and display name pairs
        
        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            for member in data.get("value", []):
                # Prefer mail, fall back to userPrincipalName
                email = member.get("mail") or member.get("userPrincipalName")
                display_name = member.get("displayName", "")
                if email:
                    members_data.append({
                        "email": email.lower(),
                        "display_name": display_name,
                    })
            
            # Handle pagination - get next page if exists
            url = data.get("@odata.nextLink")
        
        emails = [m["email"] for m in members_data]
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
        
        # Create/update individual user records with display names
        for member in members_data:
            try:
                # Update display_name without overwriting weight
                table.update_item(
                    Key={"email": member["email"]},
                    UpdateExpression="SET display_name = :dn",
                    ExpressionAttributeValues={":dn": member["display_name"]},
                )
            except Exception as e:
                LOG.warning(f"Failed to update display_name for {member['email']}: {e}")
        
        LOG.info(f"Updated DynamoDB table {dynamodb_table_name} with {len(emails)} members")
        
        # Clean up departed users - remove weight records for users no longer in Azure
        current_members_set = set(emails)
        
        # Scan table for all user records (not the "members" record)
        scan_response = table.scan(
            FilterExpression="email <> :members",
            ExpressionAttributeValues={":members": "members"}
        )
        
        departed_count = 0
        for item in scan_response.get("Items", []):
            user_email = item.get("email", "").lower()
            if user_email and user_email not in current_members_set:
                # User no longer in Azure AD - delete their record
                table.delete_item(Key={"email": item["email"]})
                LOG.info(f"Removed departed user from DB: {item['email']}")
                departed_count += 1
        
        # Handle pagination if table is large
        while scan_response.get("LastEvaluatedKey"):
            scan_response = table.scan(
                FilterExpression="email <> :members",
                ExpressionAttributeValues={":members": "members"},
                ExclusiveStartKey=scan_response["LastEvaluatedKey"]
            )
            for item in scan_response.get("Items", []):
                user_email = item.get("email", "").lower()
                if user_email and user_email not in current_members_set:
                    table.delete_item(Key={"email": item["email"]})
                    LOG.info(f"Removed departed user from DB: {item['email']}")
                    departed_count += 1
        
        if departed_count > 0:
            LOG.info(f"Cleaned up {departed_count} departed users from {dynamodb_table_name}")
        
        return departed_count  # Return for Slack notification
        
    except Exception as e:
        LOG.error(f"Failed to sync Azure AD group: {e}", exc_info=True)
        raise
