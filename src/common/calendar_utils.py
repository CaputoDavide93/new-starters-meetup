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
) -> datetime.datetime | None:
    """
    Find next free 15-minute slot across multiple calendars.
    
    Args:
        service: Google Calendar service
        calendar_ids: List of calendar IDs to check
        start_date: Date to search from
        window_start: Start of business hours (HH:MM)
        window_end: End of business hours (HH:MM)
        duration: Meeting duration in minutes
        
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
        LOG.debug(f"Checking {len(calendar_ids)} calendars: {calendar_ids}")
        
        # Check in 15-minute increments
        current = search_dt
        slot_count = 0
        while current + datetime.timedelta(minutes=duration) <= search_dt_end:
            slot_count += 1
            slot_end = current + datetime.timedelta(minutes=duration)
            
            # Check if slot is free on all calendars
            is_free = True
            for cal_id in calendar_ids:
                try:
                    # Format times in RFC 3339 without Z - just ISO format for timezone-aware datetimes
                    time_min = current.isoformat()
                    time_max = slot_end.isoformat()
                    
                    LOG.debug(f"  Checking slot {slot_count} {current.strftime('%H:%M')} - {slot_end.strftime('%H:%M')} for {cal_id}")
                    events = service.events().list(
                        calendarId=cal_id,
                        timeMin=time_min,
                        timeMax=time_max,
                        maxResults=1,
                    ).execute()
                    
                    if events.get("items"):
                        is_free = False
                        break
                except Exception as e:
                    LOG.warning(f"Could not check calendar {cal_id}: {e}")
                    # Assume busy if can't check
                    is_free = False
                    break
            
            if is_free:
                LOG.debug(f"Found free slot: {current}")
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
