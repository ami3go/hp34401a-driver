#!/usr/bin/env python3
"""Build and validate the current rf_hp34401a RFDS release package.

The release number is derived from the package authorities instead of being
frozen in this script.  A build fails when driver/distribution versions drift,
when current history/review evidence is missing, or when quality gates fail.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_NAME = "rf_hp34401a"
EXCLUDED_PARTS = {
    ".git", ".venv", "__pycache__", ".pytest_cache", "build", "dist",
    "results", "htmlcov", ".mypy_cache", ".ruff_cache", "site",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".ttf", ".otf", ".woff", ".woff2", ".zip"}


def _read_driver_version(root: Path) -> str:
    text = (root / "rf_hp34401a" / "version.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    if not match:
        raise SystemExit("Cannot resolve __version__ from rf_hp34401a/version.py")
    return match.group(1)


def _read_distribution_version(root: Path) -> str:
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    project = text.split("[project.optional-dependencies]", 1)[0]
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', project, re.MULTILINE)
    if not match:
        raise SystemExit("Cannot resolve project.version from pyproject.toml")
    return match.group(1)


def _expected_distribution_version(release: str) -> str:
    match = re.fullmatch(r"(\d{2})\.(\d+)", release)
    if not match:
        raise SystemExit(f"Driver release {release!r} must use YY.N RFDS format")
    return f"{int(match.group(1))}.{int(match.group(2))}.0"


RELEASE = _read_driver_version(ROOT)
DIST_VERSION = _read_distribution_version(ROOT)
EXPECTED_DIST_VERSION = _expected_distribution_version(RELEASE)
if DIST_VERSION != EXPECTED_DIST_VERSION:
    raise SystemExit(
        f"Version drift: driver release {RELEASE} requires distribution "
        f"{EXPECTED_DIST_VERSION}, pyproject declares {DIST_VERSION}"
    )
ZIP_NAME = f"rf_hp34401a_v{RELEASE}.zip"


def run(command: list[str], cwd: Path) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def include(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if any(part in EXCLUDED_PARTS or part.endswith(".egg-info") for part in rel.parts):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES or path.name in {".coverage"}:
        return False
    return True


def validate_layout(root: Path) -> None:
    required = [
        "rf_hp34401a/library.py", "hp34401a_dmm", "api/public_api.yaml",
        "capability/capability_model.yaml", "config/schema.json", "config/schema.lock",
        "ai/hp34401a_ai_contract.yaml", "ai/hp34401a_ai_contract.lock",
        f"history/v{RELEASE}.md", f"review/v{RELEASE}_code_review.md",
        "examples/index.yaml", "scripts", "guide", "docs", "README.md", "pyproject.toml",
        "release/release_manifest.yaml", "release/sbom.json",
        "release/checksums.sha256", "release/requirements_traceability.csv",
        "release/compatibility_report.json", "release/provenance.json",
        "tests/conformance/driver_call_protocol_conformance.robot",
        "tests/conformance/data/keyword_inventory.yaml",
        "tests/conformance/data/protocol_vectors.yaml",
        "tests/conformance/data/exclusions.yaml",
        "tests/hil/verify_all_public_api_real_hardware.robot",
    ]
    missing = [item for item in required if not (root / item).exists()]
    if missing:
        raise SystemExit(f"Missing required release content: {missing}")
    if any(path.name == "src" and path.is_dir() for path in root.rglob("src")):
        raise SystemExit("A src/ directory is not permitted by this project profile")
    if len(list((root / "examples").glob("[0-9][0-9]_*.robot"))) < 10:
        raise SystemExit("At least ten numbered Robot examples are required")


def validate_zip(output: Path) -> None:
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        roots = {name.split("/", 1)[0] for name in names if name}
        if roots != {ROOT_NAME}:
            raise SystemExit(f"Invalid ZIP roots: {sorted(roots)}")
        forbidden = [
            name for name in names
            if "/src/" in f"/{name}" or Path(name).suffix.lower() in EXCLUDED_SUFFIXES
            or any(part in EXCLUDED_PARTS for part in Path(name).parts)
        ]
        if forbidden:
            raise SystemExit(f"ZIP contains forbidden content: {forbidden[:10]}")
        required = {
            f"{ROOT_NAME}/api/public_api.yaml",
            f"{ROOT_NAME}/capability/capability_model.yaml",
            f"{ROOT_NAME}/config/schema.json",
            f"{ROOT_NAME}/ai/hp34401a_ai_contract.yaml",
            f"{ROOT_NAME}/tests/conformance/data/keyword_inventory.yaml",
            f"{ROOT_NAME}/tests/hil/verify_all_public_api_real_hardware.robot",
            f"{ROOT_NAME}/release/release_manifest.yaml",
            f"{ROOT_NAME}/release/sbom.json",
            f"{ROOT_NAME}/release/checksums.sha256",
            f"{ROOT_NAME}/release/requirements_traceability.csv",
            f"{ROOT_NAME}/history/v{RELEASE}.md",
            f"{ROOT_NAME}/review/v{RELEASE}_code_review.md",
        }
        missing = sorted(required - set(names))
        if missing:
            raise SystemExit(f"ZIP is missing mandatory files: {missing}")


def generate_internal_checksums(root: Path) -> Path:
    destination = root / "release" / "checksums.sha256"
    lines: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or not include(path, root) or path == destination:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(root).as_posix()}")
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return destination


def _source_revision(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "UNKNOWN"


def update_provenance(root: Path) -> None:
    path = root / "release" / "provenance.json"
    payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    payload.update(
        {
            "schema_version": "1.0",
            "artifact": ZIP_NAME,
            "builder_environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
            },
            "source_revision": _source_revision(root),
            "status": "SOURCE_CANDIDATE",
        }
    )
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_zip(root: Path, output: Path) -> Path:
    with tempfile.TemporaryDirectory(prefix="rf_hp34401a_release_") as temp:
        staged = Path(temp) / ROOT_NAME
        shutil.copytree(
            root,
            staged,
            ignore=lambda directory, names: {
                name for name in names if not include(Path(directory) / name, root)
            },
        )
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(staged.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(staged.parent).as_posix())
    validate_zip(output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--skip-quality-gates", action="store_true")
    args = parser.parse_args()
    root = ROOT
    output_dir = (args.output_dir or root.parent).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    validate_layout(root)
    update_provenance(root)
    generate_internal_checksums(root)

    run([sys.executable, "scripts/validate_ai_contract.py"], root)
    run([sys.executable, "scripts/validate_call_protocol_conformance.py"], root)
    run([sys.executable, "scripts/validate_real_hardware_api_suite.py"], root)
    run([sys.executable, "scripts/validate_hil_coverage_state.py"], root)
    if not args.skip_quality_gates:
        run(
            [
                sys.executable, "-m", "pytest",
                "--cov=rf_hp34401a", "--cov=hp34401a_dmm", "--cov-fail-under=80",
            ],
            root,
        )
        run([sys.executable, "scripts/run_call_protocol_conformance.py"], root)
        run([sys.executable, "-m", "robot", "--outputdir", "results/robot", "tests/robot"], root)
        run([sys.executable, "-m", "robot", "--exclude", "hardware", "--outputdir", "results/examples", "examples"], root)
        run([sys.executable, "-m", "robot.libdoc", "rf_hp34401a.Hp34401ALibrary", "generated/libdoc/Hp34401ALibrary.html"], root)
        run([sys.executable, "-m", "robot.libdoc", "rf_hp34401a.Hp34401ALibrary", "generated/libdoc/Hp34401ALibrary.xml"], root)
        run([sys.executable, "-m", "mkdocs", "build", "--strict"], root)

    shutil.rmtree(root / "dist", ignore_errors=True)
    (root / "dist").mkdir()
    run([sys.executable, "-m", "pip", "wheel", "--no-build-isolation", "--no-deps", "-w", "dist", "."], root)
    run([
        sys.executable,
        "-c",
        "from setuptools.build_meta import build_sdist; print(build_sdist('dist'))",
    ], root)
    wheel = next((root / "dist").glob(f"rf_hp34401a-{DIST_VERSION}-*.whl"), None)
    sdist = next((root / "dist").glob(f"rf_hp34401a-{DIST_VERSION}.tar.gz"), None)
    if wheel is None or sdist is None:
        raise SystemExit(
            f"Expected {DIST_VERSION} wheel and source distribution were not built"
        )

    generate_internal_checksums(root)
    output = output_dir / ZIP_NAME
    output.unlink(missing_ok=True)
    build_zip(root, output)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    checksum = output.with_suffix(output.suffix + ".sha256")
    checksum.write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    print(f"Built {output}\nSHA-256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
