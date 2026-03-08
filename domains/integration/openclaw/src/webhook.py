from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs

from applier import CatalogApplier
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse
from planner import Planner

router = APIRouter(prefix="/slack")

PLAN_MODAL_CALLBACK_ID = "openclaw_plan_modal"
DATASET_BLOCK_ID = "dataset_block"
DATASET_ACTION_ID = "dataset_select"
SEED_BLOCK_ID = "seed_block"
SEED_ACTION_ID = "seed_input"


def _iso_now() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def verify_slack_signature(
    *, body: bytes, timestamp: str, signature: str, signing_secret: str
) -> bool:
    if not timestamp or not signature:
        return False
    try:
        parsed_ts = int(timestamp)
    except ValueError:
        return False
    if abs(time.time() - parsed_ts) > 300:
        return False
    base = f"v0:{timestamp}:{body.decode('utf-8')}"
    computed = (
        "v0="
        + hmac.new(
            signing_secret.encode("utf-8"),
            base.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    )
    return hmac.compare_digest(computed, signature)


def _extract_plan_seed(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("plan"):
        return stripped[4:].strip().strip('"')
    return stripped.strip('"')


def _plan_error_message(exc: Exception) -> tuple[str, str]:
    raw = str(exc)
    lowered = raw.lower()
    if "timed out" in lowered or "timeout" in lowered:
        return (
            "Claude 응답 시간이 초과되었습니다. 잠시 후 다시 시도하거나 시드 텍스트를 더 짧게 입력해 주세요.",
            "anthropic_timeout",
        )
    return (raw, "plan_generation_error")


def _dataset_option(dataset: dict[str, Any]) -> dict[str, Any] | None:
    dataset_id = str(dataset.get("id") or "").strip()
    if not dataset_id:
        return None
    domain = str(dataset.get("domain") or "unknown").strip()
    name = str(dataset.get("name") or dataset_id).strip()
    label = f"{dataset_id} | {name} ({domain})"
    if len(label) > 75:
        label = label[:72] + "..."
    return {
        "text": {
            "type": "plain_text",
            "text": label,
        },
        "value": dataset_id,
    }


def _build_plan_modal_view(*, initial_seed: str, channel_id: str) -> dict[str, Any]:
    return {
        "type": "modal",
        "callback_id": PLAN_MODAL_CALLBACK_ID,
        "private_metadata": json.dumps({"channel_id": channel_id}, ensure_ascii=False),
        "title": {"type": "plain_text", "text": "Clawbot Plan"},
        "submit": {"type": "plain_text", "text": "Generate"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": DATASET_BLOCK_ID,
                "label": {"type": "plain_text", "text": "Dataset"},
                "element": {
                    "type": "external_select",
                    "action_id": DATASET_ACTION_ID,
                    "placeholder": {"type": "plain_text", "text": "Select dataset"},
                    "min_query_length": 0,
                },
            },
            {
                "type": "input",
                "block_id": SEED_BLOCK_ID,
                "label": {"type": "plain_text", "text": "Natural language request"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": SEED_ACTION_ID,
                    "multiline": True,
                    "max_length": 3000,
                    "initial_value": initial_seed[:3000],
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Describe what to improve for this dataset",
                    },
                },
            },
        ],
    }


async def _fetch_dataset_options(
    runtime: Any, *, request_id: str, query: str
) -> list[dict[str, Any]]:
    base_url = str(runtime.settings.catalog_api_base_url).rstrip("/")
    try:
        response = await runtime.http_client.get(
            f"{base_url}/api/catalog/datasets",
            params={"page": 1, "pageSize": 100},
            timeout=2.0,
        )
        response.raise_for_status()
        body = response.json()
        datasets = body.get("data") or []
    except Exception as exc:
        runtime.logger.warning(
            "dataset options load failed",
            extra={
                "event_code": "OCW0301",
                "request_id": request_id,
                "failure_cause": str(exc),
                "result": "degraded",
            },
        )
        return []
    keyword = query.strip().lower()

    options: list[dict[str, Any]] = []
    for dataset in datasets:
        if not isinstance(dataset, dict):
            continue
        haystack = " ".join(
            [
                str(dataset.get("id") or ""),
                str(dataset.get("name") or ""),
                str(dataset.get("domain") or ""),
            ]
        ).lower()
        if keyword and keyword not in haystack:
            continue
        option = _dataset_option(dataset)
        if option is None:
            continue
        options.append(option)
        if len(options) >= 100:
            break

    runtime.logger.info(
        "dataset options loaded",
        extra={
            "event_code": "OCW0101",
            "request_id": request_id,
            "result": "success",
        },
    )
    return options


