#!/usr/local/bin/python
"""Give each container conversion a writable, isolated LibreOffice profile."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile


with tempfile.TemporaryDirectory(prefix="ksrf-lo-profile-") as profile:
    environment = os.environ.copy()
    environment["XDG_CACHE_HOME"] = str(Path(profile) / "cache")
    environment["XDG_CONFIG_HOME"] = str(Path(profile) / "config")
    result = subprocess.run(
        ["/usr/bin/soffice", "-env:UserInstallation=" + Path(profile).as_uri(), *sys.argv[1:]],
        env=environment,
    )
raise SystemExit(result.returncode)
