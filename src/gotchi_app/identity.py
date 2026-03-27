from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

try:
    import pwd
except ImportError:  # pragma: no cover - Windows fallback for local dev/tests
    pwd = None


@dataclass(frozen=True)
class UserIdentity:
    uid: int
    username: str
    home: Path

    @property
    def safe_name(self) -> str:
        return self.username or f"uid-{self.uid}"


def _resolve_unix_identity() -> UserIdentity:
    assert pwd is not None
    uid = os.getuid()
    account = pwd.getpwuid(uid)
    return UserIdentity(uid=uid, username=account.pw_name, home=Path(account.pw_dir))


def _resolve_fallback_identity() -> UserIdentity:
    uid = os.getuid() if hasattr(os, "getuid") else os.getpid()
    username = os.environ.get("USERNAME") or os.environ.get("USER") or f"user-{uid}"
    home = Path.home()
    return UserIdentity(uid=uid, username=username, home=home)


def resolve_identity() -> UserIdentity:
    if pwd is not None and hasattr(os, "getuid"):
        return _resolve_unix_identity()
    return _resolve_fallback_identity()


def _resolve_unix_account(username: str) -> UserIdentity:
    assert pwd is not None
    account = pwd.getpwnam(username)
    return UserIdentity(uid=account.pw_uid, username=account.pw_name, home=Path(account.pw_dir))


def _resolve_test_account(username: str) -> UserIdentity:
    raw = os.environ.get("GOTCHI_TEST_USERS")
    if not raw:
        raise KeyError(username)
    mapping = json.loads(raw)
    if username not in mapping:
        raise KeyError(username)
    entry = mapping[username]
    return UserIdentity(uid=int(entry["uid"]), username=username, home=Path(entry["home"]))


def resolve_account(username: str) -> UserIdentity:
    target = (username or "").strip()
    if not target:
        raise KeyError(username)
    if pwd is not None:
        return _resolve_unix_account(target)
    current = resolve_identity()
    if current.username == target:
        return current
    return _resolve_test_account(target)
