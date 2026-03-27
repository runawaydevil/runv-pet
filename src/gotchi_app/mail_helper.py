from __future__ import annotations

import argparse
import json
import os
import sys

from .identity import resolve_identity
from .mail import (
    MailError,
    archive_message_direct,
    delete_message_direct,
    initialize_mail_backend_direct,
    list_inbox_direct,
    read_message_direct,
    reply_message_direct,
    send_message_direct,
    unread_notice_direct,
    _message_to_dict,
    _notice_to_dict,
)


def parser() -> argparse.ArgumentParser:
    command_parser = argparse.ArgumentParser(prog="gotchi-mail-helper")
    command_parser.add_argument("--mail-root", required=True)
    subparsers = command_parser.add_subparsers(dest="command", required=True)

    send_parser = subparsers.add_parser("send")
    send_parser.add_argument("--to", required=True)
    send_parser.add_argument("--body", required=True)

    subparsers.add_parser("unread")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--include-archived", action="store_true")

    read_parser = subparsers.add_parser("read")
    read_parser.add_argument("message_id", type=int)

    archive_parser = subparsers.add_parser("archive")
    archive_parser.add_argument("message_id", type=int)

    delete_parser = subparsers.add_parser("delete")
    delete_parser.add_argument("message_id", type=int)

    reply_parser = subparsers.add_parser("reply")
    reply_parser.add_argument("message_id", type=int)
    reply_parser.add_argument("--body", required=True)

    subparsers.add_parser("init")
    return command_parser


def emit(payload) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=True))
    sys.stdout.write("\n")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    os.environ["GOTCHI_MAIL_ROOT"] = args.mail_root
    identity = resolve_identity()

    try:
        if args.command == "init":
            paths = initialize_mail_backend_direct()
            emit({"root": str(paths.root), "db_path": str(paths.db_path), "lock_path": str(paths.lock_path)})
            return 0
        if args.command == "send":
            emit(_message_to_dict(send_message_direct(args.body, args.to, sender=identity)))
            return 0
        if args.command == "unread":
            emit(_notice_to_dict(unread_notice_direct(identity)))
            return 0
        if args.command == "list":
            emit({"messages": [_message_to_dict(item) for item in list_inbox_direct(identity, include_archived=args.include_archived)]})
            return 0
        if args.command == "read":
            emit(_message_to_dict(read_message_direct(args.message_id, identity)))
            return 0
        if args.command == "archive":
            emit(_message_to_dict(archive_message_direct(args.message_id, identity)))
            return 0
        if args.command == "delete":
            emit(_message_to_dict(delete_message_direct(args.message_id, identity)))
            return 0
        if args.command == "reply":
            emit(_message_to_dict(reply_message_direct(args.message_id, args.body, identity)))
            return 0
        raise MailError("Comando de helper desconhecido.")
    except MailError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
