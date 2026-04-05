"""PseudoLab Supabase 카탈로그 동기화 — HTTP API 방식."""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

import httpx

from pseudolab_etl.table_registry import ALL_TABLES, TableDef
from pseudolab_etl.type_mapping import pg_to_d1_type

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# ---------------------------------------------------------------------------
# 카테고리 매핑 (15개 카테고리)
# ---------------------------------------------------------------------------
TABLE_CATEGORY: dict[str, str] = {
    # event
    "events": "event", "event_registrations": "event", "event_sessions": "event",
    "event_speaker_submissions": "event", "event_sponsor_submissions": "event",
    "event_sponsors": "event", "event_timeline": "event", "event_cards": "event",
    "event_committee": "event", "event_missions": "event",
    "event_participants": "event", "event_staff": "event",
    # project
    "projects": "project", "project_applications": "project",
    "project_members": "project", "project_sessions": "project",
    "project_tasks": "project", "project_docs": "project",
    # user
    "profiles": "user", "profile_careers": "user", "user_which_projects": "user",
    "user_roles": "user", "follows": "user", "user_follows": "user",
    "user_influences": "user", "legacy_members": "user", "project_attendance": "user",
    # community
    "blogs": "community", "community_feed": "community", "highlights": "community",
    "feed_comments": "community", "resource_comments": "community",
    "highlight_comments": "community", "highlight_likes": "community",
    "dormitory_messages": "community",
    # secret
    "secret_posts": "secret", "secret_profiles": "secret",
    "secret_comments": "secret", "secret_interactions": "secret",
    # bug
    "bug_reports": "bug", "bug_comments": "bug",
    "bug_events": "bug", "bug_assignees": "bug",
    # gamification
    "badges": "gamification", "quest_definitions": "gamification",
    "user_missions": "gamification", "user_badges": "gamification",
    "user_quests": "gamification", "xp_history": "gamification",
    # recruitment
    "builder_onboarding": "recruitment", "recruit_applications": "recruitment",
    "registration_submissions": "recruitment", "project_application_history": "recruitment",
    # opportunity
    "opportunities": "opportunity", "opportunity_beneficiaries": "opportunity",
    "opportunity_likes": "opportunity",
    # wiki
    "wiki_articles": "wiki", "wiki_categories": "wiki",
    "wiki_pages": "wiki", "wiki_revisions": "wiki",
    # squad
    "squads": "squad", "squad_applications": "squad",
    "random_squad_queue": "squad",
    # magic
    "magic_maps": "magic", "magic_progress": "magic",
    # submission
    "session_submissions": "submission", "speaker_submissions": "submission",
    "sponsor_submissions": "submission", "sponsorship_requests": "submission",
    # engagement
    "page_views": "engagement", "notifications": "engagement",
    "program_feedbacks": "engagement", "program_followups": "engagement",
    "program_likes": "engagement", "resource_reactions": "engagement",
    "artifact_logs": "engagement",
    # system
    "action_items": "system", "admin_calendar_events": "system",
    "email_verification_codes": "system",
}

