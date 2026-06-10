import re
from datetime import timedelta

_TIME_REGEX = re.compile(
    r"(-?\d+(?:\.\d+)?)(mic|ms|mil|s|m|min|h|d|w|mn|mon|q|y)", re.IGNORECASE
)

_TIME_DELTA_DICT = {
    "mic": lambda d: d.microseconds or None,
    "s": lambda d: d.seconds or None,
    "d": lambda d: d.days or None,
}


def create_timedelta_str(delta: timedelta):
    res = ""
    for k, f in _TIME_DELTA_DICT.items():
        res_f = f(delta)
        if res_f:
            res += f"{f(delta)}{k}"
    return res or "0s"


def parse_timedelta(input_string: str):
    sp = timedelta()

    for match in _TIME_REGEX.finditer(input_string.replace(" ", "")):
        time = float(match.group(1))
        unit = match.group(2)
        _matched = True
        _sp = timedelta()

        try:
            if unit == "mic":
                _sp = timedelta(microseconds=time)
            elif unit == "ms" or unit == "mil":
                _sp = timedelta(milliseconds=time)
            elif unit == "s":
                _sp = timedelta(seconds=time)
            elif unit == "m" or unit == "min":
                _sp = timedelta(minutes=time)
            elif unit == "h":
                _sp = timedelta(hours=time)
            elif unit == "d":
                _sp = timedelta(days=time)
            elif unit == "w":
                _sp = timedelta(weeks=time)
            elif unit == "mn" or unit == "mon":
                _sp = timedelta(days=time * 30)
            elif unit == "q":
                _sp = timedelta(days=time * 90)
            elif unit == "y":
                _sp = timedelta(days=time * 365.2422)
            else:
                _matched = False
        except OverflowError:
            _sp = timedelta.max if time > 0 else timedelta.min

        if _matched:
            sp += _sp

    return sp
