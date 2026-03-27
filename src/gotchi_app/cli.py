from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import load_tuning, write_default_config
from .identity import resolve_identity
from .mail import (
    MailError,
    archive_message,
    delete_message,
    list_inbox,
    read_message,
    reply_message,
    send_message,
    unread_notice,
)
from .runv_mode import inspect_server_pet
from .simulator import SPECIES, apply_carry_trip, apply_time, carry_viability_reason, create_pet, interact
from .storage import (
    StorageError,
    doctor_storage,
    export_pet,
    import_pet,
    migrate_legacy_save,
    path_report,
    require_pet,
    update_pet,
)
from .ui import (
    doctor_storage_screen,
    help_text,
    mail_action_screen,
    mail_list_screen,
    mail_read_screen,
    migration_screen,
    path_screen,
    runv_status_screen,
    status_line,
    status_screen,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parser() -> argparse.ArgumentParser:
    command_parser = argparse.ArgumentParser(prog="gotchi", add_help=False)
    command_parser.add_argument("command", nargs="?", default="dashboard")
    command_parser.add_argument("argument", nargs="?")
    command_parser.add_argument("extra_argument", nargs="?")
    command_parser.add_argument("tail", nargs="*")
    command_parser.add_argument("--species", choices=SPECIES, default=SPECIES[0])
    command_parser.add_argument("--name")
    command_parser.add_argument("--write-config", action="store_true")
    command_parser.add_argument("--storage", action="store_true")
    command_parser.add_argument("--user")
    command_parser.add_argument("--message")
    return command_parser


def require_existing(pet):
    if pet is None:
        raise StorageError("Nenhum pet encontrado. Rode `gotchi init` primeiro.")
    return pet


def ensure_pet_available(identity):
    return require_pet(identity=identity)


def load_and_tick(identity=None) -> tuple:
    user = identity or resolve_identity()
    ensure_pet_available(user)
    tuning = load_tuning(user)

    def mutate(current):
        return apply_time(require_existing(current), utcnow(), tuning)

    pet = update_pet(user, mutate)
    assert pet is not None
    return pet, tuning


def current_notice(identity=None):
    return unread_notice(identity or resolve_identity())


def cmd_init(args: argparse.Namespace) -> int:
    identity = resolve_identity()
    existing = None
    try:
        existing = require_pet(identity=identity)
    except StorageError:
        existing = None
    if existing and existing.alive:
        print("Voce ja tem um pet. Use `gotchi status` para encontra-lo.")
        return 1

    if args.write_config:
        path = write_default_config(identity)
        print(f"Config padrao criada em {path}")

    name = args.name or identity.username.capitalize()
    pet = create_pet(identity.uid, identity.username, name, args.species, utcnow())
    update_pet(identity, lambda _current: pet)
    print(status_screen(pet, utcnow(), current_notice(identity)))
    return 0


def cmd_status() -> int:
    identity = resolve_identity()
    pet, _ = load_and_tick(identity)
    print(status_screen(pet, utcnow(), current_notice(identity)))
    return 0


def cmd_action(action: str) -> int:
    identity = resolve_identity()
    ensure_pet_available(identity)
    tuning = load_tuning(identity)

    def mutate(current):
        pet = apply_time(require_existing(current), utcnow(), tuning)
        return interact(pet, action, utcnow(), tuning)

    updated = update_pet(identity, mutate)
    assert updated is not None
    print(status_screen(updated, utcnow(), current_notice(identity)))
    return 0


def cmd_rename(new_name: str | None) -> int:
    if not new_name:
        print("Uso: gotchi rename NOVO_NOME")
        return 1
    identity = resolve_identity()
    ensure_pet_available(identity)

    def mutate(current):
        pet = require_existing(current)
        if not pet.alive:
            raise StorageError("Nao da para renomear um pet morto.")
        return pet.evolve(name=new_name, last_message=f"Agora atende por {new_name}.")

    pet = update_pet(identity, mutate)
    assert pet is not None
    print(status_screen(pet, utcnow(), current_notice(identity)))
    return 0


def cmd_path() -> int:
    print(path_screen(path_report(resolve_identity())))
    return 0


def cmd_line() -> int:
    identity = resolve_identity()
    pet, _ = load_and_tick(identity)
    print(status_line(pet, current_notice(identity)))
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    identity = resolve_identity()
    if args.storage:
        print(doctor_storage_screen(doctor_storage(identity)))
        return 0
    return cmd_action("doctor")


def cmd_migrate() -> int:
    print(migration_screen(migrate_legacy_save(resolve_identity())))
    return 0


def cmd_export(target_arg: str | None) -> int:
    payload = export_pet(resolve_identity())
    if target_arg:
        target = Path(target_arg)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Exportado para {target}")
        return 0
    print(json.dumps(payload, indent=2))
    return 0


def cmd_import(target_arg: str | None) -> int:
    if not target_arg:
        print("Uso: gotchi import ARQUIVO.json")
        return 1
    payload = json.loads(Path(target_arg).read_text(encoding="utf-8"))
    pet = import_pet(payload, resolve_identity())
    print(status_screen(pet, utcnow(), current_notice(resolve_identity())))
    return 0


def cmd_carry(args: argparse.Namespace) -> int:
    identity = resolve_identity()
    ensure_pet_available(identity)
    target_user = args.user
    if not target_user:
        print("Uso: gotchi carry \"mensagem\" --user USER")
        return 1
    body = args.message or args.argument or " ".join(args.tail).strip()
    if not body:
        print("Uso: gotchi carry \"mensagem\" --user USER")
        return 1

    now = utcnow()
    tuning = load_tuning(identity)
    pet = update_pet(identity, lambda current: apply_time(require_existing(current), now, tuning))
    assert pet is not None
    reason = carry_viability_reason(pet)
    if reason is not None:
        raise StorageError(reason)

    message = send_message(body=body, recipient_username=target_user, sender=identity)
    updated = update_pet(identity, lambda current: apply_carry_trip(apply_time(require_existing(current), now, tuning), now))
    assert updated is not None
    print(status_screen(updated, now, current_notice(identity)))
    print(f"\nCarta #{message.id} enviada para {message.recipient_username}.")
    return 0


def cmd_mail(args: argparse.Namespace) -> int:
    identity = resolve_identity()
    ensure_pet_available(identity)
    action = args.argument
    if not action:
        print(mail_list_screen(list_inbox(identity)))
        return 0
    if action == "read":
        if not args.extra_argument:
            print("Uso: gotchi mail read ID")
            return 1
        print(mail_read_screen(read_message(int(args.extra_argument), identity)))
        return 0
    if action == "reply":
        if not args.extra_argument:
            print("Uso: gotchi mail reply ID --message TEXTO")
            return 1
        body = args.message or " ".join(args.tail).strip()
        if not body:
            print("Uso: gotchi mail reply ID --message TEXTO")
            return 1
        message = reply_message(int(args.extra_argument), body, identity)
        print(mail_action_screen(message, "respondida"))
        return 0
    if action == "archive":
        if not args.extra_argument:
            print("Uso: gotchi mail archive ID")
            return 1
        print(mail_action_screen(archive_message(int(args.extra_argument), identity), "arquivada"))
        return 0
    if action == "delete":
        if not args.extra_argument:
            print("Uso: gotchi mail delete ID")
            return 1
        print(mail_action_screen(delete_message(int(args.extra_argument), identity), "apagada"))
        return 0
    print("Uso: gotchi mail [read|reply|archive|delete]")
    return 1


def cmd_runv() -> int:
    print(runv_status_screen(inspect_server_pet()))
    return 0


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if raw_argv and raw_argv[0] == "-runv":
        return cmd_runv()

    args = parser().parse_args(raw_argv)
    command = args.command

    try:
        if command in ("help", "--help", "-h"):
            print(help_text())
            return 0
        if command == "init":
            return cmd_init(args)
        if command in ("dashboard", "status"):
            return cmd_status()
        if command == "path":
            return cmd_path()
        if command == "line":
            return cmd_line()
        if command == "doctor":
            return cmd_doctor(args)
        if command == "migrate":
            return cmd_migrate()
        if command == "export":
            return cmd_export(args.argument)
        if command == "import":
            return cmd_import(args.argument)
        if command == "carry":
            return cmd_carry(args)
        if command == "mail":
            return cmd_mail(args)
        if command in {"feed", "play", "sleep", "clean"}:
            return cmd_action(command)
        if command == "rename":
            return cmd_rename(args.argument)
        print(help_text())
        return 1
    except (StorageError, MailError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ValueError:
        print("ID de carta invalido.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrompido.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
