"""Measure a real Docker build and inspect its resulting local image."""

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--target")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    command = ["docker", "build", "--file", str(args.file), "--tag", args.tag]
    if args.target:
        command += ["--target", args.target]
    command.append(".")
    started = time.perf_counter()
    subprocess.run(command, check=True)
    elapsed = time.perf_counter() - started
    image = json.loads(subprocess.check_output(["docker", "image", "inspect", args.tag], text=True))[0]
    record = {"command": command, "elapsed_build_seconds": elapsed, "size_bytes": image["Size"],
              "image_id": image["Id"], "os": image["Os"], "architecture": image["Architecture"],
              "dockerfile_sha256": hashlib.sha256(args.file.read_bytes()).hexdigest(),
              "cache_policy": "Normal Docker layer cache; base layers may already be available. Not a guaranteed cold build."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
