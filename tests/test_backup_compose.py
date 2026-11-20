"""Tests of what the backup of Forgejo adds to the deployment files
(container-deployment: Web server and Compose file, Forgejo): the
services ``backup``, ``restore`` and ``forge`` and the volume
``forge-control`` in ``deploy/compose.yaml``, and ``forge-db`` handing
that volume to UID 1000.

The Compose file is read as text, in the style of the neighbouring
tests, so a volume is read from lines of the short form
``      - source:target[:ro]``. The ``docker compose config`` tests skip
without Docker, as those of the other deployment files do.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_forge_deploy import (COMPOSE, DATABASE, DEPLOY, ENV_EXAMPLE,
                               parse_env, service_block)

CONTROL = "/var/lib/orgsyndb-forge-control"
PUSHES = "/var/lib/orgsyndb-pushes"
FORGE = "/var/lib/gitea"
DATA = "/var/lib/orgsyndb"
SETTINGS = "/opt/orgsyndb/orgsyndb.env"
MOUNT = re.compile(r"(?m)^      - ([^\s:]+):(/[^\s:]*)(?::(ro|rw))?\s*"
                   r"(?:#.*)?$")


def mounts(name: str) -> dict[str, tuple[str, str]]:
    """The volumes of the service NAME in compose.yaml as {target:
    (source, mode)}, mode being "ro" or "rw"."""
    return {target: (source, mode or "rw")
            for source, target, mode in MOUNT.findall(service_block(name))}


def volume_users(source: str) -> dict[str, str]:
    """{service: mode} for every service that mounts the named volume
    SOURCE."""
    found = {}
    for name in ("builder", "web", "db", "app", "backup", "restore",
                 "forge-db", "forge"):
        for volume, mode in mounts(name).values():
            if volume == source:
                found[name] = mode
    return found


def command_words(name: str, key: str) -> list[str]:
    """The words of the service NAME's ``entrypoint`` or ``command``,
    given as a list in flow or block style, or as a string."""
    block = service_block(name)
    flow = re.search(rf"(?ms)^    {key}:\s*(\[.*?\])", block)
    if flow:
        return [a or b for a, b in re.findall(
            r"\"([^\"]*)\"|'([^']*)'", flow.group(1))]
    listed = re.search(rf"(?m)^    {key}:\s*\n((?:      - .*\n)+)", block)
    if listed:
        return [line.strip()[2:].strip("\"'")
                for line in listed.group(1).splitlines()]
    plain = re.search(rf"(?m)^    {key}:\s*(\S.*)$", block)
    return plain.group(1).strip("\"'").split() if plain else []


class ComposeTextTests(unittest.TestCase):
    """Scenario: Compose file (read without Docker)."""

    def test_the_volume_forge_control_is_declared(self) -> None:
        """Requirement: Web server and Compose file (the volume
        `forge-control`)."""
        self.assertRegex(COMPOSE.read_text(encoding="utf-8"),
                         r"(?ms)^volumes:\n.*^  forge-control:")

    def test_backup_reads_forgejos_data_and_the_push_log(self) -> None:
        """Requirement: Web server and Compose file (`backup` mounting
        the volumes `forge` and `pushes` read-only)."""
        found = mounts("backup")
        self.assertEqual(found.get(FORGE), ("forge", "ro"), found)
        self.assertEqual(found.get(PUSHES), ("pushes", "ro"), found)

    def test_backup_answers_through_the_control_volume(self) -> None:
        """Requirement: Web server and Compose file (`forge-control`
        read-write at `/var/lib/orgsyndb-forge-control`)."""
        self.assertEqual(mounts("backup").get(CONTROL),
                         ("forge-control", "rw"), mounts("backup"))

    def test_backup_reads_the_settings_file(self) -> None:
        """Requirement: Web server and Compose file (`orgsyndb.env`
        read-only at `/opt/orgsyndb/orgsyndb.env`)."""
        self.assertEqual(mounts("backup").get(SETTINGS),
                         ("./orgsyndb.env", "ro"), mounts("backup"))

    def test_backup_keeps_its_script_and_its_directory(self) -> None:
        """Requirement: Web server and Compose file (the script
        read-only, `deploy/backups/` at `/backups`)."""
        found = mounts("backup")
        self.assertEqual(found.get("/backups"), ("./backups", "rw"))
        scripts = [m for m in found.values()
                   if m[0].rstrip("/").endswith(("/backup", "backup"))
                   and m[0] != "./backups"]
        self.assertEqual(scripts, [("./backup", "ro")], found)

    def test_backup_does_not_mount_the_builders_data(self) -> None:
        self.assertNotIn(DATA, mounts("backup"))

    def test_restore_is_a_service_of_the_profile_restore(self) -> None:
        """Requirement: Web server and Compose file (`restore`, only in
        the profile `restore`)."""
        block = service_block("restore")
        found = re.search(r"(?m)^    profiles:(.*(?:\n      - .*)*)", block)
        self.assertIsNotNone(found, "restore has no profiles")
        self.assertIn("restore", found.group(1))
        self.assertRegex(block, r"(?m)^    image: postgres:\S+$")

    def test_restore_runs_the_script_with_restore(self) -> None:
        """Requirement: Web server and Compose file (`restore` running
        `orgsyndb-backup restore`)."""
        words = command_words("restore", "entrypoint")
        self.assertTrue(any(w.endswith("orgsyndb-backup") for w in words),
                        words)
        self.assertEqual(command_words("restore", "command")[-1:],
                         ["restore"])
        self.assertRegex(service_block("restore"),
                         r"(?m)^    env_file: orgsyndb\.env$")

    def test_restore_writes_what_it_restores(self) -> None:
        """Requirement: Web server and Compose file (the volumes
        `forge`, `pushes` and `data` read-write)."""
        found = mounts("restore")
        self.assertEqual(found.get(FORGE), ("forge", "rw"), found)
        self.assertEqual(found.get(PUSHES), ("pushes", "rw"), found)
        self.assertEqual(found.get(DATA), ("data", "rw"), found)

    def test_restore_reads_the_backups_and_keeps_the_script(self) -> None:
        """Requirement: Web server and Compose file (`deploy/backups/`
        read-only)."""
        found = mounts("restore")
        self.assertEqual(found.get("/backups"), ("./backups", "ro"), found)
        self.assertIn(("./backup", "ro"), found.values())

    def test_restore_starts_once_the_database_is_healthy(self) -> None:
        """Requirement: Web server and Compose file (starting once `db`
        is healthy)."""
        self.assertRegex(
            service_block("restore"),
            r"(?s)depends_on:.*db:\s*\n\s*condition: service_healthy")

    def test_restore_starts_once_forge_db_has_completed(self) -> None:
        """Requirement: Web server and Compose file (`restore` starting
        once `forge-db` has completed, since it creates `forge` owned by
        the role `forge`)."""
        self.assertRegex(
            service_block("restore"),
            r"(?s)depends_on:.*\bforge-db:\s*\n\s*"
            r"condition: service_completed_successfully")

    def test_forge_has_an_init_process(self) -> None:
        """Requirement: Forgejo (with an init process)."""
        self.assertRegex(service_block("forge"), r"(?m)^    init: true$")

    def test_forge_mounts_the_control_volume(self) -> None:
        """Requirement: Forgejo (the volume `forge-control` at
        `/var/lib/orgsyndb-forge-control`)."""
        self.assertEqual(mounts("forge").get(CONTROL),
                         ("forge-control", "rw"), mounts("forge"))

    def test_forge_still_keeps_its_data_and_the_push_log(self) -> None:
        found = mounts("forge")
        self.assertEqual(found.get(FORGE), ("forge", "rw"), found)
        self.assertEqual(found.get(PUSHES), ("pushes", "rw"), found)

    def test_forge_db_can_change_the_control_volume(self) -> None:
        """Requirement: Forgejo (`forge-db` makes the root of
        `forge-control` owned by UID 1000)."""
        self.assertEqual(mounts("forge-db").get(CONTROL),
                         ("forge-control", "rw"), mounts("forge-db"))

    def test_the_control_volume_is_shared_by_three_services(self) -> None:
        self.assertEqual(volume_users("forge-control"),
                         {"forge": "rw", "backup": "rw", "forge-db": "rw"})

    def test_forgejos_volume_is_used_by_forgejo_and_the_backup_pair(
            self) -> None:
        self.assertEqual(volume_users("forge"),
                         {"forge": "rw", "backup": "ro", "restore": "rw"})

    def test_the_push_log_volume_users(self) -> None:
        """Requirement: Web server and Compose file (`builder` and
        `backup` read-only, `forge`, `forge-db` and `restore`
        read-write)."""
        self.assertEqual(
            volume_users("pushes"),
            {"builder": "ro", "backup": "ro", "forge": "rw",
             "forge-db": "rw", "restore": "rw"})

    def test_the_builders_data_is_written_by_the_builder_and_restore(
            self) -> None:
        users = volume_users("data")
        self.assertEqual(users.get("restore"), "rw", users)
        self.assertEqual(users.get("builder"), "rw", users)
        self.assertEqual(users.get("web"), "ro", users)
        self.assertEqual(users.get("app"), "ro", users)
        self.assertNotIn("backup", users)


class ComposeConfigTests(unittest.TestCase):
    """Scenario: Compose file (`docker compose config`)."""

    def config(self, *profiles: str) -> dict:
        if shutil.which("docker") is None:
            self.skipTest("docker not found")
        env = {name: value for name, value in os.environ.items()
               if not name.startswith(("ORGSYNDB_", "FORGE_"))}
        flags = [word for name in profiles
                 for word in ("--profile", name)]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "deploy"
            shutil.copytree(DEPLOY, target)
            shutil.copy(target / "orgsyndb.env.example",
                        target / "orgsyndb.env")
            done = subprocess.run(
                ["docker", "compose", *flags, "config", "--format",
                 "json"],
                cwd=target, env=env, capture_output=True, text=True)
        if done.returncode != 0 and "is not a docker command" in done.stderr:
            self.skipTest("docker compose not found")
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)

    def volumes(self, config: dict, name: str) -> dict[str, dict]:
        return {m["target"]: m
                for m in config["services"][name].get("volumes", [])}

    def test_restore_only_belongs_to_its_profile(self) -> None:
        self.assertEqual(
            sorted(self.config()["services"]),
            ["app", "backup", "builder", "db", "forge", "forge-db", "web"])
        self.assertIn("restore", self.config("restore")["services"])

    def test_the_volume_is_declared(self) -> None:
        self.assertIn("forge-control", self.config()["volumes"])

    def test_backup(self) -> None:
        config = self.config()
        found = self.volumes(config, "backup")
        for target, source, read_only in (
                (FORGE, "forge", True), (PUSHES, "pushes", True),
                (CONTROL, "forge-control", False)):
            with self.subTest(target=target):
                self.assertEqual(found[target]["type"], "volume")
                self.assertEqual(found[target]["source"], source)
                self.assertEqual(bool(found[target].get("read_only")),
                                 read_only)
        settings = found[SETTINGS]
        self.assertEqual(settings["type"], "bind")
        self.assertTrue(settings["source"].endswith("/orgsyndb.env"))
        self.assertTrue(settings["read_only"])

    def test_restore(self) -> None:
        config = self.config("restore")
        restore = config["services"]["restore"]
        self.assertEqual(restore["image"], config["services"]["db"]["image"])
        self.assertEqual(restore["command"][-1], "restore")
        self.assertEqual(restore["depends_on"]["db"]["condition"],
                         "service_healthy")
        found = self.volumes(config, "restore")
        for target, source in ((FORGE, "forge"), (PUSHES, "pushes"),
                               (DATA, "data")):
            with self.subTest(target=target):
                self.assertEqual(found[target]["source"], source)
                self.assertFalse(found[target].get("read_only"))
        self.assertEqual(found["/backups"]["type"], "bind")
        self.assertTrue(found["/backups"]["read_only"])

    def test_restore_waits_for_forge_db(self) -> None:
        restore = self.config("restore")["services"]["restore"]
        self.assertEqual(restore["depends_on"]["forge-db"]["condition"],
                         "service_completed_successfully")

    def test_forge(self) -> None:
        config = self.config()
        forge = config["services"]["forge"]
        self.assertTrue(forge["init"])
        mount = self.volumes(config, "forge")[CONTROL]
        self.assertEqual(mount["source"], "forge-control")
        self.assertFalse(mount.get("read_only"))
        self.assertEqual(
            self.volumes(config, "forge-db")[CONTROL]["source"],
            "forge-control")


def mount_namespaces_work() -> bool:
    """Whether a private mount namespace, with a tmpfs over /var/lib,
    can be made."""
    if shutil.which("unshare") is None:
        return False
    done = subprocess.run(
        ["unshare", "--user", "--map-root-user", "--mount", "sh", "-c",
         "mount -t tmpfs none /var/lib"],
        stdin=subprocess.DEVNULL, capture_output=True)
    return done.returncode == 0


class ForgeDatabaseTests(unittest.TestCase):
    """Scenario: The push log's volume."""

    def test_it_names_the_control_volume(self) -> None:
        """Scenario: The push log's volume (reads
        `/var/lib/orgsyndb-forge-control`)."""
        self.assertTrue(DATABASE.is_file(),
                        "deploy/forge/forge-db is missing")
        text = DATABASE.read_text(encoding="utf-8")
        self.assertIn(CONTROL, text)
        self.assertIn(PUSHES, text)
        self.assertRegex(text, r"\bchown\b[^\n]*\b1000\b")

    @unittest.skipUnless(mount_namespaces_work(),
                         "no mount namespace can be made")
    def test_it_hands_both_volumes_and_their_files_to_uid_1000(
            self) -> None:
        """Scenario: The push log's volume (makes
        `/var/lib/orgsyndb-pushes` and `/var/lib/orgsyndb-forge-control`
        owned by UID 1000). The script runs with fake `psql` and
        `chown` on `PATH`, in a mount namespace whose /var/lib holds the
        two directories."""
        with tempfile.TemporaryDirectory(prefix="osdb-forge-db-") as name:
            tmp = Path(name)
            (tmp / "bin").mkdir()
            for tool, body in (("psql", "cat > /dev/null\n"),
                               ("chown", 'echo "$@" >> "$FAKE_LOG"\n')):
                (tmp / "bin" / tool).write_text("#!/bin/sh\n" + body)
                (tmp / "bin" / tool).chmod(0o755)
            done = subprocess.run(
                ["unshare", "--user", "--map-root-user", "--mount", "sh",
                 "-c",
                 f'mount -t tmpfs none /var/lib && mkdir {PUSHES} {CONTROL}'
                 f' && : > {PUSHES}/pushes.log && : > {CONTROL}/paused'
                 ' && exec sh "$0"', str(DATABASE)],
                env={"PATH": f"{tmp / 'bin'}{os.pathsep}"
                             f"{os.environ['PATH']}",
                     "FAKE_LOG": str(tmp / "chown.log"),
                     "FORGE_DB_PASSWORD": "x", "POSTGRES_USER": "u",
                     "POSTGRES_PASSWORD": "p", "POSTGRES_DB": "d"},
                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                timeout=60)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            calls = [line.split() for line in
                     (tmp / "chown.log").read_text().splitlines()]
        for volume, leaf in ((PUSHES, "pushes.log"), (CONTROL, "paused")):
            with self.subTest(volume=volume):
                own = [c for c in calls if any(
                    re.fullmatch(r"1000(:1000)?", a) for a in c)]
                self.assertTrue(
                    any(volume in c or volume + "/" in c for c in own),
                    f"the root of {volume} is not handed over: {calls}")
                self.assertTrue(
                    any(("-R" in c or "--recursive" in c
                         or any(a.startswith("-") and "R" in a
                                for a in c)) and volume in c
                        or f"{volume}/{leaf}" in c for c in own),
                    f"the files of {volume} are not handed over: {calls}")


if __name__ == "__main__":
    unittest.main()
