import re
from datetime import datetime, timezone
from typing import Optional, Dict, List

def format_number(num: int) -> str:
    """Format number with commas for better readability"""
    return f"{num:,}"

def parse_mention(mention_str: str) -> Optional[int]:
    """Parse user ID from mention string"""
    match = re.match(r'<@!?(\d+)>', mention_str)
    if match:
        return int(match.group(1))
    return None

def is_weekend() -> bool:
    """Check if current day is weekend (Saturday or Sunday)"""
    now = datetime.now(timezone.utc)
    return now.weekday() in [5, 6]  # Saturday = 5, Sunday = 6

def get_week_start() -> datetime:
    """Get the start of current week (Monday)"""
    now = datetime.now(timezone.utc)
    days_since_monday = now.weekday()
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = week_start - timezone.timedelta(days=days_since_monday)
    return week_start

def validate_player_name(name: str) -> bool:
    """Validate player name format"""
    if not name or len(name.strip()) == 0:
        return False
    
    # Check length
    if len(name) > 50:
        return False
    
    # Check for valid characters (letters, numbers, spaces, basic symbols)
    pattern = r'^[a-zA-Z0-9\s\-_\.]+$'
    return bool(re.match(pattern, name.strip()))

def sanitize_player_name(name: str) -> str:
    """Sanitize player name by removing/replacing invalid characters"""
    if not name:
        return ""
    
    # Remove leading/trailing whitespace
    name = name.strip()
    
    # Replace multiple spaces with single space
    name = re.sub(r'\s+', ' ', name)
    
    # Remove any non-alphanumeric characters except space, dash, underscore, dot
    name = re.sub(r'[^a-zA-Z0-9\s\-_\.]', '', name)
    
    # Limit length
    if len(name) > 50:
        name = name[:50].strip()
    
    return name

def format_duration(seconds: int) -> str:
    """Format duration in seconds to human readable format"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h"

def create_progress_bar(current: int, total: int, length: int = 10) -> str:
    """Create a simple text progress bar"""
    if total == 0:
        return "░" * length
    
    filled = int((current / total) * length)
    bar = "█" * filled + "░" * (length - filled)
    percentage = int((current / total) * 100)
    
    return f"{bar} {percentage}%"

def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split a list into chunks of specified size"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def get_ordinal(n: int) -> str:
    """Get ordinal suffix for a number (1st, 2nd, 3rd, etc.)"""
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

def calculate_donation_streak(donations: List[Dict]) -> int:
    """Calculate current donation streak in days"""
    if not donations:
        return 0
    
    # Sort donations by timestamp (newest first)
    sorted_donations = sorted(
        donations,
        key=lambda x: datetime.fromisoformat(x['timestamp'].replace('Z', '+00:00')),
        reverse=True
    )
    
    # Check for donations in consecutive days
    streak = 0
    current_date = datetime.now(timezone.utc).date()
    
    for donation in sorted_donations:
        donation_date = datetime.fromisoformat(
            donation['timestamp'].replace('Z', '+00:00')
        ).date()
        
        # Check if donation is from current date or previous consecutive date
        if donation_date == current_date:
            if streak == 0:
                streak = 1
        elif donation_date == current_date - timezone.timedelta(days=streak + 1):
            streak += 1
        else:
            break
        
        current_date = donation_date
    
    return streak