# ---------------------------------------------------------------------------
# 79개 테이블 메타데이터 (group*.md에서 추출)
# ---------------------------------------------------------------------------
TABLE_METADATA: dict[str, dict[str, Any]] = {
    "events": {
        "title": "이벤트 목록",
        "subtitle": "PseudoLab 공식 이벤트 마스터 데이터",
        "description": "PseudoCon 등 공식 이벤트의 기본 정보(제목, 일시, 장소, 상태, 카테고리)를 관리하는 마스터 테이블.",
        "purpose": "이벤트 개최 이력 조회, 시즌별 이벤트 트렌드 분석",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관", "삭제된 이벤트는 추적 불가"],
        "usage_examples": ["시즌별 이벤트 개최 횟수 추이", "카테고리별 이벤트 분포"],
        "tags": ["pseudolab", "event", "master"],
    },
    "event_registrations": {
        "title": "이벤트 등록",
        "subtitle": "참가자 등록 및 체크인 현황",
        "description": "이벤트별 참가 등록 정보. 등록 유형, 상태, 체크인 여부를 추적하여 참여율 분석 가능.",
        "purpose": "이벤트별 등록자 수 및 체크인율 분석",
        "limitations": ["PII(email, name) HMAC 해싱 적용", "스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["이벤트별 등록 vs 체크인 비율", "등록 유형별 분포"],
        "tags": ["pseudolab", "event", "registration", "participation"],
    },
    "event_sessions": {
        "title": "이벤트 세션",
        "subtitle": "발표 세션 구성 및 스피커 정보",
        "description": "이벤트 내 개별 세션(발표, 워크숍 등)의 시간, 유형, 발표자 정보를 관리.",
        "purpose": "세션 구성 분석, 세션 유형별 트렌드",
        "limitations": ["PII(speaker_name, speaker_email) 해싱 적용", "스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["세션 유형(session_type)별 분포", "이벤트별 평균 세션 수"],
        "tags": ["pseudolab", "event", "session", "speaker"],
    },
    "event_speaker_submissions": {
        "title": "스피커 지원",
        "subtitle": "발표자 지원서 접수 및 심사 현황",
        "description": "이벤트 발표자 공모 지원서. 주제, 개요, 대상 청중 등 지원 내용과 심사 상태 추적.",
        "purpose": "스피커 지원 트렌드, 주제 분포 분석",
        "limitations": ["PII(email, speaker_name) 해싱 적용", "스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["심사 상태(status)별 지원서 수", "이벤트별 지원 주제 분포"],
        "tags": ["pseudolab", "event", "speaker", "submission"],
    },
    "event_sponsor_submissions": {
        "title": "스폰서 지원",
        "subtitle": "후원사 지원서 접수 현황",
        "description": "이벤트 후원 지원서. 회사명, 후원 등급, 연락처 정보와 심사 상태 관리.",
        "purpose": "후원 지원 현황 추적",
        "limitations": ["PII(contact_name, email, phone) 해싱 적용", "스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["후원 등급(sponsorship_level)별 지원 현황", "이벤트별 후원 지원 수"],
        "tags": ["pseudolab", "event", "sponsor", "submission"],
    },
    "event_sponsors": {
        "title": "이벤트 후원사",
        "subtitle": "확정된 후원사 정보 및 등급",
        "description": "이벤트별 확정 후원사의 등급, 로고, 웹사이트, 혜택 정보를 관리.",
        "purpose": "후원사 이력 조회, 등급별 후원 현황",
        "limitations": ["PII(contact_name, contact_email, contact_phone) 해싱 적용", "스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["등급(level)별 후원사 분포", "이벤트별 후원사 수 추이"],
        "tags": ["pseudolab", "event", "sponsor"],
    },
    "event_timeline": {
        "title": "이벤트 타임라인",
        "subtitle": "이벤트 진행 단계별 일정",
        "description": "이벤트의 단계(phase)별 일정과 활성 상태를 관리하는 타임라인 데이터.",
        "purpose": "이벤트 준비/진행 단계 추적",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["이벤트별 진행 단계 현황", "단계별 평균 소요 기간"],
        "tags": ["pseudolab", "event", "timeline", "schedule"],
    },
    "event_cards": {
        "title": "이벤트 카드",
        "subtitle": "이벤트 관련 카드형 콘텐츠",
        "description": "이벤트와 연관된 카드형 콘텐츠(이미지, 링크 등). 홍보/공유용 자료 관리.",
        "purpose": "이벤트 홍보 콘텐츠 현황 파악",
        "limitations": ["PII(user_email) 해싱 적용", "incremental 적재로 삭제 미반영"],
        "usage_examples": ["카드 유형(card_type)별 분포"],
        "tags": ["pseudolab", "event", "card", "content"],
    },
    "event_committee": {
        "title": "이벤트 위원회",
        "subtitle": "이벤트 조직위원 구성",
        "description": "이벤트 기획/운영 조직위원의 역할, 소속, 연락처 정보.",
        "purpose": "조직위 구성 이력 조회",
        "limitations": ["PII(name, email) 해싱 적용", "incremental 적재로 삭제 미반영"],
        "usage_examples": ["역할(role)별 위원 분포", "이벤트별 조직위 규모"],
        "tags": ["pseudolab", "event", "committee", "organization"],
    },
    "event_missions": {
        "title": "이벤트 미션",
        "subtitle": "이벤트 내 미션/퀘스트 정의",
        "description": "이벤트 참가자에게 부여되는 미션의 이름, XP 보상, 인증 방식 등 정의.",
        "purpose": "이벤트 참여 유도 미션 설계 분석",
        "limitations": ["incremental 적재로 삭제 미반영"],
        "usage_examples": ["미션 유형(mission_type)별 분포", "XP 보상 분포"],
        "tags": ["pseudolab", "event", "mission", "gamification"],
    },
    "event_participants": {
        "title": "이벤트 참가자",
        "subtitle": "이벤트 실제 참가 기록",
        "description": "이벤트별 실제 참가자와 참가 유형(온라인/오프라인 등) 기록.",
        "purpose": "참가 유형별 분포 분석",
        "limitations": ["incremental 적재로 삭제 미반영"],
        "usage_examples": ["참가 유형(participation_type)별 분포", "이벤트별 실참가자 수"],
        "tags": ["pseudolab", "event", "participant"],
    },
    "event_staff": {
        "title": "이벤트 스태프",
        "subtitle": "이벤트 운영 스태프 정보",
        "description": "이벤트 운영을 담당하는 스태프의 역할, 직함, 정렬 순서 등 관리.",
        "purpose": "스태프 구성 이력 조회",
        "limitations": ["PII(name, email) 해싱 적용", "incremental 적재로 삭제 미반영"],
        "usage_examples": ["역할(role)별 스태프 분포", "이벤트별 스태프 규모"],
        "tags": ["pseudolab", "event", "staff", "operations"],
    },
    "projects": {
        "title": "프로젝트 목록",
        "subtitle": "PseudoLab 스터디/프로젝트 마스터 데이터",
        "description": "스터디, 프로젝트의 기본 정보(제목, 유형, 상태, 코호트, 난이도, 미팅 정보 등)를 관리하는 마스터 테이블.",
        "purpose": "시즌별 프로젝트 현황 조회, 유형/난이도별 분포 분석",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관", "삭제된 프로젝트는 추적 불가"],
        "usage_examples": ["코호트(cohort)별 프로젝트 수 추이", "유형(type)별/난이도(difficulty)별 분포"],
        "tags": ["pseudolab", "project", "master", "study"],
    },
    "project_applications": {
        "title": "프로젝트 지원서",
        "subtitle": "프로젝트 참가 지원 접수 및 매칭 현황",
        "description": "프로젝트 참가 지원서. 지원자 정보, 지원 동기, 희망 프로젝트(1~3지망), 심사 상태 및 최종 매칭 결과를 관리.",
        "purpose": "시즌별 지원 현황, 매칭 성공률 분석",
        "limitations": ["PII(applicant_name_kr/en, applicant_email, applicant_phone) 해싱 적용", "스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["시즌별 지원서 수 추이", "심사 상태(status)별 분포"],
        "tags": ["pseudolab", "project", "application", "recruitment"],
    },
    "project_members": {
        "title": "프로젝트 멤버",
        "subtitle": "프로젝트별 참여 멤버 및 역할",
        "description": "프로젝트별 참여 멤버의 역할(러너, 빌더 등), 출석률, 참여 상태를 관리.",
        "purpose": "프로젝트별 멤버 구성 분석, 역할별 출석률 비교",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["역할(role)별 멤버 분포", "프로젝트별 평균 출석률"],
        "tags": ["pseudolab", "project", "member", "participation"],
    },
    "project_sessions": {
        "title": "프로젝트 세션",
        "subtitle": "주차별 스터디/미팅 세션",
        "description": "프로젝트별 주차(week_number)단위 세션 일정, 활성 상태, 설명을 관리.",
        "purpose": "프로젝트별 세션 진행률 추적",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["프로젝트별 세션 진행 현황(활성/비활성)", "주차별 세션 분포"],
        "tags": ["pseudolab", "project", "session", "meeting"],
    },
    "project_tasks": {
        "title": "프로젝트 태스크",
        "subtitle": "프로젝트 내 작업 관리",
        "description": "프로젝트별 태스크의 제목, 상태, 우선순위, 담당자, 진행률을 관리.",
        "purpose": "태스크 완료율 분석, 우선순위별 분포 파악",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["상태(status)별 태스크 분포", "프로젝트별 평균 진행률(progress)"],
        "tags": ["pseudolab", "project", "task", "management"],
    },
    "project_docs": {
        "title": "프로젝트 문서",
        "subtitle": "프로젝트 관련 문서 및 자료",
        "description": "프로젝트별 문서의 제목, 내용, 카테고리, 공개 여부를 관리.",
        "purpose": "프로젝트별 문서화 현황 파악",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["카테고리(category)별 문서 수", "공개/비공개 문서 비율"],
        "tags": ["pseudolab", "project", "document", "knowledge"],
    },
    "profiles": {
        "title": "사용자 프로필",
        "subtitle": "PseudoLab 멤버 프로필 및 활동 지표",
        "description": "멤버의 기본 정보(소속, 직군, 경험 수준), 활동 지표(레벨, 포인트, 활동 점수, 러너/빌더 횟수), 관심 키워드 등을 관리하는 핵심 테이블.",
        "purpose": "멤버 구성 분석, 경험 수준별/소속별 분포 파악, 활동 지표 분포 분석",
        "limitations": ["PII(email, name, name_kr) 해싱 적용", "스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["경험 수준(experience_level)별 멤버 분포", "레벨/포인트 분포 히스토그램"],
        "tags": ["pseudolab", "user", "profile", "master"],
    },
    "profile_careers": {
        "title": "멤버 경력",
        "subtitle": "멤버 경력/학력 이력",
        "description": "멤버의 경력 및 학력 이력. 직함, 유형(career_type), 역할, 재직 기간을 관리.",
        "purpose": "멤버 경력 배경 분석, 직군별 분포 파악",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["경력 유형(career_type)별 분포", "현재 재직 중(is_current) 멤버의 역할 분포"],
        "tags": ["pseudolab", "user", "career", "background"],
    },
    "user_which_projects": {
        "title": "멤버-프로젝트 매핑",
        "subtitle": "멤버와 프로젝트 연결 정보",
        "description": "멤버가 참여한 프로젝트 이름을 매핑하는 레거시 테이블.",
        "purpose": "멤버별 프로젝트 참여 이력 조회",
        "limitations": ["PII(name) 해싱 적용", "타임스탬프 없어 변경 추적 불가"],
        "usage_examples": ["멤버당 평균 프로젝트 참여 수", "프로젝트별 참여 멤버 수"],
        "tags": ["pseudolab", "user", "project", "mapping"],
    },
    "user_roles": {
        "title": "사용자 역할",
        "subtitle": "멤버 역할 부여 이력",
        "description": "멤버에게 부여된 역할(admin, builder, runner 등)의 이력을 추적.",
        "purpose": "역할별 멤버 분포 분석, 역할 부여 추이 파악",
        "limitations": ["incremental 적재로 삭제/변경 미반영"],
        "usage_examples": ["역할(role)별 멤버 수", "월별 역할 부여 추이"],
        "tags": ["pseudolab", "user", "role", "permission"],
    },
    "follows": {
        "title": "팔로우 관계",
        "subtitle": "멤버 간 팔로우 네트워크",
        "description": "멤버 간 팔로우 관계 데이터. 소셜 그래프 분석의 기초 데이터.",
        "purpose": "커뮤니티 소셜 네트워크 분석, 핵심 인물 파악",
        "limitations": ["incremental 적재로 언팔로우(삭제) 미반영"],
        "usage_examples": ["팔로워 수 상위 멤버", "팔로우 관계 증가 추이"],
        "tags": ["pseudolab", "user", "follow", "social"],
    },
    "user_follows": {
        "title": "프로그램 팔로우",
        "subtitle": "프로그램 단위 팔로우 관계",
        "description": "특정 프로그램(program_id) 맥락에서의 팔로우 관계. 이메일 기반 매핑.",
        "purpose": "프로그램별 팔로우 네트워크 분석",
        "limitations": ["PII(follower_email, following_email) 해싱 적용", "incremental 적재로 삭제 미반영"],
        "usage_examples": ["프로그램별 팔로우 관계 수"],
        "tags": ["pseudolab", "user", "follow", "program"],
    },
    "user_influences": {
        "title": "멤버 영향력",
        "subtitle": "멤버 간 영향력 기록",
        "description": "멤버가 다른 멤버에게 미친 영향력을 기록. 맥락(context_type, context_id)과 메시지 포함.",
        "purpose": "영향력 네트워크 분석, 핵심 멘토/리더 파악",
        "limitations": ["incremental 적재로 삭제 미반영"],
        "usage_examples": ["영향력 수신 상위 멤버", "맥락 유형(context_type)별 영향력 분포"],
        "tags": ["pseudolab", "user", "influence", "network"],
    },
    "legacy_members": {
        "title": "레거시 멤버",
        "subtitle": "기존 시스템 멤버 데이터",
        "description": "이전 시스템에서 마이그레이션된 역사적 멤버 데이터. 아카이브 성격.",
        "purpose": "초기 멤버 이력 참조, 마이그레이션 검증",
        "limitations": ["PII(email, name) 해싱 적용", "더 이상 업데이트되지 않는 레거시 데이터"],
        "usage_examples": ["레거시 멤버의 코호트(cohorts) 분포", "역할(role)별 초기 멤버 구성"],
        "tags": ["pseudolab", "user", "legacy", "archive"],
    },
    "project_attendance": {
        "title": "프로젝트 출석",
        "subtitle": "세션별 출석 기록",
        "description": "프로젝트 세션별 멤버 출석 상태(출석, 지각, 결석 등)를 기록.",
        "purpose": "프로젝트별/멤버별 출석률 분석",
        "limitations": ["incremental 적재로 삭제 미반영"],
        "usage_examples": ["상태(status)별 출석 분포", "프로젝트별 평균 출석률 추이"],
        "tags": ["pseudolab", "user", "attendance", "project"],
    },
    "blogs": {
        "title": "블로그",
        "subtitle": "멤버 블로그 게시글",
        "description": "멤버가 작성한 블로그 게시글. 제목, 내용, 태그, 조회수, 큐레이션 여부를 관리.",
        "purpose": "콘텐츠 생산 추이 분석, 인기 주제 파악",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["유형(type)별 게시글 분포", "큐레이션(is_curated) 게시글 비율"],
        "tags": ["pseudolab", "community", "blog", "content"],
    },
    "community_feed": {
        "title": "커뮤니티 피드",
        "subtitle": "커뮤니티 활동 피드",
        "description": "다양한 유형(type)의 커뮤니티 활동 피드. URL, 메타데이터, 카테고리를 포함.",
        "purpose": "커뮤니티 활동 유형별 분포 분석, 인기 피드 파악",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["유형(type)별 피드 분포", "카테고리별 조회수 분포"],
        "tags": ["pseudolab", "community", "feed", "activity"],
    },
    "highlights": {
        "title": "하이라이트",
        "subtitle": "주요 활동 하이라이트",
        "description": "프로젝트, 멤버의 주요 활동/성과를 소개하는 하이라이트 콘텐츠.",
        "purpose": "하이라이트 콘텐츠 현황, featured 활용도 분석",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["하이라이트 유형(highlight_type)별 분포", "featured 게시글 비율 및 조회수 비교"],
        "tags": ["pseudolab", "community", "highlight", "showcase"],
    },
    "feed_comments": {
        "title": "피드 댓글",
        "subtitle": "커뮤니티 피드 댓글",
        "description": "커뮤니티 피드에 달린 댓글.",
        "purpose": "피드별 댓글 참여도 분석",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["피드당 평균 댓글 수"],
        "tags": ["pseudolab", "community", "comment", "feed"],
    },
    "resource_comments": {
        "title": "리소스 댓글",
        "subtitle": "리소스에 대한 댓글",
        "description": "리소스(resource_id)에 달린 댓글. 대댓글(parent_id) 구조 지원.",
        "purpose": "리소스별 토론 활성도 분석",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["리소스당 평균 댓글 수", "대댓글 비율"],
        "tags": ["pseudolab", "community", "comment", "resource"],
    },
    "highlight_comments": {
        "title": "하이라이트 댓글",
        "subtitle": "하이라이트 게시글 댓글",
        "description": "하이라이트 게시글에 달린 댓글. 대댓글(parent_id) 구조 지원.",
        "purpose": "하이라이트별 반응 분석",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["하이라이트당 평균 댓글 수"],
        "tags": ["pseudolab", "community", "comment", "highlight"],
    },
    "highlight_likes": {
        "title": "하이라이트 좋아요",
        "subtitle": "하이라이트 게시글 좋아요 기록",
        "description": "하이라이트 게시글에 대한 좋아요 기록.",
        "purpose": "인기 하이라이트 파악, 좋아요 추이 분석",
        "limitations": ["incremental 적재로 좋아요 취소(삭제) 미반영"],
        "usage_examples": ["좋아요 수 상위 하이라이트", "월별 좋아요 증가 추이"],
        "tags": ["pseudolab", "community", "like", "highlight"],
    },
    "dormitory_messages": {
        "title": "기숙사 메시지",
        "subtitle": "기숙사 채팅 메시지",
        "description": "기숙사(dormitory) 단위 채팅 메시지.",
        "purpose": "기숙사별 메시지 활성도 분석",
        "limitations": ["incremental 적재로 삭제 미반영"],
        "usage_examples": ["기숙사(dormitory)별 메시지 수", "월별 메시지 추이"],
        "tags": ["pseudolab", "community", "dormitory", "chat"],
    },
    "secret_posts": {
        "title": "비밀 게시글",
        "subtitle": "익명 게시판 게시글",
        "description": "익명 게시판의 게시글. 카테고리, 반응(동의/유용), 조회수, hot 여부를 관리.",
        "purpose": "익명 게시판 활성도 분석, 인기 카테고리 파악",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["카테고리별 게시글 분포", "hot 게시글 비율"],
        "tags": ["pseudolab", "secret", "post", "anonymous"],
    },
    "secret_profiles": {
        "title": "비밀 프로필",
        "subtitle": "익명 게시판 닉네임 프로필",
        "description": "익명 게시판에서 사용하는 닉네임과 공유 횟수를 관리.",
        "purpose": "익명 활동 참여자 규모 파악",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["비밀 프로필 보유 멤버 수", "공유 횟수(share_count) 분포"],
        "tags": ["pseudolab", "secret", "profile"],
    },
    "secret_comments": {
        "title": "비밀 댓글",
        "subtitle": "익명 게시판 댓글",
        "description": "익명 게시판 게시글에 달린 댓글.",
        "purpose": "익명 게시판 댓글 참여도 분석",
        "limitations": ["incremental 적재로 삭제 미반영"],
        "usage_examples": ["게시글당 평균 댓글 수", "월별 댓글 증가 추이"],
        "tags": ["pseudolab", "secret", "comment"],
    },
    "secret_interactions": {
        "title": "비밀 반응",
        "subtitle": "익명 게시판 반응/인터랙션",
        "description": "익명 게시판 게시글에 대한 반응(interaction_type)을 기록.",
        "purpose": "반응 유형별 분포 분석, 게시글 인기도 측정",
        "limitations": ["incremental 적재로 삭제 미반영"],
        "usage_examples": ["반응 유형(interaction_type)별 분포"],
        "tags": ["pseudolab", "secret", "interaction", "reaction"],
    },
    "bug_reports": {
        "title": "버그 리포트",
        "subtitle": "버그 신고 접수 및 처리 현황",
        "description": "플랫폼 버그 신고 내용, 상태(open/resolved 등), 유형, 관련 페이지 URL을 관리.",
        "purpose": "버그 상태별 현황 파악, 유형별 분포 분석",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["상태(status)별 버그 분포", "유형(type)별 버그 빈도"],
        "tags": ["pseudolab", "bug", "report", "quality"],
    },
    "bug_comments": {
        "title": "버그 댓글",
        "subtitle": "버그 리포트 토론 댓글",
        "description": "버그 리포트에 달린 댓글.",
        "purpose": "버그별 토론 참여도 분석",
        "limitations": ["incremental 적재로 삭제 미반영"],
        "usage_examples": ["버그당 평균 댓글 수"],
        "tags": ["pseudolab", "bug", "comment"],
    },
    "bug_events": {
        "title": "버그 이벤트",
        "subtitle": "버그 상태 변경 이력",
        "description": "버그의 상태 변경, 담당자 배정 등 이벤트 이력.",
        "purpose": "버그 처리 흐름 분석, 평균 처리 시간 파악",
        "limitations": ["incremental 적재로 삭제 미반영"],
        "usage_examples": ["이벤트 유형(event_type)별 분포"],
        "tags": ["pseudolab", "bug", "event", "workflow"],
    },
    "bug_assignees": {
        "title": "버그 담당자",
        "subtitle": "버그별 담당자 배정 기록",
        "description": "버그 리포트에 배정된 담당자 기록.",
        "purpose": "담당자별 버그 처리 현황 분석",
        "limitations": ["incremental 적재로 배정 해제 미반영"],
        "usage_examples": ["담당자별 배정 버그 수"],
        "tags": ["pseudolab", "bug", "assignee"],
    },
    "badges": {
        "title": "뱃지 정의",
        "subtitle": "뱃지 마스터 데이터",
        "description": "커뮤니티 뱃지의 이름, 설명, 카테고리, 포인트, 희귀도(rarity) 등 정의 데이터.",
        "purpose": "뱃지 체계 현황 파악, 카테고리/희귀도별 분포",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["카테고리별 뱃지 수", "희귀도(rarity)별 분포"],
        "tags": ["pseudolab", "gamification", "badge", "master"],
    },
    "quest_definitions": {
        "title": "퀘스트 정의",
        "subtitle": "퀘스트/챌린지 마스터 데이터",
        "description": "퀘스트의 이름, 설명, 목표 횟수(target_count), XP 보상, 유형, 활성 상태를 정의.",
        "purpose": "퀘스트 설계 현황 파악, 보상 체계 분석",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["유형(type)별 퀘스트 분포", "XP 보상 분포"],
        "tags": ["pseudolab", "gamification", "quest", "master"],
    },
    "user_missions": {
        "title": "미션 달성",
        "subtitle": "멤버별 미션 완료 현황",
        "description": "멤버가 완료한 미션의 달성 시점, 인증 데이터, 검증 여부를 관리.",
        "purpose": "미션 달성률 분석, 인기 미션 파악",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["미션별 달성 멤버 수", "검증(verified) 비율"],
        "tags": ["pseudolab", "gamification", "mission", "achievement"],
    },
    "user_badges": {
        "title": "뱃지 획득",
        "subtitle": "멤버별 뱃지 획득 이력",
        "description": "멤버가 획득한 뱃지 이력. 이벤트 연계 뱃지와 인증 데이터를 포함.",
        "purpose": "뱃지별 획득률 분석, 인기 뱃지 파악",
        "limitations": ["incremental 적재로 뱃지 회수(삭제) 미반영"],
        "usage_examples": ["뱃지별 획득 멤버 수", "월별 뱃지 발급 추이"],
        "tags": ["pseudolab", "gamification", "badge", "achievement"],
    },
    "user_quests": {
        "title": "퀘스트 달성",
        "subtitle": "멤버별 퀘스트 완료 이력",
        "description": "멤버가 완료한 퀘스트 이력과 달성 시점을 기록.",
        "purpose": "퀘스트별 달성률 분석, 참여도 측정",
        "limitations": ["incremental 적재로 삭제 미반영"],
        "usage_examples": ["퀘스트별 달성 멤버 수", "월별 퀘스트 달성 추이"],
        "tags": ["pseudolab", "gamification", "quest", "achievement"],
    },
    "xp_history": {
        "title": "XP 이력",
        "subtitle": "멤버별 경험치 획득 이력",
        "description": "멤버의 XP 획득/차감 이력. 사유(reason), 카테고리, 수량을 기록.",
        "purpose": "XP 획득 패턴 분석, 카테고리별 XP 분포 파악",
        "limitations": ["incremental 적재로 삭제 미반영"],
        "usage_examples": ["카테고리별 XP 총합", "월별 XP 발급 추이"],
        "tags": ["pseudolab", "gamification", "xp", "reward"],
    },
    "builder_onboarding": {
        "title": "빌더 온보딩",
        "subtitle": "빌더 온보딩 체크리스트 진행 현황",
        "description": "빌더의 온보딩 단계별 체크리스트 완료 여부를 추적.",
        "purpose": "온보딩 완료율 분석, 단계별 병목 파악",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["체크리스트 항목별 완료율", "프로젝트별 온보딩 진행 현황"],
        "tags": ["pseudolab", "recruitment", "onboarding", "builder"],
    },
    "recruit_applications": {
        "title": "운영진 지원",
        "subtitle": "운영진 모집 지원서 현황",
        "description": "운영진 모집 지원서. 시즌, 역할, 심사 상태, 지원 답변(answers JSON)을 관리.",
        "purpose": "시즌별/역할별 지원 현황 분석",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["시즌별 지원서 수", "역할(role)별 지원 분포"],
        "tags": ["pseudolab", "recruitment", "application", "staff"],
    },
    "registration_submissions": {
        "title": "가입 신청서",
        "subtitle": "신규 멤버 가입 신청 현황",
        "description": "신규 멤버 가입 신청서. 등록 유형, 소속, 직군, 경험 수준, 관심 키워드를 포함.",
        "purpose": "신규 가입 추이, 멤버 배경 분석",
        "limitations": ["PII(name, email) 해싱 적용", "스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["등록 유형(registration_type)별 분포", "경험 수준(experience_level)별 분포"],
        "tags": ["pseudolab", "recruitment", "registration", "onboarding"],
    },
    "project_application_history": {
        "title": "지원 이력",
        "subtitle": "프로젝트 지원 상태 변경 이력",
        "description": "프로젝트 지원서의 상태 변경 이력. 시즌, 지망 슬롯, 액션 유형을 기록.",
        "purpose": "지원 프로세스 흐름 분석, 상태 변경 패턴 파악",
        "limitations": ["PII(applicant_name_kr) 해싱 적용", "incremental 적재로 삭제 미반영"],
        "usage_examples": ["액션 유형(action_type)별 분포", "시즌별 지원 이력 수"],
        "tags": ["pseudolab", "recruitment", "application", "history"],
    },
    "opportunities": {
        "title": "기회 목록",
        "subtitle": "멤버 기회 정보 마스터 데이터",
        "description": "멤버에게 제공되는 기회(대회, 장학금, 인턴, 콘퍼런스 등)의 제목, 카테고리, 마감일, 태그, 활성 상태를 관리.",
        "purpose": "카테고리별 기회 분포 파악, 활성 기회 현황 조회",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["카테고리별 기회 분포", "활성(is_active) 기회 수"],
        "tags": ["pseudolab", "opportunity", "master"],
    },
    "opportunity_beneficiaries": {
        "title": "기회 수혜자",
        "subtitle": "기회별 지원/수혜 현황",
        "description": "기회별 지원자의 지원 사유, 심사 상태, 리뷰 URL을 관리.",
        "purpose": "기회별 지원/수혜 현황 분석",
        "limitations": ["PII(beneficiary_name) 해싱 적용", "스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["기회별 지원자 수", "심사 상태(status)별 분포"],
        "tags": ["pseudolab", "opportunity", "beneficiary", "application"],
    },
    "opportunity_likes": {
        "title": "기회 관심",
        "subtitle": "기회 좋아요 기록",
        "description": "멤버가 기회에 누른 좋아요 기록.",
        "purpose": "인기 기회 파악, 관심도 추이 분석",
        "limitations": ["incremental 적재로 좋아요 취소 미반영"],
        "usage_examples": ["좋아요 수 상위 기회", "월별 좋아요 추이"],
        "tags": ["pseudolab", "opportunity", "like", "interest"],
    },
    "wiki_articles": {
        "title": "위키 문서",
        "subtitle": "위키 문서 마스터 데이터",
        "description": "위키 문서의 제목, 슬러그, 내용, 카테고리, 발행 상태, 조회수를 관리.",
        "purpose": "위키 콘텐츠 현황 파악, 인기 문서 분석",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["카테고리별 문서 수", "조회수 상위 문서"],
        "tags": ["pseudolab", "wiki", "article", "knowledge"],
    },
    "wiki_categories": {
        "title": "위키 카테고리",
        "subtitle": "위키 카테고리 분류 체계",
        "description": "위키 카테고리의 이름, 슬러그, 설명, 아이콘을 관리.",
        "purpose": "위키 분류 체계 파악",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["카테고리 계층 구조 조회"],
        "tags": ["pseudolab", "wiki", "category", "taxonomy"],
    },
    "wiki_pages": {
        "title": "위키 페이지",
        "subtitle": "카테고리 소속 위키 페이지",
        "description": "카테고리에 속한 위키 페이지의 제목, 슬러그, 내용, 조회수, 발행 상태를 관리.",
        "purpose": "카테고리별 페이지 분포 파악, 인기 페이지 분석",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["카테고리별 페이지 수", "조회수 상위 페이지"],
        "tags": ["pseudolab", "wiki", "page", "content"],
    },
    "wiki_revisions": {
        "title": "위키 수정 이력",
        "subtitle": "위키 문서/페이지 편집 이력",
        "description": "위키 문서의 수정 이력. 편집 내용, 변경 요약, 리뷰 상태를 기록.",
        "purpose": "위키 편집 활동 분석, 기여자 파악",
        "limitations": ["incremental 적재로 삭제 미반영"],
        "usage_examples": ["월별 편집 횟수 추이", "기여자별 편집 횟수"],
        "tags": ["pseudolab", "wiki", "revision", "history"],
    },
    "squads": {
        "title": "스쿼드 목록",
        "subtitle": "소규모 협업 스쿼드 마스터 데이터",
        "description": "소규모 협업 스쿼드의 제목, 설명, 프로젝트 유형, 기간, 기술 스택, 상태를 관리.",
        "purpose": "스쿼드 운영 현황 파악, 프로젝트 유형/기술 스택별 분포 분석",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["프로젝트 유형(project_type)별 분포", "상태(status)별 스쿼드 현황"],
        "tags": ["pseudolab", "squad", "collaboration", "team"],
    },
    "squad_applications": {
        "title": "스쿼드 지원",
        "subtitle": "스쿼드 참여 지원 현황",
        "description": "스쿼드 참여 지원서. 지원 슬롯 번호, 메시지, 심사 상태를 관리.",
        "purpose": "스쿼드별 지원 현황, 매칭 성공률 분석",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["스쿼드당 평균 지원 수", "심사 상태(status)별 분포"],
        "tags": ["pseudolab", "squad", "application"],
    },
    "random_squad_queue": {
        "title": "랜덤 스쿼드 대기열",
        "subtitle": "랜덤 매칭 대기 현황",
        "description": "랜덤 스쿼드 매칭 대기열. 리더 가능 여부, 매칭 상태, 매칭된 스쿼드 ID를 관리.",
        "purpose": "랜덤 매칭 대기 현황, 매칭 성공률 분석",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["대기 상태(status)별 분포", "매칭 성공률"],
        "tags": ["pseudolab", "squad", "matching", "queue"],
    },
    "magic_maps": {
        "title": "매직 맵",
        "subtitle": "매직스쿨 맵 설계 데이터",
        "description": "매직스쿨의 맵 정의. 타일 구성, 발견 요소, 해금 규칙을 관리. JSON 구조.",
        "purpose": "맵 설계 현황 파악, 콘텐츠 규모 분석",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관", "JSON 필드 내부 분석 필요"],
        "usage_examples": ["맵별 타일/발견 요소 수"],
        "tags": ["pseudolab", "magic", "map", "content"],
    },
    "magic_progress": {
        "title": "매직 진행률",
        "subtitle": "멤버별 매직스쿨 탐험 진행 현황",
        "description": "멤버별 맵 탐험 진행 상태. 발견한 타일, 획득 카드/뱃지, 일일 이동 횟수를 관리.",
        "purpose": "멤버별 진행률 분석, 일일 활동량 파악",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관", "JSON 필드 내부 분석 필요"],
        "usage_examples": ["맵별 평균 진행률", "일일 이동 횟수(daily_moves) 분포"],
        "tags": ["pseudolab", "magic", "progress", "exploration"],
    },
    "session_submissions": {
        "title": "세션 제출",
        "subtitle": "발표 세션 제안서 접수 현황",
        "description": "발표 세션 제안서. 제목, 발표자명, 소요 시간, 대상 청중을 포함.",
        "purpose": "세션 제안 트렌드 분석, 주제 다양성 파악",
        "limitations": ["PII(speaker_name, email) 해싱 적용", "incremental 적재로 삭제 미반영"],
        "usage_examples": ["월별 세션 제안 수 추이", "소요 시간(duration)별 분포"],
        "tags": ["pseudolab", "submission", "session", "proposal"],
    },
    "speaker_submissions": {
        "title": "스피커 제출",
        "subtitle": "외부 스피커 지원서 접수 현황",
        "description": "외부 스피커 지원서. 주제, 약력, 발표 개요, 포트폴리오 URL을 포함.",
        "purpose": "외부 스피커 지원 트렌드, 주제 분포 분석",
        "limitations": ["PII(speaker_name, email) 해싱 적용", "incremental 적재로 삭제 미반영"],
        "usage_examples": ["제출 유형(submission_type)별 분포"],
        "tags": ["pseudolab", "submission", "speaker"],
    },
    "sponsor_submissions": {
        "title": "스폰서 제출",
        "subtitle": "후원사 지원서 접수 현황",
        "description": "후원사 지원서. 회사명, 후원 등급, 메시지, 로고 URL을 포함.",
        "purpose": "후원 지원 트렌드 분석",
        "limitations": ["PII(contact_name, email, phone) 해싱 적용", "incremental 적재로 삭제 미반영"],
        "usage_examples": ["후원 등급(sponsorship_level)별 분포"],
        "tags": ["pseudolab", "submission", "sponsor"],
    },
    "sponsorship_requests": {
        "title": "후원 요청",
        "subtitle": "후원/협찬 요청 접수 현황",
        "description": "외부로부터의 후원/협찬 요청. 요청자 이름, 소속, 후원 유형, 메시지를 포함.",
        "purpose": "후원 요청 현황 분석, 후원 유형별 분포 파악",
        "limitations": ["PII(name, email) 해싱 적용", "incremental 적재로 삭제 미반영"],
        "usage_examples": ["후원 유형(sponsorship_type)별 분포"],
        "tags": ["pseudolab", "submission", "sponsorship", "request"],
    },
    "page_views": {
        "title": "페이지뷰",
        "subtitle": "플랫폼 페이지 조회 기록",
        "description": "플랫폼 페이지 조회 기록. ID와 조회 시점(viewed_at)만 포함하는 경량 로그.",
        "purpose": "플랫폼 트래픽 추이 분석",
        "limitations": ["viewed_at 기준 추출(created_at 없음)", "incremental 적재"],
        "usage_examples": ["일별/월별 페이지뷰 추이", "시간대별 트래픽 패턴"],
        "tags": ["pseudolab", "engagement", "pageview", "analytics"],
    },
    "notifications": {
        "title": "알림",
        "subtitle": "멤버 알림 발송 기록",
        "description": "멤버에게 발송된 알림. 유형(type), 대상 엔티티, 읽음 여부를 관리.",
        "purpose": "알림 유형별 분포 분석, 읽음률 파악",
        "limitations": ["incremental 적재로 삭제 미반영"],
        "usage_examples": ["알림 유형(type)별 분포", "읽음(is_read) 비율"],
        "tags": ["pseudolab", "engagement", "notification"],
    },
    "program_feedbacks": {
        "title": "프로그램 피드백",
        "subtitle": "프로그램별 피드백 접수 현황",
        "description": "프로그램에 대한 멤버 피드백.",
        "purpose": "프로그램별 피드백 현황 분석",
        "limitations": ["PII(user_email) 해싱 적용", "incremental 적재로 삭제 미반영"],
        "usage_examples": ["프로그램별 피드백 수"],
        "tags": ["pseudolab", "engagement", "feedback", "program"],
    },
    "program_followups": {
        "title": "프로그램 팔로업",
        "subtitle": "프로그램 후속 활동 기록",
        "description": "프로그램 후속 활동(팔로업) 기록.",
        "purpose": "프로그램별 팔로업 참여 현황 분석",
        "limitations": ["PII(user_email) 해싱 적용", "incremental 적재로 삭제 미반영"],
        "usage_examples": ["프로그램별 팔로업 참여 수"],
        "tags": ["pseudolab", "engagement", "followup", "program"],
    },
    "program_likes": {
        "title": "프로그램 좋아요",
        "subtitle": "프로그램 관심 표시 기록",
        "description": "프로그램에 대한 멤버 좋아요 기록.",
        "purpose": "인기 프로그램 파악, 관심도 추이 분석",
        "limitations": ["PII(user_email) 해싱 적용", "incremental 적재로 좋아요 취소 미반영"],
        "usage_examples": ["좋아요 수 상위 프로그램"],
        "tags": ["pseudolab", "engagement", "like", "program"],
    },
    "resource_reactions": {
        "title": "리소스 반응",
        "subtitle": "리소스별 반응/리액션 기록",
        "description": "리소스에 대한 멤버 반응 기록. 반응 유형(reaction_type)을 포함.",
        "purpose": "반응 유형별 분포 분석, 인기 리소스 파악",
        "limitations": ["incremental 적재로 반응 취소 미반영"],
        "usage_examples": ["반응 유형(reaction_type)별 분포"],
        "tags": ["pseudolab", "engagement", "reaction", "resource"],
    },
    "artifact_logs": {
        "title": "아티팩트 로그",
        "subtitle": "기숙사별 아티팩트 활동 기록",
        "description": "기숙사(dormitory) 단위 아티팩트 활동 로그.",
        "purpose": "기숙사별 활동량 비교 분석",
        "limitations": ["incremental 적재로 삭제 미반영"],
        "usage_examples": ["기숙사(dormitory)별 활동 횟수"],
        "tags": ["pseudolab", "engagement", "artifact", "dormitory"],
    },
    "action_items": {
        "title": "액션 아이템",
        "subtitle": "멤버별 할 일 관리",
        "description": "멤버에게 할당된 액션 아이템. 유형, 제목, 우선순위, 마감일, 완료 여부를 관리.",
        "purpose": "액션 아이템 완료율 분석, 우선순위별 분포 파악",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["유형(type)별 액션 아이템 분포", "완료율(is_completed) 분석"],
        "tags": ["pseudolab", "system", "action", "task"],
    },
    "admin_calendar_events": {
        "title": "관리자 일정",
        "subtitle": "운영진 캘린더 이벤트",
        "description": "운영진 캘린더에 등록된 일정. 제목, 설명, 시작/종료 시간, 이벤트 유형을 관리.",
        "purpose": "운영진 일정 현황 파악",
        "limitations": ["스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["이벤트 유형(event_type)별 일정 분포"],
        "tags": ["pseudolab", "system", "calendar", "admin"],
    },
    "email_verification_codes": {
        "title": "이메일 인증",
        "subtitle": "이메일 인증 코드 발급 현황",
        "description": "이메일 인증 코드의 발급, 만료, 인증 완료 여부를 관리.",
        "purpose": "인증 완료율 분석, 인증 프로세스 효율 파악",
        "limitations": ["PII(email, code) 해싱 적용", "스냅샷 방식으로 최근 30일만 D1 보관"],
        "usage_examples": ["인증 완료(verified) 비율"],
        "tags": ["pseudolab", "system", "verification", "auth"],
    },
}


# ---------------------------------------------------------------------------
# 데이터 빌더
# ---------------------------------------------------------------------------

def _dataset_id(table_name: str) -> str:
    """테이블명 → dataset ID (underscore → hyphen)."""
    return f"pseudolab.{table_name.replace('_', '-')}.v1"


def _coverage_summary(table_def: TableDef) -> str:
    if table_def.mode == "snapshot":
        return "Supabase → D1 daily snapshot, 최근 30일 보관"
    return "Supabase → D1 daily incremental, 누적 적재"


def _column_description(table_name: str, col_name: str) -> str:
    """패턴 기반 컬럼 설명 생성."""
    if col_name == "id":
        return "레코드 고유 ID (PK)."
    if col_name == "base_date":
        return "ETL 배치 기준일 (YYYY-MM-DD)."
    if col_name == "load_dt":
        return "D1 적재 시각 (ISO-8601)."
    if col_name == "created_at":
        return "레코드 생성 시각."
    if col_name == "updated_at":
        return "레코드 최종 수정 시각."
    if col_name.endswith("_id"):
        return f"연관 엔터티 `{col_name}` 외래키."
    if col_name.startswith("is_"):
        return f"`{col_name}` 여부를 나타내는 불리언 플래그."
    if col_name.endswith("_at"):
        return f"`{col_name}` 시각."
    if col_name.endswith("_url"):
        return f"`{col_name}` URL."
    if col_name.endswith("_count"):
        return f"`{col_name}` 수치."
    return f"`{table_name}` 테이블의 `{col_name}` 속성."


def build_column_metadata(table_def: TableDef) -> list[dict[str, Any]]:
    """TableDef의 컬럼 + 시스템 컬럼(base_date, load_dt) 메타데이터 생성."""
    columns: list[dict[str, Any]] = []

    for col in table_def.columns:
        columns.append({
            "column_name": col.name,
            "data_type": pg_to_d1_type(col.pg_type),
            "description": _column_description(table_def.name, col.name),
            "is_pii": col.name in table_def.pii_columns,
            "examples": None,
        })

    # 시스템 컬럼 (schema.py가 모든 dl_* 테이블에 추가)
    columns.append({
        "column_name": "base_date",
        "data_type": "TEXT",
        "description": "ETL 배치 기준일 (YYYY-MM-DD).",
        "is_pii": False,
        "examples": None,
    })
    columns.append({
        "column_name": "load_dt",
        "data_type": "TEXT",
        "description": "D1 적재 시각 (ISO-8601).",
        "is_pii": False,
        "examples": None,
    })

    return columns


def build_lineage(table_def: TableDef) -> dict[str, Any]:
    """Supabase source → dl_* target 리니지 그래프."""
    dataset_id = _dataset_id(table_def.name)
    source_id = "pseudolab.supabase-source"

    return {
        "version": 1,
        "nodes": [
            {
                "id": source_id,
                "type": "dataset",
                "position": {"x": -280, "y": 0},
                "data": {
                    "datasetId": source_id,
                    "label": f"Supabase {table_def.name}",
                    "domain": "pseudolab",
                },
            },
            {
                "id": dataset_id,
                "type": "dataset",
                "position": {"x": 0, "y": 0},
                "data": {
                    "datasetId": dataset_id,
                    "label": f"{table_def.dl_name}",
                    "domain": "pseudolab",
                },
            },
        ],
        "edges": [
            {
                "id": f"{source_id}->{dataset_id}:etl",
                "source": source_id,
                "target": dataset_id,
                "data": {"step": "supabase-etl"},
                "label": "supabase-etl",
            },
        ],
    }


def build_dataset_snapshot(table_def: TableDef) -> dict[str, Any]:
    """하나의 테이블 → PUT snapshot payload 생성."""
    dataset_id = _dataset_id(table_def.name)
    meta = TABLE_METADATA.get(table_def.name, {})
    category = TABLE_CATEGORY.get(table_def.name, "system")

    return {
        "dataset_id": dataset_id,
        "snapshot": {
            "dataset": {
                "id": dataset_id,
                "domain": "pseudolab",
                "name": table_def.dl_name,
                "description": meta.get("description", f"{table_def.name} 테이블."),
                "schema_json": {
                    "version": 1,
                    "source_table": table_def.name,
                    "dl_table": table_def.dl_name,
                    "mode": table_def.mode,
                },
                "owner": "pseudolab-data",
                "tags": meta.get("tags", ["pseudolab"]),
                "purpose": meta.get("purpose"),
                "limitations": meta.get("limitations", []),
                "usage_examples": meta.get("usage_examples", []),
            },
            "columns": build_column_metadata(table_def),
            "lineage": build_lineage(table_def),
        },
    }


def build_all_snapshots() -> list[dict[str, Any]]:
    """79개 테이블 전체 스냅샷 빌드."""
    return [
        build_dataset_snapshot(table_def)
        for table_def in sorted(ALL_TABLES.values(), key=lambda t: t.name)
    ]


# ---------------------------------------------------------------------------
# HTTP 클라이언트
# ---------------------------------------------------------------------------

@dataclass
class SyncError:
    dataset_id: str
    stage: str
    message: str


@dataclass
class SyncSummary:
    datasets_total: int = 0
    datasets_succeeded: int = 0
    dataset_errors: list[SyncError] = field(default_factory=list)
    lineage_errors: list[SyncError] = field(default_factory=list)

    @property
    def errors(self) -> list[SyncError]:
        return [*self.dataset_errors, *self.lineage_errors]


def _backoff_seconds(attempt: int, base: float = 0.5, cap: float = 30.0) -> float:
    delay = min(base * (2**attempt), cap)
    jitter = random.uniform(0, 0.2 * delay)
    return delay + jitter


def _request_with_retry(
    *,
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any],
    timeout_sec: float = 10.0,
    max_retries: int = 3,
) -> tuple[bool, int | None, str | None]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=timeout_sec) as client:
        for attempt in range(max_retries + 1):
            try:
                response = client.request(method, url, headers=headers, json=payload)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt >= max_retries:
                    return False, None, str(exc)
                time.sleep(_backoff_seconds(attempt))
                continue

            if response.status_code < 400:
                return True, response.status_code, None

            if response.status_code in RETRYABLE_STATUS_CODES and attempt < max_retries:
                retry_after = response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    time.sleep(float(retry_after))
                else:
                    time.sleep(_backoff_seconds(attempt))
                continue

            return False, response.status_code, response.text

    return False, None, "unknown retry loop failure"


def put_dataset_snapshot(
    base_url: str, token: str, dataset_id: str, payload: dict[str, Any],
) -> tuple[bool, int | None, str | None]:
    encoded_id = quote(dataset_id, safe="")
    url = f"{base_url.rstrip('/')}/catalog/datasets/{encoded_id}/snapshot"
    return _request_with_retry(method="PUT", url=url, token=token, payload=payload)


def put_lineage(
    base_url: str, token: str, dataset_id: str, lineage: dict[str, Any],
) -> tuple[bool, int | None, str | None]:
    encoded_id = quote(dataset_id, safe="")
    url = f"{base_url.rstrip('/')}/catalog/lineage/{encoded_id}"
    return _request_with_retry(method="PUT", url=url, token=token, payload=lineage)


def sync_catalog(
    *,
    base_url: str,
    token: str,
    dry_run: bool = False,
) -> SyncSummary:
    summary = SyncSummary()
    snapshots = build_all_snapshots()
    summary.datasets_total = len(snapshots)

    for item in snapshots:
        dataset_id = item["dataset_id"]
        snapshot = item["snapshot"]
        lineage = snapshot.get("lineage")

        if dry_run:
            logger.info("[catalog-sync][dry-run] dataset=%s", dataset_id)
            summary.datasets_succeeded += 1
            continue

        ok, status, detail = put_dataset_snapshot(
            base_url=base_url, token=token, dataset_id=dataset_id, payload=snapshot,
        )
        if not ok:
            summary.dataset_errors.append(
                SyncError(dataset_id=dataset_id, stage="snapshot",
                          message=f"status={status}, detail={detail}")
            )
            continue

        if isinstance(lineage, dict):
            ok_l, status_l, detail_l = put_lineage(
                base_url=base_url, token=token, dataset_id=dataset_id, lineage=lineage,
            )
            if not ok_l:
                summary.lineage_errors.append(
                    SyncError(dataset_id=dataset_id, stage="lineage",
                              message=f"status={status_l}, detail={detail_l}")
                )

        summary.datasets_succeeded += 1

    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="PseudoLab catalog sync")
    parser.add_argument("--base-url", required=True, help="Workers API base URL")
    parser.add_argument("--token", required=True, help="Internal bearer token")
    parser.add_argument("--dry-run", action="store_true", help="Log payloads without sending")
    args = parser.parse_args()

    result = sync_catalog(base_url=args.base_url, token=args.token, dry_run=args.dry_run)

    logger.info(
        "sync complete: total=%d succeeded=%d errors=%d",
        result.datasets_total,
        result.datasets_succeeded,
        len(result.errors),
    )
    for err in result.errors:
        logger.error("  %s [%s] %s", err.dataset_id, err.stage, err.message)

    if result.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
