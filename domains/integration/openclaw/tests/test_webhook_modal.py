from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode

import httpx
import pytest
import webhook as webhook_module
from app import Runtime, app
from config import load_settings
from webhook import (
    DATASET_ACTION_ID,
    DATASET_BLOCK_ID,
    PLAN_MODAL_CALLBACK_ID,
    SEED_ACTION_ID,
    SEED_BLOCK_ID,
    _build_plan_modal_view,
    _dataset_option,
)


def _set_required_env() -> None:
    os.environ["SLACK_BOT_TOKEN"] = "xoxb-test"
    os.environ["SLACK_SIGNING_SECRET"] = "secret"
    os.environ["SLACK_CHANNEL_ID"] = "C123"
    os.environ["ANTHROPIC_API_KEY"] = "test"
    os.environ["CATALOG_API_BASE_URL"] = "http://127.0.0.1:8787"
    os.environ["CATALOG_INTERNAL_BEARER"] = "token"


async def _post_interactive(body: bytes, headers: dict[str, str]) -> httpx.Response:
    runtime = Runtime(load_settings())
    app.state.runtime = runtime
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post("/slack/interactive", content=body, headers=headers)
    finally:
        await runtime.close()


def _signed_headers(body: bytes, *, signing_secret: str) -> dict[str, str]:
    timestamp = str(int(time.time()))
    base = f"v0:{timestamp}:{body.decode('utf-8')}"
    signature = (
        "v0="
        + hmac.new(
            signing_secret.encode("utf-8"),
            base.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    )
    return {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Slack-Request-Timestamp": timestamp,
        "X-Slack-Signature": signature,
    }


def test_build_plan_modal_view_contract() -> None:
    view = _build_plan_modal_view(initial_seed="watch event 설명 보강", channel_id="C999")
    assert view["type"] == "modal"
    assert view["callback_id"] == PLAN_MODAL_CALLBACK_ID
    metadata = json.loads(view["private_metadata"])
    assert metadata["channel_id"] == "C999"

    dataset_element = view["blocks"][0]["element"]
    assert dataset_element["type"] == "external_select"
    assert dataset_element["action_id"] == DATASET_ACTION_ID

    seed_element = view["blocks"][1]["element"]
    assert seed_element["type"] == "plain_text_input"
    assert seed_element["action_id"] == SEED_ACTION_ID
    assert seed_element["initial_value"] == "watch event 설명 보강"


def test_dataset_option_uses_dataset_id_as_value() -> None:
    option = _dataset_option(
        {
            "id": "github.watch-events.v1",
            "domain": "github",
            "name": "Watch Events",
        }
    )
    assert option is not None
    assert option["value"] == "github.watch-events.v1"
    assert "github.watch-events.v1" in option["text"]["text"]


def test_interactive_view_submission_schedules_targeted_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_required_env()
    captured: dict[str, str | None] = {}

    async def fake_handle_plan_async(
        runtime,
        seed: str,
        request_id: str,
        user_id: str,
        channel_id: str,
        selected_dataset_id: str | None = None,
    ) -> None:
        captured["seed"] = seed
        captured["request_id"] = request_id
        captured["user_id"] = user_id
        captured["channel_id"] = channel_id
        captured["selected_dataset_id"] = selected_dataset_id

    monkeypatch.setattr(webhook_module, "_handle_plan_async", fake_handle_plan_async)

    payload = {
        "type": "view_submission",
        "user": {"id": "U123"},
        "view": {
            "callback_id": PLAN_MODAL_CALLBACK_ID,
            "private_metadata": json.dumps({"channel_id": "COPS"}, ensure_ascii=False),
            "state": {
                "values": {
                    DATASET_BLOCK_ID: {
                        DATASET_ACTION_ID: {"selected_option": {"value": "github.watch-events.v1"}}
                    },
                    SEED_BLOCK_ID: {
                        SEED_ACTION_ID: {"value": "watch 이벤트 설명을 제품 지표 중심으로 개선"}
                    },
                }
            },
        },
    }
    body = urlencode({"payload": json.dumps(payload, ensure_ascii=False)}).encode("utf-8")
    headers = _signed_headers(body, signing_secret="secret")

    response = asyncio.run(_post_interactive(body, headers))
    assert response.status_code == 200
    assert response.json()["response_action"] == "clear"
    assert captured["selected_dataset_id"] == "github.watch-events.v1"
    assert captured["channel_id"] == "COPS"
    assert captured["user_id"] == "U123"
    assert captured["seed"] == "watch 이벤트 설명을 제품 지표 중심으로 개선"


def test_interactive_block_suggestion_returns_options(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env()
    captured_query: dict[str, str] = {}

    async def fake_fetch_dataset_options(runtime, *, request_id: str, query: str):
        captured_query["value"] = query
        return [
            {
                "text": {
                    "type": "plain_text",
                    "text": "github.watch-events.v1 | Watch Events (github)",
                },
                "value": "github.watch-events.v1",
            }
        ]

    monkeypatch.setattr(webhook_module, "_fetch_dataset_options", fake_fetch_dataset_options)

    payload = {
        "type": "block_suggestion",
        "value": "watch",
    }
    body = urlencode({"payload": json.dumps(payload, ensure_ascii=False)}).encode("utf-8")
    headers = _signed_headers(body, signing_secret="secret")

    response = asyncio.run(_post_interactive(body, headers))
    assert response.status_code == 200
    assert response.json()["options"][0]["value"] == "github.watch-events.v1"
    assert captured_query["value"] == "watch"
