#!/usr/bin/env python3
"""Freeze non-ignored backend sources for a reproducible, uncommitted local release."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
paths = subprocess.check_output(
    ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", "backend"],
    cwd=root,
).decode().split("\0")
staging = Path(tempfile.mkdtemp(prefix="peach-backend-"))
hash_value = hashlib.sha256()
for relative in sorted(set(p for p in paths if p)):
    source = root / relative
    if not source.is_file():
        continue
    if source.is_symlink():
        raise SystemExit("Symlinks are not accepted in local release snapshots")
    data = source.read_bytes()
    mode = source.stat().st_mode & 0o777
    hash_value.update(relative.encode() + b"\0" + str(mode).encode() + b"\0" + data + b"\0")
    target = staging / Path(relative).relative_to("backend")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
print(json.dumps({"directory": str(staging), "tag": "local-" + hash_value.hexdigest()}))