def _plan_blocks(
    plan_id: str, dataset_id: str, payload: dict[str, Any], expires_at: float
) -> list[dict[str, Any]]:
    ttl_minutes = max(1, int((expires_at - time.time()) // 60))
    usage = payload.get("usage_examples") or []
    purpose = payload.get("purpose") or ""
    description = payload.get("dataset", {}).get("description") or ""
    usage_preview = usage[0] if usage else "(none)"
    columns = payload.get("columns") or []
    described_columns = [
        col
        for col in columns
        if isinstance(col, dict) and str(col.get("description") or "").strip()
    ]
    preview_limit = 6
    preview_lines: list[str] = []
    for col in described_columns[:preview_limit]:
        name = str(col.get("column_name") or "").strip()
        col_desc = str(col.get("description") or "").strip()
        if not name:
            continue
        if len(col_desc) > 90:
            col_desc = col_desc[:87].rstrip() + "..."
        preview_lines.append(f"- `{name}`: {col_desc}")

    blocks: list[dict[str, Any]] = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"📋 *Plan #{plan_id}* (만료: 약 {ttl_minutes}분)\n"
                    f"dataset: `{dataset_id}`\n"
                    f"description: {description}\n"
                    f"usage_example: {usage_preview}\n"
                    f"purpose: {purpose}\n"
                    f"columns_with_description: {len(described_columns)}"
                ),
            },
        },
    ]

    if preview_lines:
        extra_count = len(described_columns) - len(preview_lines)
        preview_text = "\n".join(preview_lines)
        if extra_count > 0:
            preview_text += f"\n- ... and {extra_count} more columns"
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Column Description Preview*\n{preview_text}",
                },
            }
        )

    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ Approve"},
                    "style": "primary",
                    "action_id": "approve_plan",
                    "value": json.dumps({"plan_id": plan_id, "action": "approve"}),
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "❌ Reject"},
                    "style": "danger",
                    "action_id": "reject_plan",
                    "value": json.dumps({"plan_id": plan_id, "action": "reject"}),
                },
            ],
        },
    )
    return blocks


def _column_description_thread_chunks(
    payload: dict[str, Any], *, lines_per_message: int = 8
) -> list[str]:
    columns = payload.get("columns") or []
    described_columns: list[tuple[str, str]] = []
    for col in columns:
        if not isinstance(col, dict):
            continue
        name = str(col.get("column_name") or "").strip()
        desc = str(col.get("description") or "").strip()
        if not name or not desc:
            continue
        if len(desc) > 180:
            desc = desc[:177].rstrip() + "..."
        described_columns.append((name, desc))

    if not described_columns:
        return []

    safe_lines = max(1, lines_per_message)
    chunks: list[str] = []
    total = len(described_columns)
    for start in range(0, total, safe_lines):
        end = min(start + safe_lines, total)
        lines = [f"- `{name}`: {desc}" for name, desc in described_columns[start:end]]
        header = f"🧾 Column description details ({start + 1}-{end}/{total})"
        chunks.append(header + "\n" + "\n".join(lines))
    return chunks


