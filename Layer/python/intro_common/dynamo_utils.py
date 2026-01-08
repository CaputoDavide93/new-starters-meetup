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
        # Normalize email to lowercase for consistent DB keys
        email = email.lower()
        
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
        # Normalize exclude_set to lowercase for comparison
        exclude_set_lower = {e.lower() for e in exclude_set}
        candidates = [m for m in members if m.lower() not in exclude_set_lower]
        LOG.info(f"Found {len(candidates)} valid candidates out of {len(members)} members")
        
        if not candidates:
            LOG.warning("No valid candidates available")
            return None
        
        # Get weights for all candidates using BatchGetItem for efficiency
        weights: dict[str, float] = {}
        LOG.debug(f"Fetching weights for {len(candidates)} candidates (batch)...")
        
        # BatchGetItem has a limit of 100 items per request
        batch_size = 100
        for i in range(0, len(candidates), batch_size):
            batch_candidates = candidates[i:i + batch_size]
            
            # Prepare batch request
            request_items = {
                table_name: {
                    "Keys": [{"email": c} for c in batch_candidates],
                    "ProjectionExpression": "email, weight"
                }
            }
            
            try:
                response = dynamodb.batch_get_item(RequestItems=request_items)
                
                # Process results
                for item in response.get("Responses", {}).get(table_name, []):
                    email = item.get("email", "").lower()
                    weight = float(item.get("weight", 0.0))
                    weights[email] = 1.0 / max(0.1, weight + 1.0)
                    LOG.debug(f"    {email}: weight={weights[email]:.2f} (intro_count={weight})")
                
                # Handle unprocessed items (throttling)
                unprocessed = response.get("UnprocessedKeys", {})
                while unprocessed:
                    LOG.debug(f"    Retrying {len(unprocessed.get(table_name, {}).get('Keys', []))} unprocessed items...")
                    response = dynamodb.batch_get_item(RequestItems=unprocessed)
                    for item in response.get("Responses", {}).get(table_name, []):
                        email = item.get("email", "").lower()
                        weight = float(item.get("weight", 0.0))
                        weights[email] = 1.0 / max(0.1, weight + 1.0)
                    unprocessed = response.get("UnprocessedKeys", {})
                    
            except Exception as e:
                LOG.warning(f"Batch get failed, falling back to individual gets: {e}")
                for candidate in batch_candidates:
                    try:
                        resp = table.get_item(Key={"email": candidate})
                        weight = float(resp.get("Item", {}).get("weight", 0.0))
                        weights[candidate.lower()] = 1.0 / max(0.1, weight + 1.0)
                    except Exception as inner_e:
                        LOG.warning(f"Could not get weight for {candidate}: {inner_e}")
                        weights[candidate.lower()] = 1.0
        
        # Add default weight for candidates not found in DB (new users)
        for candidate in candidates:
            if candidate.lower() not in weights:
                weights[candidate.lower()] = 1.0  # Default: 0 intros
                LOG.debug(f"    {candidate}: default weight=1.0 (new user)")
        
        LOG.debug(f"Weight calculation complete. Selecting from {len(weights)} candidates...")
        
        if not weights:
            LOG.info(f"No weights calculated, returning random choice")
            return random.choice(candidates)
        
        # Find minimum weight (intro_count) - these are users with fewest intros
        # Note: weights dict stores inverse probability, we need to find users with lowest intro_count
        # Reconstruct intro counts from inverse weights: weight = 1/(intro_count+1), so intro_count = 1/weight - 1
        intro_counts = {email: (1.0 / w) - 1.0 for email, w in weights.items()}
        min_intro_count = min(intro_counts.values())
        
        # Filter to only candidates with minimum intro count (fairest selection)
        min_weight_candidates = [email for email, count in intro_counts.items() if count == min_intro_count]
        
        LOG.info(f"Found {len(min_weight_candidates)} candidates with min intro_count={min_intro_count:.0f}")
        
        # Random selection from minimum-weight pool
        selected = random.choice(min_weight_candidates)
        LOG.info(f"Selected partner: {selected} (intro_count: {min_intro_count:.0f})")
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
        # Normalize email to lowercase for consistent DB keys
        email = email.lower()
        
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)
        
        from decimal import Decimal
        table.update_item(
            Key={"email": email},
            UpdateExpression="SET weight = if_not_exists(weight, :zero) + :inc",
            ExpressionAttributeValues={
                ":zero": Decimal("0"),
                ":inc": Decimal("1"),
            },
        )
        
        LOG.debug(f"Incremented weight for {email}")
        
    except Exception as e:
        LOG.error(f"Failed to increment weight: {e}", exc_info=True)
        raise
