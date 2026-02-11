"""
Time utility module - provides accurate timezone-aware timestamps.
Uses NTP for initial sync, falls back to system time with timezone.
"""
import logging
import time
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Turkey timezone: UTC+3
TZ_TURKEY = timezone(timedelta(hours=3))

# NTP offset cache
_ntp_offset = None
_ntp_last_sync = 0
_NTP_SYNC_INTERVAL = 3600  # Re-sync every hour


def _sync_ntp():
    """Sync time offset from NTP server"""
    global _ntp_offset, _ntp_last_sync
    
    try:
        import ntplib
        client = ntplib.NTPClient()
        # Try multiple NTP servers
        servers = ['pool.ntp.org', 'time.google.com', 'time.cloudflare.com']
        
        for server in servers:
            try:
                response = client.request(server, version=3, timeout=5)
                _ntp_offset = response.offset
                _ntp_last_sync = time.time()
                logger.info(f"NTP sync successful from {server}, offset: {_ntp_offset:.3f}s")
                return True
            except Exception:
                continue
        
        logger.warning("All NTP servers failed, using system time")
        return False
        
    except ImportError:
        logger.warning("ntplib not installed, using system time")
        return False


def get_now():
    """
    Get current time with Turkey timezone (UTC+3).
    Uses NTP offset if available for accuracy.
    
    Returns: timezone-aware datetime in Europe/Istanbul (UTC+3)
    """
    global _ntp_offset, _ntp_last_sync
    
    # Try to sync NTP if not synced or stale
    if _ntp_offset is None or (time.time() - _ntp_last_sync > _NTP_SYNC_INTERVAL):
        _sync_ntp()
    
    # Get current UTC time
    now_utc = datetime.now(timezone.utc)
    
    # Apply NTP offset if available
    if _ntp_offset is not None:
        now_utc = now_utc + timedelta(seconds=_ntp_offset)
    
    # Convert to Turkey timezone
    now_turkey = now_utc.astimezone(TZ_TURKEY)
    
    return now_turkey


def get_now_for_db():
    """
    Get current time for database storage.
    Returns naive datetime (without timezone info) in Turkey time,
    for compatibility with existing SQLite schema.
    """
    return get_now().replace(tzinfo=None)


# Initial NTP sync on module load
_sync_ntp()
