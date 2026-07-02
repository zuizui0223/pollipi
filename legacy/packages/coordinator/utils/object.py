from datetime import datetime


def format_time(dt: datetime):
    return dt.strftime("%H:%M:%S.%f")[:-3]
