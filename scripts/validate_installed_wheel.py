#!/usr/bin/env python3
"""Install the built wheel into an isolated venv and validate plugin resources."""

from __future__ import annotations

import os
import subprocess
import tempfile
import venv
from pathlib import Path


def _venv_python(root: Path) -> Path:
    if os.name == "nt":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def main() -> int:
    package_root = Path(__file__).resolve().parents[1]
    wheels = sorted((package_root / "dist").glob("rf_hp34401a-*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"Expected exactly one rf_hp34401a wheel, found {len(wheels)}")
    wheel = wheels[0]

    with tempfile.TemporaryDirectory(prefix="rf_hp34401a_wheel_") as tmp:
        env = Path(tmp) / "venv"
        # Do not inherit the CI/source-checkout site-packages. The purpose of
        # this gate is to prove that the built wheel is self-describing and its
        # RFDS plugin data files resolve without help from an editable install.
        venv.EnvBuilder(with_pip=True, system_site_packages=False).create(env)
        python = _venv_python(env)
        subprocess.run(
            [str(python), "-m", "pip", "install", "--no-deps", str(wheel)],
            check=True,
        )
        code = r'''
from pathlib import Path
from importlib.metadata import entry_points
from rf_hp34401a.plugin import Hp34401APluginProvider

matches = [
    ep for ep in entry_points(group="rfds.drivers")
    if ep.name == "rf_hp34401a"
]
assert len(matches) == 1, matches
provider = matches[0].load()
assert provider is Hp34401APluginProvider

descriptor = provider.get_descriptor()
for name, path in descriptor["resolved_artifacts"].items():
    assert Path(path).is_file(), f"{name}: {path}"
print("Installed wheel plugin/resource validation PASS")
'''
        subprocess.run([str(python), "-c", code], check=True, cwd=tmp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
