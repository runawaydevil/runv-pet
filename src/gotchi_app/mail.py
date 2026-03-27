from __future__ import annotations

import json
import os
import sqlite3
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .filelock import LockError, file_lock
from .identity import UserIdentity, resolve_account, resolve_identity


MAIL_SCHEMA_VERSION = 1
MAIL_TIMEOUT_SECONDS = 5.0
MAIL_MAX_BODY = 1000
MAIL_DEFAULT_ROOT = Path("/var/lib/gotchi-mail")
MAIL_FALLBACK_ROOT = Path("/var/spool/gotchi-mail")
MAIL_DEFAULT_HELPER = Path("/opt/gotchi/bin/gotchi-mail-bridge")


class MailError(RuntimeError):
    pass


@dataclass(frozen=True)
class MailMessage:
    id: int
    sender_uid: int
    sender_username: str
    recipient_uid: int
    recipient_username: str
    body: str
    created_at: datetime
    read_at: datetime | None
    archived_at: datetime | None
    deleted_at: datetime | None
    status: str
    reply_to_id: int | None


@dataclass(frozen=True)
class MailNotice:
    unread_count: int
    latest_sender: str | None


@dataclass(frozen=True)
class MailPaths:
    root: Path
    db_path: Path
    lock_path: Path


def _materialize(path: Path) -> Path:
    if os.name == "nt":
        path.mkdir(parents=True, exist_ok=True)
        return path
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


@contextmanager
def _temporary_umask(mask: int) -> Iterator[None]:
    if os.name == "nt":
        yield
        return
    previous = os.umask(mask)
    try:
        yield
    finally:
        os.umask(previous)


def _helper_path() -> Path:
    raw = os.environ.get("GOTCHI_MAIL_HELPER")
    if raw:
        return Path(raw).expanduser()
    return MAIL_DEFAULT_HELPER


def _helper_available() -> bool:
    if os.environ.get("GOTCHI_MAIL_FORCE_DIRECT") == "1":
        return False
    path = _helper_path()
    return os.name != "nt" and path.is_file() and os.access(path, os.X_OK)


def _message_to_dict(message: MailMessage) -> dict[str, Any]:
    return {
        "id": message.id,
        "sender_uid": message.sender_uid,
        "sender_username": message.sender_username,
        "recipient_uid": message.recipient_uid,
        "recipient_username": message.recipient_username,
        "body": message.body,
        "created_at": message.created_at.isoformat(),
        "read_at": message.read_at.isoformat() if message.read_at else None,
        "archived_at": message.archived_at.isoformat() if message.archived_at else None,
        "deleted_at": message.deleted_at.isoformat() if message.deleted_at else None,
        "status": message.status,
        "reply_to_id": message.reply_to_id,
    }


def _message_from_dict(payload: dict[str, Any]) -> MailMessage:
    return MailMessage(
        id=int(payload["id"]),
        sender_uid=int(payload["sender_uid"]),
        sender_username=str(payload["sender_username"]),
        recipient_uid=int(payload["recipient_uid"]),
        recipient_username=str(payload["recipient_username"]),
        body=str(payload["body"]),
        created_at=datetime.fromisoformat(str(payload["created_at"])),
        read_at=datetime.fromisoformat(str(payload["read_at"])) if payload.get("read_at") else None,
        archived_at=datetime.fromisoformat(str(payload["archived_at"])) if payload.get("archived_at") else None,
        deleted_at=datetime.fromisoformat(str(payload["deleted_at"])) if payload.get("deleted_at") else None,
        status=str(payload["status"]),
        reply_to_id=int(payload["reply_to_id"]) if payload.get("reply_to_id") is not None else None,
    )


def _notice_to_dict(notice: MailNotice) -> dict[str, Any]:
    return {"unread_count": notice.unread_count, "latest_sender": notice.latest_sender}


def _notice_from_dict(payload: dict[str, Any]) -> MailNotice:
    return MailNotice(unread_count=int(payload.get("unread_count", 0)), latest_sender=payload.get("latest_sender"))


