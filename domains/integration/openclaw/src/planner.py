from __future__ import annotations

import json
import logging
from typing import Any

import anthropic
import httpx
from config import Settings
from pydantic import BaseModel, Field

SYSTEM_PROMPT = """당신은 데이터 카탈로그 메타데이터 전문가입니다.
주어진 테이블 스키마와 시드 텍스트를 분석하여 데이터 활용성을 높이는 풍성한 메타데이터를 작성하세요.
출력은 JSON 객체만 반환하세요.

JSON 형식:
{
  "table_description": "...",
  "column_descriptions": {"col_name": "..."},
  "usage_examples": ["..."],
  "purpose": "..."
}
"""


class PlanDraft(BaseModel):
    table_description: str = Field(min_length=1)
    column_descriptions: dict[str, str] = Field(default_factory=dict)
    usage_examples: list[str] = Field(default_factory=list)
    purpose: str = Field(min_length=1)


class Planner:
    def __init__(
        self, settings: Settings, http_client: httpx.AsyncClient, logger: logging.Logger
    ) -> None:
        self._settings = settings
        self._http = http_client
        self._logger = logger
        self._anthropic = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            timeout=settings.anthropic_timeout_seconds,
            max_retries=settings.anthropic_max_retries,
        )

    async def generate_plan(self, seed_text: str, request_id: str) -> tuple[str, dict[str, Any]]:
        snapshot = await self._fetch_catalog_snapshot(request_id)
        dataset = snapshot["dataset"]
        columns = snapshot["columns"]
        draft = await self._generate_draft(seed_text=seed_text, snapshot=snapshot)

        updated_columns: list[dict[str, Any]] = []
        for column in columns:
            column_name = str(column.get("column_name", ""))
            updated_columns.append(
                {
                    "column_name": column_name,
                    "data_type": str(column.get("data_type", "text")),
                    "description": draft.column_descriptions.get(column_name)
                    or str(column.get("description") or ""),
                    "is_pii": bool(column.get("is_pii", False)),
                    "examples": column.get("examples"),
                }
            )

        payload = {
            "dataset": {
                "id": dataset["id"],
                "domain": dataset["domain"],
                "name": dataset["name"],
                "description": draft.table_description,
                "schema_json": dataset.get("schema_json"),
                "owner": dataset.get("owner"),
                "tags": dataset.get("tags"),
            },
            "columns": updated_columns,
            "lineage": dataset.get("lineage_json"),
            "usage_examples": draft.usage_examples,
            "purpose": draft.purpose,
            "seed_text": seed_text,
        }
        return str(dataset["id"]), payload

    async def _fetch_catalog_snapshot(self, request_id: str) -> dict[str, Any]:
        base_url = str(self._settings.catalog_api_base_url).rstrip("/")
        datasets_res = await self._http.get(
            f"{base_url}/api/catalog/datasets",
            params={"page": 1, "pageSize": 20},
            timeout=10.0,
        )
        datasets_res.raise_for_status()
        datasets_body = datasets_res.json()
        datasets = datasets_body.get("data") or []
        if not datasets:
            raise ValueError("No catalog datasets available for planning")

        dataset = datasets[0]
        dataset_id = str(dataset["id"])
        columns_res = await self._http.get(
            f"{base_url}/api/catalog/datasets/{dataset_id}/columns",
            timeout=10.0,
        )
        columns_res.raise_for_status()
        columns_body = columns_res.json()

        self._logger.info(
            "catalog snapshot fetched",
            extra={
                "event_code": "OCW0101",
                "request_id": request_id,
                "result": "success",
            },
        )

        return {
            "dataset": dataset,
            "columns": columns_body.get("data") or [],
        }

    async def _generate_draft(self, *, seed_text: str, snapshot: dict[str, Any]) -> PlanDraft:
        full_prompt_snapshot = self._compact_snapshot(
            snapshot,
            max_columns=self._settings.planner_prompt_max_columns,
        )
        try:
            return await self._request_draft(
                seed_text=seed_text,
                prompt_snapshot=full_prompt_snapshot,
                max_tokens=self._settings.anthropic_max_tokens,
            )
        except (anthropic.APITimeoutError, TimeoutError) as exc:
            self._logger.warning(
                "anthropic timeout, retrying with compact snapshot",
                extra={
                    "event_code": "OCW0301",
                    "failure_cause": str(exc),
                    "result": "degraded",
                },
            )
            compact_prompt_snapshot = self._compact_snapshot(
                snapshot,
                max_columns=self._settings.planner_fallback_max_columns,
            )
            fallback_tokens = min(self._settings.anthropic_max_tokens, 512)
            return await self._request_draft(
                seed_text=seed_text,
                prompt_snapshot=compact_prompt_snapshot,
                max_tokens=fallback_tokens,
            )

    async def _request_draft(
        self,
        *,
        seed_text: str,
        prompt_snapshot: dict[str, Any],
        max_tokens: int,
    ) -> PlanDraft:
        user_payload = {
            "seed_text": seed_text,
            "snapshot": prompt_snapshot,
        }
        response = await self._anthropic.messages.create(
            model=self._settings.anthropic_model,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False),
                }
            ],
        )

        text_blocks: list[str] = []
        for block in response.content:
            block_text = getattr(block, "text", None)
            if isinstance(block_text, str):
                text_blocks.append(block_text)

        raw = "\n".join(text_blocks).strip()
        parsed = self._parse_json_text(raw)
        draft = PlanDraft.model_validate(parsed)
        return draft

    @staticmethod
    def _compact_snapshot(snapshot: dict[str, Any], *, max_columns: int) -> dict[str, Any]:
        dataset = snapshot.get("dataset") or {}
        columns = snapshot.get("columns") or []
        compact_columns: list[dict[str, Any]] = []
        for raw_column in columns[:max_columns]:
            compact_columns.append(
                {
                    "column_name": raw_column.get("column_name"),
                    "data_type": raw_column.get("data_type"),
                    "description": raw_column.get("description"),
                    "is_pii": raw_column.get("is_pii"),
                }
            )

        return {
            "dataset": {
                "id": dataset.get("id"),
                "domain": dataset.get("domain"),
                "name": dataset.get("name"),
                "description": dataset.get("description"),
                "owner": dataset.get("owner"),
                "tags": dataset.get("tags"),
            },
            "columns": compact_columns,
            "summary": {
                "total_columns": len(columns),
                "columns_in_prompt": len(compact_columns),
            },
        }

    @staticmethod
    def _parse_json_text(raw: str) -> dict[str, Any]:
        try:
            decoded = json.loads(raw)
            if isinstance(decoded, dict):
                return decoded
        except json.JSONDecodeError:
            pass

        left = raw.find("{")
        right = raw.rfind("}")
        if left >= 0 and right > left:
            candidate = raw[left : right + 1]
            decoded = json.loads(candidate)
            if isinstance(decoded, dict):
                return decoded
        raise ValueError("Claude response is not valid JSON object")
