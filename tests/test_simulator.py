from __future__ import annotations

import io
import os
import shutil
import sqlite3
import sys
import threading
import time
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
ARTIFACTS = ROOT / ".test-artifacts" / "multiuser"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gotchi_app.cli import main
from gotchi_app.config import Tuning, resolve_paths
from gotchi_app.filelock import file_lock
from gotchi_app.identity import UserIdentity
from gotchi_app.runv_mode import inspect_server_pet
from gotchi_app.simulator import apply_time, create_pet, interact
from gotchi_app.storage import (
    doctor_storage,
    export_pet,
    import_pet,
    load_pet,
    migrate_legacy_save,
    path_report,
    require_pet,
    save_pet,
    update_pet,
)
from gotchi_app.ui import status_screen


def workspace_case(name: str) -> Path:
    case = ARTIFACTS / name
    if case.exists():
        shutil.rmtree(case, ignore_errors=True)
    case.mkdir(parents=True, exist_ok=True)
    return case


def write_legacy_db(path: Path, username: str, name: str, now: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE pets (
                username TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                species TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_interaction_at TEXT NOT NULL,
                last_update_at TEXT NOT NULL,
                age_hours REAL NOT NULL,
                hunger REAL NOT NULL,
                energy REAL NOT NULL,
                mood REAL NOT NULL,
                hygiene REAL NOT NULL,
                health REAL NOT NULL,
                is_sleeping INTEGER NOT NULL,
                sleeping_since TEXT,
                illness INTEGER NOT NULL,
                alive INTEGER NOT NULL,
                cause_of_death TEXT,
                last_message TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO pets (
                username, name, species, created_at, last_interaction_at, last_update_at,
                age_hours, hunger, energy, mood, hygiene, health, is_sleeping,
                sleeping_since, illness, alive, cause_of_death, last_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                name,
                "crow",
                now.isoformat(),
                now.isoformat(),
                now.isoformat(),
                0.0,
                18.0,
                78.0,
                82.0,
                76.0,
                92.0,
                0,
                None,
                0,
                1,
                None,
                "legacy save",
            ),
        )
        conn.commit()
    finally:
        conn.close()


class IdentityIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = workspace_case("identity")
        self.user_a = UserIdentity(uid=1001, username="alice", home=self.root / "homes" / "alice")
        self.user_b = UserIdentity(uid=1002, username="bob", home=self.root / "homes" / "bob")
        os.environ["XDG_STATE_HOME"] = str(self.root / "xdg-state")
        os.environ["XDG_CONFIG_HOME"] = str(self.root / "xdg-config")
        os.environ["XDG_DATA_HOME"] = str(self.root / "xdg-data")

    def tearDown(self) -> None:
        for key in ("XDG_STATE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "HOME", "USER", "LOGNAME"):
            os.environ.pop(key, None)

    def test_uid_identity_loads_correct_pet(self) -> None:
        now = datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc)
        pet_a = create_pet(self.user_a.uid, self.user_a.username, "Nyx", "crow", now)
        pet_b = create_pet(self.user_b.uid, self.user_b.username, "Corvus", "cat", now)
        save_pet(pet_a, identity=self.user_a)
        save_pet(pet_b, identity=self.user_b)
        self.assertEqual(require_pet(identity=self.user_a).name, "Nyx")
        self.assertEqual(require_pet(identity=self.user_b).name, "Corvus")

    def test_env_spoof_does_not_switch_owner(self) -> None:
        now = datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc)
        save_pet(create_pet(self.user_a.uid, self.user_a.username, "Nyx", "crow", now), identity=self.user_a)
        os.environ["HOME"] = str(self.user_b.home)
        os.environ["USER"] = "bob"
        os.environ["LOGNAME"] = "bob"
        loaded = require_pet(identity=self.user_a)
        self.assertEqual(loaded.owner_uid, self.user_a.uid)
        self.assertEqual(loaded.username, self.user_a.username)

    def test_different_users_do_not_collide(self) -> None:
        paths_a = resolve_paths(self.user_a)
        paths_b = resolve_paths(self.user_b)
        self.assertNotEqual(paths_a.state_dir, paths_b.state_dir)
        self.assertNotEqual(paths_a.save_path, paths_b.save_path)

    def test_migration_from_legacy_username_db(self) -> None:
        legacy_dir = Path(os.environ["XDG_DATA_HOME"]) / "runv-pet"
        legacy_db = legacy_dir / "gotchi.db"
        now = datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc)
        write_legacy_db(legacy_db, self.user_a.username, "Legacy", now)
        report = migrate_legacy_save(self.user_a)
        self.assertTrue(report.migrated)
        migrated = require_pet(identity=self.user_a)
        self.assertEqual(migrated.name, "Legacy")
        self.assertEqual(migrated.owner_uid, self.user_a.uid)


class SimulatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc)
        self.tuning = Tuning()
        self.pet = create_pet(1001, "alice", "Nix", "crow", self.now)

    def test_time_passage_degrades_needs(self) -> None:
        later = self.now + timedelta(hours=4)
        updated = apply_time(self.pet, later, self.tuning)
        self.assertGreater(updated.hunger, self.pet.hunger)
        self.assertLess(updated.energy, self.pet.energy)
        self.assertLess(updated.hygiene, self.pet.hygiene)

    def test_feed_reduces_hunger(self) -> None:
        hungry = self.pet.evolve(hunger=80.0, energy=50.0, mood=40.0)
        fed = interact(hungry, "feed", self.now, self.tuning)
        self.assertLess(fed.hunger, hungry.hunger)
        self.assertGreater(fed.mood, hungry.mood)

    def test_sleep_restores_energy_over_time(self) -> None:
        sleepy = interact(self.pet.evolve(energy=20.0), "sleep", self.now, self.tuning)
        later = self.now + timedelta(hours=3)
        rested = apply_time(sleepy, later, self.tuning)
        self.assertGreater(rested.energy, sleepy.energy)

    def test_sleep_is_idempotent_while_already_sleeping(self) -> None:
        sleepy = interact(self.pet.evolve(energy=20.0, mood=40.0), "sleep", self.now, self.tuning)
        same_sleep = interact(sleepy, "sleep", self.now + timedelta(seconds=5), self.tuning)
        self.assertTrue(same_sleep.is_sleeping)
        self.assertEqual(same_sleep.sleeping_since, sleepy.sleeping_since)
        self.assertIn("ja esta dormindo", same_sleep.last_message)

    def test_clean_improves_hygiene(self) -> None:
        dirty = self.pet.evolve(hygiene=10.0)
        cleaned = interact(dirty, "clean", self.now, self.tuning)
        self.assertGreater(cleaned.hygiene, dirty.hygiene)

    def test_neglect_causes_illness(self) -> None:
        weak = self.pet.evolve(hunger=92.0, energy=8.0, hygiene=6.0, health=42.0)
        later = self.now + timedelta(hours=6)
        updated = apply_time(weak, later, self.tuning)
        self.assertTrue(updated.illness)
        self.assertLess(updated.health, weak.health)

    def test_extreme_neglect_causes_death(self) -> None:
        doomed = self.pet.evolve(hunger=100.0, energy=0.0, hygiene=0.0, health=8.0)
        later = self.now + timedelta(hours=24)
        updated = apply_time(doomed, later, self.tuning)
        self.assertFalse(updated.alive)
        self.assertEqual(updated.health, 0.0)

    def test_cat_species_renders_cat_art(self) -> None:
        pet = create_pet(1001, "alice", "King", "cat", self.now)
        screen = status_screen(pet, self.now)
        self.assertIn("King [cat]", screen)
        self.assertIn("/\\_/\\", screen)
        self.assertNotIn("corvo", screen.lower())


class StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = workspace_case("storage")
        self.identity = UserIdentity(uid=1001, username="alice", home=self.root / "homes" / "alice")
        os.environ["XDG_STATE_HOME"] = str(self.root / "state")
        os.environ["XDG_CONFIG_HOME"] = str(self.root / "config")
        os.environ["XDG_DATA_HOME"] = str(self.root / "data")

    def tearDown(self) -> None:
        for key in ("XDG_STATE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME"):
            os.environ.pop(key, None)

    def test_save_and_load_roundtrip(self) -> None:
        now = datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc)
        pet = create_pet(self.identity.uid, self.identity.username, "Rune", "crow", now)
        save_pet(pet, identity=self.identity)
        loaded = load_pet(identity=self.identity)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.name, "Rune")

    def test_private_dirs_are_created(self) -> None:
        paths = resolve_paths(self.identity)
        self.assertTrue(paths.state_dir.exists())
        self.assertTrue(paths.config_dir.exists())
        self.assertTrue(paths.data_dir.exists())

    def test_lock_prevents_corruption_under_concurrent_writes(self) -> None:
        now = datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc)
        save_pet(create_pet(self.identity.uid, self.identity.username, "Rune", "crow", now), identity=self.identity)

        def worker():
            update_pet(
                self.identity,
                lambda pet: pet.evolve(mood=min(100.0, pet.mood + 1.0), last_message="worker tick") if pet is not None else None,
            )

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        loaded = require_pet(identity=self.identity)
        self.assertEqual(loaded.last_message, "worker tick")
        self.assertGreaterEqual(loaded.mood, 82.0)

    def test_file_lock_blocks_second_writer(self) -> None:
        lock_path = resolve_paths(self.identity).lock_path
        order: list[str] = []

        def holder():
            with file_lock(lock_path, timeout=1.0):
                order.append("first")
                time.sleep(0.2)

        thread = threading.Thread(target=holder)
        thread.start()
        time.sleep(0.05)
        with file_lock(lock_path, timeout=1.0):
            order.append("second")
        thread.join()
        self.assertEqual(order, ["first", "second"])

    def test_export_import_roundtrip(self) -> None:
        now = datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc)
        save_pet(create_pet(self.identity.uid, self.identity.username, "Rune", "crow", now), identity=self.identity)
        payload = export_pet(self.identity)
        imported = import_pet(payload, self.identity)
        self.assertEqual(imported.name, "Rune")

    def test_import_rejects_other_owner(self) -> None:
        payload = {"owner_uid": 9999, "pet": create_pet(9999, "mallory", "X", "crow", datetime.now(timezone.utc)).to_record()}
        with self.assertRaisesRegex(Exception, "outro UID"):
            import_pet(payload, self.identity)

    def test_path_and_doctor_reports(self) -> None:
        report = path_report(self.identity)
        self.assertEqual(report["uid"], str(self.identity.uid))
        doctor = doctor_storage(self.identity)
        self.assertTrue(any("integrity=ok" in check for check in doctor.checks))


class CommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = workspace_case("commands")
        os.environ["XDG_STATE_HOME"] = str(self.root / "state")
        os.environ["XDG_CONFIG_HOME"] = str(self.root / "config")
        os.environ["XDG_DATA_HOME"] = str(self.root / "data")

    def tearDown(self) -> None:
        for key in ("XDG_STATE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME"):
            os.environ.pop(key, None)

    def test_hidden_runv_flag_does_not_crash(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["-runv"])
        self.assertEqual(code, 0)
        output = buffer.getvalue()
        self.assertIn("corvo do servidor", output)
        self.assertIn("Estado geral:", output)

    def test_path_command_works(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["path"])
        self.assertEqual(code, 0)
        self.assertIn("save_path", buffer.getvalue())

    def test_help_still_works(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["help"])
        self.assertEqual(code, 0)
        self.assertIn("gotchi doctor --storage", buffer.getvalue())


class RunvModeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = workspace_case("runv-mode")
        os.environ["XDG_STATE_HOME"] = str(self.root / "state")
        os.environ["XDG_CONFIG_HOME"] = str(self.root / "config")
        os.environ["XDG_DATA_HOME"] = str(self.root / "data")

    def tearDown(self) -> None:
        for key in ("XDG_STATE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME"):
            os.environ.pop(key, None)

    def test_runv_status_is_renderable(self) -> None:
        status = inspect_server_pet()
        self.assertIn(status.status, {"excelente", "bem", "atencao", "critico"})


if __name__ == "__main__":
    unittest.main()
