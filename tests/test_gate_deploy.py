"""Tests of the files the gate adds to the deployment (container-
deployment: Web server and Compose file, Forgejo, Gate): the Caddyfile's
check path, Forgejo's disabled features, what ``forge-setup`` sets up for
the collection's repository and its gate, and the example settings."""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_forge_deploy import (CADDYFILE, COMPOSE, DEPLOY, ENV_EXAMPLE,
                               SERVICES, SETUP, comment_above,
                               forgejo_setting, parse_env, service_block)

GATE = DEPLOY / "forge" / "gate"


class CaddyfileTests(unittest.TestCase):
    """Scenario: Caddyfile (`/lab/collection/check*`)."""

    def text(self) -> str:
        return CADDYFILE.read_text(encoding="utf-8")

    def test_the_check_path_answers_404_ahead_of_the_lab_route(
            self) -> None:
        text = self.text()
        self.assertRegex(
            text, r"handle\s+/lab/collection/check\*\s*\{[^}]*"
                  r"respond[^}\n]*\b404\b")
        self.assertLess(text.index("/lab/collection/check*"),
                        text.index("handle /lab/*"))

    def test_the_manifest_path_still_answers_404(self) -> None:
        """Scenario: Caddyfile (`/lab/collection/manifest*`)."""
        self.assertRegex(
            self.text(), r"handle\s+/lab/collection/manifest\*\s*\{[^}]*"
                         r"respond[^}\n]*\b404\b")

    def test_nothing_routes_to_the_check_server(self) -> None:
        """Requirement: Gate (no port is published and Caddy routes
        nothing there)."""
        self.assertNotIn("8091", self.text())

    @unittest.skipIf(shutil.which("caddy") is None, "caddy not found")
    def test_caddy_adapts_the_file(self) -> None:
        done = subprocess.run(
            ["caddy", "adapt", "--adapter", "caddyfile", "--config",
             str(CADDYFILE)], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("/lab/collection/check*", done.stdout)
        self.assertLess(done.stdout.index("/lab/collection/check*"),
                        done.stdout.index('"/lab/*"'))
        between = done.stdout[done.stdout.index("/lab/collection/check*"):
                              done.stdout.index('"/lab/*"')]
        self.assertRegex(between, r'"status_code":\s*"?404')


class ComposeTextTests(unittest.TestCase):
    """Requirement: Forgejo (`USER_DISABLED_FEATURES`), Gate."""

    def test_forgejo_keeps_the_lab_user_names(self) -> None:
        """Scenario: Forgejo's service (`USER_DISABLED_FEATURES`
        `change_username,deletion`)."""
        block = service_block("forge")
        found = re.search(
            r'FORGEJO__admin__USER_DISABLED_FEATURES:\s*"?([^"\n]+)"?',
            block)
        self.assertIsNotNone(found, "the setting is not in the service")
        self.assertEqual(
            {name.strip() for name in found.group(1).split(",")},
            {"change_username", "deletion"})

    def test_the_setting_is_not_substituted_from_the_shell(self) -> None:
        """Requirement: Forgejo (none substituted by Compose from the
        shell)."""
        self.assertNotIn("${", service_block("forge"))

    def test_no_port_of_the_check_server_is_published(self) -> None:
        """Requirement: Gate (no port is published)."""
        self.assertNotIn("8091", COMPOSE.read_text(encoding="utf-8"))

    def test_the_forge_and_the_builder_read_the_settings(self) -> None:
        """Requirement: Gate (the hook runs in `forge`, the check server
        in `builder`, both reading `orgsyndb.env`)."""
        for name in ("forge", "builder"):
            with self.subTest(service=name):
                self.assertRegex(service_block(name),
                                 r"(?m)^    env_file: orgsyndb\.env$")

    def test_the_hook_is_mounted_into_the_forge(self) -> None:
        """Requirement: Forgejo (`forge-setup` links `deploy/forge/gate`;
        the directory is mounted read-only)."""
        self.assertTrue(GATE.is_file(), "deploy/forge/gate is missing")
        self.assertRegex(service_block("forge"),
                         r"(?m)^      - \./forge[^:\n]*:[^:\n]+:ro$")


class ComposeConfigTests(unittest.TestCase):
    """Scenario: Forgejo's service (`docker compose config`)."""

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

    def test_the_services_are_the_same(self) -> None:
        config, _example = self.config()
        self.assertEqual(sorted(config["services"]), SERVICES)

    def test_forgejo_disables_renaming_and_deleting(self) -> None:
        config, _example = self.config()
        value = forgejo_setting(config["services"]["forge"]["environment"],
                                "USER_DISABLED_FEATURES")
        self.assertEqual(
            {name.strip() for name in (value or "").split(",")},
            {"change_username", "deletion"})

    def test_the_forge_and_the_builder_get_the_gate_token(self) -> None:
        config, example = self.config()
        for name in ("forge", "builder"):
            with self.subTest(service=name):
                env = config["services"][name]["environment"]
                self.assertEqual(env["ORGSYNDB_GATE_TOKEN"],
                                 example["ORGSYNDB_GATE_TOKEN"])

    def test_the_builder_publishes_no_port(self) -> None:
        config, _example = self.config()
        self.assertFalse(config["services"]["builder"].get("ports"))
        for service in config["services"].values():
            for port in service.get("ports", []):
                self.assertNotIn(8091, (port.get("target"),
                                        port.get("published")))


class ForgeSetupTests(unittest.TestCase):
    """Scenario: The set-up script (the organisation, the team, the
    repository, the protection, the group mapping and the gate)."""

    def text(self) -> str:
        self.assertTrue(SETUP.is_file(),
                        "deploy/forge/forge-setup is missing")
        return SETUP.read_text(encoding="utf-8")

    def test_it_is_still_posix_shell(self) -> None:
        self.text()
        done = subprocess.run(["sh", "-n", str(SETUP)],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_the_organisation_lab_is_public_and_made_when_missing(
            self) -> None:
        text = self.text()
        self.assertRegex(text, r"orgs/lab\b")
        self.assertRegex(text, r"/orgs[\"'\s]")
        self.assertRegex(text, r"(?i)visibility\W{1,6}public")

    def test_the_team_authors_has_write_access(self) -> None:
        text = self.text()
        self.assertRegex(text, r"orgs/lab/teams")
        self.assertRegex(text, r"\bauthors\b")
        self.assertRegex(text, r"permission\W{1,6}write")

    def test_the_team_is_scoped_to_the_repository_alone(self) -> None:
        text = self.text()
        self.assertRegex(text, r"includes_all_repositories\W{1,6}false")
        self.assertRegex(text, r"teams/\S*?/repos/lab/collection")

    def test_the_repository_is_public_with_main_as_its_branch(
            self) -> None:
        text = self.text()
        self.assertRegex(text, r"orgs/lab/repos")
        self.assertRegex(text, r"\bcollection\b")
        self.assertRegex(text, r"private\W{1,6}false")
        self.assertRegex(text, r"default_branch\W{1,6}main")

    def test_main_is_protected(self) -> None:
        text = self.text()
        self.assertRegex(text, r"repos/lab/collection/branch_protections")
        self.assertRegex(text, r"rule_name\W{1,6}main")

    def test_the_source_maps_the_groups_claim_to_the_team(self) -> None:
        text = self.text()
        self.assertRegex(text, r"--group-claim-name[= ]['\"]?groups\b")
        self.assertRegex(text, r"--group-team-map(?!-)")
        self.assertRegex(
            text, r'\{\s*\\?"authors\\?"\s*:\s*\{\s*\\?"lab\\?"\s*:\s*'
                  r'\[\s*\\?"authors\\?"\s*\]\s*\}\s*\}')
        self.assertRegex(text, r"--group-team-map-removal")

    def test_the_source_is_still_added_or_updated(self) -> None:
        """Requirement: Forgejo (adds or updates the source)."""
        text = self.text()
        self.assertRegex(text, r"admin\s+auth\s+add-oauth")
        self.assertRegex(text, r"admin\s+auth\s+update-oauth")

    def test_the_gate_is_linked_into_the_pre_receive_hooks(self) -> None:
        text = self.text()
        self.assertRegex(text,
                         r"lab/collection\.git/hooks/pre-receive\.d")
        self.assertIn("orgsyndb-gate", text)
        self.assertRegex(text, r"\bln\s+-[a-z]*s")
        self.assertRegex(text, r"forge/gate\b|\bgate\b")

    def test_the_secrets_are_still_read_from_the_environment(self) -> None:
        text = self.text()
        self.assertNotRegex(text, r"--secret[= ]['\"]?[A-Za-z0-9]{6,}")
        self.assertIn("ORGSYNDB_FORGE_PASSWORD", text)


class EnvExampleTests(unittest.TestCase):
    """Requirement: Forgejo (the example settings), Gate."""

    def test_the_gate_token_is_set(self) -> None:
        env = parse_env(ENV_EXAMPLE)
        self.assertIn("ORGSYNDB_GATE_TOKEN", env)
        self.assertTrue(env["ORGSYNDB_GATE_TOKEN"])

    def test_the_gate_token_says_how_to_generate_it(self) -> None:
        comment = comment_above(ENV_EXAMPLE, "ORGSYNDB_GATE_TOKEN")
        self.assertRegex(comment, r"(?i)generat")
        self.assertRegex(comment, r"secrets\.|openssl")

    def test_the_gate_token_is_not_the_builders(self) -> None:
        """Requirement: Gate (two tokens, two secrets)."""
        env = parse_env(ENV_EXAMPLE)
        self.assertNotEqual(env["ORGSYNDB_GATE_TOKEN"],
                            env["ORGSYNDB_BUILDER_TOKEN"])

    def test_the_collection_is_fetched_from_forgejo(self) -> None:
        self.assertEqual(
            parse_env(ENV_EXAMPLE).get("ORGSYNDB_COLLECTION_REPO"),
            "http://forge:3000/lab/collection.git")

    def test_the_comment_above_the_repository_names_forgejo(self) -> None:
        comment = comment_above(ENV_EXAMPLE, "ORGSYNDB_COLLECTION_REPO")
        self.assertRegex(comment, r"(?i)forgejo|forge-setup")

    def test_the_other_gate_settings_are_listed(self) -> None:
        """Requirement: Gate (`ORGSYNDB_GATE_URL`, `ORGSYNDB_CHECK_URL`
        and `ORGSYNDB_GATE_TIMEOUT`, set or commented out)."""
        text = ENV_EXAMPLE.read_text(encoding="utf-8")
        for name in ("ORGSYNDB_GATE_URL", "ORGSYNDB_CHECK_URL",
                     "ORGSYNDB_GATE_TIMEOUT"):
            with self.subTest(name=name):
                self.assertRegex(text, rf"(?m)^#?{name}=")


if __name__ == "__main__":
    unittest.main()
