"""Tests of the deployment of Forgejo: the services in
deploy/compose.yaml, deploy/forge/, the Caddyfile's /git/ route, the
application image's command and the example settings
(container-deployment: Web server and Compose file, Application image,
Forgejo)."""

import glob
import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parent.parent
DEPLOY = REPO / "deploy"
COMPOSE = DEPLOY / "compose.yaml"
CADDYFILE = DEPLOY / "docker" / "Caddyfile"
DOCKERFILE = DEPLOY / "webapp" / "Dockerfile"
ENV_EXAMPLE = DEPLOY / "orgsyndb.env.example"
FORGE = DEPLOY / "forge"
START = FORGE / "forge-start"
DATABASE = FORGE / "forge-db"
SETUP = FORGE / "forge-setup"

IMAGE = "codeberg.org/forgejo/forgejo:15.0.11-rootless"
IMAGE_ENTRYPOINT = ["/usr/bin/dumb-init", "--",
                    "/usr/local/bin/docker-entrypoint.sh"]
SERVICES = ["app", "backup", "builder", "db", "forge", "forge-db", "web"]
FORGE_SETTINGS = ["ORGSYNDB_URL", "ORGSYNDB_OIDC_KEY",
                  "ORGSYNDB_FORGE_CLIENT_SECRET", "ORGSYNDB_FORGE_PASSWORD",
                  "FORGE_DB_PASSWORD", "ORGSYNDB_FORGE_URL"]


def parse_env(path: Path) -> dict[str, str]:
    """The settings an env file sets, leaving out comments."""
    found = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            found[key.strip()] = value.strip()
    return found


def service_block(name: str) -> str:
    """The text of the service NAME in compose.yaml, without its
    name."""
    found = re.search(rf"(?ms)^  {re.escape(name)}:\n(.*?)(?=^\S|^  \S)",
                      COMPOSE.read_text(encoding="utf-8") + "\n")
    assert found is not None, f"compose.yaml has no service {name}"
    return found.group(1)


def words(command: object) -> list[str]:
    if command is None:
        return []
    return [command] if isinstance(command, str) else list(command)


def comment_above(path: Path, key: str) -> str:
    """The comment lines directly above the line that sets KEY (set or
    commented out) in the env file PATH."""
    lines = path.read_text().splitlines()
    found = [number for number, line in enumerate(lines)
             if re.match(rf"#?{re.escape(key)}=", line)]
    assert len(found) == 1, f"{key} is not set once in {path.name}: {found}"
    index = found[0]
    comment = []
    for line in reversed(lines[:index]):
        if not line.startswith("#") or re.match(r"#[A-Z_]+=", line):
            break
        comment.insert(0, line)
    return "\n".join(comment)


def forgejo_setting(env: dict[str, str], key: str) -> str | None:
    """The value of the Forgejo setting KEY, whatever its section, in
    the environment ENV of a service."""
    found = [value for name, value in env.items()
             if re.fullmatch(rf"FORGEJO__[a-z0-9_]+__{key}", name)]
    assert len(found) <= 1, f"{key} is set more than once: {found}"
    return found[0] if found else None