async def _slack_api_post(
    runtime: Any,
    *,
    method: str,
    payload: dict[str, Any],
    request_id: str,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    response = await runtime.http_client.post(
        f"https://slack.com/api/{method}",
        headers={
            "Authorization": f"Bearer {runtime.settings.slack_bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        json=payload,
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    body = response.json()
    if not body.get("ok"):
        raise ValueError(f"slack api {method} failed: {body.get('error')}")
    runtime.logger.info(
        "slack api success",
        extra={
            "event_code": "OCW0103",
            "request_id": request_id,
            "result": "success",
        },
    )
    return body


@router.post("/command")
async def slash_command(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    runtime = request.app.state.runtime
    raw_body = await request.body()
    signature = request.headers.get("X-Slack-Signature", "")
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")

    if not verify_slack_signature(
        body=raw_body,
        timestamp=timestamp,
        signature=signature,
        signing_secret=runtime.settings.slack_signing_secret,
    ):
        raise HTTPException(status_code=403, detail="invalid slack signature")

    runtime.logger.info(
        "slack signature verified", extra={"event_code": "OCW0002", "result": "success"}
    )
    parsed = parse_qs(raw_body.decode("utf-8"), keep_blank_values=True)
    text = (parsed.get("text") or [""])[0]
    trigger_id = (parsed.get("trigger_id") or [""])[0]
    request_id = f"req_{int(time.time() * 1000)}"
    user_id = (parsed.get("user_id") or [""])[0]
    channel_id = (parsed.get("channel_id") or [runtime.settings.slack_channel_id])[0]

    runtime.logger.info(
        "slash command received",
        extra={
            "event_code": "OCW0001",
            "request_id": request_id,
            "slack_user_id": user_id,
            "slack_channel_id": channel_id,
            "result": "success",
        },
    )

    seed = _extract_plan_seed(text)
    if not trigger_id:
        background_tasks.add_task(
            _handle_plan_async, runtime, seed, request_id, user_id, channel_id
        )
        return JSONResponse(
            status_code=200,
            content={
                "response_type": "ephemeral",
                "text": "분석 중입니다. 잠시 후 #clawbot-ops에 계획을 게시합니다.",
            },
        )

    view = _build_plan_modal_view(initial_seed=seed, channel_id=channel_id)
    try:
        await _slack_api_post(
            runtime,
            method="views.open",
            payload={
                "trigger_id": trigger_id,
                "view": view,
            },
            request_id=request_id,
            timeout_seconds=2.5,
        )
    except Exception as exc:
        runtime.logger.error(
            "modal open failed, falling back to direct plan handling",
            extra={
                "event_code": "OCW0901",
                "request_id": request_id,
                "failure_code": "modal_open_failed",
                "failure_cause": str(exc),
                "result": "degraded",
            },
        )
        background_tasks.add_task(
            _handle_plan_async,
            runtime,
            seed,
            request_id,
            user_id,
            channel_id,
        )
        return JSONResponse(
            status_code=200,
            content={
                "response_type": "ephemeral",
                "text": "입력 창 열기에 실패해 기본 모드로 처리합니다. 잠시 후 #clawbot-ops를 확인해 주세요.",
            },
        )
    return JSONResponse(
        status_code=200,
        content={
            "response_type": "ephemeral",
            "text": "카탈로그 선택 창을 열었습니다. dataset과 요청 내용을 입력해 주세요.",
        },
    )


@router.post("/command/")
async def slash_command_trailing_slash(
    request: Request, background_tasks: BackgroundTasks
) -> JSONResponse:
    return await slash_command(request, background_tasks)


@router.post("/interactive")
async def interactive(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    runtime = request.app.state.runtime
    raw_body = await request.body()
    signature = request.headers.get("X-Slack-Signature", "")
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")

    if not verify_slack_signature(
        body=raw_body,
        timestamp=timestamp,
        signature=signature,
        signing_secret=runtime.settings.slack_signing_secret,
    ):
        raise HTTPException(status_code=403, detail="invalid slack signature")

    parsed = parse_qs(raw_body.decode("utf-8"), keep_blank_values=True)
    payload_raw = (parsed.get("payload") or ["{}"])[0]
    try:
        payload = json.loads(payload_raw)
    except json.JSONDecodeError:
        runtime.logger.error(
            "interactive payload decode failed",
            extra={
                "event_code": "OCW0901",
                "failure_code": "interactive_payload_decode_failed",
                "result": "failed",
            },
        )
        return JSONResponse(status_code=200, content={"ok": True, "timestamp": _iso_now()})

    request_id = f"req_{int(time.time() * 1000)}"
    payload_type = str(payload.get("type") or "")
    runtime.logger.info(
        "interactive payload received",
        extra={
            "event_code": "OCW0002",
            "request_id": request_id,
            "payload_type": payload_type or "unknown",
            "result": "success",
        },
    )

    try:
        if payload_type == "block_suggestion":
            query = str(payload.get("value") or "")
            options = await _fetch_dataset_options(runtime, request_id=request_id, query=query)
            return JSONResponse(status_code=200, content={"options": options})

        if payload_type == "view_submission":
            view = payload.get("view") or {}
            values = (view.get("state") or {}).get("values") or {}
            dataset_values = (values.get(DATASET_BLOCK_ID) or {}).get(DATASET_ACTION_ID) or {}
            selected_option = dataset_values.get("selected_option") or {}
            selected_dataset_id = str(selected_option.get("value") or "").strip()
            seed_values = (values.get(SEED_BLOCK_ID) or {}).get(SEED_ACTION_ID) or {}
            seed = str(seed_values.get("value") or "").strip()

            errors: dict[str, str] = {}
            if not selected_dataset_id:
                errors[DATASET_BLOCK_ID] = "dataset을 선택해 주세요."
            if not seed:
                errors[SEED_BLOCK_ID] = "요청 문장을 입력해 주세요."
            if errors:
                return JSONResponse(
                    status_code=200,
                    content={
                        "response_action": "errors",
                        "errors": errors,
                    },
                )

            private_metadata_raw = str(view.get("private_metadata") or "{}")
            private_metadata: dict[str, Any]
            try:
                parsed_metadata = json.loads(private_metadata_raw)
                private_metadata = parsed_metadata if isinstance(parsed_metadata, dict) else {}
            except json.JSONDecodeError:
                private_metadata = {}

            channel_id = str(
                private_metadata.get("channel_id") or runtime.settings.slack_channel_id
            )
            user_id = str(((payload.get("user") or {}).get("id")) or "")
            background_tasks.add_task(
                _handle_plan_async,
                runtime,
                seed,
                request_id,
                user_id,
                channel_id,
                selected_dataset_id,
            )
            return JSONResponse(status_code=200, content={"response_action": "clear"})
    except Exception as exc:
        runtime.logger.error(
            "interactive handling failed",
            extra={
                "event_code": "OCW0901",
                "request_id": request_id,
                "failure_code": "interactive_handling_failed",
                "failure_cause": str(exc),
                "payload_type": payload_type,
                "result": "failed",
            },
        )
        if payload_type == "view_submission":
            return JSONResponse(
                status_code=200,
                content={
                    "response_action": "errors",
                    "errors": {
                        SEED_BLOCK_ID: "요청 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
                    },
                },
            )
        return JSONResponse(status_code=200, content={"ok": True, "timestamp": _iso_now()})

    background_tasks.add_task(_handle_interactive_async, runtime, payload, request_id)
    return JSONResponse(status_code=200, content={"ok": True, "timestamp": _iso_now()})


@router.post("/interactive/")
async def interactive_trailing_slash(
    request: Request, background_tasks: BackgroundTasks
) -> JSONResponse:
    return await interactive(request, background_tasks)


async def _handle_plan_async(
    runtime: Any,
    seed: str,
    request_id: str,
    user_id: str,
    channel_id: str,
    selected_dataset_id: str | None = None,
) -> None:
    planner = Planner(runtime.settings, runtime.http_client, runtime.logger)
    try:
        dataset_id, plan_payload = await planner.generate_plan(
            seed,
            request_id,
            dataset_id=selected_dataset_id,
        )
        plan_record = runtime.plan_store.create(
            request_id=request_id,
            slack_user_id=user_id,
            slack_channel_id=channel_id,
            dataset_id=dataset_id,
            payload=plan_payload,
        )

        posted = await _slack_api_post(
            runtime,
            method="chat.postMessage",
            payload={
                "channel": runtime.settings.slack_channel_id,
                "text": f"Plan #{plan_record.plan_id}",
                "blocks": _plan_blocks(
                    plan_record.plan_id,
                    dataset_id,
                    plan_payload,
                    plan_record.expires_at,
                ),
            },
            request_id=request_id,
        )
        if isinstance(posted.get("ts"), str):
            runtime.plan_store.set_message_ts(plan_record.plan_id, posted["ts"])
            thread_ts = posted["ts"]
            for chunk in _column_description_thread_chunks(plan_payload):
                try:
                    await _slack_api_post(
                        runtime,
                        method="chat.postMessage",
                        payload={
                            "channel": runtime.settings.slack_channel_id,
                            "thread_ts": thread_ts,
                            "text": chunk,
                        },
                        request_id=request_id,
                    )
                except Exception as exc:
                    runtime.logger.warning(
                        "column detail thread post failed",
                        extra={
                            "event_code": "OCW0301",
                            "request_id": request_id,
                            "plan_id": plan_record.plan_id,
                            "failure_cause": str(exc),
                            "result": "degraded",
                        },
                    )
        runtime.logger.info(
            "plan generated",
            extra={
                "event_code": "OCW0102",
                "request_id": request_id,
                "plan_id": plan_record.plan_id,
                "slack_user_id": user_id,
                "slack_channel_id": channel_id,
                "result": "success",
            },
        )
    except Exception as exc:
        message, failure_code = _plan_error_message(exc)
        runtime.logger.error(
            "plan generation failed",
            extra={
                "event_code": "OCW0901",
                "request_id": request_id,
                "failure_code": failure_code,
                "failure_cause": str(exc),
                "result": "failed",
            },
        )
        await _slack_api_post(
            runtime,
            method="chat.postMessage",
            payload={
                "channel": runtime.settings.slack_channel_id,
                "text": f"❌ plan 생성 실패: {message}",
            },
            request_id=request_id,
        )


async def _handle_interactive_async(runtime: Any, payload: dict[str, Any], request_id: str) -> None:
    actions = payload.get("actions") or []
    if not actions:
        return

    action = actions[0]
    value_raw = str(action.get("value") or "{}")
    value = json.loads(value_raw)
    plan_id = str(value.get("plan_id") or "")
    action_name = str(value.get("action") or "")

    channel_id = str(
        ((payload.get("channel") or {}).get("id")) or runtime.settings.slack_channel_id
    )
    message_ts = str(((payload.get("container") or {}).get("message_ts")) or "")
    user_id = str(((payload.get("user") or {}).get("id")) or "")

    record = runtime.plan_store.get(plan_id)
    if record is None:
        await _slack_api_post(
            runtime,
            method="chat.update",
            payload={
                "channel": channel_id,
                "ts": message_ts,
                "text": f"❌ Plan #{plan_id}을 찾을 수 없습니다.",
            },
            request_id=request_id,
        )
        return

    if record.status == "expired":
        runtime.logger.warning(
            "apply blocked due to ttl",
            extra={
                "event_code": "OCW0202",
                "request_id": request_id,
                "plan_id": record.plan_id,
                "approval_state": "expired",
                "result": "degraded",
            },
        )
        await _slack_api_post(
            runtime,
            method="chat.update",
            payload={
                "channel": channel_id,
                "ts": message_ts,
                "text": f"⌛ Plan #{plan_id} 만료됨. /clawbot plan 으로 재요청하세요.",
            },
            request_id=request_id,
        )
        return

    if action_name == "reject":
        runtime.plan_store.mark(plan_id, "rejected")
        runtime.logger.info(
            "plan rejected",
            extra={
                "event_code": "OCW0204",
                "request_id": request_id,
                "plan_id": plan_id,
                "slack_user_id": user_id,
                "slack_channel_id": channel_id,
                "result": "success",
            },
        )
        await _slack_api_post(
            runtime,
            method="chat.update",
            payload={
                "channel": channel_id,
                "ts": message_ts,
                "text": f"❌ Plan #{plan_id} 거부됨",
            },
            request_id=request_id,
        )
        return

    runtime.plan_store.mark(plan_id, "approved")
    applier = CatalogApplier(runtime.settings, runtime.http_client, runtime.logger)
    result = await applier.apply_plan(record)

    if result["status"] == "success":
        text = f"✅ Plan #{plan_id} 적용 완료 — description 1건, columns {len(record.payload.get('columns', []))}건 반영"
    elif result["status"] == "blocked":
        text = f"⛔ Plan #{plan_id} 차단됨 (dry-run/write 비활성)"
    else:
        text = f"❌ Plan #{plan_id} 적용 실패: {result.get('reason', 'unknown')}"

    await _slack_api_post(
        runtime,
        method="chat.update",
        payload={
            "channel": channel_id,
            "ts": message_ts,
            "text": text,
        },
        request_id=request_id,
    )
