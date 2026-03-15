from __future__ import annotations

import argparse
import re
import subprocess
import time
from pathlib import Path


def _run_once(config_path: str) -> tuple[int, str]:
    command = [
        "uv",
        "run",
        "--project",
        "domains/discord/ingestion",
        "discord-etl",
        "backfill-profiles-safe",
        "--config",
        config_path,
        "--json-log",
        "--max-steps",
        "1",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode, output


def _extract_wait_seconds(output: str, default_wait: int) -> int:
    match = re.search(r"wait_sec=(\d+)", output)
    if not match:
        return default_wait
    return max(int(match.group(1)), 1)


def _log(message: str) -> None:
    print(message, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="domains/discord/ingestion/config.backfill-053.yaml",
        help="Path to backfill config file",
    )
    parser.add_argument("--success-interval-sec", type=int, default=60)
    parser.add_argument("--default-429-wait-sec", type=int, default=900)
    parser.add_argument("--error-wait-sec", type=int, default=1800)
    parser.add_argument("--max-cycles", type=int, default=0)
    args = parser.parse_args()

    config_path = str(Path(args.config))
    cycles = 0

    while True:
        if args.max_cycles > 0 and cycles >= args.max_cycles:
            _log(f"worker stopped: reached max_cycles={args.max_cycles}")
            return 0

        code, output = _run_once(config_path)
        if output:
            print(output, end="" if output.endswith("\n") else "\n", flush=True)

        cycles += 1

        if code == 0:
            if "remaining=0" in output:
                _log("worker complete: remaining=0")
                return 0
            time.sleep(max(args.success_interval_sec, 1))
            continue

        if code == 75:
            wait_sec = _extract_wait_seconds(output, args.default_429_wait_sec)
            _log(f"worker cooldown: wait_sec={wait_sec}")
            time.sleep(wait_sec)
            continue

        if "auth/permission issue" in output:
            _log("worker stopped: auth/permission issue")
            return 1

        _log(f"worker transient failure: code={code}, sleeping={args.error_wait_sec}s")
        time.sleep(max(args.error_wait_sec, 1))


if __name__ == "__main__":
    raise SystemExit(main())
