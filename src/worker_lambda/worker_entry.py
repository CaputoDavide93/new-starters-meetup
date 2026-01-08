"""
IntroWorker Lambda - Background worker for booking intros

Handles the actual booking logic:
- Syncs Azure AD groups
- Books calendar meetings
- Updates DynamoDB weights

Uses AWS Lambda with ARM64 (Graviton) architecture.
Python 3.13+
"""

import json
import datetime
import logging
import time

import boto3
from slack_sdk import WebClient

from intro_common.config import (
    slack_cfg,
    azure_cfg,
    buddy_azure_cfg,
    google_sa_key,
    google_delegated_user,
    google_calendar_id,
    dynamodb_table_name,
    buddy_dynamodb_table_name,
    meeting_title_template,
    meeting_description_template,
    buddy_meeting_title_template,
    buddy_meeting_description_template,
)
from intro_common.azure_sync import sync_azure_group
from intro_common.dynamo_utils import (
    ensure_user_in_db,
    pick_one_intro_partner,
    increment_user_weight,
    get_display_name,
)
from intro_common.calendar_utils import (
    get_calendar_service,
    find_next_free_slot,
    create_event,
)

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    level=logging.DEBUG
)

SLACK = WebClient(token=slack_cfg["bot_token"])
CLOUDWATCH = boto3.client('cloudwatch')

# Meeting cadence (business days, not calendar days)
CADENCE_BUSINESS_DAYS = 2


def add_business_days(start: datetime.date, business_days: int) -> datetime.date:
    """
    Add business days to a date, skipping weekends.
    
    Args:
        start: Starting date
        business_days: Number of business days to add
        
    Returns:
        Date after adding business days
    """
    current = start
    days_added = 0
    
    while days_added < business_days:
        current += datetime.timedelta(days=1)
        # Monday=0, Friday=4, Saturday=5, Sunday=6
        if current.weekday() < 5:  # Weekday
            days_added += 1
    
    return current


def _publish_metrics(namespace: str, metrics: dict) -> None:
    """Publish custom metrics to CloudWatch."""
    try:
        metric_data = []
        for metric_name, value in metrics.items():
            metric_data.append({
                'MetricName': metric_name,
                'Value': value,
                'Unit': 'Count' if 'Count' in metric_name else 'Milliseconds',
                'Timestamp': datetime.datetime.now(datetime.timezone.utc)
            })

        if metric_data:
            CLOUDWATCH.put_metric_data(
                Namespace=namespace,
                MetricData=metric_data
            )
            LOG.debug(f"Published {len(metric_data)} metrics to CloudWatch")
    except Exception as e:
        LOG.warning(f"Failed to publish metrics: {e}")


def _safe_slack_post(channel: str, text: str, max_retries: int = 2) -> dict | None:
    """Post to Slack with retry logic and error handling."""
    for attempt in range(max_retries):
        try:
            response = SLACK.chat_postMessage(channel=channel, text=text)
            if not response.get("ok"):
                raise Exception(f"Slack API returned ok=False: {response.get('error')}")
            return response
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                LOG.warning(f"Slack post failed (attempt {attempt + 1}/{max_retries}): {e}, retrying in {wait_time}s")
                time.sleep(wait_time)
            else:
                LOG.error(f"Failed to post to Slack after {max_retries} attempts: {e}")
                return None


