"""Record and verify the exact distributions passed from CI to publication."""

import argparse
import configparser
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def package_version():
    config = configparser.ConfigParser()
    config.read(ROOT / "setup.cfg")
    version = config["metadata"]["version"]
    recipe = (ROOT / "conda-recipe/meta.yaml").read_text()
    if f'{{% set version = "{version}" %}}' not in recipe:
        raise ValueError("Python and Conda versions differ")
    return version


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(directory, source):
    if not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("Source must be a full Git commit ID")
    version = package_version()
    expected = {
        f"vscode_hpc-{version}-py3-none-any.whl",
        f"vscode_hpc-{version}.tar.gz",
    }
    packages = list(directory.glob(f"vscode-hpc-{version}-*.conda"))
    if len(packages) != 1:
        raise ValueError("Expected exactly one Conda distribution")
    expected.add(packages[0].name)
    actual = {p.name for p in directory.iterdir() if p.name != "manifest.json"}
    if actual != expected:
        raise ValueError(f"Unexpected distribution set: {actual}; expected {expected}")
    return {
        "source": source, "version": version,
        "sha256": {name: digest(directory / name) for name in sorted(expected)},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["version", "record", "verify"])
    parser.add_argument("--directory", type=Path, default=Path("dist"))
    parser.add_argument("--source")
    parser.add_argument("--tag")
    args = parser.parse_args()
    if args.command == "version":
        print(package_version())
        return
    if not args.source:
        parser.error("--source is required")
    calculated = manifest(args.directory, args.source)
    if args.tag and args.tag != "v" + calculated["version"]:
        raise ValueError("Tag and package version differ")
    path = args.directory / "manifest.json"
    if args.command == "record":
        with path.open("x") as stream:
            stream.write(json.dumps(calculated, indent=2) + "\n")
    elif json.loads(path.read_text()) != calculated:
        raise ValueError("Distribution identity or checksums differ from the CI manifest")
    print(f"{args.command}: {calculated['version']} at {args.source}")


if __name__ == "__main__":
    main()