class ComposeTextTests(unittest.TestCase):
    """Scenario: Forgejo's service (read without Docker)."""

    def test_the_services_are_defined(self) -> None:
        for name in ("forge", "forge-db"):
            with self.subTest(service=name):
                self.assertTrue(service_block(name).strip())

    def test_forge_runs_the_pinned_rootless_image(self) -> None:
        self.assertRegex(service_block("forge"),
                         rf"(?m)^    image: {re.escape(IMAGE)}$")

    def test_forge_starts_through_forge_start(self) -> None:
        block = service_block("forge")
        self.assertRegex(
            block, r"(?ms)^    entrypoint:(?:(?!^    \w).)*?forge-start")
        for word in IMAGE_ENTRYPOINT:
            self.assertIn(word, block)
        self.assertRegex(block, r"(?m)^    command:")

    def test_forge_reads_the_settings_and_keeps_its_data(self) -> None:
        block = service_block("forge")
        self.assertRegex(block, r"(?m)^    env_file: orgsyndb\.env$")
        self.assertRegex(block, r"(?m)^      - forge:/")
        self.assertRegex(COMPOSE.read_text(),
                         r"(?ms)^volumes:\n.*^  forge:")

    def test_forge_mounts_its_scripts_read_only(self) -> None:
        self.assertRegex(service_block("forge"),
                         r"(?m)^      - \./forge[^:\n]*:[^:\n]+:ro$")

    def test_forge_publishes_the_ssh_port(self) -> None:
        self.assertRegex(service_block("forge"), r'"?2222:2222"?')

    def test_forge_waits_for_the_database_to_be_made(self) -> None:
        self.assertRegex(
            service_block("forge"),
            r"(?s)depends_on:.*forge-db:\s*\n\s*condition: "
            r"service_completed_successfully")

    def test_forge_db_runs_once_after_the_database_is_healthy(self) -> None:
        block = service_block("forge-db")
        self.assertRegex(block, r"(?m)^    image: postgres:18$")
        self.assertRegex(block, r"(?m)^    env_file: orgsyndb\.env$")
        self.assertRegex(block, r"(?s)depends_on:.*db:\s*\n\s*condition: "
                                r"service_healthy")
        self.assertRegex(block, r"forge-db")
        self.assertRegex(block, r"(?m)^      - \./forge[^:\n]*:[^:\n]+:ro$")
        self.assertNotRegex(block,
                            r"(?m)^    restart: (unless-stopped|always|"
                            r"on-failure)")

    def test_nothing_is_substituted_from_the_shell(self) -> None:
        """Requirement: Forgejo (none substituted by Compose from the
        shell)."""
        for name in ("forge", "forge-db"):
            with self.subTest(service=name):
                self.assertNotIn("${", service_block(name))

    def test_the_constant_settings_are_variables_of_the_service(
            self) -> None:
        block = service_block("forge")
        for name, value in (
                ("database__DB_TYPE", "postgres"),
                ("database__NAME", "forge"), ("database__USER", "forge"),
                ("database__HOST", "db"), ("security__INSTALL_LOCK", "true"),
                ("oauth2_client__ENABLE_AUTO_REGISTRATION", "true"),
                ("oauth2_client__ACCOUNT_LINKING", "disabled"),
                ("service__ENABLE_INTERNAL_SIGNIN", "false"),
                ("service__ALLOW_ONLY_EXTERNAL_REGISTRATION", "true"),
                ("server__START_SSH_SERVER", "true"),
                ("server__SSH_LISTEN_PORT", "2222")):
            with self.subTest(setting=name):
                self.assertRegex(
                    block, rf"FORGEJO__{name}[:=]\s*\"?{value}\b")

    def test_the_root_url_and_the_password_come_from_the_script(
            self) -> None:
        block = service_block("forge")
        self.assertNotIn("FORGEJO__server__ROOT_URL", block)
        self.assertNotIn("FORGEJO__database__PASSWD", block)


