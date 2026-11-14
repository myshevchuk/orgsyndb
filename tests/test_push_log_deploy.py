"""Tests of the files the push log adds to the deployment
(container-deployment: Web server and Compose file, Forgejo, Mirror,
Push log): the volume ``pushes`` in ``deploy/compose.yaml``, what
``forge-db`` and ``forge-setup`` do about it and the mirror, the
image's mount point and the example settings.

The scripts are read, not run: they need Forgejo and PostgreSQL. Where
``docker compose config`` is needed the tests skip without Docker, as
those of the other deployment files do.
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
                               SETUP, comment_above, parse_env,
                               service_block)

DOCKERFILE = DEPLOY / "docker" / "Dockerfile"
PUSHES = "/var/lib/orgsyndb-pushes"
LOG = f"{PUSHES}/pushes.log"


class ComposeTextTests(unittest.TestCase):
    """Requirement: Web server and Compose file (the volume `pushes`),
    read without Docker."""

    def mount(self, name: str) -> str | None:
        """The text of the mount of ``pushes`` in the service ``name``,
        or None."""
        found = re.search(
            rf"(?m)^      - pushes:{re.escape(PUSHES)}(:\w+)?$",
            service_block(name))
        return None if found is None else found.group(0)

    def test_the_volume_is_declared(self) -> None:
        self.assertRegex(COMPOSE.read_text(encoding="utf-8"),
                         r"(?ms)^volumes:\n.*^  pushes:")

    def test_the_builder_reads_the_log(self) -> None:
        """Requirement: Web server and Compose file (`builder` mounting
        `pushes` read-only)."""
        mount = self.mount("builder")
        self.assertIsNotNone(mount, "builder does not mount pushes")
        self.assertTrue(mount.endswith(":ro"), mount)

    def test_the_forge_and_its_database_job_write_it(self) -> None:
        """Requirement: Web server and Compose file (`forge-db` and
        `forge` both mounting `pushes` read-write)."""
        for name in ("forge", "forge-db"):
            with self.subTest(service=name):
                mount = self.mount(name)
                self.assertIsNotNone(mount, f"{name} does not mount pushes")
                self.assertFalse(mount.endswith(":ro"), mount)

    def test_nothing_else_mounts_the_volume(self) -> None:
        """Requirement: Web server and Compose file (the services that
        write or read the push log)."""
        for name in ("web", "db", "app", "backup"):
            with self.subTest(service=name):
                self.assertNotIn("pushes", service_block(name))


class ComposeConfigTests(unittest.TestCase):
    """Scenario: Compose file (`docker compose config`)."""

    def config(self) -> tuple[dict, dict[str, str]]:
        if shutil.which("docker") is None:
            self.skipTest("docker not found")
        env = {name: value for name, value in os.environ.items()
               if not name.startswith(("ORGSYNDB_", "FORGE_"))}
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "deploy"
            shutil.copytree(DEPLOY, target)
            shutil.copy(target / "orgsyndb.env.example",
                        target / "orgsyndb.env")
            done = subprocess.run(
                ["docker", "compose", "config", "--format", "json"],
                cwd=target, env=env, capture_output=True, text=True)
        if done.returncode != 0 and "is not a docker command" in done.stderr:
            self.skipTest("docker compose not found")
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout), parse_env(ENV_EXAMPLE)

    def mounts(self, config: dict, name: str) -> dict[str, dict]:
        return {m["target"]: m
                for m in config["services"][name].get("volumes", [])}

    def test_the_volume_is_mounted_where_the_image_expects_it(
            self) -> None:
        config, _example = self.config()
        self.assertIn("pushes", config["volumes"])
        for name in ("builder", "forge", "forge-db"):
            with self.subTest(service=name):
                mount = self.mounts(config, name)[PUSHES]
                self.assertEqual(mount["type"], "volume")
                self.assertEqual(mount["source"], "pushes")

    def test_the_builder_mounts_it_read_only(self) -> None:
        config, _example = self.config()
        self.assertTrue(self.mounts(config, "builder")[PUSHES][
            "read_only"])

    def test_the_forge_and_its_database_job_mount_it_read_write(
            self) -> None:
        config, _example = self.config()
        for name in ("forge", "forge-db"):
            with self.subTest(service=name):
                self.assertFalse(
                    self.mounts(config, name)[PUSHES].get("read_only"))

    def test_the_wake_up_address_reaches_the_forge_and_the_app(
            self) -> None:
        """Requirement: Web server and Compose file (each service reads
        `orgsyndb.env`)."""
        config, example = self.config()
        for name in ("forge", "app"):
            with self.subTest(service=name):
                env = config["services"][name]["environment"]
                self.assertEqual(env["ORGSYNDB_WAKE_URL"],
                                 example["ORGSYNDB_WAKE_URL"])

    def test_the_services_are_the_same(self) -> None:
        config, _example = self.config()
        self.assertEqual(
            sorted(config["services"]),
            ["app", "backup", "builder", "db", "forge", "forge-db", "web"])


class ForgeDatabaseTests(unittest.TestCase):
    """Scenario: The push log's volume."""

    def text(self) -> str:
        self.assertTrue(DATABASE.is_file(),
                        "deploy/forge/forge-db is missing")
        return DATABASE.read_text(encoding="utf-8")

    def test_it_makes_the_volume_owned_by_uid_1000(self) -> None:
        text = self.text()
        self.assertIn(PUSHES, text)
        self.assertRegex(text, r"\bchown\b[^\n]*\b1000\b")

    def test_it_hands_over_the_files_in_it_too(self) -> None:
        """Requirement: Forgejo (the root of the volume, and the files
        in it)."""
        text = self.text()
        recursive = (
            re.search(r"\bchown\s+(-\S*R\S*|--recursive)\s[^\n]*\b1000\b",
                      text)
            or re.search(r"\bfind\b[^\n]*\bchown\b[^\n]*\b1000\b", text)
            or re.search(r"\bchown\b[^\n]*\b1000\b[^\n]*/\*", text))
        self.assertIsNotNone(recursive,
                             "no chown of the files in the volume")

    def test_the_script_is_still_posix_shell(self) -> None:
        self.text()
        done = subprocess.run(["sh", "-n", str(DATABASE)],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_the_database_part_is_kept(self) -> None:
        """Requirement: Forgejo (creates the role and the database when
        either is missing)."""
        text = self.text()
        self.assertIn("pg_roles", text)
        self.assertIn("pg_database", text)
        self.assertIn("FORGE_DB_PASSWORD", text)


class ForgeSetupTests(unittest.TestCase):
    """Scenario: The set-up script (the push log's hook and the check of
    the log), Scenario: The mirror in the set-up script."""

    def text(self) -> str:
        self.assertTrue(SETUP.is_file(),
                        "deploy/forge/forge-setup is missing")
        return SETUP.read_text(encoding="utf-8")

    def test_it_is_still_posix_shell(self) -> None:
        self.text()
        done = subprocess.run(["sh", "-n", str(SETUP)],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_the_push_log_is_linked_into_the_post_receive_hooks(
            self) -> None:
        """Scenario: The set-up script (links the push log into
        `hooks/post-receive.d/`)."""
        text = self.text()
        self.assertRegex(text,
                         r"lab/collection\.git/hooks/post-receive\.d")
        self.assertIn("orgsyndb-push-log", text)
        self.assertRegex(text, r"\bln\s+-[a-z]*s[^\n]*push-log")
        self.assertRegex(text, r"forge/push-log\b")

    def test_the_gate_is_still_linked(self) -> None:
        """Requirement: Forgejo (links `deploy/forge/gate` into the
        repository's `hooks/pre-receive.d/`)."""
        text = self.text()
        self.assertRegex(text,
                         r"lab/collection\.git/hooks/pre-receive\.d")
        self.assertIn("orgsyndb-gate", text)

    def test_the_push_log_is_checked_for_appending(self) -> None:
        """Requirement: Forgejo (creates the push log when missing and
        stops with an error naming `ORGSYNDB_PUSH_LOG` when it cannot
        append to it)."""
        text = self.text()
        self.assertIn("ORGSYNDB_PUSH_LOG", text)
        self.assertIn(LOG, text)
        self.assertIn(">>", text)
        self.assertRegex(text, r"(?is)ORGSYNDB_PUSH_LOG.*\bexit\s+1\b")

    def test_the_mirror_reads_its_three_settings(self) -> None:
        """Scenario: The mirror in the set-up script."""
        text = self.text()
        for name in ("ORGSYNDB_MIRROR_URL", "ORGSYNDB_MIRROR_USER",
                     "ORGSYNDB_MIRROR_TOKEN"):
            with self.subTest(name=name):
                self.assertIn(name, text)

    def test_the_mirror_address_must_be_https(self) -> None:
        """Requirement: Mirror (it stops with an error naming the
        variable when `ORGSYNDB_MIRROR_URL` does not begin with
        `https://`)."""
        code = "\n".join(line for line in self.text().splitlines()
                         if not line.lstrip().startswith("#"))
        self.assertIn("https://", code)

    def test_both_credentials_are_required(self) -> None:
        """Requirement: Mirror (it stops when either credential is
        empty): the script tests for an empty value."""
        text = self.text()
        for name in ("ORGSYNDB_MIRROR_USER", "ORGSYNDB_MIRROR_TOKEN"):
            with self.subTest(name=name):
                self.assertIn(name, text)
        self.assertRegex(text, r"-z\b|:\?")

    def test_the_mirrors_to_that_address_are_deleted(self) -> None:
        """Requirement: Mirror (it removes every push mirror of
        `lab/collection` whose address is that URL)."""
        text = self.text()
        self.assertRegex(text, r"repos/lab/collection/push_mirrors")
        self.assertRegex(text, r"\bDELETE\b")
        self.assertRegex(text, r"remote_address")

    def test_a_new_mirror_is_posted_syncing_on_every_push(self) -> None:
        """Requirement: Mirror (an interval of 8 hours, syncing on every
        push, with the credentials)."""
        text = self.text()
        self.assertRegex(text, r"\bPOST\b")
        self.assertRegex(text, r"sync_on_commit\W{1,6}true")
        self.assertRegex(text, r"interval\W{1,6}8h")
        for field in ("remote_address", "remote_username",
                      "remote_password"):
            with self.subTest(field=field):
                self.assertIn(field, text)

    def test_the_old_mirrors_go_before_the_new_one_is_added(self) -> None:
        """Requirement: Mirror (a run applies changed credentials)."""
        text = self.text()
        self.assertLess(text.index("DELETE"),
                        text.rindex("sync_on_commit"))

    def lookup(self, mirror_url: str, answer: str) -> list[str]:
        """Run the script's own lookup of the mirrors to MIRROR_URL, the
        block that assigns ``mirrors``, with sh over the API answer
        ANSWER, and return the remote names it prints."""
        block = re.search(r"(?ms)^mirrors=\$\(.*?^\tdone\)$",
                          self.text())
        self.assertIsNotNone(block, "no lookup assigning mirrors")
        with tempfile.TemporaryDirectory() as work:
            path = Path(work) / "answer"
            path.write_text(answer, encoding="utf-8")
            done = subprocess.run(
                ["sh", "-c", block.group(0) + '\nprintf "%s\\n" $mirrors',
                 "sh"], env={**os.environ, "answer": str(path),
                             "mirror_url": mirror_url},
                capture_output=True, text=True, timeout=30,
                stdin=subprocess.DEVNULL)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.split()

    def test_the_lookup_finds_every_mirror_to_the_address(self) -> None:
        """Requirement: Mirror (it removes every push mirror of
        `lab/collection` whose address is that URL): Forgejo's answer,
        as Go encodes it, ends without a newline and writes `&`, `<` and
        `>` as escapes; the lookup finds the last mirror too, and an
        address holding `&`."""
        url = "https://git.example.org/r&d/<x>.git"
        encoded = url.replace("&", "\\u0026").replace(
            "<", "\\u003c").replace(">", "\\u003e")
        answer = json.dumps([
            {"repo_name": "collection", "remote_name": "remote_mirror_a",
             "remote_address": encoded, "sync_on_commit": True},
            {"repo_name": "collection", "remote_name": "remote_mirror_b",
             "remote_address": "https://other.example.org/c.git"},
            {"remote_address": encoded, "remote_name": "remote_mirror_c"},
        ], separators=(",", ":")).replace("\\\\u", "\\u")
        self.assertIn("\\u0026", answer)
        self.assertEqual(self.lookup(url, answer),
                         ["remote_mirror_a", "remote_mirror_c"])
        self.assertEqual(self.lookup(
            "https://other.example.org/c.git", answer), ["remote_mirror_b"])

    def test_without_the_address_no_mirror_is_changed(self) -> None:
        """Requirement: Mirror (without `ORGSYNDB_MIRROR_URL` it changes
        no mirror and says that no mirror is configured)."""
        self.assertRegex(self.text(), r"(?i)no mirror is configured")

    def test_the_credentials_are_not_written_into_the_script(self) -> None:
        text = self.text()
        self.assertNotRegex(
            text, r"remote_password\W{1,6}[A-Za-z0-9]{6,}(?![A-Za-z0-9_$])")


class DockerfileTests(unittest.TestCase):
    """Requirement: Application image, Push log (the mount point)."""

    def test_the_mount_point_is_made_for_the_images_user(self) -> None:
        text = DOCKERFILE.read_text(encoding="utf-8")
        self.assertRegex(
            text, r"(?s)\binstall\s+-d[^&]*?-o\s+orgsyndb[^&]*?"
                  + re.escape(PUSHES) + r"(?![\w-])"
                  r"|\bchown\b[^&\n]*\borgsyndb\b[^&\n]*"
                  + re.escape(PUSHES) + r"(?![\w-])")

    def test_the_directory_is_made_before_the_user_runs(self) -> None:
        """Requirement: Push log (a mount of the volume takes its owner
        from the image)."""
        text = DOCKERFILE.read_text(encoding="utf-8")
        self.assertLess(text.index(PUSHES), text.rindex("USER orgsyndb"))


class EnvExampleTests(unittest.TestCase):
    """Requirement: Forgejo (the example settings), Mirror."""

    def test_the_wake_up_address_is_the_builders(self) -> None:
        env = parse_env(ENV_EXAMPLE)
        self.assertEqual(env.get("ORGSYNDB_WAKE_URL"),
                         "http://builder:8091/wake")

    def test_the_wake_up_address_has_a_comment(self) -> None:
        """Requirement: Forgejo (the example settings name
        `ORGSYNDB_WAKE_URL`)."""
        self.assertRegex(comment_above(ENV_EXAMPLE, "ORGSYNDB_WAKE_URL"),
                         r"(?i)wake|builder")

    def test_the_mirror_settings_are_empty(self) -> None:
        text = ENV_EXAMPLE.read_text(encoding="utf-8")
        for name in ("ORGSYNDB_MIRROR_URL", "ORGSYNDB_MIRROR_USER",
                     "ORGSYNDB_MIRROR_TOKEN"):
            with self.subTest(name=name):
                self.assertRegex(text, rf"(?m)^#?{name}=$")
                self.assertEqual(parse_env(ENV_EXAMPLE).get(name, ""), "")

    def test_the_mirror_says_it_overwrites_its_target(self) -> None:
        """Requirement: Mirror (the example settings say that the
        address must name a repository used for nothing else)."""
        comment = comment_above(ENV_EXAMPLE, "ORGSYNDB_MIRROR_URL")
        self.assertRegex(comment, r"(?i)overwrit")
        self.assertRegex(comment, r"(?i)nothing else|no other|nobody "
                                  r"else|anything else")
        self.assertRegex(comment, r"https://")

    def test_the_other_settings_stay(self) -> None:
        env = parse_env(ENV_EXAMPLE)
        for name in ("ORGSYNDB_GATE_TOKEN", "ORGSYNDB_BUILDER_TOKEN",
                     "ORGSYNDB_FORGE_URL", "ORGSYNDB_COLLECTION_REPO"):
            with self.subTest(name=name):
                self.assertTrue(env.get(name))


if __name__ == "__main__":
    unittest.main()
