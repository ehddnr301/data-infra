"""GitHub 이벤트 데이터 모델 (Pydantic)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Actor(BaseModel):
    id: int
    login: str
    display_login: str | None = None
    gravatar_id: str | None = None
    url: str | None = None
    avatar_url: str | None = None


class Repo(BaseModel):
    id: int
    name: str
    url: str | None = None


class Org(BaseModel):
    id: int
    login: str
    gravatar_id: str | None = None
    url: str | None = None
    avatar_url: str | None = None


class GitHubEvent(BaseModel):
    """GitHub Archive 이벤트.

    - id는 필수 필드: 멱등성 보장(D1 PRIMARY KEY, INSERT OR IGNORE)에 사용
    - org는 선택 필드: org 소속이 아닌 이벤트도 존재
    """

    id: str = Field(..., description="이벤트 고유 ID (멱등성 키)")
    type: str
    actor: Actor
    repo: Repo
    org: Org | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    public: bool = True
    created_at: datetime