class ComposeConfigTests(unittest.TestCase):
    """Scenario: Forgejo's service."""

    def config(self) -> tuple[dict, str, dict[str, str]]:
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
        return json.loads(done.stdout), done.stdout, parse_env(ENV_EXAMPLE)

    def test_the_services(self) -> None:
        config, _text, _example = self.config()
        self.assertEqual(sorted(config["services"]), SERVICES)

    def test_forge(self) -> None:
        config, _text, example = self.config()
        forge = config["services"]["forge"]
        self.assertEqual(forge["image"], IMAGE)
        self.assertTrue(
            any(word.endswith("forge-start")
                for word in words(forge.get("entrypoint"))),
            forge.get("entrypoint"))
        self.assertEqual(words(forge["command"]), IMAGE_ENTRYPOINT)
        mounts = {m["target"]: m for m in forge["volumes"]}
        self.assertIn("forge", {m.get("source") for m in forge["volumes"]
                                if m.get("type") == "volume"})
        scripts = [m for m in forge["volumes"] if m.get("type") == "bind"]
        self.assertTrue(scripts, mounts)
        for mount in scripts:
            self.assertTrue(mount.get("read_only"), mount)
        sources = [m["source"] for m in scripts]
        for script in ("forge-start", "forge-setup"):
            with self.subTest(script=script):
                self.assertTrue(
                    any(s.rstrip("/").endswith(("/forge", f"/{script}"))
                        for s in sources), sources)
        self.assertTrue(any(p["target"] == 2222
                            and str(p["published"]) == "2222"
                            for p in forge["ports"]), forge["ports"])
        self.assertEqual(forge["depends_on"]["forge-db"]["condition"],
                         "service_completed_successfully")
        env = forge["environment"]
        self.assertEqual(env["FORGEJO__database__NAME"], "forge")
        self.assertEqual(env["FORGEJO__database__USER"], "forge")
        self.assertTrue(env["FORGEJO__database__HOST"].startswith("db"))
        self.assertEqual(forgejo_setting(env, "ACCOUNT_LINKING"),
                         "disabled")
        self.assertEqual(forgejo_setting(env, "ENABLE_INTERNAL_SIGNIN"),
                         "false")
        self.assertEqual(forgejo_setting(env, "ENABLE_AUTO_REGISTRATION"),
                         "true")
        self.assertNotIn("FORGEJO__server__ROOT_URL", env)
        self.assertNotIn("FORGEJO__database__PASSWD", env)
        for key in ("ORGSYNDB_URL", "FORGE_DB_PASSWORD"):
            self.assertEqual(env[key], example[key])

    def test_forge_db(self) -> None:
        config, _text, example = self.config()
        forge_db = config["services"]["forge-db"]
        self.assertEqual(forge_db["image"], "postgres:18")
        self.assertEqual(forge_db["depends_on"]["db"]["condition"],
                         "service_healthy")
        self.assertIn(forge_db.get("restart", "no"), ("no", ""))
        self.assertTrue(
            any(word.endswith("forge-db")
                for word in (*words(forge_db.get("entrypoint")),
                             *words(forge_db.get("command")))),
            forge_db)
        self.assertEqual(forge_db["environment"]["FORGE_DB_PASSWORD"],
                         example["FORGE_DB_PASSWORD"])

    def test_nothing_is_unresolved_or_empty(self) -> None:
        config, text, _example = self.config()
        self.assertNotIn("${", text)
        for name in ("forge", "forge-db"):
            for key, value in config["services"][name].get(
                    "environment", {}).items():
                if key.startswith("FORGEJO__"):
                    with self.subTest(service=name, key=key):
                        self.assertNotIn(value, ("", None))

    def test_the_application_gets_the_forge_settings(self) -> None:
        config, _text, example = self.config()
        env = config["services"]["app"]["environment"]
        for key in FORGE_SETTINGS:
            with self.subTest(key=key):
                self.assertEqual(env[key], example[key])


