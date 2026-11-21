from datetime import datetime
from pytz import timezone

def get_current_time(timezone_name='Asia/Jakarta', format_string="%Y-%m-%d %H:%M:%S"):
    """
    Get the current time formatted as per the specified timezone and format string.
    Default timezone is 'Asia/Jakarta' and default format is '%Y-%m-%d %H:%M:%S'.
    """
    tz = timezone(timezone_name)
    current_time = datetime.now(tz)
    formatted_time = current_time.strftime(format_string)
    return formatted_time
