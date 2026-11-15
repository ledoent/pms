#!/usr/bin/env python3
# pylint: disable=print-used
"""Initialize a new isolated PMS evaluation database from the checked lock file."""

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="pms20_ui")
    parser.add_argument("--tests", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"pms20_[a-z0-9_]+", args.database):
        raise SystemExit("Database name must match pms20_[a-z0-9_]+")
    subprocess.run(["python3", str(ROOT / "scripts/assemble.py")], check=True)
    compose = ["docker", "compose", "-f", str(ROOT / "docker-compose.20dev.yml")]
    subprocess.run(compose + ["up", "-d", "db-prod-20"], check=True)
    query = subprocess.check_output(
        compose
        + [
            "exec",
            "-T",
            "db-prod-20",
            "psql",
            "-U",
            "odoo",
            "-d",
            "postgres",
            "-Atc",
            f"SELECT 1 FROM pg_database WHERE datname='{args.database}'",
        ],
        text=True,
    )
    if query.strip():
        raise SystemExit(
            f"{args.database} exists; choose another fresh synthetic database. "
            "Nothing was dropped."
        )
    modules = ",".join(json.loads((ROOT / "migration-lock.json").read_text()))
    command = compose + [
        "run",
        "--rm",
        "--no-deps",
        "odoo-prod-20",
        "odoo",
        "-d",
        args.database,
        f"--db-filter=^{args.database}$",
        "-i",
        modules,
        "--with-demo",
        "--stop-after-init",
    ]
    if args.tests:
        tags = ",".join("/" + m for m in modules.split(","))
        # Native browser evidence handles these two tours separately; the amd64
        # container's Chrome exits under ARM emulation on the original review host.
        command += [
            "--test-enable",
            f"--test-tags={tags},-hoot,-/pms_sale:TestPmsFrontend,-/pms_website_sale:TestWebsiteSaleCartRecovery",
        ]
    subprocess.run(command, check=True)
    print(f"Initialized {args.database}. UI service selects pms20_ui by default.")


if __name__ == "__main__":
    main()
