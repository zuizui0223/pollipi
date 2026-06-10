from aenum import Enum, skip, EnumType
from typing import Optional, Dict, Set, Any
import json

from config import AppConfig


class UserGroup(str, Enum):  # type: ignore
    Guest = "guest"
    User = "user"
    Host = "host"
    Admin = "admin"
    Root = "root"


_g_id = 0


def _groups(*g: str):
    global _g_id
    ret = json.dumps((str(_g_id), *g))
    _g_id += 1
    return ret


_g_hierarchy = [
    UserGroup.Guest,
    UserGroup.User,
    UserGroup.Host,
    UserGroup.Admin,
    UserGroup.Root,
]


def _group(g: str):
    if not g in _g_hierarchy:
        return _group(UserGroup.Root)
    global _g_id
    ret = json.dumps((str(_g_id), *_g_hierarchy[_g_hierarchy.index(g) :]))
    _g_id += 1
    return ret


def _parse_groups(ret: str):
    g_arr = json.loads(ret)[1:]
    return [UserGroup.Guest._value_] if not g_arr else g_arr  # type: ignore


# define access here
class Token(str, Enum):  # type: ignore

    Refresh = _group(UserGroup.User)

    @skip
    class Access(str, Enum):  # type: ignore

        General = _group(UserGroup.User)

        @skip
        class User(str, Enum):  # type: ignore

            Register = _groups(UserGroup.Guest, UserGroup.Admin, UserGroup.Root)
            Login = _groups(UserGroup.Guest)
            ChangeInfo = _group(UserGroup.User)
            ChangeCriticalInfo = _group(UserGroup.User)


def _gen_access(
    e: Any, prefix: str = "", group_map: Optional[Dict[str, Set[str]]] = None
):
    str_fields = []
    cls_fields = []
    name = e.__name__
    group_map = {} if group_map is None else group_map

    for k, v in e.__dict__.items():
        if type(v) == e:
            str_fields.append((k, v))
        elif type(v) == EnumType:
            cls_fields.append((k, v))

    for field, groups in str_fields:
        field_fullname = prefix + "." + field if prefix else field
        group_map[field_fullname] = set(_parse_groups(groups))
        groups._value_ = field_fullname

    for field, enum in cls_fields:
        field_fullname = prefix + "." + field if prefix else field
        _gen_access(enum, field_fullname, group_map)

    return group_map


_group_map = _gen_access(Token, "Token")
for field, data in AppConfig.TokenAccessOverride.items():
    _group_map[field] = set(
        _parse_groups(_group(data)) if isinstance(data, str) else data
    )


def hasAccess(group: str, access: str):
    if access not in _group_map:
        return True
    return group in _group_map[access]
