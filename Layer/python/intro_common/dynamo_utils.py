"""
DynamoDB utilities for intro matching

Manages user weights and partner selection.
"""

import logging
import random
from typing import Optional

import boto3

LOG = logging.getLogger(__name__)


def ensure_user_in_db(
    email: str,
    table_name: str,
    initial_weight: float = 0.0,
) -> None:
    """
    Ensure user exists in DynamoDB table with initial weight.
    
    Args:
        email: User email
        table_name: DynamoDB table name
        initial_weight: Initial weight value
    """
    try:
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)
        
        # Check if user exists
        response = table.get_item(Key={"email": email})
        
        if "Item" not in response:
            # User doesn't exist, create with initial weight
            table.put_item(
                Item={
                    "email": email,
                    "weight": initial_weight,
                }
            )
            LOG.debug(f"Created user in DB: {email}")
        else:
            LOG.debug(f"User already exists in DB: {email}")
            
    except Exception as e:
        LOG.error(f"Failed to ensure user in DB: {e}", exc_info=True)
        raise


def pick_one_intro_partner(
    table_name: str,
    exclude_set: set[str],
) -> Optional[str]:
    """
    Pick one intro partner weighted by inverse of introduction count.
    
    Users with lower weights (fewer intros) are picked more frequently.
    
    Args:
        table_name: DynamoDB table name
        exclude_set: Set of emails to exclude
        
    Returns:
        Partner email, or None if no valid partner found
    """
    try:
        LOG.info(f"pick_one_intro_partner: Starting with exclude_set size={len(exclude_set)}")
        LOG.debug(f"  Creating dynamodb resource...")
        dynamodb = boto3.resource("dynamodb")
        LOG.debug(f"  Getting table: {table_name}")
        table = dynamodb.Table(table_name)
        LOG.debug(f"  Table acquired")
        
        # Get all members (stored with email="members")
        LOG.debug(f"Fetching members list from {table_name}...")
        response = table.get_item(Key={"email": "members"})
        LOG.debug(f"Members list fetch complete")
        
        if "Item" not in response or not response["Item"].get("member_list"):
            LOG.warning("No members found in DB")
            return None
        
        members = response["Item"]["member_list"]
        candidates = [m for m in members if m not in exclude_set]
        LOG.info(f"Found {len(candidates)} valid candidates out of {len(members)} members")
        
        if not candidates:
            LOG.warning("No valid candidates available")
            return None
        
        # Get weights for all candidates
        weights: dict[str, float] = {}
        LOG.debug(f"Fetching weights for {len(candidates)} candidates...")
        for i, candidate in enumerate(candidates):
            try:
                LOG.debug(f"  Fetching weight for candidate {i+1}/{len(candidates)}: {candidate}")
                resp = table.get_item(Key={"email": candidate})
                weight = float(resp.get("Item", {}).get("weight", 0.0))
                # Inverse weight: lower intro count = higher selection probability
                weights[candidate] = 1.0 / max(0.1, weight + 1.0)
                LOG.debug(f"    Weight: {weights[candidate]:.2f} (intro_count={weight})")
            except Exception as e:
                LOG.warning(f"Could not get weight for {candidate}: {e}")
                weights[candidate] = 1.0
        
        LOG.debug(f"Weight calculation complete. Selecting from {len(weights)} candidates...")
        # Weighted random selection
        if not weights:
            LOG.info(f"No weights calculated, returning random choice")
            return random.choice(candidates)
        
        total_weight = sum(weights.values())
        pick = random.uniform(0, total_weight)
        current = 0
        
        for candidate, weight in weights.items():
            current += weight
            if pick <= current:
                LOG.info(f"Selected partner: {candidate} (weight: {weight:.2f})")
                return candidate
        
        # Fallback
        selected = list(weights.keys())[0]
        LOG.info(f"Fallback selection: {selected}")
        return selected
        
    except Exception as e:
        LOG.error(f"Failed to pick partner: {e}", exc_info=True)
        return None


def increment_user_weight(email: str, table_name: str) -> None:
    """
    Increment user's intro count (weight).
    
    Args:
        email: User email
        table_name: DynamoDB table name
    """
    try:
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)
        
        table.update_item(
            Key={"email": email},
            UpdateExpression="SET weight = if_not_exists(weight, :zero) + :inc",
            ExpressionAttributeValues={
                ":zero": 0.0,
                ":inc": 1.0,
            },
        )
        
        LOG.debug(f"Incremented weight for {email}")
        
    except Exception as e:
        LOG.error(f"Failed to increment weight: {e}", exc_info=True)
        raise
