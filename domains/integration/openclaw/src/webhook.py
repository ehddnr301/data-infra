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


def _plan_blocks(
    plan_id: str, dataset_id: str, payload: dict[str, Any], expires_at: float
) -> list[dict[str, Any]]:
    ttl_minutes = max(1, int((expires_at - time.time()) // 60))
    usage = payload.get("usage_examples") or []
    purpose = payload.get("purpose") or ""
    description = payload.get("dataset", {}).get("description") or ""
    usage_preview = usage[0] if usage else "(none)"
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"📋 *Plan #{plan_id}* (만료: 약 {ttl_minutes}분)\n"
                    f"dataset: `{dataset_id}`\n"
                    f"description: {description}\n"
                    f"usage_example: {usage_preview}\n"
                    f"purpose: {purpose}"
                ),
            },
        },
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
    ]


async def _slack_api_post(
    runtime: Any,
    *,
    method: str,
    payload: dict[str, Any],
    request_id: str,
) -> dict[str, Any]:
    response = await runtime.http_client.post(
        f"https://slack.com/api/{method}",
        headers={
            "Authorization": f"Bearer {runtime.settings.slack_bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        json=payload,
        timeout=10.0,
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
    background_tasks.add_task(_handle_plan_async, runtime, seed, request_id, user_id, channel_id)
    return JSONResponse(
        status_code=200,
        content={
            "response_type": "ephemeral",
            "text": "분석 중입니다. 잠시 후 #clawbot-ops에 계획을 게시합니다.",
        },
    )


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
    payload = json.loads(payload_raw)
    request_id = f"req_{int(time.time() * 1000)}"

    background_tasks.add_task(_handle_interactive_async, runtime, payload, request_id)
    return JSONResponse(status_code=200, content={"ok": True, "timestamp": _iso_now()})


async def _handle_plan_async(
    runtime: Any,
    seed: str,
    request_id: str,
    user_id: str,
    channel_id: str,
) -> None:
    planner = Planner(runtime.settings, runtime.http_client, runtime.logger)
    try:
        dataset_id, plan_payload = await planner.generate_plan(seed, request_id)
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
