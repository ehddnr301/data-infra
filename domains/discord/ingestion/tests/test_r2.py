"""R2 업로드 테스트."""

from __future__ import annotations

import gzip
from pathlib import Path
from unittest.mock import MagicMock, patch

from discord_etl.r2 import upload_to_r2

CHANNEL_NAME = "test-channel"
DATE = "2024-06-15"
SAMPLE_CONTENT = b'{"id":"1","content":"hello"}\n{"id":"2","content":"world"}\n'


def _create_jsonl(tmp_path: Path) -> Path:
    """테스트용 JSONL 파일 생성."""
    jsonl_path = tmp_path / "messages.jsonl"
    jsonl_path.write_bytes(SAMPLE_CONTENT)
    return jsonl_path


class TestUploadToR2:
    """R2 업로드 테스트."""

    @patch("discord_etl.r2.subprocess.run")
    def test_upload_to_r2_success(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        jsonl_path = _create_jsonl(tmp_path)

        result = upload_to_r2(jsonl_path, channel_name=CHANNEL_NAME, date=DATE)

        assert result is True
        mock_run.assert_called_once()

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert cmd[0] == "npx"
        assert cmd[1] == "wrangler"
        assert cmd[2] == "r2"
        assert cmd[3] == "object"
        assert cmd[4] == "put"
        assert f"github-archive-raw/discord/{CHANNEL_NAME}/{DATE}.json.gz" in cmd[5]
        assert "--file" in cmd

    @patch("discord_etl.r2.subprocess.run")
    def test_upload_to_r2_failure(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="upload error")
        jsonl_path = _create_jsonl(tmp_path)

        result = upload_to_r2(jsonl_path, channel_name=CHANNEL_NAME, date=DATE)

        assert result is False

    @patch("discord_etl.r2.subprocess.run")
    def test_upload_to_r2_cleanup_on_failure(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        jsonl_path = _create_jsonl(tmp_path)
        gz_path = jsonl_path.with_suffix(".json.gz")

        upload_to_r2(jsonl_path, channel_name=CHANNEL_NAME, date=DATE)

        assert not gz_path.exists(), "gz file should be cleaned up after failure"

    @patch("discord_etl.r2.subprocess.run")
    def test_upload_to_r2_cleanup_on_success(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        jsonl_path = _create_jsonl(tmp_path)
        gz_path = jsonl_path.with_suffix(".json.gz")

        upload_to_r2(jsonl_path, channel_name=CHANNEL_NAME, date=DATE)

        assert not gz_path.exists(), "gz file should be cleaned up after success"

    def test_gzip_compression(self, tmp_path: Path) -> None:
        """gzip 압축이 올바르게 수행되는지 확인."""
        jsonl_path = _create_jsonl(tmp_path)
        gz_path = jsonl_path.with_suffix(".json.gz")

        # gzip 압축 직접 수행 (subprocess mock 없이 압축 로직만 테스트)
        with open(jsonl_path, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
            f_out.write(f_in.read())

        assert gz_path.exists()
        with gzip.open(gz_path, "rb") as f:
            decompressed = f.read()
        assert decompressed == SAMPLE_CONTENT

        gz_path.unlink()

    @patch("discord_etl.r2.subprocess.run")
    def test_upload_custom_bucket(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        jsonl_path = _create_jsonl(tmp_path)

        result = upload_to_r2(
            jsonl_path, channel_name=CHANNEL_NAME, date=DATE, bucket="custom-bucket",
        )

        assert result is True
        cmd = mock_run.call_args[0][0]
        assert "custom-bucket/" in cmd[5]
