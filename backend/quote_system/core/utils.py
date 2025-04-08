# core/utils.py

import math
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def format_time(seconds: float) -> str:
    """
    Formats a duration in seconds into a human-readable string (e.g., "1h 30m 15s").

    Args:
        seconds: The duration in seconds.

    Returns:
        A formatted string representation of the duration. Returns "< 1 second"
        if the duration is very short or "N/A" if input is invalid.
    """
    if seconds is None or not isinstance(seconds, (int, float)) or seconds < 0:
        return "N/A"
    if seconds < 1:
        # Handle very short durations specifically if needed, e.g. for slicer times
        if seconds < 0.01:
             return "< 0.01 seconds"
        return f"{seconds:.2f} seconds" # Or return "< 1 second" if preferred

    # Calculate hours, minutes, and remaining seconds
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    parts = []
    if hours > 0:
        parts.append(f"{int(hours)}h")
    if minutes > 0:
        parts.append(f"{int(minutes)}m")
    # Only show seconds if duration is less than an hour or if there are remaining seconds
    if hours == 0 and sec > 0:
         # Show seconds with precision if needed, especially for short times
         if sec < 1:
             parts.append(f"{sec:.1f}s")
         else:
              parts.append(f"{int(math.ceil(sec))}s") # Round up seconds if > 1
    elif hours > 0 and sec > 0:
         # Optionally omit seconds for longer durations
         pass # e.g., don't show seconds if hours are present

    if not parts: # Should only happen if seconds was exactly 0
         return "0s"

    return " ".join(parts)

# Example Usage:
# print(format_time(9876))   # Output: 2h 44m 36s (or similar based on rounding/precision)
# print(format_time(75.5))    # Output: 1m 16s
# print(format_time(0.5))     # Output: 0.50 seconds (or < 1 second)
# print(format_time(-10))     # Output: N/A 