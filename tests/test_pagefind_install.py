"""Offline verification and extraction of the Pagefind binary
(site-build)."""

import io
import os
import shutil
import tarfile
import tempfile
import unittest
from pathlib import Path

from pipeline_support import pipeline, sha256

BINARY = b"#!/bin/sh\necho fictitious search binary\n"


class PagefindInstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="orgsyndb pagefind "))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.dest = self.base / "dest dir"
        self.dest.mkdir()

    def tarball(self, member: tarfile.TarInfo,
                data: bytes | None = None) -> Path:
        path = self.base / "pagefind.tar.gz"
        with tarfile.open(path, "w:gz") as tar:
            tar.addfile(member, io.BytesIO(data) if data is not None
                        else None)
        return path

    def regular_tarball(self) -> Path:
        member = tarfile.TarInfo("pagefind")
        member.size, member.mode = len(BINARY), 0o644
        return self.tarball(member, BINARY)

    def outside(self) -> list[str]:
        """Entries next to dest/, other than the tarball and dest."""
        return sorted(p.name for p in self.base.iterdir()
                      if p.name not in ("pagefind.tar.gz", "dest dir"))

    def test_valid_tarball_installs_the_binary(self) -> None:
        """Scenario: Valid tarball installs the binary."""
        tarball = self.regular_tarball()
        result = pipeline().install_pagefind(
            tarball, sha256(tarball.read_bytes()), sha256(BINARY), self.dest)
        binary = self.dest / "pagefind"
        self.assertEqual(Path(result), binary)
        self.assertEqual(binary.read_bytes(), BINARY)
        self.assertTrue(os.access(binary, os.X_OK))

    def test_wrong_tarball_hash_is_refused(self) -> None:
        """Scenario: Wrong tarball hash."""
        tarball = self.regular_tarball()
        actual = sha256(tarball.read_bytes())
        expected = sha256(b"another tarball")
        with self.assertRaises(pipeline().PagefindError) as caught:
            pipeline().install_pagefind(tarball, expected, sha256(BINARY),
                                        self.dest)
        self.assertIn(expected, str(caught.exception))
        self.assertIn(actual, str(caught.exception))
        self.assertFalse((self.dest / "pagefind").exists())

    def test_wrong_binary_hash_is_refused(self) -> None:
        """Scenario: Wrong binary hash."""
        tarball = self.regular_tarball()
        with self.assertRaises(pipeline().PagefindError):
            pipeline().install_pagefind(
                tarball, sha256(tarball.read_bytes()),
                sha256(b"another binary"), self.dest)
        self.assertFalse((self.dest / "pagefind").exists())

    def test_symbolic_link_member_is_refused(self) -> None:
        """Scenario: Unsafe member is refused."""
        member = tarfile.TarInfo("pagefind")
        member.type = tarfile.SYMTYPE
        member.linkname = "../outside-target"
        tarball = self.tarball(member)
        before = self.outside()
        with self.assertRaises(pipeline().PagefindError):
            pipeline().install_pagefind(
                tarball, sha256(tarball.read_bytes()), sha256(BINARY),
                self.dest)
        self.assertFalse((self.dest / "pagefind").exists())
        self.assertEqual(self.outside(), before)
        self.assertFalse((self.base / "outside-target").exists())
