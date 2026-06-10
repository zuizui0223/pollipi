from typing import Tuple


class Codes:

    DONE: int = (0, "Done.", 200)  # type: ignore

    ERR_INVALID_USERNAME = 10
    ERR_INVALID_PASSWORD = 11
    ERR_INVALID_EMAIL = 12

    ERR_EXISTENT_EMAIL = 15

    ERR_WRONG_UNAME_OR_PW = 30
    ERR_AUTH_FAILED: int = (50, "Could not validate credentials.", 401)  # type: ignore
    ERR_WRONG_TOKEN_TYPE: int = (51, "Wrong token type.", 401)  # type: ignore

    ERR_SESSION_DB = 80
    ERR_MEETING_STARTED = 81, "Meeting already started.", 400
    ERR_MEETING_NOT_STARTED = 82, "Meeting not started.", 400


def _gen_desc():
    res = {}
    for code_str, c in Codes.__dict__.items():
        if not isinstance(c, (int, tuple)):
            continue
        if isinstance(c, int):
            c = (c,)

        code_int = c[0]
        desc = c[1] if len(c) > 1 and c[1] else code_str
        status = c[2] if len(c) > 2 else 400

        setattr(Codes, code_str, code_int)

        res[code_int] = (code_str, desc, status)
    return res


_descs = _gen_desc()


def getDescription(code: int) -> Tuple[str, str, int]:
    return _descs.get(code, (f"UNKNOWN_${code}", "Unknown Status.", 200))


def getDescriptionWs(code: int) -> dict:
    return dict(code=4000 + code, reason=getDescription(code)[1])


def getDescriptionHttp(code: int) -> dict:
    _, detail, status_code = getDescription(code)
    return dict(status_code=status_code, detail=detail)