class ForgeStartTests(unittest.TestCase):
    """Scenario: The start script."""

    ENV = {"ORGSYNDB_URL": "http://localhost:8080", "FORGE_DB_PASSWORD": "x"}

    def run_script(self, *command: str, **env: str
                   ) -> subprocess.CompletedProcess:
        """Run the script with COMMAND (by default ``env``) and the
        environment ``ENV`` with OVER on top."""
        self.assertTrue(START.is_file(),
                        "deploy/forge/forge-start is missing")
        return subprocess.run(
            ["sh", str(START), *(command or ("env",))],
            env={"PATH": os.environ["PATH"], **{**self.ENV, **env}},
            capture_output=True, text=True, timeout=30)

    def environment(self, **env: str) -> dict[str, str]:
        done = self.run_script(**env)
        self.assertEqual(done.returncode, 0, done.stderr)
        return dict(line.split("=", 1) for line in done.stdout.splitlines()
                    if "=" in line)

    def test_the_command_runs_with_the_root_url_and_the_password(
            self) -> None:
        found = self.environment()
        self.assertEqual(found["FORGEJO__server__ROOT_URL"],
                         "http://localhost:8080/git/")
        self.assertEqual(found["FORGEJO__database__PASSWD"], "x")

    def test_the_root_url_follows_the_public_address(self) -> None:
        found = self.environment(ORGSYNDB_URL="https://lab.example.org")
        self.assertEqual(found["FORGEJO__server__ROOT_URL"],
                         "https://lab.example.org/git/")

    def test_a_password_with_special_characters_arrives_as_it_is(
            self) -> None:
        for password in ("p@ss w\"rd$x", "o'hara", "back\\slash",
                         "a b  c", "`id`", "$(id)", "#hash", "=x="):
            with self.subTest(password=password):
                found = self.environment(FORGE_DB_PASSWORD=password)
                self.assertEqual(found["FORGEJO__database__PASSWD"],
                                 password)

    def test_the_rest_of_the_environment_is_kept(self) -> None:
        found = self.environment(SOMETHING="kept",
                                 FORGEJO__server__DOMAIN="forge.test")
        self.assertEqual(found["SOMETHING"], "kept")
        self.assertEqual(found["FORGEJO__server__DOMAIN"], "forge.test")

    def test_the_arguments_reach_the_command_as_they_are(self) -> None:
        done = self.run_script(
            "sh", "-c", 'for a in "$@"; do printf "[%s]" "$a"; done', "_",
            "a b", "", "c*")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, "[a b][][c*]")

    def test_the_exit_status_of_the_command_is_the_scripts(self) -> None:
        self.assertEqual(self.run_script("sh", "-c", "exit 7").returncode, 7)

    def test_the_script_is_posix_shell_that_ends_in_exec(self) -> None:
        self.assertTrue(START.is_file(),
                        "deploy/forge/forge-start is missing")
        text = START.read_text(encoding="utf-8")
        self.assertIn(text.splitlines()[0],
                      ("#!/bin/sh", "#!/usr/bin/env sh"))
        lines = [line.strip() for line in text.splitlines()
                 if line.strip() and not line.strip().startswith("#")]
        self.assertEqual(lines[-1], 'exec "$@"')
        done = subprocess.run(["sh", "-n", str(START)],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)