def book_all_intros(
    mode: str,
    channel: str,
    emails: list[str],
    start_date: datetime.date,
    n_meet: int,
) -> None:
    """
    Schedule n_meet 15-minute meetings per email in emails,
    spaced by CADENCE days from start_date.
    """
    LOG.info(f"Starting booking: mode={mode}, emails={len(emails)}, meetings={n_meet}")

    successes: list[str] = []
    failures: list[str] = []
    start_time = time.time()
    timeout_warning_sent = False

    # Select correct Azure config and DynamoDB table
    if mode == "coffee":
        departed_count = sync_azure_group(
            azure_cfg["tenant_id"],
            azure_cfg["client_id"],
            azure_cfg["client_secret"],
            azure_cfg["group_id"],
            dynamodb_table_name
        )
        table_name = dynamodb_table_name
        title_tpl, desc_tpl = meeting_title_template, meeting_description_template
    else:
        departed_count = sync_azure_group(
            buddy_azure_cfg["tenant_id"],
            buddy_azure_cfg["client_id"],
            buddy_azure_cfg["client_secret"],
            buddy_azure_cfg["group_id"],
            buddy_dynamodb_table_name
        )
        table_name = buddy_dynamodb_table_name
        title_tpl, desc_tpl = buddy_meeting_title_template, buddy_meeting_description_template
    
    if departed_count and departed_count > 0:
        _safe_slack_post(
            channel=channel,
            text=f":broom: Cleaned up {departed_count} departed user(s) from the database"
        )

    LOG.info(f"Azure sync completed. Table: {table_name}")

    # Build Calendar service
    svc = get_calendar_service(sa_key=google_sa_key, subject=google_delegated_user)
    LOG.info("Google Calendar service initialized")

    MAX_SEARCH_DAYS = 7
    MAX_PARTNER_ATTEMPTS = max(10, len(emails) * 2)
    global_used_partners: set[str] = set()

    for new_email in emails:
        # Check for timeout (Lambda has 15min max, warn at 14min)
        elapsed = time.time() - start_time
        if elapsed > 840 and not timeout_warning_sent:
            LOG.warning(f"Approaching Lambda timeout ({elapsed:.0f}s elapsed)")
            _safe_slack_post(
                channel=channel,
                text=":warning: Booking process taking longer than expected, may time out"
            )
            timeout_warning_sent = True

        if elapsed > 870:
            LOG.error(f"Stopping early to avoid timeout ({elapsed:.0f}s)")
            failures.append(f"Timeout: remaining emails not processed")
            break

        LOG.info(f"Booking for: {new_email}")
        LOG.debug(f"  n_meet={n_meet}")
        used_partners: set[str] = set()
        booked_slots: list[datetime.datetime] = []  # Track slots booked in this session
        last_booked_date: datetime.date | None = None  # Track last meeting date for cadence
        LOG.debug(f"  Initialized used_partners set and booked_slots list")

        LOG.debug(f"  Starting loop: for meet_i in range({n_meet})")
        for meet_i in range(n_meet):
            LOG.debug(f"  Meeting {meet_i + 1}/{n_meet} for {new_email}")
            
            # Calculate search start: either from last booked + CADENCE business days, or start_date
            if last_booked_date:
                # Must be at least CADENCE_BUSINESS_DAYS after the last booked meeting
                min_search_date = add_business_days(last_booked_date, CADENCE_BUSINESS_DAYS)
            else:
                # First meeting: start from start_date
                min_search_date = start_date
            
            LOG.debug(f"  Search starts from: {min_search_date}")
            slot = None
            partner = None

            # Try multiple partners if first is busy
            for attempt in range(MAX_PARTNER_ATTEMPTS):
                LOG.debug(f"    Partner attempt {attempt + 1}/{MAX_PARTNER_ATTEMPTS}")
                candidate_partner = pick_one_intro_partner(
                    table_name,
                    exclude_set={*emails, *used_partners, *global_used_partners}
                )
                LOG.debug(f"    Selected candidate: {candidate_partner}")
                if not candidate_partner:
                    LOG.warning(f"No partner available for {new_email}")
                    _safe_slack_post(
                        channel=channel,
                        text=f":warning: No partner available for {new_email}"
                    )
                    break

                LOG.debug(f"    Searching for slot with {candidate_partner}...")
                # Search for available slot
                for day_offset in range(MAX_SEARCH_DAYS):
                    candidate_day = min_search_date + datetime.timedelta(days=day_offset)
                    LOG.debug(f"      Day offset {day_offset}: {candidate_day.strftime('%Y-%m-%d %A')}")

                    # Skip past dates and weekends
                    if candidate_day < datetime.date.today() or candidate_day.weekday() >= 5:
                        LOG.debug(f"        Skipped (past date or weekend)")
                        continue

                    LOG.debug(f"        Querying calendar...")
                    slot = find_next_free_slot(
                        service=svc,
                        calendar_ids=[google_calendar_id, new_email, candidate_partner],
                        start_date=candidate_day,
                        window_start="11:00",
                        window_end="15:00",
                        excluded_slots=booked_slots,
                    )
                    LOG.debug(f"        Slot result: {slot}")
                    if slot:
                        LOG.info(f"    Found slot: {slot}")
                        partner = candidate_partner
                        break

                if slot and partner:
                    break

            if not slot or not partner:
                failures.append(f"No slot for {new_email}")
                continue

            # Create event
            try:
                # Get display names from DB (falls back to email-derived names)
                new_name = get_display_name(new_email, table_name)
                partner_name = get_display_name(partner, table_name)
                
                format_kwargs = {
                    # Standard placeholders
                    'person1': new_name,
                    'person2': partner_name,
                    # Alternative placeholders (legacy)
                    'new_first': new_name,
                    'new_second': partner_name,
                    'new_starter': new_name,
                    'buddy': partner_name,
                    'partner_first': partner_name,
                    # Email variants
                    'email1': new_email,
                    'email2': partner,
                }
                
                try:
                    summary = title_tpl.format(**format_kwargs) if '{' in title_tpl else f"Intro: {new_name} & {partner_name}"
                except KeyError as e:
                    LOG.warning(f"Unknown placeholder {e} in title template, using fallback")
                    summary = f"Intro: {new_name} & {partner_name}"

                try:
                    description = desc_tpl.format(**format_kwargs) if '{' in desc_tpl else f"{new_email} ↔ {partner}"
                except KeyError as e:
                    LOG.warning(f"Unknown placeholder {e} in description template, using fallback")
                    description = f"{new_email} ↔ {partner}"

                create_event(
                    service=svc,
                    calendar_id=google_calendar_id,
                    summary=summary,
                    description=description,
                    start_dt=slot,
                    duration=15,
                    attendees=[new_email, partner],
                )

                increment_user_weight(partner, table_name)
                used_partners.add(partner)
                global_used_partners.add(partner)
                booked_slots.append(slot)  # Track this slot to avoid double-booking
                last_booked_date = slot.date()  # Track for cadence - next meeting must be CADENCE days after this

                _safe_slack_post(
                    channel=channel,
                    text=f"✅ {new_email.split('@')[0].title()} ↔ {partner.split('@')[0].title()} — {slot:%d %b %H:%M}"
                )
                successes.append(f"{new_email} ↔ {partner}")

                LOG.info(f"Created event: {new_email} ↔ {partner} at {slot}")

            except Exception as e:
                LOG.error(f"Failed to create event: {e}")
                failures.append(f"Event creation failed: {e}")
                _safe_slack_post(
                    channel=channel,
                    text=f":warning: Failed to book meeting: {e}"
                )

    # Final summary
    _safe_slack_post(
        channel=channel,
        text=f":white_check_mark: Booking complete! {len(successes)} succeeded, {len(failures)} failed."
    )
    LOG.info(f"Booking complete: {len(successes)} successes, {len(failures)} failures")


def lambda_handler(event, context):
    """Lambda entry point for worker."""
    try:
        # Parse event payload
        payload = event if isinstance(event, dict) else json.loads(event.get("body", "{}"))

        emails = [e.strip().lower() for e in payload["emails"].split(",") if e.strip()]
        start_date = datetime.date.fromisoformat(payload["start"])
        n_meet = int(payload["count"])
        mode = payload["mode"]
        channel = payload["channel"]

        # Execute booking
        book_all_intros(
            mode=mode,
            channel=channel,
            emails=emails,
            start_date=start_date,
            n_meet=n_meet,
        )

        return {"statusCode": 200, "body": "Success"}

    except Exception as e:
        LOG.error(f"Worker Lambda failed: {e}", exc_info=True)
        return {"statusCode": 500, "body": str(e)}
