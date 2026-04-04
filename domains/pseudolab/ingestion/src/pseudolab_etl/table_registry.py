"""79개 Supabase 테이블 정의 레지스트리.

postgres_table.md + SUMMARY.md + pii_deidentification.md 기반 정적 정의.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pseudolab_etl.pii import PII_COLUMNS

# ── 데이터 구조 ──────────────────────────────────────────

_T = "timestamp with time zone"


@dataclass(frozen=True)
class ColumnDef:
    name: str
    pg_type: str
    nullable: bool


@dataclass(frozen=True)
class TableDef:
    name: str
    mode: Literal["incremental", "snapshot"]
    columns: tuple[ColumnDef, ...]
    timestamp_column: str | None = "created_at"
    pii_columns: frozenset[str] = field(default_factory=frozenset)

    @property
    def dl_name(self) -> str:
        return f"dl_{self.name}"

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]


# ── 헬퍼 ─────────────────────────────────────────────────

def _cols(*defs: tuple[str, str, bool]) -> tuple[ColumnDef, ...]:
    return tuple(ColumnDef(name=d[0], pg_type=d[1], nullable=d[2]) for d in defs)


def _tbl(
    name: str,
    mode: Literal["incremental", "snapshot"],
    columns: tuple[ColumnDef, ...],
    *,
    ts: str | None = "created_at",
) -> TableDef:
    return TableDef(
        name=name,
        mode=mode,
        columns=columns,
        timestamp_column=ts,
        pii_columns=PII_COLUMNS.get(name, frozenset()),
    )


# ── 79개 테이블 정의 ─────────────────────────────────────

# --- Snapshot 테이블 (44개) ---

action_items = _tbl("action_items", "snapshot", _cols(
    ("id", "uuid", False), ("user_id", "uuid", False), ("type", "text", False),
    ("title", "text", False), ("description", "text", True), ("priority", "text", False),
    ("due_date", _T, True), ("is_completed", "boolean", True),
    ("related_project_id", "uuid", True), ("created_at", _T, False),
))

admin_calendar_events = _tbl("admin_calendar_events", "snapshot", _cols(
    ("id", "uuid", False), ("title", "text", False), ("description", "text", True),
    ("start_at", _T, False), ("end_at", _T, False), ("event_type", "text", False),
    ("created_by", "uuid", True), ("created_at", _T, False), ("updated_at", _T, False),
))

badges = _tbl("badges", "snapshot", _cols(
    ("id", "uuid", False), ("name", "text", False), ("description", "text", True),
    ("icon", "text", True), ("category", "text", False), ("points", "integer", True),
    ("created_at", _T, False), ("rarity", "text", True),
))

blogs = _tbl("blogs", "snapshot", _cols(
    ("id", "uuid", False), ("created_at", _T, False), ("updated_at", _T, False),
    ("user_id", "uuid", False), ("title", "text", False), ("content", "text", True),
    ("summary", "text", True), ("cover_image_url", "text", True), ("tags", "ARRAY", True),
    ("view_count", "integer", True), ("is_curated", "boolean", True),
    ("related_project_id", "uuid", True), ("related_event_id", "uuid", True),
    ("type", "text", True), ("metadata", "jsonb", True),
))

bug_reports = _tbl("bug_reports", "snapshot", _cols(
    ("id", "uuid", False), ("user_id", "uuid", False), ("title", "text", False),
    ("content", "text", False), ("status", "text", False), ("created_at", _T, False),
    ("updated_at", _T, False), ("page_url", "text", True), ("image_urls", "ARRAY", True),
    ("type", "text", True), ("report_no", "bigint", True),
))

builder_onboarding = _tbl("builder_onboarding", "snapshot", _cols(
    ("id", "uuid", False), ("user_id", "uuid", False), ("project_id", "uuid", True),
    ("linkedin_post", "boolean", False), ("magic_school_apr", "boolean", False),
    ("magic_school_may", "boolean", False), ("midterm_check", "boolean", False),
    ("final_report", "boolean", False), ("pseudocon_presentation", "boolean", False),
    ("created_at", _T, False), ("updated_at", _T, False),
))

community_feed = _tbl("community_feed", "snapshot", _cols(
    ("id", "uuid", False), ("user_id", "uuid", False), ("type", "text", False),
    ("title", "text", True), ("url", "text", True), ("metadata", "jsonb", True),
    ("created_at", _T, False), ("related_project_id", "uuid", True),
    ("related_opportunity_id", "uuid", True), ("content", "text", True),
    ("related_event_id", "uuid", True), ("is_curated", "boolean", True),
    ("view_count", "integer", True), ("image_url", "text", True), ("category", "text", True),
))

email_verification_codes = _tbl("email_verification_codes", "snapshot", _cols(
    ("id", "uuid", False), ("user_id", "uuid", False), ("email", "text", False),
    ("code", "text", False), ("expires_at", _T, False), ("verified", "boolean", True),
    ("created_at", _T, False),
))

event_registrations = _tbl("event_registrations", "snapshot", _cols(
    ("id", "uuid", False), ("event_id", "uuid", False), ("user_id", "uuid", True),
    ("email", "text", False), ("name", "text", False), ("organization", "text", True),
    ("role", "text", True), ("registration_type", "text", True), ("status", "text", True),
    ("registration_data", "jsonb", True), ("interested_sessions", "ARRAY", True),
    ("notes", "text", True), ("checked_in_at", _T, True),
    ("created_at", _T, True), ("updated_at", _T, True),
))

event_sessions = _tbl("event_sessions", "snapshot", _cols(
    ("id", "uuid", False), ("event_id", "uuid", False), ("title", "text", False),
    ("description", "text", True), ("speaker_id", "uuid", True),
    ("speaker_name", "text", True), ("speaker_email", "text", True),
    ("speaker_bio", "text", True), ("speaker_photo_url", "text", True),
    ("start_time", _T, True), ("end_time", _T, True),
    ("duration_minutes", "integer", True), ("session_type", "text", True),
    ("location", "text", True), ("max_participants", "integer", True),
    ("sort_order", "integer", True), ("status", "text", True),
    ("created_at", _T, True), ("updated_at", _T, True),
))

event_speaker_submissions = _tbl("event_speaker_submissions", "snapshot", _cols(
    ("id", "uuid", False), ("event_id", "uuid", False), ("user_id", "uuid", True),
    ("email", "text", False), ("speaker_name", "text", False), ("bio", "text", True),
    ("topic", "text", False), ("description", "text", True), ("outline", "text", True),
    ("duration", "text", True), ("target_audience", "text", True),
    ("portfolio_url", "text", True), ("additional_info", "text", True),
    ("status", "text", True), ("created_at", _T, True), ("updated_at", _T, True),
))

event_sponsor_submissions = _tbl("event_sponsor_submissions", "snapshot", _cols(
    ("id", "uuid", False), ("event_id", "uuid", False), ("company_name", "text", False),
    ("contact_name", "text", False), ("email", "text", False), ("phone", "text", True),
    ("sponsorship_level", "text", True), ("message", "text", True), ("status", "text", True),
    ("created_at", _T, True), ("updated_at", _T, True),
))

event_sponsors = _tbl("event_sponsors", "snapshot", _cols(
    ("id", "uuid", False), ("event_id", "uuid", False), ("company_name", "text", False),
    ("contact_name", "text", True), ("contact_email", "text", True),
    ("contact_phone", "text", True), ("level", "text", True), ("logo_url", "text", True),
    ("website_url", "text", True), ("description", "text", True), ("message", "text", True),
    ("status", "text", True), ("benefits", "jsonb", True),
    ("created_at", _T, True), ("updated_at", _T, True),
))

event_timeline = _tbl("event_timeline", "snapshot", _cols(
    ("id", "uuid", False), ("event_id", "uuid", False), ("phase", "text", False),
    ("title", "text", True), ("description", "text", True), ("start_date", _T, True),
    ("end_date", _T, True), ("is_active", "boolean", True), ("sort_order", "integer", True),
    ("created_at", _T, True), ("updated_at", _T, True),
))

events = _tbl("events", "snapshot", _cols(
    ("id", "uuid", False), ("title", "text", False), ("description", "text", True),
    ("event_date", "date", False), ("start_time", "time without time zone", True),
    ("end_time", "time without time zone", True), ("location", "text", True),
    ("image_url", "text", True), ("external_url", "text", True),
    ("max_participants", "integer", True), ("is_active", "boolean", True),
    ("created_at", _T, False), ("updated_at", _T, False), ("subtitle", "text", True),
    ("category", "text", True), ("organizer_id", "uuid", True), ("status", "text", True),
    ("target_audience", "text", True), ("registration_start", _T, True),
    ("registration_end", _T, True), ("metadata", "jsonb", True), ("content", "text", True),
))

feed_comments = _tbl("feed_comments", "snapshot", _cols(
    ("id", "uuid", False), ("feed_id", "uuid", False), ("user_id", "uuid", False),
    ("content", "text", False), ("created_at", _T, False), ("updated_at", _T, False),
))

highlight_comments = _tbl("highlight_comments", "snapshot", _cols(
    ("id", "uuid", False), ("highlight_id", "uuid", False), ("user_id", "uuid", False),
    ("content", "text", False), ("parent_id", "uuid", True),
    ("created_at", _T, False), ("updated_at", _T, False),
))

highlights = _tbl("highlights", "snapshot", _cols(
    ("id", "uuid", False), ("title", "text", False), ("content", "text", False),
    ("summary", "text", True), ("cover_image_url", "text", True),
    ("highlight_type", "text", False), ("tags", "ARRAY", True),
    ("related_project_id", "uuid", True), ("related_user_id", "uuid", True),
    ("author_id", "uuid", False), ("is_featured", "boolean", True),
    ("view_count", "integer", True), ("created_at", _T, False), ("updated_at", _T, False),
))

magic_maps = _tbl("magic_maps", "snapshot", _cols(
    ("id", "uuid", False), ("name", "text", False), ("tiles", "jsonb", False),
    ("discoveries", "jsonb", False), ("special_tiles", "jsonb", False),
    ("created_by", "uuid", True), ("created_at", _T, False), ("updated_at", _T, False),
    ("unlock_rule", "text", True), ("npc_tiles", "jsonb", True),
))

magic_progress = _tbl("magic_progress", "snapshot", _cols(
    ("id", "uuid", False), ("user_id", "uuid", False), ("map_id", "text", False),
    ("found_indices", "jsonb", False), ("revealed_tiles", "jsonb", False),
    ("unlocked_cards", "jsonb", False), ("unlocked_badges", "jsonb", False),
    ("created_at", _T, False), ("updated_at", _T, False),
    ("daily_moves", "integer", False), ("daily_moves_date", "text", False),
    ("npc_states", "jsonb", False), ("npc_quests", "jsonb", False),
    ("last_position", "jsonb", False),
))

opportunities = _tbl("opportunities", "snapshot", _cols(
    ("id", "uuid", False), ("title", "text", False), ("description", "text", True),
    ("category", "text", False), ("category_label", "text", False),
    ("image_url", "text", True), ("external_url", "text", True), ("deadline", "text", True),
    ("tags", "ARRAY", True), ("created_at", _T, False), ("created_by", "uuid", True),
    ("is_active", "boolean", True),
))

opportunity_beneficiaries = _tbl("opportunity_beneficiaries", "snapshot", _cols(
    ("id", "uuid", False), ("opportunity_id", "uuid", False), ("user_id", "uuid", True),
    ("review_url", "text", True), ("created_at", _T, False), ("status", "text", True),
    ("application_reason", "text", True), ("beneficiary_name", "text", True),
))

profile_careers = _tbl("profile_careers", "snapshot", _cols(
    ("id", "uuid", False), ("user_id", "uuid", False), ("title", "text", False),
    ("career_type", "text", True), ("role", "text", True), ("start_date", "date", True),
    ("end_date", "date", True), ("is_current", "boolean", True), ("created_at", _T, False),
))

profiles = _tbl("profiles", "snapshot", _cols(
    ("id", "uuid", False), ("email", "text", True), ("name", "text", True),
    ("profile_image", "text", True), ("level", "integer", True), ("points", "integer", True),
    ("created_at", _T, True), ("updated_at", _T, True), ("backup_emails", "ARRAY", True),
    ("cohorts", "text", True), ("runner_count", "integer", True),
    ("builder_count", "integer", True), ("activity_score", "integer", True),
    ("participated_projects", "text", True), ("bio", "text", True),
    ("github_url", "text", True), ("linkedin_url", "text", True),
    ("legacy_imported", "boolean", True), ("legacy_imported_at", _T, True),
    ("influence_given_count", "integer", True), ("influence_received_count", "integer", True),
    ("discord_nickname", "text", True), ("organization", "text", True),
    ("job_roles", "ARRAY", True), ("experience_level", "text", True),
    ("current_status", "ARRAY", True), ("expectations", "text", True),
    ("interest_keywords", "ARRAY", True), ("message_2026", "text", True),
    ("featured_badges", "ARRAY", True), ("highlighted_items", "jsonb", True),
    ("organization_type", "text", True), ("name_en", "text", True),
    ("dormitory", "text", True), ("name_kr", "text", True),
    ("talents", "ARRAY", True), ("ai_services", "ARRAY", True),
))

project_applications = _tbl("project_applications", "snapshot", _cols(
    ("id", "uuid", False), ("created_at", _T, False), ("updated_at", _T, False),
    ("user_id", "uuid", False), ("season", "text", False),
    ("applicant_name_kr", "text", False), ("applicant_name_en", "text", True),
    ("applicant_email", "text", False), ("applicant_phone", "text", False),
    ("applicant_discord", "text", True), ("applicant_github", "text", True),
    ("introduction", "text", False), ("motive", "text", False),
    ("growth_plan", "text", False), ("expectations", "text", False),
    ("sharing_plan", "text", False), ("schedule_availability", "text", False),
    ("privacy_consent", "boolean", False), ("data_usage_consent", "boolean", False),
    ("primary_project_id", "uuid", True), ("secondary_project_id", "uuid", True),
    ("tertiary_project_id", "uuid", True), ("status", "text", True),
    ("reviewer_note", "text", True), ("final_matched_project_id", "uuid", True),
))

project_docs = _tbl("project_docs", "snapshot", _cols(
    ("id", "uuid", False), ("project_id", "uuid", False), ("title", "text", False),
    ("content", "text", True), ("category", "text", True), ("author_id", "uuid", True),
    ("linked_task_ids", "ARRAY", True), ("created_at", _T, False), ("updated_at", _T, False),
    ("is_public", "boolean", True), ("type", "text", False), ("metadata", "jsonb", True),
    ("position", "integer", True),
))

project_members = _tbl("project_members", "snapshot", _cols(
    ("id", "uuid", False), ("project_id", "uuid", False), ("user_id", "uuid", False),
    ("role", "text", False), ("attendance_rate", "integer", True),
    ("joined_at", _T, False), ("status", "text", False),
))

project_sessions = _tbl("project_sessions", "snapshot", _cols(
    ("id", "uuid", False), ("project_id", "uuid", False), ("week_number", "integer", False),
    ("session_date", "date", False), ("auth_code", "text", False),
    ("is_active", "boolean", False), ("created_at", _T, False),
    ("start_at", _T, True), ("end_at", _T, True), ("description", "text", True),
))

project_tasks = _tbl("project_tasks", "snapshot", _cols(
    ("id", "uuid", False), ("project_id", "uuid", False), ("title", "text", False),
    ("description", "text", True), ("status", "text", False), ("priority", "text", True),
    ("assignee_id", "uuid", True), ("helper_ids", "ARRAY", True),
    ("start_date", "date", True), ("end_date", "date", True),
    ("result_link", "text", True), ("parent_task_id", "uuid", True),
    ("created_at", _T, False), ("updated_at", _T, False), ("progress", "integer", True),
    ("related_link", "text", True), ("position", "double precision", True),
))

projects = _tbl("projects", "snapshot", _cols(
    ("id", "uuid", False), ("title", "text", False), ("description", "text", True),
    ("type", "text", False), ("status", "text", False), ("current_week", "integer", True),
    ("total_weeks", "integer", True), ("next_meeting", _T, True),
    ("max_members", "integer", True), ("created_by", "uuid", True),
    ("created_at", _T, False), ("updated_at", _T, False), ("cohort", "text", True),
    ("meeting_time", "text", True), ("meeting_location", "text", True),
    ("difficulty", "text", True), ("period", "text", True),
    ("team_page_url", "text", True), ("project_plan_url", "text", True),
    ("data_sharing_method", "text", True), ("auditing_allowed", "boolean", True),
    ("tags", "ARRAY", True), ("builder_name", "text", True),
    ("completed_count", "integer", True), ("dropout_count", "integer", True),
    ("start_member_count", "integer", True), ("legacy_member_ids", "ARRAY", True),
    ("image_url", "text", True), ("requirements", "text", True),
    ("start_date", _T, True), ("milestones", "jsonb", True), ("notice", "text", True),
    ("meeting_type", "text", True), ("region", "text", True),
    ("desired_talents", "ARRAY", True), ("ai_services", "ARRAY", True),
    ("recruit_start_date", _T, True), ("recruit_end_date", _T, True),
    ("discord_webhook_url", "text", True), ("weekly_plan", "jsonb", True),
    ("research_group", "text", True), ("tier", "text", True),
))

quest_definitions = _tbl("quest_definitions", "snapshot", _cols(
    ("id", "uuid", False), ("title", "text", False), ("description", "text", True),
    ("target_count", "integer", True), ("xp_reward", "integer", True),
    ("type", "text", False), ("is_active", "boolean", True), ("created_at", _T, False),
    ("icon", "text", True), ("event_id", "uuid", True),
))

random_squad_queue = _tbl("random_squad_queue", "snapshot", _cols(
    ("id", "uuid", False), ("user_id", "uuid", False), ("can_be_leader", "boolean", True),
    ("status", "text", True), ("matched_squad_id", "uuid", True), ("created_at", _T, True),
))

recruit_applications = _tbl("recruit_applications", "snapshot", _cols(
    ("id", "uuid", False), ("user_id", "uuid", False), ("season", "text", False),
    ("role", "text", False), ("status", "text", False), ("answers", "jsonb", True),
    ("reviewer_note", "text", True), ("created_at", _T, False), ("updated_at", _T, False),
))

registration_submissions = _tbl("registration_submissions", "snapshot", _cols(
    ("id", "uuid", False), ("created_at", _T, False), ("registration_type", "text", False),
    ("name", "text", False), ("referrer", "text", True), ("email", "text", False),
    ("discord_nickname", "text", False), ("organization", "text", False),
    ("job_role", "text", False), ("experience_level", "text", False),
    ("pseudolab_role", "text", False), ("interested_sessions", "ARRAY", False),
    ("participation_purpose", "ARRAY", False), ("growth_keyword_2025", "text", False),
    ("expectations_2026", "ARRAY", False), ("message_to_pseudolab", "text", True),
    ("email_consent", "boolean", False), ("status", "text", False),
    ("networking_participation", "boolean", False), ("linkedin_url", "text", False),
    ("github_url", "text", True), ("third_party_consent", "boolean", False),
    ("mbti", "text", True), ("favorite_season", "text", True),
    ("interest_keywords", "ARRAY", True), ("people_to_meet", "ARRAY", True),
))

resource_comments = _tbl("resource_comments", "snapshot", _cols(
    ("id", "uuid", False), ("resource_id", "uuid", False), ("user_id", "uuid", False),
    ("content", "text", False), ("parent_id", "uuid", True),
    ("created_at", _T, True), ("updated_at", _T, True),
))

secret_posts = _tbl("secret_posts", "snapshot", _cols(
    ("id", "uuid", False), ("author_id", "uuid", False), ("category", "text", False),
    ("title", "text", False), ("content", "text", False),
    ("reactions_agree", "integer", True), ("reactions_useful", "integer", True),
    ("view_count", "integer", True), ("is_hot", "boolean", True),
    ("created_at", _T, True), ("updated_at", _T, True),
))

secret_profiles = _tbl("secret_profiles", "snapshot", _cols(
    ("id", "uuid", False), ("user_id", "uuid", False), ("nickname", "text", False),
    ("share_count", "integer", True), ("created_at", _T, True),
))

squad_applications = _tbl("squad_applications", "snapshot", _cols(
    ("id", "uuid", False), ("squad_id", "uuid", False), ("user_id", "uuid", False),
    ("slot_number", "integer", False), ("message", "text", True),
    ("status", "text", True), ("created_at", _T, True),
))

squads = _tbl("squads", "snapshot", _cols(
    ("id", "uuid", False), ("leader_id", "uuid", False), ("title", "text", False),
    ("description", "text", True), ("project_type", "text", True),
    ("reference_url", "text", True), ("reference_title", "text", True),
    ("member_1_id", "uuid", True), ("member_2_id", "uuid", True),
    ("member_3_id", "uuid", True), ("slot_1_role", "text", True),
    ("slot_2_role", "text", True), ("slot_3_role", "text", True),
    ("duration", "text", True), ("meeting_type", "text", True),
    ("ai_services", "ARRAY", True), ("tech_stack", "ARRAY", True),
    ("collab_style", "text", True), ("region", "text", True),
    ("status", "text", True), ("is_active", "boolean", True),
    ("created_at", _T, True), ("updated_at", _T, True),
))

user_missions = _tbl("user_missions", "snapshot", _cols(
    ("id", "uuid", False), ("user_id", "uuid", False), ("mission_id", "uuid", False),
    ("completed_at", _T, False), ("verification_data", "jsonb", True),
    ("verified", "boolean", True),
))

user_which_projects = _tbl("user_which_projects", "snapshot", _cols(
    ("name", "text", True), ("project", "text", True),
), ts=None)

wiki_articles = _tbl("wiki_articles", "snapshot", _cols(
    ("id", "uuid", False), ("title", "text", False), ("slug", "text", False),
    ("content", "text", False), ("parent_id", "uuid", True), ("category", "text", True),
    ("created_by", "uuid", True), ("updated_by", "uuid", True),
    ("created_at", _T, False), ("updated_at", _T, False),
    ("is_published", "boolean", False), ("view_count", "integer", False),
    ("sort_order", "integer", False),
))

wiki_categories = _tbl("wiki_categories", "snapshot", _cols(
    ("id", "uuid", False), ("name", "text", False), ("slug", "text", False),
    ("description", "text", True), ("icon", "text", True), ("parent_id", "uuid", True),
    ("sort_order", "integer", True), ("created_at", _T, False), ("updated_at", _T, False),
))

wiki_pages = _tbl("wiki_pages", "snapshot", _cols(
    ("id", "uuid", False), ("category_id", "uuid", True), ("title", "text", False),
    ("slug", "text", False), ("content", "text", True), ("view_count", "integer", True),
    ("is_published", "boolean", True), ("created_by", "uuid", True),
    ("updated_by", "uuid", True), ("created_at", _T, False), ("updated_at", _T, False),
))

# --- Incremental 테이블 (35개) ---

artifact_logs = _tbl("artifact_logs", "incremental", _cols(
    ("id", "uuid", False), ("dormitory", "text", False), ("user_id", "uuid", False),
    ("created_at", _T, False),
))

bug_assignees = _tbl("bug_assignees", "incremental", _cols(
    ("bug_id", "uuid", False), ("user_id", "uuid", False), ("created_at", _T, False),
))

bug_comments = _tbl("bug_comments", "incremental", _cols(
    ("id", "uuid", False), ("report_id", "uuid", False), ("user_id", "uuid", False),
    ("content", "text", False), ("created_at", _T, False),
))

bug_events = _tbl("bug_events", "incremental", _cols(
    ("id", "uuid", False), ("bug_id", "uuid", False), ("user_id", "uuid", True),
    ("event_type", "text", False), ("metadata", "jsonb", True), ("created_at", _T, False),
))

dormitory_messages = _tbl("dormitory_messages", "incremental", _cols(
    ("id", "uuid", False), ("dormitory", "text", False), ("user_id", "uuid", True),
    ("content", "text", False), ("created_at", _T, False),
))

event_cards = _tbl("event_cards", "incremental", _cols(
    ("id", "uuid", False), ("card_type", "text", False), ("content", "text", True),
    ("image_url", "text", True), ("link_url", "text", True), ("link_preview", "jsonb", True),
    ("user_email", "text", False), ("created_at", _T, False),
))

event_committee = _tbl("event_committee", "incremental", _cols(
    ("id", "uuid", False), ("event_id", "text", False), ("name", "text", False),
    ("role", "text", False), ("organization", "text", False), ("email", "text", True),
    ("image_url", "text", True), ("linkedin_url", "text", True), ("created_at", _T, False),
))

event_missions = _tbl("event_missions", "incremental", _cols(
    ("id", "uuid", False), ("event_id", "uuid", True), ("name", "text", False),
    ("description", "text", True), ("xp_reward", "integer", False),
    ("mission_type", "text", False), ("verification_type", "text", False),
    ("created_at", _T, False),
))

event_participants = _tbl("event_participants", "incremental", _cols(
    ("id", "uuid", False), ("event_id", "uuid", False), ("user_id", "uuid", False),
    ("participation_type", "text", False), ("created_at", _T, False),
))

event_staff = _tbl("event_staff", "incremental", _cols(
    ("id", "uuid", False), ("event_id", "uuid", False), ("user_id", "uuid", True),
    ("name", "text", True), ("email", "text", True), ("role", "text", False),
    ("title", "text", True), ("profile_image_url", "text", True),
    ("sort_order", "integer", True), ("created_at", _T, True),
))

follows = _tbl("follows", "incremental", _cols(
    ("follower_id", "uuid", False), ("following_id", "uuid", False),
    ("created_at", _T, False),
))

highlight_likes = _tbl("highlight_likes", "incremental", _cols(
    ("id", "uuid", False), ("highlight_id", "uuid", False), ("user_id", "uuid", False),
    ("created_at", _T, False),
))

legacy_members = _tbl("legacy_members", "incremental", _cols(
    ("id", "uuid", False), ("email", "text", False), ("name", "text", True),
    ("cv_url", "text", True), ("huggingface_krew", "text", True),
    ("linkedin_url", "text", True), ("role", "text", True), ("youtube_url", "text", True),
    ("github_url", "text", True), ("interest_keywords", "text", True),
    ("cohorts", "text", True), ("dormitory", "text", True), ("date_field", "text", True),
    ("runner_count", "integer", True), ("blog_url", "text", True),
    ("builder_count", "integer", True), ("original_created_at", "text", True),
    ("talent_pool_project", "text", True), ("talent_pool_work", "text", True),
    ("research_teams", "text", True), ("participated_projects", "text", True),
    ("bio", "text", True), ("activity_score", "integer", True),
    ("created_at", _T, False), ("updated_at", _T, False),
))

notifications = _tbl("notifications", "incremental", _cols(
    ("id", "uuid", False), ("recipient_id", "uuid", False), ("actor_id", "uuid", True),
    ("type", "text", False), ("entity_type", "text", False), ("entity_id", "uuid", False),
    ("link_url", "text", True), ("is_read", "boolean", True), ("created_at", _T, False),
))

opportunity_likes = _tbl("opportunity_likes", "incremental", _cols(
    ("user_id", "uuid", False), ("opportunity_id", "uuid", False),
    ("created_at", _T, False),
))

page_views = _tbl("page_views", "incremental", _cols(
    ("id", "uuid", False), ("viewed_at", _T, False),
), ts="viewed_at")

program_feedbacks = _tbl("program_feedbacks", "incremental", _cols(
    ("id", "uuid", False), ("program_id", "text", False), ("user_email", "text", False),
    ("content", "text", False), ("created_at", _T, False),
))

program_followups = _tbl("program_followups", "incremental", _cols(
    ("id", "uuid", False), ("program_id", "text", False), ("user_email", "text", False),
    ("created_at", _T, False),
))

program_likes = _tbl("program_likes", "incremental", _cols(
    ("id", "uuid", False), ("program_id", "text", False), ("user_email", "text", False),
    ("created_at", _T, False),
))

project_application_history = _tbl("project_application_history", "incremental", _cols(
    ("id", "uuid", False), ("user_id", "uuid", False), ("season", "text", False),
    ("project_id", "uuid", False), ("preference_slot", "text", False),
    ("action_type", "text", False), ("applicant_name_kr", "text", True),
    ("created_at", _T, False),
))

project_attendance = _tbl("project_attendance", "incremental", _cols(
    ("id", "uuid", False), ("session_id", "uuid", False), ("user_id", "uuid", False),
    ("status", "text", False), ("created_at", _T, False),
))

resource_reactions = _tbl("resource_reactions", "incremental", _cols(
    ("id", "uuid", False), ("resource_id", "uuid", False), ("user_id", "uuid", False),
    ("reaction_type", "text", False), ("created_at", _T, True),
))

secret_comments = _tbl("secret_comments", "incremental", _cols(
    ("id", "uuid", False), ("post_id", "uuid", False), ("author_id", "uuid", False),
    ("content", "text", False), ("created_at", _T, True),
))

secret_interactions = _tbl("secret_interactions", "incremental", _cols(
    ("id", "uuid", False), ("user_id", "uuid", False), ("post_id", "uuid", False),
    ("interaction_type", "text", False), ("created_at", _T, True),
))

session_submissions = _tbl("session_submissions", "incremental", _cols(
    ("id", "uuid", False), ("title", "text", False), ("speaker_name", "text", False),
    ("email", "text", False), ("duration", "text", False), ("description", "text", False),
    ("target_audience", "text", True), ("additional_info", "text", True),
    ("created_at", _T, False),
))

speaker_submissions = _tbl("speaker_submissions", "incremental", _cols(
    ("id", "uuid", False), ("topic", "text", False), ("speaker_name", "text", False),
    ("email", "text", False), ("bio", "text", False), ("duration", "text", False),
    ("outline", "text", False), ("portfolio_url", "text", True),
    ("additional_info", "text", True), ("created_at", _T, False),
    ("short_desc", "text", True), ("event_id", "uuid", True),
    ("submission_type", "text", True),
))

sponsor_submissions = _tbl("sponsor_submissions", "incremental", _cols(
    ("id", "uuid", False), ("company_name", "text", False), ("contact_name", "text", False),
    ("email", "text", False), ("phone", "text", True),
    ("sponsorship_level", "text", False), ("message", "text", True),
    ("created_at", _T, False), ("logo_url", "text", True), ("event_id", "uuid", True),
))

sponsorship_requests = _tbl("sponsorship_requests", "incremental", _cols(
    ("id", "uuid", False), ("name", "text", False), ("email", "text", False),
    ("organization", "text", True), ("sponsorship_type", "text", False),
    ("message", "text", True), ("created_at", _T, False),
))

user_badges = _tbl("user_badges", "incremental", _cols(
    ("id", "uuid", False), ("user_id", "uuid", False), ("badge_id", "uuid", False),
    ("event_id", "uuid", True), ("verified", "boolean", True),
    ("verification_data", "jsonb", True), ("claimed_at", _T, False),
), ts="claimed_at")

user_follows = _tbl("user_follows", "incremental", _cols(
    ("id", "uuid", False), ("program_id", "text", False),
    ("follower_email", "text", False), ("following_email", "text", False),
    ("created_at", _T, False),
))

user_influences = _tbl("user_influences", "incremental", _cols(
    ("id", "uuid", False), ("influenced_by_id", "uuid", False),
    ("influenced_user_id", "uuid", False), ("context_type", "text", False),
    ("context_id", "uuid", True), ("message", "text", True), ("created_at", _T, False),
))

user_quests = _tbl("user_quests", "incremental", _cols(
    ("id", "uuid", False), ("user_id", "uuid", False), ("quest_id", "uuid", False),
    ("completed_at", _T, True), ("created_at", _T, True),
))

user_roles = _tbl("user_roles", "incremental", _cols(
    ("id", "uuid", False), ("user_id", "uuid", False), ("role", "text", False),
    ("created_at", _T, False),
))

wiki_revisions = _tbl("wiki_revisions", "incremental", _cols(
    ("id", "uuid", False), ("article_id", "uuid", True), ("content", "text", False),
    ("edited_by", "uuid", True), ("edit_summary", "text", True), ("created_at", _T, False),
    ("page_id", "uuid", True), ("author_id", "uuid", True),
    ("change_summary", "text", True), ("status", "text", True),
    ("reviewer_id", "uuid", True), ("review_comment", "text", True),
    ("reviewed_at", _T, True),
))

xp_history = _tbl("xp_history", "incremental", _cols(
    ("id", "uuid", False), ("user_id", "uuid", False), ("amount", "integer", False),
    ("reason", "text", False), ("category", "text", True), ("created_at", _T, False),
))


# ── 레지스트리 ────────────────────────────────────────────

ALL_TABLES: dict[str, TableDef] = {
    t.name: t for t in [
        # Snapshot (44)
        action_items, admin_calendar_events, badges, blogs, bug_reports,
        builder_onboarding, community_feed, email_verification_codes,
        event_registrations, event_sessions, event_speaker_submissions,
        event_sponsor_submissions, event_sponsors, event_timeline, events,
        feed_comments, highlight_comments, highlights, magic_maps, magic_progress,
        opportunities, opportunity_beneficiaries, profile_careers, profiles,
        project_applications, project_docs, project_members, project_sessions,
        project_tasks, projects, quest_definitions, random_squad_queue,
        recruit_applications, registration_submissions, resource_comments,
        secret_posts, secret_profiles, squad_applications, squads, user_missions,
        user_which_projects, wiki_articles, wiki_categories, wiki_pages,
        # Incremental (35)
        artifact_logs, bug_assignees, bug_comments, bug_events, dormitory_messages,
        event_cards, event_committee, event_missions, event_participants, event_staff,
        follows, highlight_likes, legacy_members, notifications, opportunity_likes,
        page_views, program_feedbacks, program_followups, program_likes,
        project_application_history, project_attendance, resource_reactions,
        secret_comments, secret_interactions, session_submissions, speaker_submissions,
        sponsor_submissions, sponsorship_requests, user_badges, user_follows,
        user_influences, user_quests, user_roles, wiki_revisions, xp_history,
    ]
}

SNAPSHOT_TABLES: dict[str, TableDef] = {
    k: v for k, v in ALL_TABLES.items() if v.mode == "snapshot"
}

INCREMENTAL_TABLES: dict[str, TableDef] = {
    k: v for k, v in ALL_TABLES.items() if v.mode == "incremental"
}
