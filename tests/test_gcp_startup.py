"""Exercise the GCP process contract without Docker or cloud access."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CloudRunStartup(unittest.TestCase):
    def test_port_and_no_startup_migration(self):
        with tempfile.TemporaryDirectory() as directory:
            bin_dir = Path(directory)
            capture = bin_dir / "args"
            for name, body in {
                "uvicorn": 'printf "%s\\n" "$@" > "$CAPTURE"',
                "alembic": "exit 99",
            }.items():
                executable = bin_dir / name
                executable.write_text("#!/bin/sh\n" + body + "\n")
                executable.chmod(0o755)
            for port in (None, "9097"):
                with self.subTest(port=port):
                    env = {
                        **os.environ,
                        "PATH": f"{bin_dir}:/usr/bin:/bin",
                        "CAPTURE": str(capture),
                        "LOG_LEVEL": "warning",
                    }
                    env.pop("PORT", None)
                    if port is not None:
                        env["PORT"] = port
                    subprocess.run(
                        ["sh", str(ROOT / "backend/scripts/cloud-run.sh")],
                        env=env,
                        check=True,
                    )
                    self.assertEqual(
                        capture.read_text().splitlines(),
                        [
                            "app.main:app",
                            "--host",
                            "0.0.0.0",
                            "--port",
                            port or "8080",
                            "--log-level",
                            "warning",
                        ],
                    )


if __name__ == "__main__":
    unittest.main()
