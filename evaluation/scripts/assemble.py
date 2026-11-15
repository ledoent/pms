#!/usr/bin/env python3
# pylint: disable=print-used
"""Assemble immutable PMS migration or corrected sources; no GoTime checkout writes."""

import argparse
import hashlib
import io
import json
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def archive(repository, sha, module, destination):
    payload = subprocess.check_output(
        ["git", "-C", str(repository), "archive", sha, module]
    )
    with tarfile.open(fileobj=io.BytesIO(payload)) as stream:
        stream.extractall(destination, filter="data")


def fetch(repo, sha):
    target = ROOT / "deps/git-cache" / repo.replace("/", "--")
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "init", "--bare", str(target)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(target),
                "remote",
                "add",
                "origin",
                f"https://github.com/{repo}.git",
            ],
            check=True,
        )
    if subprocess.run(
        ["git", "-C", str(target), "cat-file", "-e", f"{sha}^{{commit}}"],
        stderr=subprocess.DEVNULL,
    ).returncode:
        subprocess.run(
            ["git", "-C", str(target), "fetch", "--depth=1", "origin", sha], check=True
        )
    actual = subprocess.check_output(
        ["git", "-C", str(target), "rev-parse", sha], text=True
    ).strip()
    if actual != sha:
        raise ValueError(f"SHA mismatch: {actual} != {sha}")
    return target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--migration-only", action="store_true")
    args = parser.parse_args()
    lock = json.loads((ROOT / "evaluation-lock.json").read_text())
    output = ROOT / ("addons" if args.migration_only else "addons-fixed")
    output.mkdir(exist_ok=True)
    modules = dict(lock["migrations"])
    if not args.migration_only:
        modules.update(lock["corrections"])
    modules.update(lock["dependencies"])
    records = {}
    for module, pin in modules.items():
        target = output / module
        if target.exists():
            shutil.rmtree(
                target
            )  # only this generated addon below the fixed output root
        if "repo" in pin:
            archive(fetch(pin["repo"], pin["sha"]), pin["sha"], module, output)
        else:
            wheel = ROOT / "deps" / pin["wheel"]
            if not wheel.exists():
                metadata = json.load(
                    urllib.request.urlopen(
                        f"https://pypi.org/pypi/{pin['package']}/{pin['version']}/json"
                    )
                )
                url = next(
                    entry["url"]
                    for entry in metadata["urls"]
                    if entry["filename"] == pin["wheel"]
                )
                with urllib.request.urlopen(url) as response:
                    wheel.write_bytes(response.read())
            if hashlib.sha256(wheel.read_bytes()).hexdigest() != pin["sha256"]:
                raise ValueError("Wheel SHA256 mismatch")
            prefix = f"odoo/addons/{module}/"
            with zipfile.ZipFile(wheel) as stream:
                for name in stream.namelist():
                    if not name.startswith(prefix) or name.endswith("/"):
                        continue
                    relative = Path(name.removeprefix(prefix))
                    if ".." in relative.parts:
                        raise ValueError(name)
                    path = target / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(stream.read(name))
        digest = hashlib.sha256()
        for path in sorted(target.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                digest.update(
                    str(path.relative_to(target)).encode() + b"\0" + path.read_bytes()
                )
        records[module] = {"source": pin, "tree_sha256": digest.hexdigest()}
    (output / "source-manifest.json").write_text(json.dumps(records, indent=2) + "\n")
    print(f"Assembled {len(records)} exact sources into {output}")


if __name__ == "__main__":
    main()