class ForgeDatabaseTextTests(unittest.TestCase):
    """Scenario: Creating the database once (read)."""

    def text(self) -> str:
        self.assertTrue(DATABASE.is_file(),
                        "deploy/forge/forge-db is missing")
        return DATABASE.read_text(encoding="utf-8")

    def test_the_script_is_posix_shell(self) -> None:
        text = self.text()
        self.assertIn(text.splitlines()[0], ("#!/bin/sh", "#!/usr/bin/env sh"))
        done = subprocess.run(["sh", "-n", str(DATABASE)],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_each_creation_is_guarded_by_a_test_of_existence(self) -> None:
        text = self.text()
        self.assertRegex(text, r"(?i)\bCREATE\s+(ROLE|USER)\b")
        self.assertRegex(text, r"(?i)\bCREATE\s+DATABASE\b")
        self.assertIn("pg_roles", text)
        self.assertIn("pg_database", text)
        self.assertRegex(text, r"(?i)not\s+exists|\bif\b")

    def test_it_reads_the_password_when_it_runs(self) -> None:
        text = self.text()
        self.assertIn("FORGE_DB_PASSWORD", text)

    def test_it_names_the_role_and_the_database_forge(self) -> None:
        text = self.text()
        self.assertRegex(text, r"(?i)create\s+(role|user)\s+\"?forge\b")
        self.assertRegex(text, r"(?i)create\s+database\s+\"?forge\b")
        self.assertRegex(text, r"(?i)owner\s+\"?forge\b")


def postgres_binaries() -> Path | None:
    """The directory of a PostgreSQL server's programs, or None."""
    wanted = ("initdb", "pg_ctl", "psql")
    where = [None, *glob.glob("/usr/lib/postgresql/*/bin"),
             *glob.glob("/usr/pgsql-*/bin")]
    for directory in where:
        found = [shutil.which(name, path=directory) for name in wanted]
        if all(found):
            return Path(found[0]).parent
    return None


class ForgeDatabaseServerTests(unittest.TestCase):
    """Scenario: Creating the database once, against a PostgreSQL
    server of its own, started for the test; skipped without the
    server's programs. The script reaches the server as libpq does, by
    ``PGHOST`` and ``PGPORT``, with the administrator the settings
    name."""

    def setUp(self) -> None:
        self.bin = postgres_binaries()
        if self.bin is None:
            self.skipTest("PostgreSQL's initdb, pg_ctl and psql not found")
        self.tmp = Path(tempfile.mkdtemp(prefix="osdb-pg-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            self.port = str(probe.getsockname()[1])
        self.data = self.tmp / "data"
        self.env = {"PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
                    "HOME": str(self.tmp), "PGHOST": str(self.tmp),
                    "PGPORT": self.port, "PGCONNECT_TIMEOUT": "5"}
        subprocess.run([str(self.bin / "initdb"), "-D", str(self.data),
                        "-U", "postgres", "--auth=trust", "-E", "UTF8"],
                       env=self.env, check=True, capture_output=True)
        subprocess.run(
            [str(self.bin / "pg_ctl"), "-D", str(self.data), "-w", "-o",
             f"-c listen_addresses= -c port={self.port} "
             f"-c unix_socket_directories={self.tmp}",
             "-l", str(self.tmp / "log"), "start"],
            env=self.env, check=True, capture_output=True)
        self.addCleanup(subprocess.run, [
            str(self.bin / "pg_ctl"), "-D", str(self.data), "-m",
            "immediate", "stop"], env=self.env, capture_output=True)

    def sql(self, statement: str, check: bool = True) -> str:
        done = subprocess.run(
            [str(self.bin / "psql"), "-X", "-At", "-U", "postgres", "-d",
             "postgres", "-c", statement],
            env=self.env, capture_output=True, text=True)
        if check:
            self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.strip()

    def run_script(self, password: str = "forge-pw", **over: str
                   ) -> subprocess.CompletedProcess:
        self.assertTrue(DATABASE.is_file(),
                        "deploy/forge/forge-db is missing")
        env = {**self.env, "POSTGRES_USER": "postgres",
               "POSTGRES_PASSWORD": "unused", "POSTGRES_DB": "postgres",
               "FORGE_DB_PASSWORD": password, **over}
        return subprocess.run(["sh", str(DATABASE)], env=env,
                              capture_output=True, text=True, timeout=120)

    def role(self) -> str:
        return self.sql("select oid || '|' || rolcanlogin || '|' || "
                        "coalesce(rolpassword, '') from pg_authid "
                        "where rolname = 'forge'")

    def database(self) -> str:
        return self.sql("select oid || '|' || pg_get_userbyid(datdba) "
                        "from pg_database where datname = 'forge'")

    def test_the_first_run_makes_the_role_and_the_database(self) -> None:
        done = self.run_script()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        role = self.role().split("|")
        self.assertEqual(role[1], "true", "the role cannot sign in")
        self.assertTrue(role[2], "the role has no password")
        self.assertTrue(self.database().endswith("|forge"))

    def test_the_second_run_succeeds_and_changes_nothing(self) -> None:
        self.assertEqual(self.run_script().returncode, 0)
        before = (self.role(), self.database())
        done = self.run_script(password="another-password")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual((self.role(), self.database()), before)

    def test_a_role_that_exists_keeps_its_password(self) -> None:
        self.sql("create role forge login password 'old-password'")
        before = self.role()
        done = self.run_script()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.role(), before)
        self.assertTrue(self.database().endswith("|forge"))

    def test_a_database_that_exists_keeps_its_owner(self) -> None:
        self.sql("create database forge")
        before = self.database()
        done = self.run_script()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.database(), before)
        self.assertTrue(self.role())

    def test_a_password_with_quotes_is_stored(self) -> None:
        done = self.run_script(password="o'hara \"x\" $y \\z")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertTrue(self.role().split("|")[2])

    def test_an_unreachable_server_fails_the_script(self) -> None:
        done = self.run_script(PGHOST=str(self.tmp / "nowhere"))
        self.assertNotEqual(done.returncode, 0)


class ForgeSetupTests(unittest.TestCase):
    """Scenario: The set-up script."""

    def text(self) -> str:
        self.assertTrue(SETUP.is_file(),
                        "deploy/forge/forge-setup is missing")
        return SETUP.read_text(encoding="utf-8")

    def test_the_script_is_posix_shell(self) -> None:
        text = self.text()
        self.assertIn(text.splitlines()[0], ("#!/bin/sh", "#!/usr/bin/env sh"))
        done = subprocess.run(["sh", "-n", str(SETUP)],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_it_creates_the_admin_only_when_it_is_missing(self) -> None:
        text = self.text()
        create = re.search(r"admin\s+user\s+create", text)
        listing = re.search(r"admin\s+user\s+list", text)
        self.assertIsNotNone(create, "the script creates no admin")
        self.assertIsNotNone(listing, "the script does not look for it")
        self.assertLess(listing.start(), create.start())
        self.assertIn("orgsyndb", text)
        self.assertIn("ORGSYNDB_FORGE_PASSWORD", text)
        self.assertRegex(text, r"--admin")

    def test_it_adds_the_source_when_missing_and_updates_it_otherwise(
            self) -> None:
        text = self.text()
        add = re.search(r"admin\s+auth\s+add-oauth", text)
        update = re.search(r"admin\s+auth\s+update-oauth", text)
        listing = re.search(r"admin\s+auth\s+list", text)
        self.assertIsNotNone(add, "the script adds no source")
        self.assertIsNotNone(update, "the script updates no source")
        self.assertIsNotNone(listing, "the script does not look for it")
        self.assertLess(listing.start(), add.start())
        self.assertLess(listing.start(), update.start())

    def test_the_source_is_the_lab_with_its_discovery_url(self) -> None:
        text = self.text()
        self.assertRegex(text, r"(--name[= ]|\bname=)['\"]?lab\b")
        self.assertRegex(text, r"openidConnect")
        self.assertRegex(
            text, r"ORGSYNDB_APP_INTERNAL_URL[^\n]*?/lab/o/\.well-known/"
                  r"openid-configuration")
        self.assertRegex(text, r"--key[= ]['\"]?forgejo\b")
        self.assertIn("ORGSYNDB_FORGE_CLIENT_SECRET", text)
        for scope in ("openid", "profile", "email"):
            with self.subTest(scope=scope):
                self.assertRegex(text, rf"--scopes?[^\n]*\b{scope}\b")

    def test_the_secrets_are_read_from_the_environment(self) -> None:
        text = self.text()
        self.assertNotRegex(text, r"--secret[= ]['\"]?[A-Za-z0-9]{6,}")
        self.assertNotRegex(text, r"--password[= ]['\"]?[A-Za-z0-9]{6,}")


def cache_headers(text: str) -> list[tuple[str, list[str]]]:
    """The Cache-Control header directives of the Caddyfile TEXT, each
    with the opening lines of the blocks that enclose it."""
    stack: list[str] = []
    found = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith("{"):
            stack.append(line)
        elif line == "}":
            stack.pop()
        elif re.match(r"header\b.*Cache-Control", line):
            found.append((line, list(stack)))
    return found


class CaddyfileTests(unittest.TestCase):
    """Scenario: Caddyfile (Forgejo's route)."""

    def text(self) -> str:
        return CADDYFILE.read_text(encoding="utf-8")

    def test_git_is_forwarded_to_forgejo_with_the_prefix_taken_off(
            self) -> None:
        text = self.text()
        self.assertRegex(text, r"handle_path\s+/git/\*\s*\{[^}]*"
                               r"reverse_proxy[^}\n]*forge:3000")
        self.assertIn("ORGSYNDB_FORGE_UPSTREAM", text)

    def test_the_upstream_can_be_set_and_defaults_to_forge(self) -> None:
        self.assertRegex(self.text(),
                         r"\{\$ORGSYNDB_FORGE_UPSTREAM:forge:3000\}")

    def test_git_without_a_slash_redirects_to_git(self) -> None:
        self.assertRegex(self.text(), r"handle\s+/git\s*\{[^}]*redir[^}\n]*"
                                      r"/git/")

    def test_the_lab_routes_stay(self) -> None:
        text = self.text()
        self.assertIn("handle /lab/*", text)
        self.assertLess(text.index("/lab/collection/manifest*"),
                        text.index("handle /lab/*"))
        self.assertRegex(text, r"admin\s+off")

    def test_cache_control_is_set_on_every_response_but_forgejos(
            self) -> None:
        """Requirement: Web server and Compose file (the header on every
        response but Forgejo's)."""
        text = self.text()
        found = cache_headers(text)
        self.assertTrue(found, "no Cache-Control header is set")
        for line, enclosing in found:
            with self.subTest(line=line, within=enclosing[-1:]):
                self.assertIn('"no-cache"', line)
                self.assertFalse(
                    any("/git" in opening for opening in enclosing),
                    "Forgejo's route sets Cache-Control")
        site_wide = [line for line, enclosing in found
                     if len(enclosing) == 1]
        for line in site_wide:
            with self.subTest(site_wide=line):
                self.assertRegex(line, r"header\s+@\S+")
                self.assertRegex(text, r"not\s+path\s+/git")

    @unittest.skipIf(shutil.which("caddy") is None, "caddy not found")
    def test_caddy_adapts_the_file(self) -> None:
        done = subprocess.run(["caddy", "adapt", "--adapter", "caddyfile",
                               "--config", str(CADDYFILE)],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("/git/*", done.stdout)
        self.assertIn("strip_path_prefix", done.stdout)
        self.assertIn("forge:3000", done.stdout)
        self.assertLess(done.stdout.index("/lab/collection/manifest*"),
                        done.stdout.index('"/lab/*"'))


class ApplicationImageTests(unittest.TestCase):
    """Scenario: Image inputs (the command's order)."""

    def command(self) -> str:
        text = DOCKERFILE.read_text(encoding="utf-8")
        return text[text.rindex("CMD"):]

    def test_the_command_runs_forge_client_before_the_server(self) -> None:
        command = self.command()
        for name in ("migrate", "demo_data", "forge_client", "gunicorn"):
            with self.subTest(name=name):
                self.assertIn(name, command)
        self.assertLess(command.index("migrate"), command.index("demo_data"))
        self.assertLess(command.index("demo_data"),
                        command.index("forge_client"))
        self.assertLess(command.index("forge_client"),
                        command.index("gunicorn"))

    def test_forge_client_is_a_step_that_must_succeed(self) -> None:
        self.assertRegex(self.command(),
                         r"manage\.py forge_client\s*\\?\s*&&")

    def test_the_server_still_replaces_the_shell(self) -> None:
        self.assertRegex(self.command(), r"exec\s+gunicorn")


class EnvExampleTests(unittest.TestCase):
    """Requirement: Forgejo (the example settings)."""

    def test_the_forge_settings_are_set(self) -> None:
        env = parse_env(ENV_EXAMPLE)
        for key in FORGE_SETTINGS:
            with self.subTest(key=key):
                self.assertIn(key, env)
                self.assertTrue(env[key], f"{key} is empty")

    def test_the_address_is_a_web_address(self) -> None:
        url = urlsplit(parse_env(ENV_EXAMPLE).get("ORGSYNDB_URL", ""))
        self.assertIn(url.scheme, ("http", "https"))
        self.assertTrue(url.hostname)

    def test_the_forge_address_is_the_service_by_default(self) -> None:
        self.assertEqual(parse_env(ENV_EXAMPLE).get("ORGSYNDB_FORGE_URL"),
                         "http://forge:3000/api/v1")

    def test_each_secret_says_how_to_generate_it(self) -> None:
        for key in ("ORGSYNDB_OIDC_KEY", "ORGSYNDB_FORGE_CLIENT_SECRET",
                    "ORGSYNDB_FORGE_PASSWORD", "FORGE_DB_PASSWORD"):
            with self.subTest(key=key):
                self.assertRegex(comment_above(ENV_EXAMPLE, key),
                                 r"(?i)generat")

    def test_the_key_command_makes_base64(self) -> None:
        comment = comment_above(ENV_EXAMPLE, "ORGSYNDB_OIDC_KEY")
        self.assertIn("base64", comment)
        self.assertRegex(comment, r"(?i)openssl|jwcrypto|cryptography")

    def test_the_hosts_include_app(self) -> None:
        """Requirement: Web server and Compose file (`app` among the
        hosts)."""
        hosts = [host.strip() for host in parse_env(ENV_EXAMPLE).get(
            "ORGSYNDB_ALLOWED_HOSTS", "").split(",")]
        self.assertIn("app", hosts)

    def test_the_demo_flag_is_still_commented_out(self) -> None:
        self.assertIn("#ORGSYNDB_DEMO=false",
                      ENV_EXAMPLE.read_text().splitlines())


if __name__ == "__main__":
    unittest.main()
