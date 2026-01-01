"""
Google Calendar utilities

Handles calendar slot finding and event creation.
"""

import logging
import datetime
from typing import Any
import pytz

import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build

LOG = logging.getLogger(__name__)

# Google Calendar scopes
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service(sa_key: dict[str, Any], subject: str):
    """
    Build Google Calendar service with delegated user credentials.
    
    Args:
        sa_key: Service account key dictionary
        subject: User email to delegate permissions to
        
    Returns:
        Google Calendar service object
    """
    # Validate required fields
    required_fields = ["client_email", "token_uri", "private_key"]
    missing = [f for f in required_fields if f not in sa_key]
    if missing:
        raise ValueError(f"Service account key missing required fields: {missing}")
    
    credentials = service_account.Credentials.from_service_account_info(
        sa_key,
        scopes=SCOPES,
    )
    
    # Delegate credentials to user
    delegated_credentials = credentials.with_subject(subject)
    
    service = build(
        "calendar",
        "v3",
        credentials=delegated_credentials,
        static_discovery=False,
    )
    LOG.debug(f"Google Calendar service initialized for {subject}")
    return service


def find_next_free_slot(
    service: Any,
    calendar_ids: list[str],
    start_date: datetime.date,
    window_start: str = "11:00",
    window_end: str = "15:00",
    duration: int = 15,
    excluded_slots: list[datetime.datetime] | None = None,
) -> datetime.datetime | None:
    """
    Find next free slot across multiple calendars using FreeBusy API.
    
    Uses a single API call to check all calendars at once, avoiding rate limits.
    
    Args:
        service: Google Calendar service
        calendar_ids: List of calendar IDs to check
        start_date: Date to search from
        window_start: Start of business hours (HH:MM)
        window_end: End of business hours (HH:MM)
        duration: Meeting duration in minutes
        excluded_slots: List of already-booked slot start times to skip
        
    Returns:
        First available datetime slot, or None
    """
    try:
        # Build time window
        start_hour, start_min = map(int, window_start.split(":"))
        end_hour, end_min = map(int, window_end.split(":"))
        
        # Create timezone-aware datetimes
        dublin_tz = pytz.timezone('Europe/Dublin')
        search_dt = dublin_tz.localize(datetime.datetime.combine(
            start_date,
            datetime.time(start_hour, start_min),
        ))
        search_dt_end = dublin_tz.localize(datetime.datetime.combine(
            start_date,
            datetime.time(end_hour, end_min),
        ))
        
        LOG.debug(f"Searching for {duration}-min slots on {start_date} between {window_start}-{window_end}")
        LOG.debug(f"Checking {len(calendar_ids)} calendars via FreeBusy API")
        
        # Use FreeBusy API - single call for all calendars
        freebusy_query = {
            "timeMin": search_dt.isoformat(),
            "timeMax": search_dt_end.isoformat(),
            "timeZone": "Europe/Dublin",
            "items": [{"id": cal_id} for cal_id in calendar_ids],
        }
        
        freebusy_result = service.freebusy().query(body=freebusy_query).execute()
        
        # Collect all busy periods across all calendars
        all_busy_periods = []
        for cal_id in calendar_ids:
            cal_info = freebusy_result.get("calendars", {}).get(cal_id, {})
            if cal_info.get("errors"):
                LOG.warning(f"FreeBusy error for {cal_id}: {cal_info['errors']}")
                continue
            for busy in cal_info.get("busy", []):
                busy_start = datetime.datetime.fromisoformat(busy["start"].replace("Z", "+00:00"))
                busy_end = datetime.datetime.fromisoformat(busy["end"].replace("Z", "+00:00"))
                all_busy_periods.append((busy_start, busy_end))
        
        # Add excluded slots (already booked in this session) as busy periods
        if excluded_slots:
            for slot_start in excluded_slots:
                slot_end = slot_start + datetime.timedelta(minutes=duration)
                all_busy_periods.append((slot_start, slot_end))
            LOG.debug(f"Added {len(excluded_slots)} excluded slots from current session")
        
        LOG.debug(f"Found {len(all_busy_periods)} busy periods across all calendars")
        
        # Check slots in 15-minute increments
        current = search_dt
        while current + datetime.timedelta(minutes=duration) <= search_dt_end:
            slot_end = current + datetime.timedelta(minutes=duration)
            
            # Check if slot overlaps with any busy period
            is_free = True
            for busy_start, busy_end in all_busy_periods:
                # Slot overlaps if: slot_start < busy_end AND slot_end > busy_start
                if current < busy_end and slot_end > busy_start:
                    is_free = False
                    break
            
            if is_free:
                LOG.info(f"Found free slot: {current.strftime('%Y-%m-%d %H:%M')}")
                return current
            
            current += datetime.timedelta(minutes=15)
        
        LOG.debug(f"No free slot found on {start_date}")
        return None
        
    except Exception as e:
        LOG.error(f"Failed to find free slot: {e}", exc_info=True)
        return None


def create_event(
    service: Any,
    calendar_id: str,
    summary: str,
    description: str,
    start_dt: datetime.datetime,
    duration: int,
    attendees: list[str],
) -> str | None:
    """
    Create calendar event.
    
    Args:
        service: Google Calendar service
        calendar_id: Calendar to create event in
        summary: Event title
        description: Event description
        start_dt: Event start datetime
        duration: Event duration in minutes
        attendees: List of attendee emails
        
    Returns:
        Event ID, or None if failed
    """
    try:
        # Ensure start_dt is timezone-aware, localize if naive
        if start_dt.tzinfo is None:
            dublin_tz = pytz.timezone('Europe/Dublin')
            start_dt = dublin_tz.localize(start_dt)
        
        end_dt = start_dt + datetime.timedelta(minutes=duration)
        
        # Format datetime in RFC 3339 without timezone suffix (Google Calendar handles timeZone parameter)
        start_str = start_dt.replace(tzinfo=None).isoformat()
        end_str = end_dt.replace(tzinfo=None).isoformat()
        
        event = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_str, "timeZone": "Europe/Dublin"},
            "end": {"dateTime": end_str, "timeZone": "Europe/Dublin"},
            "attendees": [{"email": attendee} for attendee in attendees],
        }
        
        result = service.events().insert(
            calendarId=calendar_id,
            body=event,
            sendUpdates="all",
        ).execute()
        
        LOG.info(f"Created event: {result['id']}")
        return result["id"]
        
    except Exception as e:
        LOG.error(f"Failed to create calendar event: {e}", exc_info=True)
        raise
