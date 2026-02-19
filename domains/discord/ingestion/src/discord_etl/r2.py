"""R2 원본 JSON 아카이브 업로드.

JSONL 파일 → gzip 압축 → Wrangler CLI로 R2 업로드.
R2 키: discord/{channel_name}/{YYYY-MM-DD}.json.gz
"""

from __future__ import annotations

import gzip
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def upload_to_r2(
    jsonl_path: Path,
    *,
    channel_name: str,
    date: str,
    bucket: str = "github-archive-raw",
) -> bool:
    """JSONL 파일을 gzip 압축 후 R2에 업로드한다."""
    gz_path = jsonl_path.with_suffix(".json.gz")
    r2_key = f"discord/{channel_name}/{date}.json.gz"

    with open(jsonl_path, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
        f_out.write(f_in.read())

    file_size = gz_path.stat().st_size
    logger.info(
        "Compressed: %s → %s (%d bytes)",
        jsonl_path.name, gz_path.name, file_size,
    )

    cmd = [
        "npx", "wrangler", "r2", "object", "put",
        f"{bucket}/{r2_key}",
        "--file", str(gz_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.error("R2 upload failed: %s", result.stderr)
            return False
        logger.info("R2 uploaded: %s (%d bytes)", r2_key, file_size)
        return True
    finally:
        gz_path.unlink(missing_ok=True)
