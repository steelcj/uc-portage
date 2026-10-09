"""Checksums that see content, not line endings.

A Windows checkout with core.autocrlf turns every LF into CRLF. If the
state file recorded raw bytes, every text file would then look edited
locally. Text is therefore normalised to LF before hashing; binary files
are hashed as they are. A file is text when it holds no NUL byte, the
same heuristic git uses.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def is_text(data: bytes) -> bool:
    return b"\0" not in data


def normalise(data: bytes) -> bytes:
    """CRLF and lone CR become LF in text; binary data is unchanged."""
    if not is_text(data):
        return data
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(normalise(data)).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())