def _run_helper(arguments: list[str]) -> Any:
    helper = _helper_path()
    result = subprocess.run([str(helper), *arguments], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Falha no helper de cartas."
        raise MailError(message)
    output = result.stdout.strip()
    if not output:
        return None
    return json.loads(output)


def resolve_mail_paths() -> MailPaths:
    env = os.environ.get("GOTCHI_MAIL_ROOT")
    candidates: list[Path] = []
    if env:
        path = Path(env).expanduser()
        if path.is_absolute():
            candidates.append(path)
    for candidate in (MAIL_DEFAULT_ROOT, MAIL_FALLBACK_ROOT):
        if candidate not in candidates:
            candidates.append(candidate)

    errors: list[str] = []
    for candidate in candidates:
        try:
            root = _materialize(candidate)
            return MailPaths(root=root, db_path=root / "mail.db", lock_path=root / "mail.lock")
        except OSError as exc:
            errors.append(f"{candidate}: {exc}")
    raise MailError(
        "Nao foi possivel preparar o backend de cartas. Rode `flash --all` no host ou configure GOTCHI_MAIL_ROOT "
        "para um spool compartilhado e gravavel."
    )


def _connect(path: Path) -> sqlite3.Connection:
    with _temporary_umask(0o077):
        conn = sqlite3.connect(path, timeout=MAIL_TIMEOUT_SECONDS, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.Error:
        pass
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version >= MAIL_SCHEMA_VERSION:
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_uid INTEGER NOT NULL,
            sender_username TEXT NOT NULL,
            recipient_uid INTEGER NOT NULL,
            recipient_username TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL,
            read_at TEXT,
            archived_at TEXT,
            deleted_at TEXT,
            status TEXT NOT NULL,
            reply_to_id INTEGER,
            FOREIGN KEY(reply_to_id) REFERENCES messages(id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_recipient_status ON messages(recipient_uid, status, created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_uid, created_at DESC)")
    conn.execute(f"PRAGMA user_version={MAIL_SCHEMA_VERSION}")


@contextmanager
def locked_mail_connection(timeout: float = MAIL_TIMEOUT_SECONDS) -> Iterator[tuple[sqlite3.Connection, MailPaths]]:
    paths = resolve_mail_paths()
    try:
        with file_lock(paths.lock_path, timeout=timeout):
            conn = _connect(paths.db_path)
            try:
                conn.execute("BEGIN IMMEDIATE")
                _migrate(conn)
                yield conn, paths
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
    except LockError as exc:
        raise MailError(str(exc)) from exc
    except sqlite3.Error as exc:
        raise MailError(f"Nao foi possivel abrir o backend de cartas: {exc}") from exc


def initialize_mail_backend_direct() -> MailPaths:
    with locked_mail_connection() as (_conn, paths):
        return paths


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _row_to_message(row: sqlite3.Row) -> MailMessage:
    return MailMessage(
        id=int(row["id"]),
        sender_uid=int(row["sender_uid"]),
        sender_username=row["sender_username"],
        recipient_uid=int(row["recipient_uid"]),
        recipient_username=row["recipient_username"],
        body=row["body"],
        created_at=datetime.fromisoformat(row["created_at"]),
        read_at=datetime.fromisoformat(row["read_at"]) if row["read_at"] else None,
        archived_at=datetime.fromisoformat(row["archived_at"]) if row["archived_at"] else None,
        deleted_at=datetime.fromisoformat(row["deleted_at"]) if row["deleted_at"] else None,
        status=row["status"],
        reply_to_id=int(row["reply_to_id"]) if row["reply_to_id"] is not None else None,
    )


def _validate_body(body: str) -> str:
    text = (body or "").strip()
    if not text:
        raise MailError("A carta nao pode estar vazia.")
    if len(text) > MAIL_MAX_BODY:
        raise MailError(f"A carta e grande demais. Limite atual: {MAIL_MAX_BODY} caracteres.")
    return text


def _get_recipient(username: str) -> UserIdentity:
    try:
        return resolve_account(username)
    except Exception as exc:
        raise MailError(f"Usuario nao encontrado: {username}") from exc


def send_message_direct(body: str, recipient_username: str, sender: UserIdentity | None = None, reply_to_id: int | None = None) -> MailMessage:
    author = sender or resolve_identity()
    recipient = _get_recipient(recipient_username)
    text = _validate_body(body)
    created_at = _now().isoformat()
    with locked_mail_connection() as (conn, _paths):
        cursor = conn.execute(
            """
            INSERT INTO messages (
                sender_uid, sender_username, recipient_uid, recipient_username, body,
                created_at, read_at, archived_at, deleted_at, status, reply_to_id
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, 'new', ?)
            """,
            (author.uid, author.username, recipient.uid, recipient.username, text, created_at, reply_to_id),
        )
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (cursor.lastrowid,)).fetchone()
    assert row is not None
    return _row_to_message(row)


def unread_notice_direct(identity: UserIdentity | None = None) -> MailNotice:
    user = identity or resolve_identity()
    with locked_mail_connection() as (conn, _paths):
        count_row = conn.execute(
            "SELECT COUNT(*) AS total FROM messages WHERE recipient_uid = ? AND status = 'new'",
            (user.uid,),
        ).fetchone()
        latest_row = conn.execute(
            "SELECT sender_username FROM messages WHERE recipient_uid = ? AND status = 'new' ORDER BY created_at DESC LIMIT 1",
            (user.uid,),
        ).fetchone()
    return MailNotice(
        unread_count=int(count_row["total"] if count_row is not None else 0),
        latest_sender=latest_row["sender_username"] if latest_row is not None else None,
    )


def list_inbox_direct(identity: UserIdentity | None = None, include_archived: bool = False) -> list[MailMessage]:
    user = identity or resolve_identity()
    query = "SELECT * FROM messages WHERE recipient_uid = ? AND status != 'deleted'"
    params: list[object] = [user.uid]
    if not include_archived:
        query += " AND status != 'archived'"
    query += " ORDER BY created_at DESC, id DESC"
    with locked_mail_connection() as (conn, _paths):
        rows = conn.execute(query, params).fetchall()
    return [_row_to_message(row) for row in rows]


def _load_owned_message(conn: sqlite3.Connection, identity: UserIdentity, message_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    if row is None:
        raise MailError(f"Carta nao encontrada: {message_id}")
    if int(row["recipient_uid"]) != identity.uid:
        raise MailError("Esta carta nao pertence ao usuario atual.")
    return row


def read_message_direct(message_id: int, identity: UserIdentity | None = None) -> MailMessage:
    user = identity or resolve_identity()
    with locked_mail_connection() as (conn, _paths):
        row = _load_owned_message(conn, user, message_id)
        if row["status"] == "new":
            now = _now().isoformat()
            conn.execute("UPDATE messages SET status = 'read', read_at = ? WHERE id = ?", (now, message_id))
            row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    assert row is not None
    return _row_to_message(row)


def archive_message_direct(message_id: int, identity: UserIdentity | None = None) -> MailMessage:
    user = identity or resolve_identity()
    with locked_mail_connection() as (conn, _paths):
        _load_owned_message(conn, user, message_id)
        now = _now().isoformat()
        conn.execute(
            "UPDATE messages SET status = 'archived', archived_at = COALESCE(archived_at, ?), read_at = COALESCE(read_at, ?) WHERE id = ?",
            (now, now, message_id),
        )
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    assert row is not None
    return _row_to_message(row)


def delete_message_direct(message_id: int, identity: UserIdentity | None = None) -> MailMessage:
    user = identity or resolve_identity()
    with locked_mail_connection() as (conn, _paths):
        _load_owned_message(conn, user, message_id)
        now = _now().isoformat()
        conn.execute(
            "UPDATE messages SET status = 'deleted', deleted_at = ?, read_at = COALESCE(read_at, ?) WHERE id = ?",
            (now, now, message_id),
        )
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    assert row is not None
    return _row_to_message(row)


def reply_message_direct(message_id: int, body: str, identity: UserIdentity | None = None) -> MailMessage:
    user = identity or resolve_identity()
    original = read_message_direct(message_id, user)
    return send_message_direct(body=body, recipient_username=original.sender_username, sender=user, reply_to_id=original.id)


def send_message(body: str, recipient_username: str, sender: UserIdentity | None = None, reply_to_id: int | None = None) -> MailMessage:
    if _helper_available():
        payload = _run_helper(["send", "--to", recipient_username, "--body", body])
        return _message_from_dict(payload)
    return send_message_direct(body=body, recipient_username=recipient_username, sender=sender, reply_to_id=reply_to_id)


def unread_notice(identity: UserIdentity | None = None) -> MailNotice:
    if _helper_available():
        payload = _run_helper(["unread"])
        return _notice_from_dict(payload)
    return unread_notice_direct(identity)


def list_inbox(identity: UserIdentity | None = None, include_archived: bool = False) -> list[MailMessage]:
    if _helper_available():
        arguments = ["list"]
        if include_archived:
            arguments.append("--include-archived")
        payload = _run_helper(arguments)
        return [_message_from_dict(item) for item in payload.get("messages", [])]
    return list_inbox_direct(identity, include_archived=include_archived)


def read_message(message_id: int, identity: UserIdentity | None = None) -> MailMessage:
    if _helper_available():
        payload = _run_helper(["read", str(message_id)])
        return _message_from_dict(payload)
    return read_message_direct(message_id, identity)


def archive_message(message_id: int, identity: UserIdentity | None = None) -> MailMessage:
    if _helper_available():
        payload = _run_helper(["archive", str(message_id)])
        return _message_from_dict(payload)
    return archive_message_direct(message_id, identity)


def delete_message(message_id: int, identity: UserIdentity | None = None) -> MailMessage:
    if _helper_available():
        payload = _run_helper(["delete", str(message_id)])
        return _message_from_dict(payload)
    return delete_message_direct(message_id, identity)


def reply_message(message_id: int, body: str, identity: UserIdentity | None = None) -> MailMessage:
    if _helper_available():
        payload = _run_helper(["reply", str(message_id), "--body", body])
        return _message_from_dict(payload)
    return reply_message_direct(message_id, body, identity)
