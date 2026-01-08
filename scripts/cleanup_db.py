#!/usr/bin/env python3
"""
DynamoDB cleanup script

Fixes:
1. Duplicate user records from email case mismatch
2. Normalizes member_list to lowercase
3. Merges weights for duplicate users (keeps highest weight)

Run with: python scripts/cleanup_db.py --table intro-weights --dry-run
         python scripts/cleanup_db.py --table intro-weights --apply
"""

import argparse
import boto3
from collections import defaultdict
from decimal import Decimal


def cleanup_table(table_name: str, dry_run: bool = True) -> None:
    """Clean up DynamoDB table by merging case-duplicate users."""
    
    dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
    table = dynamodb.Table(table_name)
    
    print(f"\n{'='*60}")
    print(f"Cleaning up table: {table_name}")
    print(f"Mode: {'DRY RUN' if dry_run else 'APPLYING CHANGES'}")
    print(f"{'='*60}\n")
    
    # Scan all items
    print("Scanning table...")
    items = []
    response = table.scan()
    items.extend(response.get("Items", []))
    
    while response.get("LastEvaluatedKey"):
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))
    
    print(f"Found {len(items)} total items\n")
    
    # Group by lowercase email to find duplicates
    email_groups = defaultdict(list)
    members_item = None
    
    for item in items:
        email = item.get("email", "")
        if email == "members":
            members_item = item
        else:
            email_groups[email.lower()].append(item)
    
    # Find duplicates (same lowercase email, different original case)
    duplicates = {k: v for k, v in email_groups.items() if len(v) > 1}
    
    if duplicates:
        print(f"Found {len(duplicates)} duplicate email groups:\n")
        for email_lower, records in duplicates.items():
            print(f"  {email_lower}:")
            for r in records:
                print(f"    - Original: {r['email']}, weight: {r.get('weight', 0)}, display_name: {r.get('display_name', 'N/A')}")
    else:
        print("No duplicate email records found.\n")
    
    # Check member_list for mixed case
    if members_item:
        member_list = members_item.get("member_list", [])
        mixed_case = [m for m in member_list if m != m.lower()]
        
        if mixed_case:
            print(f"\nFound {len(mixed_case)} mixed-case emails in member_list:")
            for m in mixed_case[:10]:  # Show first 10
                print(f"  - {m}")
            if len(mixed_case) > 10:
                print(f"  ... and {len(mixed_case) - 10} more")
        else:
            print("\nmember_list is already lowercase.")
    
    if dry_run:
        print("\n" + "="*60)
        print("DRY RUN - No changes made. Run with --apply to fix issues.")
        print("="*60)
        return
    
    # Apply fixes
    print("\nApplying fixes...")
    
    # 1. Merge duplicate users (keep highest weight, latest display_name)
    for email_lower, records in duplicates.items():
        # Find the record with the highest weight
        max_weight = max(float(r.get("weight", 0)) for r in records)
        display_name = next((r.get("display_name") for r in records if r.get("display_name")), "")
        
        # Delete all old records
        for r in records:
            table.delete_item(Key={"email": r["email"]})
            print(f"  Deleted: {r['email']}")
        
        # Create single lowercase record with merged data
        table.put_item(Item={
            "email": email_lower,
            "weight": Decimal(str(max_weight)),
            "display_name": display_name,
        })
        print(f"  Created: {email_lower} (weight: {max_weight}, display_name: {display_name})")
    
    # 2. Fix member_list to be all lowercase
    if members_item:
        member_list = members_item.get("member_list", [])
        lowercase_list = [m.lower() for m in member_list]
        
        if member_list != lowercase_list:
            table.update_item(
                Key={"email": "members"},
                UpdateExpression="SET member_list = :ml",
                ExpressionAttributeValues={":ml": lowercase_list}
            )
            print(f"\n  Updated member_list to lowercase ({len(lowercase_list)} members)")
    
    print("\n" + "="*60)
    print("Cleanup complete!")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description="Clean up DynamoDB tables after case-sensitivity fix")
    parser.add_argument("--table", required=True, help="DynamoDB table name (e.g., intro-weights)")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without applying")
    
    args = parser.parse_args()
    
    # Default to dry-run unless --apply is specified
    dry_run = not args.apply
    
    cleanup_table(args.table, dry_run=dry_run)


if __name__ == "__main__":
    main()
