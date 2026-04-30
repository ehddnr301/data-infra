# Supabase DB 정보

총 테이블 수: **80**

## Overview

| table | rows | data period | description |
| --- | --- | --- | --- |
| `action_items` | 9 | — | 대시보드 할일/액션 아이템 |
| `admin_calendar_events` | 3 | — | 관리자 캘린더 이벤트 |
| `artifact_logs` | 0 | — | 마법학교 아티팩트 사용 로그 |
| `badges` | 9 | — | 뱃지 마스터 데이터 정의 |
| `blogs` | 17 | — | 사용자 블로그 포스트 및 문서 |
| `bug_assignees` | 0 | — | 버그 담당자 (미사용) |
| `bug_comments` | 45 | — | 버그 리포트 댓글 |
| `bug_events` | 0 | — | 버그 이벤트 로그 (미사용) |
| `bug_reports` | 50 | — | 버그 리포트 및 피드백 |
| `builder_onboarding` | 12 | — | 빌더 온보딩 진행상황 추적 |
| `community_feed` | 43 | — | 커뮤니티 피드 포스트 및 활동 내역 |
| `dormitory_messages` | 18 | — | 기숙사 글로벌 채팅 메시지 |
| `email_verification_codes` | 4 | — | 이메일 인증 코드 |
| `event_cards` | 4 | — | 이벤트 카드/정보 카드 |
| `event_committee` | 10 | — | 이벤트 위원회 멤버 |
| `event_missions` | 2 | — | 이벤트 미션 (미사용) |
| `event_participants` | 10 | — | 이벤트 참가자 관리 |
| `event_registrations` | 153 | — | 이벤트 참가 등록 및 현황 |
| `event_sessions` | 0 | — | 이벤트 세션 정보 |
| `event_speaker_submissions` | 7 | — | 이벤트 스피커 신청 및 승인 |
| `event_sponsor_submissions` | 0 | — | 이벤트 스폰서 신청 |
| `event_sponsors` | 0 | — | 이벤트 스폰서 (미사용) |
| `event_staff` | 23 | — | 이벤트 스태프 및 역할 관리 |
| `event_timeline` | 0 | — | 이벤트 타임라인 (미사용) |
| `events` | 34 | — | 이벤트 마스터 데이터 및 개최자 정보 |
| `feed_comments` | 11 | — | 커뮤니티 피드 댓글 |
| `follows` | 72 | — | 사용자 팔로우 관계 |
| `highlight_comments` | 0 | — | 하이라이트 댓글 |
| `highlight_likes` | 0 | — | 하이라이트 좋아요 |
| `highlights` | 0 | — | 블로그 포스트 하이라이트/요약 |
| `legacy_members` | 759 | — | 레거시 멤버 데이터 (이전 세션) |
| `magic_maps` | 3 | — | 마법 학교 맵 데이터 |
| `magic_progress` | 50 | — | 마법 학교 맵 탐험 진행률 |
| `notifications` | 1,001 | — | 사용자 알림 (시스템, 댓글, 상태 변경) |
| `opportunities` | 8 | — | 기회/공고 정보 |
| `opportunity_beneficiaries` | 27 | — | 기회 수혜자 추적 |
| `opportunity_likes` | 5 | — | 기회/공고 좋아요 |
| `page_views` | 3,062 | — | 페이지 조회 분석 데이터 |
| `profile_careers` | 142 | — | 사용자 경력/직업 정보 |
| `profiles` | 617 | — | 사용자 프로필 및 게이미피케이션 (XP, 포인트, 레벨, 영향력) |
| `program_feedbacks` | 1 | — | 프로그램 피드백 (미사용) |
| `program_followups` | 102 | — | 프로그램 후속 처리 |
| `program_likes` | 66 | — | 프로그램 좋아요 (미사용) |
| `project_application_history` | 302 | — | 프로젝트 지원 이력 추적 |
| `project_applications` | 265 | — | 프로젝트 지원 및 승인 현황 |
| `project_attendance` | 290 | — | 프로젝트 세션 출석 기록 |
| `project_docs` | 28 | — | 프로젝트 위키 및 공유 문서 |
| `project_members` | 304 | — | 프로젝트별 팀원 정보 및 출석률 |
| `project_sessions` | 198 | — | 프로젝트 주간 세션 및 일정 |
| `project_tasks` | 30 | — | 프로젝트 칸반 보드 작업 아이템 |
| `projects` | 292 | — | 프로젝트 마스터 데이터 (제목, 설명, 상태, 진행상황) |
| `quest_definitions` | 5 | — | 게임화 퀘스트 정의 및 설정 |
| `random_squad_queue` | 0 | — | 랜덤 스쿼드 매칭 큐 |
| `recruit_applications` | 64 | — | 모집 지원서 및 진행상황 |
| `registration_submissions` | 157 | — | 이벤트 등록 제출 데이터 |
| `resource_comments` | 9 | — | 블로그/리소스 댓글 |
| `resource_reactions` | 89 | — | 블로그/리소스 좋아요 반응 |
| `secret_comments` | 3 | — | 비밀 포스트 댓글 |
| `secret_interactions` | 2 | — | 비밀 포스트 상호작용 (좋아요) |
| `secret_posts` | 1 | — | 비밀 커뮤니티 포스트 |
| `secret_profiles` | 1 | — | 비밀 커뮤니티 사용자 프로필 |
| `session_submissions` | 1 | — | 세션 제출 (미사용) |
| `speaker_submissions` | 21 | — | 스피커 신청 (미사용) |
| `sponsor_submissions` | 4 | — | 스폰서 신청 |
| `sponsorship_requests` | 0 | — | 스폰십 요청 |
| `squad_applications` | 2 | — | 스쿼드 신청 및 승인 |
| `squads` | 5 | — | 스쿼드/소그룹 마스터 데이터 |
| `table` | 0 | — | 예약어 테이블명 (오류 가능) |
| `user_badges` | 14 | — | 사용자가 획득한 뱃지 기록 |
| `user_follows` | 37 | — | 사용자 팔로우 관계 정보 |
| `user_influences` | 106 | — | 사용자 영향력 거래 (블로그, 리소스 기반) |
| `user_missions` | 1 | — | 사용자 미션 (미사용) |
| `user_quests` | 10 | — | 사용자 퀘스트 진행상황 |
| `user_roles` | 664 | — | 사용자 역할 (admin, moderator 등) |
| `user_which_projects` | 178 | — | 사용자-프로젝트 매핑 (미사용) |
| `wiki_articles` | 0 | — | 위키 아티클/문서 |
| `wiki_categories` | 8 | — | 위키 카테고리 분류 |
| `wiki_pages` | 6 | — | 위키 페이지 콘텐츠 및 메타데이터 |
| `wiki_revisions` | 10 | — | 위키 페이지 변경 이력 |
| `xp_history` | 439 | — | XP/경험치 획득 이력 기록 |

---

## `action_items` (≈9 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| user_id | uuid | N |  |  |
| type | text | N | 'notification'::text |  |
| title | text | N |  |  |
| description | text | Y |  |  |
| priority | text | N | 'medium'::text |  |
| due_date | timestamp with time zone | Y |  |  |
| is_completed | boolean | Y | false |  |
| related_project_id | uuid | Y |  |  |
| created_at | timestamp with time zone | N | now() |  |

**Indexes**

- `action_items_pkey: CREATE UNIQUE INDEX action_items_pkey ON public.action_items USING btree (id)`

---

## `admin_calendar_events` (≈3 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| title | text | N |  |  |
| description | text | Y |  |  |
| start_at | timestamp with time zone | N |  |  |
| end_at | timestamp with time zone | N |  |  |
| event_type | text | N | 'operation'::text |  |
| created_by | uuid | Y |  |  |
| created_at | timestamp with time zone | N | now() |  |
| updated_at | timestamp with time zone | N | now() |  |

**`event_type` 값 목록:** `operation`

**Indexes**

- `admin_calendar_events_pkey: CREATE UNIQUE INDEX admin_calendar_events_pkey ON public.admin_calendar_events USING btree (id)`

---

## `artifact_logs` (≈0 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| dormitory | text | N |  |  |
| user_id | uuid | N |  |  |
| created_at | timestamp with time zone | N | now() |  |

**Indexes**

- `artifact_logs_dormitory_created_at_idx: CREATE INDEX artifact_logs_dormitory_created_at_idx ON public.artifact_logs USING btree (dormitory, created_at DESC)`
- `artifact_logs_pkey: CREATE UNIQUE INDEX artifact_logs_pkey ON public.artifact_logs USING btree (id)`

---

## `badges` (≈9 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| name | text | N |  |  |
| description | text | Y |  |  |
| icon | text | Y |  |  |
| category | text | N |  |  |
| points | integer | Y | 0 |  |
| created_at | timestamp with time zone | N | now() |  |
| rarity | text | Y | 'common'::text | Badge rarity level: common, uncommon, rare, epic, legendary |

**`category` 값 목록:** `achievement`, `event`

**`rarity` 값 목록:** `common`, `rare`, `uncommon`

**Indexes**

- `badges_pkey: CREATE UNIQUE INDEX badges_pkey ON public.badges USING btree (id)`

---

## `blogs` (≈17 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| created_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |
| updated_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |
| user_id | uuid | N |  |  |
| title | text | N |  |  |
| content | text | Y |  |  |
| summary | text | Y |  |  |
| cover_image_url | text | Y |  |  |
| tags | ARRAY | Y | '{}'::text[] |  |
| view_count | integer | Y | 0 |  |
| is_curated | boolean | Y | false |  |
| related_project_id | uuid | Y |  |  |
| related_event_id | uuid | Y |  |  |
| type | text | Y | 'blog'::text |  |
| metadata | jsonb | Y | '{}'::jsonb |  |

**`type` 값 목록:** `blog`

**`metadata` keys:** `category`, `content`, `coverImage`, `description`, `influence_count`, `influenced`, `influenced_users`, `likes`, `reactions`, `readingTime`, `resource_type`, `status`, `tags`, `url`, `view_count`

**Indexes**

- `blogs_pkey: CREATE UNIQUE INDEX blogs_pkey ON public.blogs USING btree (id)`

---

## `bug_assignees` (≈0 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| bug_id | uuid | N |  |  |
| user_id | uuid | N |  |  |
| created_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |

**Indexes**

- `bug_assignees_pkey: CREATE UNIQUE INDEX bug_assignees_pkey ON public.bug_assignees USING btree (bug_id, user_id)`

---

## `bug_comments` (≈45 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| report_id | uuid | N |  |  |
| user_id | uuid | N |  |  |
| content | text | N |  |  |
| created_at | timestamp with time zone | N | now() |  |

**Indexes**

- `bug_comments_pkey: CREATE UNIQUE INDEX bug_comments_pkey ON public.bug_comments USING btree (id)`

---

## `bug_events` (≈0 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| bug_id | uuid | N |  |  |
| user_id | uuid | Y |  |  |
| event_type | text | N |  |  |
| metadata | jsonb | Y | '{}'::jsonb |  |
| created_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |

**Indexes**

- `bug_events_pkey: CREATE UNIQUE INDEX bug_events_pkey ON public.bug_events USING btree (id)`

---

## `bug_reports` (≈50 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| user_id | uuid | N |  |  |
| title | text | N |  |  |
| content | text | N |  |  |
| status | text | N | 'open'::text |  |
| created_at | timestamp with time zone | N | now() |  |
| updated_at | timestamp with time zone | N | now() |  |
| page_url | text | Y |  |  |
| image_urls | ARRAY | Y | '{}'::text[] |  |
| type | text | Y | 'bug'::text |  |
| report_no | bigint | Y | nextval('bug_reports_report_no_seq'::regclass) |  |

**`status` 값 목록:** `open`, `solved`

**`type` 값 목록:** `bug`, `design`, `feature`, `issue`

**Indexes**

- `bug_reports_pkey: CREATE UNIQUE INDEX bug_reports_pkey ON public.bug_reports USING btree (id)`
- `bug_reports_report_no_key: CREATE UNIQUE INDEX bug_reports_report_no_key ON public.bug_reports USING btree (report_no)`

---

## `builder_onboarding` (≈12 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| user_id | uuid | N |  |  |
| project_id | uuid | Y |  |  |
| linkedin_post | boolean | N | false |  |
| magic_school_apr | boolean | N | false |  |
| magic_school_may | boolean | N | false |  |
| midterm_check | boolean | N | false |  |
| final_report | boolean | N | false |  |
| pseudocon_presentation | boolean | N | false |  |
| created_at | timestamp with time zone | N | now() |  |
| updated_at | timestamp with time zone | N | now() |  |

**Indexes**

- `builder_onboarding_pkey: CREATE UNIQUE INDEX builder_onboarding_pkey ON public.builder_onboarding USING btree (id)`
- `builder_onboarding_user_id_key: CREATE UNIQUE INDEX builder_onboarding_user_id_key ON public.builder_onboarding USING btree (user_id)`

---

## `community_feed` (≈43 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| user_id | uuid | N |  |  |
| type | text | N |  |  |
| title | text | Y |  |  |
| url | text | Y |  |  |
| metadata | jsonb | Y |  |  |
| created_at | timestamp with time zone | N | now() |  |
| related_project_id | uuid | Y |  |  |
| related_opportunity_id | uuid | Y |  |  |
| content | text | Y |  |  |
| related_event_id | uuid | Y |  |  |
| is_curated | boolean | Y | false |  |
| view_count | integer | Y | 0 |  |
| image_url | text | Y |  |  |
| category | text | Y | 'general'::text |  |

**`type` 값 목록:** `linkedin`, `project_post`, `share`, `talk`

**`category` 값 목록:** `general`

**`metadata` keys:** `content`, `content_type`, `description`, `image_url`, `influenced`, `is_original`, `likes`, `source`, `tags`, `url`

**Indexes**

- `community_feed_pkey: CREATE UNIQUE INDEX community_feed_pkey ON public.community_feed USING btree (id)`
- `community_feed_related_event_id_idx: CREATE INDEX community_feed_related_event_id_idx ON public.community_feed USING btree (related_event_id)`
- `idx_community_feed_category: CREATE INDEX idx_community_feed_category ON public.community_feed USING btree (category)`
- `idx_community_feed_is_curated: CREATE INDEX idx_community_feed_is_curated ON public.community_feed USING btree (is_curated)`
- `idx_community_feed_project_id: CREATE INDEX idx_community_feed_project_id ON public.community_feed USING btree (related_project_id)`
- `idx_community_feed_view_count: CREATE INDEX idx_community_feed_view_count ON public.community_feed USING btree (view_count)`

---

## `dormitory_messages` (≈18 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| dormitory | text | N |  |  |
| user_id | uuid | Y |  |  |
| content | text | N |  |  |
| created_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |

**Indexes**

- `dormitory_messages_pkey: CREATE UNIQUE INDEX dormitory_messages_pkey ON public.dormitory_messages USING btree (id)`
- `idx_dormitory_messages_created_at: CREATE INDEX idx_dormitory_messages_created_at ON public.dormitory_messages USING btree (created_at DESC)`
- `idx_dormitory_messages_dormitory: CREATE INDEX idx_dormitory_messages_dormitory ON public.dormitory_messages USING btree (dormitory)`

---

## `email_verification_codes` (≈4 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| user_id | uuid | N |  |  |
| email | text | N |  |  |
| code | text | N |  |  |
| expires_at | timestamp with time zone | N | (now() + '00:10:00'::interval) |  |
| verified | boolean | Y | false |  |
| created_at | timestamp with time zone | N | now() |  |

**Indexes**

- `email_verification_codes_pkey: CREATE UNIQUE INDEX email_verification_codes_pkey ON public.email_verification_codes USING btree (id)`

---

## `event_cards` (≈4 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| card_type | text | N |  |  |
| content | text | Y |  |  |
| image_url | text | Y |  |  |
| link_url | text | Y |  |  |
| link_preview | jsonb | Y |  |  |
| user_email | text | N |  |  |
| created_at | timestamp with time zone | N | now() |  |

**`card_type` 값 목록:** `link`, `photo`

**`link_preview` keys:** `description`, `image`, `title`

**Indexes**

- `event_cards_pkey: CREATE UNIQUE INDEX event_cards_pkey ON public.event_cards USING btree (id)`

---

## `event_committee` (≈10 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| event_id | text | N | 'grand-gathering-9th'::text |  |
| name | text | N |  |  |
| role | text | N |  |  |
| organization | text | N |  |  |
| email | text | Y |  |  |
| image_url | text | Y |  |  |
| linkedin_url | text | Y |  |  |
| created_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |

**`role` 값 목록:** `준비위원회`

**Indexes**

- `event_committee_pkey: CREATE UNIQUE INDEX event_committee_pkey ON public.event_committee USING btree (id)`

---

## `event_missions` (≈2 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| event_id | uuid | Y |  |  |
| name | text | N |  |  |
| description | text | Y |  |  |
| xp_reward | integer | N | 0 |  |
| mission_type | text | N | 'general'::text |  |
| verification_type | text | N | 'self_report'::text |  |
| created_at | timestamp with time zone | N | now() |  |

**`mission_type` 값 목록:** `support`, `talk`

**`verification_type` 값 목록:** `db_check`

**Indexes**

- `event_missions_pkey: CREATE UNIQUE INDEX event_missions_pkey ON public.event_missions USING btree (id)`

---

## `event_participants` (≈10 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| event_id | uuid | N |  |  |
| user_id | uuid | N |  |  |
| participation_type | text | N | 'interested'::text |  |
| created_at | timestamp with time zone | N | now() |  |

**`participation_type` 값 목록:** `interested`

**Indexes**

- `event_participants_event_id_user_id_key: CREATE UNIQUE INDEX event_participants_event_id_user_id_key ON public.event_participants USING btree (event_id, user_id)`
- `event_participants_pkey: CREATE UNIQUE INDEX event_participants_pkey ON public.event_participants USING btree (id)`

---

## `event_registrations` (≈153 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| event_id | uuid | N |  |  |
| user_id | uuid | Y |  |  |
| email | text | N |  |  |
| name | text | N |  |  |
| organization | text | Y |  |  |
| role | text | Y |  |  |
| registration_type | text | Y | 'general'::text |  |
| status | text | Y | 'pending'::text |  |
| registration_data | jsonb | Y | '{}'::jsonb |  |
| interested_sessions | ARRAY | Y |  |  |
| notes | text | Y |  |  |
| checked_in_at | timestamp with time zone | Y |  |  |
| created_at | timestamp with time zone | Y | now() |  |
| updated_at | timestamp with time zone | Y | now() |  |

**Indexes**

- `event_registrations_event_id_email_key: CREATE UNIQUE INDEX event_registrations_event_id_email_key ON public.event_registrations USING btree (event_id, email)`
- `event_registrations_pkey: CREATE UNIQUE INDEX event_registrations_pkey ON public.event_registrations USING btree (id)`
- `idx_event_registrations_event_id: CREATE INDEX idx_event_registrations_event_id ON public.event_registrations USING btree (event_id)`
- `idx_event_registrations_user_id: CREATE INDEX idx_event_registrations_user_id ON public.event_registrations USING btree (user_id)`

---

## `event_sessions` (≈0 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| event_id | uuid | N |  |  |
| title | text | N |  |  |
| description | text | Y |  |  |
| speaker_id | uuid | Y |  |  |
| speaker_name | text | Y |  |  |
| speaker_email | text | Y |  |  |
| speaker_bio | text | Y |  |  |
| speaker_photo_url | text | Y |  |  |
| start_time | timestamp with time zone | Y |  |  |
| end_time | timestamp with time zone | Y |  |  |
| duration_minutes | integer | Y | 30 |  |
| session_type | text | Y | 'talk'::text |  |
| location | text | Y |  |  |
| max_participants | integer | Y |  |  |
| sort_order | integer | Y | 0 |  |
| status | text | Y | 'pending'::text |  |
| created_at | timestamp with time zone | Y | now() |  |
| updated_at | timestamp with time zone | Y | now() |  |

**Indexes**

- `event_sessions_pkey: CREATE UNIQUE INDEX event_sessions_pkey ON public.event_sessions USING btree (id)`
- `idx_event_sessions_event_id: CREATE INDEX idx_event_sessions_event_id ON public.event_sessions USING btree (event_id)`

---

## `event_speaker_submissions` (≈7 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| event_id | uuid | N |  |  |
| user_id | uuid | Y |  |  |
| email | text | N |  |  |
| speaker_name | text | N |  |  |
| bio | text | Y |  |  |
| topic | text | N |  |  |
| description | text | Y |  |  |
| outline | text | Y |  |  |
| duration | text | Y | '30min'::text |  |
| target_audience | text | Y |  |  |
| portfolio_url | text | Y |  |  |
| additional_info | text | Y |  |  |
| status | text | Y | 'pending'::text |  |
| created_at | timestamp with time zone | Y | now() |  |
| updated_at | timestamp with time zone | Y | now() |  |

**Indexes**

- `event_speaker_submissions_pkey: CREATE UNIQUE INDEX event_speaker_submissions_pkey ON public.event_speaker_submissions USING btree (id)`
- `idx_event_speaker_submissions_event_id: CREATE INDEX idx_event_speaker_submissions_event_id ON public.event_speaker_submissions USING btree (event_id)`

---

## `event_sponsor_submissions` (≈0 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| event_id | uuid | N |  |  |
| company_name | text | N |  |  |
| contact_name | text | N |  |  |
| email | text | N |  |  |
| phone | text | Y |  |  |
| sponsorship_level | text | Y |  |  |
| message | text | Y |  |  |
| status | text | Y | 'pending'::text |  |
| created_at | timestamp with time zone | Y | now() |  |
| updated_at | timestamp with time zone | Y | now() |  |

**Indexes**

- `event_sponsor_submissions_pkey: CREATE UNIQUE INDEX event_sponsor_submissions_pkey ON public.event_sponsor_submissions USING btree (id)`
- `idx_event_sponsor_submissions_event_id: CREATE INDEX idx_event_sponsor_submissions_event_id ON public.event_sponsor_submissions USING btree (event_id)`

---

## `event_sponsors` (≈0 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| event_id | uuid | N |  |  |
| company_name | text | N |  |  |
| contact_name | text | Y |  |  |
| contact_email | text | Y |  |  |
| contact_phone | text | Y |  |  |
| level | text | Y | 'bronze'::text |  |
| logo_url | text | Y |  |  |
| website_url | text | Y |  |  |
| description | text | Y |  |  |
| message | text | Y |  |  |
| status | text | Y | 'pending'::text |  |
| benefits | jsonb | Y | '{}'::jsonb |  |
| created_at | timestamp with time zone | Y | now() |  |
| updated_at | timestamp with time zone | Y | now() |  |

**Indexes**

- `event_sponsors_pkey: CREATE UNIQUE INDEX event_sponsors_pkey ON public.event_sponsors USING btree (id)`
- `idx_event_sponsors_event_id: CREATE INDEX idx_event_sponsors_event_id ON public.event_sponsors USING btree (event_id)`

---

## `event_staff` (≈23 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| event_id | uuid | N |  |  |
| user_id | uuid | Y |  |  |
| name | text | Y |  |  |
| email | text | Y |  |  |
| role | text | N | 'staff'::text |  |
| title | text | Y |  |  |
| profile_image_url | text | Y |  |  |
| sort_order | integer | Y | 0 |  |
| created_at | timestamp with time zone | Y | now() |  |

**Indexes**

- `event_staff_event_id_user_id_key: CREATE UNIQUE INDEX event_staff_event_id_user_id_key ON public.event_staff USING btree (event_id, user_id)`
- `event_staff_pkey: CREATE UNIQUE INDEX event_staff_pkey ON public.event_staff USING btree (id)`
- `idx_event_staff_event_id: CREATE INDEX idx_event_staff_event_id ON public.event_staff USING btree (event_id)`

---

## `event_timeline` (≈0 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| event_id | uuid | N |  |  |
| phase | text | N |  |  |
| title | text | Y |  |  |
| description | text | Y |  |  |
| start_date | timestamp with time zone | Y |  |  |
| end_date | timestamp with time zone | Y |  |  |
| is_active | boolean | Y | false |  |
| sort_order | integer | Y | 0 |  |
| created_at | timestamp with time zone | Y | now() |  |
| updated_at | timestamp with time zone | Y | now() |  |

**Indexes**

- `event_timeline_pkey: CREATE UNIQUE INDEX event_timeline_pkey ON public.event_timeline USING btree (id)`
- `idx_event_timeline_event_id: CREATE INDEX idx_event_timeline_event_id ON public.event_timeline USING btree (event_id)`

---

## `events` (≈34 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| title | text | N |  |  |
| description | text | Y |  |  |
| event_date | date | N |  |  |
| start_time | time without time zone | Y |  |  |
| end_time | time without time zone | Y |  |  |
| location | text | Y |  |  |
| image_url | text | Y |  |  |
| external_url | text | Y |  |  |
| max_participants | integer | Y |  |  |
| is_active | boolean | Y | true |  |
| created_at | timestamp with time zone | N | now() |  |
| updated_at | timestamp with time zone | N | now() |  |
| subtitle | text | Y |  |  |
| category | text | Y | 'gathering'::text |  |
| organizer_id | uuid | Y |  |  |
| status | text | Y | 'draft'::text |  |
| target_audience | text | Y | 'everyone'::text |  |
| registration_start | timestamp with time zone | Y |  |  |
| registration_end | timestamp with time zone | Y |  |  |
| metadata | jsonb | Y | '{}'::jsonb |  |
| content | text | Y |  |  |

**`category` 값 목록:** `gathering`, `magical_week`, `meetup`, `seminar`, `workshop`

**`status` 값 목록:** `completed`, `draft`, `pending`

**`metadata` keys:** `api_id`, `enable_registration`, `enable_speakers`, `enable_sponsors`, `host_type`, `source`

**Indexes**

- `events_pkey: CREATE UNIQUE INDEX events_pkey ON public.events USING btree (id)`

---

## `feed_comments` (≈11 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| feed_id | uuid | N |  |  |
| user_id | uuid | N |  |  |
| content | text | N |  |  |
| created_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |
| updated_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |

**Indexes**

- `feed_comments_pkey: CREATE UNIQUE INDEX feed_comments_pkey ON public.feed_comments USING btree (id)`

---

## `follows` (≈72 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| follower_id | uuid | N |  |  |
| following_id | uuid | N |  |  |
| created_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |

**Indexes**

- `follows_pkey: CREATE UNIQUE INDEX follows_pkey ON public.follows USING btree (follower_id, following_id)`

---

## `highlight_comments` (≈0 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| highlight_id | uuid | N |  |  |
| user_id | uuid | N |  |  |
| content | text | N |  |  |
| parent_id | uuid | Y |  |  |
| created_at | timestamp with time zone | N | now() |  |
| updated_at | timestamp with time zone | N | now() |  |

**Indexes**

- `highlight_comments_pkey: CREATE UNIQUE INDEX highlight_comments_pkey ON public.highlight_comments USING btree (id)`

---

## `highlight_likes` (≈0 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| highlight_id | uuid | N |  |  |
| user_id | uuid | N |  |  |
| created_at | timestamp with time zone | N | now() |  |

**Indexes**

- `highlight_likes_highlight_id_user_id_key: CREATE UNIQUE INDEX highlight_likes_highlight_id_user_id_key ON public.highlight_likes USING btree (highlight_id, user_id)`
- `highlight_likes_pkey: CREATE UNIQUE INDEX highlight_likes_pkey ON public.highlight_likes USING btree (id)`

---

## `highlights` (≈0 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| title | text | N |  |  |
| content | text | N |  |  |
| summary | text | Y |  |  |
| cover_image_url | text | Y |  |  |
| highlight_type | text | N | 'general'::text |  |
| tags | ARRAY | Y | '{}'::text[] |  |
| related_project_id | uuid | Y |  |  |
| related_user_id | uuid | Y |  |  |
| author_id | uuid | N |  |  |
| is_featured | boolean | Y | false |  |
| view_count | integer | Y | 0 |  |
| created_at | timestamp with time zone | N | now() |  |
| updated_at | timestamp with time zone | N | now() |  |

**Indexes**

- `highlights_pkey: CREATE UNIQUE INDEX highlights_pkey ON public.highlights USING btree (id)`

---

## `legacy_members` (≈759 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| email | text | N |  |  |
| name | text | Y |  |  |
| cv_url | text | Y |  |  |
| huggingface_krew | text | Y |  |  |
| linkedin_url | text | Y |  |  |
| role | text | Y |  |  |
| youtube_url | text | Y |  |  |
| github_url | text | Y |  |  |
| interest_keywords | text | Y |  |  |
| cohorts | text | Y |  |  |
| dormitory | text | Y |  |  |
| date_field | text | Y |  |  |
| runner_count | integer | Y | 0 |  |
| blog_url | text | Y |  |  |
| builder_count | integer | Y | 0 |  |
| original_created_at | text | Y |  |  |
| talent_pool_project | text | Y |  |  |
| talent_pool_work | text | Y |  |  |
| research_teams | text | Y |  |  |
| participated_projects | text | Y |  |  |
| bio | text | Y |  |  |
| activity_score | integer | Y | 0 |  |
| created_at | timestamp with time zone | N | now() |  |
| updated_at | timestamp with time zone | N | now() |  |

**`role` 값 목록:** `아카데믹 러너`, `아카데믹 러너, 아카데믹 빌더`, `아카데믹 러너, 아카데믹 빌더, 이니셔티브 빌더`, `아카데믹 빌더`, `아카데믹 빌더, 위원회`, `아카데믹 빌더, 위원회, 커뮤니티 빌더`, `아카데믹 빌더, 이니셔티브 빌더`, `아카데믹 빌더, 커뮤니티 빌더`, `위원회`, `위원회, 커뮤니티 빌더`, `이니셔티브 빌더`, `커뮤니티 빌더`

**Indexes**

- `legacy_members_email_key: CREATE UNIQUE INDEX legacy_members_email_key ON public.legacy_members USING btree (email)`
- `legacy_members_email_unique: CREATE UNIQUE INDEX legacy_members_email_unique ON public.legacy_members USING btree (lower(email))`
- `legacy_members_pkey: CREATE UNIQUE INDEX legacy_members_pkey ON public.legacy_members USING btree (id)`

---

## `magic_maps` (≈3 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| name | text | N |  |  |
| tiles | jsonb | N | '[]'::jsonb |  |
| discoveries | jsonb | N | '[]'::jsonb |  |
| special_tiles | jsonb | N | '{}'::jsonb |  |
| created_by | uuid | Y |  |  |
| created_at | timestamp with time zone | N | now() |  |
| updated_at | timestamp with time zone | N | now() |  |
| unlock_rule | text | Y |  |  |
| npc_tiles | jsonb | Y |  |  |

**Indexes**

- `magic_maps_name_key: CREATE UNIQUE INDEX magic_maps_name_key ON public.magic_maps USING btree (name)`
- `magic_maps_npc_tiles_idx: CREATE INDEX magic_maps_npc_tiles_idx ON public.magic_maps USING gin (npc_tiles)`
- `magic_maps_pkey: CREATE UNIQUE INDEX magic_maps_pkey ON public.magic_maps USING btree (id)`
- `magic_maps_unlock_rule_idx: CREATE INDEX magic_maps_unlock_rule_idx ON public.magic_maps USING btree (unlock_rule)`

---

## `magic_progress` (≈50 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| user_id | uuid | N |  |  |
| map_id | text | N |  |  |
| found_indices | jsonb | N | '[]'::jsonb |  |
| revealed_tiles | jsonb | N | '[]'::jsonb |  |
| unlocked_cards | jsonb | N | '[]'::jsonb |  |
| unlocked_badges | jsonb | N | '[]'::jsonb |  |
| created_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |
| updated_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |
| daily_moves | integer | N | 0 |  |
| daily_moves_date | text | N | to_char(timezone('utc'::text, now()), 'YYYY-MM-DD'::text) |  |
| npc_states | jsonb | N | '{}'::jsonb |  |
| npc_quests | jsonb | N | '[]'::jsonb |  |
| last_position | jsonb | N | '{"x": 5, "y": 5}'::jsonb |  |

**Indexes**

- `magic_progress_daily_moves_date_idx: CREATE INDEX magic_progress_daily_moves_date_idx ON public.magic_progress USING btree (daily_moves_date)`
- `magic_progress_map_id_idx: CREATE INDEX magic_progress_map_id_idx ON public.magic_progress USING btree (map_id)`
- `magic_progress_pkey: CREATE UNIQUE INDEX magic_progress_pkey ON public.magic_progress USING btree (id)`
- `magic_progress_user_id_idx: CREATE INDEX magic_progress_user_id_idx ON public.magic_progress USING btree (user_id)`
- `magic_progress_user_id_map_id_key: CREATE UNIQUE INDEX magic_progress_user_id_map_id_key ON public.magic_progress USING btree (user_id, map_id)`

---

## `notifications` (≈1,001 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| recipient_id | uuid | N |  |  |
| actor_id | uuid | Y |  |  |
| type | text | N |  |  |
| entity_type | text | N |  |  |
| entity_id | uuid | N |  |  |
| link_url | text | Y |  |  |
| is_read | boolean | Y | false |  |
| created_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |

**Indexes**

- `notifications_created_at_idx: CREATE INDEX notifications_created_at_idx ON public.notifications USING btree (created_at DESC)`
- `notifications_pkey: CREATE UNIQUE INDEX notifications_pkey ON public.notifications USING btree (id)`
- `notifications_recipient_id_idx: CREATE INDEX notifications_recipient_id_idx ON public.notifications USING btree (recipient_id)`

---

## `opportunities` (≈8 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| title | text | N |  |  |
| description | text | Y |  |  |
| category | text | N |  |  |
| category_label | text | N |  |  |
| image_url | text | Y |  |  |
| external_url | text | Y |  |  |
| deadline | text | Y |  |  |
| tags | ARRAY | Y | '{}'::text[] |  |
| created_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |
| created_by | uuid | Y |  |  |
| is_active | boolean | Y | true |  |

**`category` 값 목록:** `collab`, `goods`, `mentoring`, `participation`, `speaking`

**Indexes**

- `opportunities_pkey: CREATE UNIQUE INDEX opportunities_pkey ON public.opportunities USING btree (id)`

---

## `opportunity_beneficiaries` (≈27 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| opportunity_id | uuid | N |  |  |
| user_id | uuid | Y |  |  |
| review_url | text | Y |  |  |
| created_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |
| status | text | Y | 'applied'::text |  |
| application_reason | text | Y |  |  |
| beneficiary_name | text | Y |  |  |

**`status` 값 목록:** `applied`, `approved`

**Indexes**

- `opportunity_beneficiaries_pkey: CREATE UNIQUE INDEX opportunity_beneficiaries_pkey ON public.opportunity_beneficiaries USING btree (id)`

---

## `opportunity_likes` (≈5 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| user_id | uuid | N |  |  |
| opportunity_id | uuid | N |  |  |
| created_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |

**Indexes**

- `opportunity_likes_pkey: CREATE UNIQUE INDEX opportunity_likes_pkey ON public.opportunity_likes USING btree (user_id, opportunity_id)`

---

## `page_views` (≈3,062 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| viewed_at | timestamp with time zone | N | now() |  |

**Indexes**

- `page_views_pkey: CREATE UNIQUE INDEX page_views_pkey ON public.page_views USING btree (id)`

---

## `profile_careers` (≈142 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| user_id | uuid | N |  |  |
| title | text | N |  |  |
| career_type | text | Y |  |  |
| role | text | Y |  |  |
| start_date | date | Y |  |  |
| end_date | date | Y |  |  |
| is_current | boolean | Y | false |  |
| created_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |

**`career_type` 값 목록:** `activity`, `ambassador`, `bachelor`, `club`, `committer`, `community`, `company`, `doctor`, `foreign`, `freelance`, `large`, `master`, `midsize`, `other`, `startup`, `university`, `전문연구요원`

**Indexes**

- `profile_careers_pkey: CREATE UNIQUE INDEX profile_careers_pkey ON public.profile_careers USING btree (id)`

---

## `profiles` (≈617 rows)

> Profiles table (Schema Reloaded)
> 

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N |  |  |
| email | text | Y |  |  |
| name | text | Y |  |  |
| profile_image | text | Y |  |  |
| level | integer | Y | 1 |  |
| points | integer | Y | 0 |  |
| created_at | timestamp with time zone | Y | now() |  |
| updated_at | timestamp with time zone | Y | now() |  |
| backup_emails | ARRAY | Y | '{}'::text[] |  |
| cohorts | text | Y |  |  |
| runner_count | integer | Y | 0 |  |
| builder_count | integer | Y | 0 |  |
| activity_score | integer | Y | 0 |  |
| participated_projects | text | Y |  |  |
| bio | text | Y |  |  |
| github_url | text | Y |  |  |
| linkedin_url | text | Y |  |  |
| legacy_imported | boolean | Y | false |  |
| legacy_imported_at | timestamp with time zone | Y |  |  |
| influence_given_count | integer | Y | 0 |  |
| influence_received_count | integer | Y | 0 |  |
| discord_nickname | text | Y |  |  |
| organization | text | Y |  | Company or school affiliation |
| job_roles | ARRAY | Y | '{}'::text[] |  |
| experience_level | text | Y |  |  |
| current_status | ARRAY | Y | '{}'::text[] |  |
| expectations | text | Y |  |  |
| interest_keywords | ARRAY | Y | '{}'::text[] |  |
| message_2026 | text | Y |  |  |
| featured_badges | ARRAY | Y | '{}'::uuid[] | Array of badge IDs user wants to feature on their profile (max 5) |
| highlighted_items | jsonb | Y | '[]'::jsonb | Array of highlighted items user wants to showcase on their profile (max 6). Each item has type (badge/project/influence) and id. |
| organization_type | text | Y |  |  |
| name_en | text | Y |  | English Name |
| dormitory | text | Y |  |  |
| name_kr | text | Y |  |  |
| talents | ARRAY | Y | '{}'::text[] | Array of talents/skills selected by the user (max 2) |
| ai_services | ARRAY | Y | '{}'::text[] |  |

**`experience_level` 값 목록:** `director`, `junior`, `mid`, `none`, `other`, `senior`, `staff`

**`organization_type` 값 목록:** `bachelor`, `company`, `doctor`, `foreign`, `graduate`, `large`, `master`, `midsize`, `other`, `startup`

**Indexes**

- `profiles_pkey: CREATE UNIQUE INDEX profiles_pkey ON public.profiles USING btree (id)`

---

## `program_feedbacks` (≈1 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| program_id | text | N |  |  |
| user_email | text | N |  |  |
| content | text | N |  |  |
| created_at | timestamp with time zone | N | now() |  |

**Indexes**

- `idx_program_feedbacks_created_at: CREATE INDEX idx_program_feedbacks_created_at ON public.program_feedbacks USING btree (created_at)`
- `idx_program_feedbacks_program_id: CREATE INDEX idx_program_feedbacks_program_id ON public.program_feedbacks USING btree (program_id)`
- `program_feedbacks_pkey: CREATE UNIQUE INDEX program_feedbacks_pkey ON public.program_feedbacks USING btree (id)`

---

## `program_followups` (≈102 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| program_id | text | N |  |  |
| user_email | text | N |  |  |
| created_at | timestamp with time zone | N | now() |  |

**Indexes**

- `program_followups_pkey: CREATE UNIQUE INDEX program_followups_pkey ON public.program_followups USING btree (id)`
- `program_followups_program_id_user_email_key: CREATE UNIQUE INDEX program_followups_program_id_user_email_key ON public.program_followups USING btree (program_id, user_email)`

---

## `program_likes` (≈66 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| program_id | text | N |  |  |
| user_email | text | N |  |  |
| created_at | timestamp with time zone | N | now() |  |

**Indexes**

- `program_likes_pkey: CREATE UNIQUE INDEX program_likes_pkey ON public.program_likes USING btree (id)`
- `program_likes_program_id_user_email_key: CREATE UNIQUE INDEX program_likes_program_id_user_email_key ON public.program_likes USING btree (program_id, user_email)`

---

## `project_application_history` (≈302 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| user_id | uuid | N |  |  |
| season | text | N | '12'::text |  |
| project_id | uuid | N |  |  |
| preference_slot | text | N |  |  |
| action_type | text | N |  |  |
| applicant_name_kr | text | Y |  |  |
| created_at | timestamp with time zone | N | now() |  |

**Indexes**

- `project_application_history_pkey: CREATE UNIQUE INDEX project_application_history_pkey ON public.project_application_history USING btree (id)`
- `project_application_history_project_id_idx: CREATE INDEX project_application_history_project_id_idx ON public.project_application_history USING btree (project_id)`
- `project_application_history_season_idx: CREATE INDEX project_application_history_season_idx ON public.project_application_history USING btree (season)`
- `project_application_history_user_id_idx: CREATE INDEX project_application_history_user_id_idx ON public.project_application_history USING btree (user_id)`

---

## `project_applications` (≈265 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| created_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |
| updated_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |
| user_id | uuid | N |  |  |
| season | text | N |  |  |
| applicant_name_kr | text | N |  |  |
| applicant_name_en | text | Y |  |  |
| applicant_email | text | N |  |  |
| applicant_phone | text | N |  |  |
| applicant_discord | text | Y |  |  |
| applicant_github | text | Y |  |  |
| introduction | text | N |  |  |
| motive | text | N |  |  |
| growth_plan | text | N |  |  |
| expectations | text | N |  |  |
| sharing_plan | text | N |  |  |
| schedule_availability | text | N |  |  |
| privacy_consent | boolean | N | false |  |
| data_usage_consent | boolean | N | false |  |
| primary_project_id | uuid | Y |  |  |
| secondary_project_id | uuid | Y |  |  |
| tertiary_project_id | uuid | Y |  |  |
| status | text | Y | 'pending'::text |  |
| reviewer_note | text | Y |  |  |
| final_matched_project_id | uuid | Y |  |  |

**`status` 값 목록:** `approved`, `pending`, `rejected`, `selected`, `waitlist`

**Indexes**

- `project_applications_pkey: CREATE UNIQUE INDEX project_applications_pkey ON public.project_applications USING btree (id)`
- `project_applications_user_id_season_key: CREATE UNIQUE INDEX project_applications_user_id_season_key ON public.project_applications USING btree (user_id, season)`

---

## `project_attendance` (≈290 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| session_id | uuid | N |  |  |
| user_id | uuid | N |  |  |
| status | text | N |  |  |
| created_at | timestamp with time zone | N | now() |  |

**`status` 값 목록:** `present`

**Indexes**

- `project_attendance_pkey: CREATE UNIQUE INDEX project_attendance_pkey ON public.project_attendance USING btree (id)`
- `project_attendance_session_id_user_id_key: CREATE UNIQUE INDEX project_attendance_session_id_user_id_key ON public.project_attendance USING btree (session_id, user_id)`

---

## `project_docs` (≈28 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| project_id | uuid | N |  |  |
| title | text | N |  |  |
| content | text | Y |  |  |
| category | text | Y | 'etc'::text |  |
| author_id | uuid | Y |  |  |
| linked_task_ids | ARRAY | Y | '{}'::uuid[] |  |
| created_at | timestamp with time zone | N | now() |  |
| updated_at | timestamp with time zone | N | now() |  |
| is_public | boolean | Y | false |  |
| type | text | N | 'markdown'::text | Document type: markdown, onboarding, etc. |
| metadata | jsonb | Y | '{}'::jsonb |  |
| position | integer | Y | 0 |  |

**`category` 값 목록:** `etc`

**`type` 값 목록:** `link_external`, `link_wiki`, `markdown`

**Indexes**

- `project_docs_pkey: CREATE UNIQUE INDEX project_docs_pkey ON public.project_docs USING btree (id)`
- `project_docs_project_id_idx: CREATE INDEX project_docs_project_id_idx ON public.project_docs USING btree (project_id)`

---

## `project_members` (≈304 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| project_id | uuid | N |  |  |
| user_id | uuid | N |  |  |
| role | text | N | 'runner'::text |  |
| attendance_rate | integer | Y | 0 |  |
| joined_at | timestamp with time zone | N | now() |  |
| status | text | N | 'active'::text | Membership status: active or pending |

**`role` 값 목록:** `builder`, `member`, `runner`

**`status` 값 목록:** `active`, `claiming`

**Indexes**

- `project_members_pkey: CREATE UNIQUE INDEX project_members_pkey ON public.project_members USING btree (id)`
- `project_members_project_id_user_id_key: CREATE UNIQUE INDEX project_members_project_id_user_id_key ON public.project_members USING btree (project_id, user_id)`

---

## `project_sessions` (≈198 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| project_id | uuid | N |  |  |
| week_number | integer | N |  |  |
| session_date | date | N | CURRENT_DATE |  |
| auth_code | text | N |  |  |
| is_active | boolean | N | true |  |
| created_at | timestamp with time zone | N | now() |  |
| start_at | timestamp with time zone | Y |  |  |
| end_at | timestamp with time zone | Y |  |  |
| description | text | Y |  |  |

**Indexes**

- `project_sessions_pkey: CREATE UNIQUE INDEX project_sessions_pkey ON public.project_sessions USING btree (id)`
- `project_sessions_project_id_week_number_key: CREATE UNIQUE INDEX project_sessions_project_id_week_number_key ON public.project_sessions USING btree (project_id, week_number)`

---

## `project_tasks` (≈30 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| project_id | uuid | N |  |  |
| title | text | N |  |  |
| description | text | Y |  |  |
| status | text | N | 'todo'::text |  |
| priority | text | Y | 'medium'::text |  |
| assignee_id | uuid | Y |  |  |
| helper_ids | ARRAY | Y | '{}'::uuid[] |  |
| start_date | date | Y |  |  |
| end_date | date | Y |  |  |
| result_link | text | Y |  |  |
| parent_task_id | uuid | Y |  |  |
| created_at | timestamp with time zone | N | now() |  |
| updated_at | timestamp with time zone | N | now() |  |
| progress | integer | Y | 0 |  |
| related_link | text | Y |  |  |
| position | double precision | Y | 0 |  |

**`status` 값 목록:** `archived`, `done`, `todo`

**`priority` 값 목록:** `high`, `medium`

**Indexes**

- `project_tasks_pkey: CREATE UNIQUE INDEX project_tasks_pkey ON public.project_tasks USING btree (id)`
- `project_tasks_project_id_idx: CREATE INDEX project_tasks_project_id_idx ON public.project_tasks USING btree (project_id)`

---

## `projects` (≈292 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| title | text | N |  |  |
| description | text | Y |  |  |
| type | text | N | 'season'::text |  |
| status | text | N | 'active'::text |  |
| current_week | integer | Y | 1 |  |
| total_weeks | integer | Y | 16 |  |
| next_meeting | timestamp with time zone | Y |  |  |
| max_members | integer | Y |  |  |
| created_by | uuid | Y |  |  |
| created_at | timestamp with time zone | N | now() |  |
| updated_at | timestamp with time zone | N | now() |  |
| cohort | text | Y |  |  |
| meeting_time | text | Y |  |  |
| meeting_location | text | Y |  |  |
| difficulty | text | Y |  |  |
| period | text | Y |  |  |
| team_page_url | text | Y |  |  |
| project_plan_url | text | Y |  |  |
| data_sharing_method | text | Y |  |  |
| auditing_allowed | boolean | Y | false |  |
| tags | ARRAY | Y |  |  |
| builder_name | text | Y |  |  |
| completed_count | integer | Y | 0 |  |
| dropout_count | integer | Y | 0 |  |
| start_member_count | integer | Y | 0 |  |
| legacy_member_ids | ARRAY | Y | '{}'::uuid[] |  |
| image_url | text | Y |  |  |
| requirements | text | Y |  |  |
| start_date | timestamp with time zone | Y |  |  |
| milestones | jsonb | Y | '[]'::jsonb |  |
| notice | text | Y |  |  |
| meeting_type | text | Y | 'online'::text | Meeting type: online, offline, hybrid, none |
| region | text | Y |  | Region for offline/hybrid meetings |
| desired_talents | ARRAY | Y |  | List of desired talents/roles for recruitment |
| ai_services | ARRAY | Y |  | List of AI services used in the project |
| recruit_start_date | timestamp with time zone | Y |  |  |
| recruit_end_date | timestamp with time zone | Y |  |  |
| discord_webhook_url | text | Y |  |  |
| weekly_plan | jsonb | Y | '[]'::jsonb |  |
| research_group | text | Y |  | Affiliated research group (e.g., 인과추론, HF KREW, etc.) |
| tier | character varying(50) | Y |  |  |

**`type` 값 목록:** `season`

**`status` 값 목록:** `active`, `completed`

**`meeting_type` 값 목록:** `none`, `offline`, `online`

**Indexes**

- `idx_projects_cohort: CREATE INDEX idx_projects_cohort ON public.projects USING btree (cohort)`
- `idx_projects_status: CREATE INDEX idx_projects_status ON public.projects USING btree (status)`
- `idx_projects_type: CREATE INDEX idx_projects_type ON public.projects USING btree (type)`
- `projects_pkey: CREATE UNIQUE INDEX projects_pkey ON public.projects USING btree (id)`

---

## `quest_definitions` (≈5 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| title | text | N |  |  |
| description | text | Y |  |  |
| target_count | integer | Y | 1 |  |
| xp_reward | integer | Y | 10 |  |
| type | text | N |  |  |
| is_active | boolean | Y | true |  |
| created_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |
| icon | text | Y | '⚔️'::text |  |
| event_id | uuid | Y |  |  |

**`type` 값 목록:** `daily`, `event`, `weekly`

**Indexes**

- `quest_definitions_pkey: CREATE UNIQUE INDEX quest_definitions_pkey ON public.quest_definitions USING btree (id)`

---

## `random_squad_queue` (≈0 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| user_id | uuid | N |  |  |
| can_be_leader | boolean | Y | false |  |
| status | text | Y | 'waiting'::text |  |
| matched_squad_id | uuid | Y |  |  |
| created_at | timestamp with time zone | Y | now() |  |

**Indexes**

- `idx_random_queue_created: CREATE INDEX idx_random_queue_created ON public.random_squad_queue USING btree (created_at)`
- `idx_random_queue_status: CREATE INDEX idx_random_queue_status ON public.random_squad_queue USING btree (status)`
- `random_squad_queue_pkey: CREATE UNIQUE INDEX random_squad_queue_pkey ON public.random_squad_queue USING btree (id)`
- `unique_random_queue_user: CREATE UNIQUE INDEX unique_random_queue_user ON public.random_squad_queue USING btree (user_id)`

---

## `recruit_applications` (≈64 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| user_id | uuid | N |  |  |
| season | text | N | '12'::text |  |
| role | text | N | 'academy'::text |  |
| status | text | N | 'applied'::text |  |
| answers | jsonb | Y |  |  |
| reviewer_note | text | Y |  |  |
| created_at | timestamp with time zone | N | now() |  |
| updated_at | timestamp with time zone | N | now() |  |

**Indexes**

- `recruit_applications_pkey: CREATE UNIQUE INDEX recruit_applications_pkey ON public.recruit_applications USING btree (id)`
- `recruit_applications_user_season_role_idx: CREATE UNIQUE INDEX recruit_applications_user_season_role_idx ON public.recruit_applications USING btree (user_id, season, role)`

---

## `registration_submissions` (≈157 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| created_at | timestamp with time zone | N | now() |  |
| registration_type | text | N |  |  |
| name | text | N |  |  |
| referrer | text | Y |  |  |
| email | text | N |  |  |
| discord_nickname | text | N |  |  |
| organization | text | N |  |  |
| job_role | text | N |  |  |
| experience_level | text | N |  |  |
| pseudolab_role | text | N |  |  |
| interested_sessions | ARRAY | N |  |  |
| participation_purpose | ARRAY | N |  |  |
| growth_keyword_2025 | text | N |  |  |
| expectations_2026 | ARRAY | N |  |  |
| message_to_pseudolab | text | Y |  |  |
| email_consent | boolean | N | false |  |
| status | text | N | 'pending'::text |  |
| networking_participation | boolean | N | false |  |
| linkedin_url | text | N | ''::text |  |
| github_url | text | Y |  |  |
| third_party_consent | boolean | N | false |  |
| mbti | text | Y |  |  |
| favorite_season | text | Y |  |  |
| interest_keywords | ARRAY | Y |  |  |
| people_to_meet | ARRAY | Y |  |  |

**`registration_type` 값 목록:** `additional`, `early`, `general`

**`job_role` 값 목록:** `기타`, `기획자`, `엔지니어`, `연구자`, `학생`

**`experience_level` 값 목록:** `CEO/VP`, `디렉터`, `시니어 8-10년`, `없음`, `주니어 1-3년`, `중니어 4-7년`, `찐니어 11년 이상`

**`pseudolab_role` 값 목록:** `뉴비`, `러너`, `리서치 리드`, `빌더`, `스폰서`, `워커`, `이사회`

**`status` 값 목록:** `approved`, `pending`, `rejected`

**Indexes**

- `registration_submissions_pkey: CREATE UNIQUE INDEX registration_submissions_pkey ON public.registration_submissions USING btree (id)`

---

## `resource_comments` (≈9 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| resource_id | uuid | N |  |  |
| user_id | uuid | N |  |  |
| content | text | N |  |  |
| parent_id | uuid | Y |  |  |
| created_at | timestamp with time zone | Y | now() |  |
| updated_at | timestamp with time zone | Y | now() |  |

**Indexes**

- `idx_resource_comments_parent: CREATE INDEX idx_resource_comments_parent ON public.resource_comments USING btree (parent_id)`
- `idx_resource_comments_resource: CREATE INDEX idx_resource_comments_resource ON public.resource_comments USING btree (resource_id)`
- `idx_resource_comments_user: CREATE INDEX idx_resource_comments_user ON public.resource_comments USING btree (user_id)`
- `resource_comments_pkey: CREATE UNIQUE INDEX resource_comments_pkey ON public.resource_comments USING btree (id)`

---

## `resource_reactions` (≈89 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| resource_id | uuid | N |  |  |
| user_id | uuid | N |  |  |
| reaction_type | text | N |  |  |
| created_at | timestamp with time zone | Y | now() |  |

**`reaction_type` 값 목록:** `celebrate`, `laugh`, `like`, `love`

**Indexes**

- `idx_resource_reactions_resource: CREATE INDEX idx_resource_reactions_resource ON public.resource_reactions USING btree (resource_id)`
- `idx_resource_reactions_user: CREATE INDEX idx_resource_reactions_user ON public.resource_reactions USING btree (user_id)`
- `resource_reactions_pkey: CREATE UNIQUE INDEX resource_reactions_pkey ON public.resource_reactions USING btree (id)`
- `resource_reactions_resource_id_user_id_reaction_type_key: CREATE UNIQUE INDEX resource_reactions_resource_id_user_id_reaction_type_key ON public.resource_reactions USING btree (resource_id, user_id, reaction_type)`

---

## `secret_comments` (≈3 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| post_id | uuid | N |  |  |
| author_id | uuid | N |  |  |
| content | text | N |  |  |
| created_at | timestamp with time zone | Y | now() |  |

**Indexes**

- `secret_comments_pkey: CREATE UNIQUE INDEX secret_comments_pkey ON public.secret_comments USING btree (id)`

---

## `secret_interactions` (≈2 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| user_id | uuid | N |  |  |
| post_id | uuid | N |  |  |
| interaction_type | text | N |  |  |
| created_at | timestamp with time zone | Y | now() |  |

**Indexes**

- `secret_interactions_pkey: CREATE UNIQUE INDEX secret_interactions_pkey ON public.secret_interactions USING btree (id)`
- `secret_interactions_user_id_post_id_interaction_type_key: CREATE UNIQUE INDEX secret_interactions_user_id_post_id_interaction_type_key ON public.secret_interactions USING btree (user_id, post_id, interaction_type)`

---

## `secret_posts` (≈1 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| author_id | uuid | N |  |  |
| category | text | N |  |  |
| title | text | N |  |  |
| content | text | N |  |  |
| reactions_agree | integer | Y | 0 |  |
| reactions_useful | integer | Y | 0 |  |
| view_count | integer | Y | 0 |  |
| is_hot | boolean | Y | false |  |
| created_at | timestamp with time zone | Y | now() |  |
| updated_at | timestamp with time zone | Y | now() |  |

**`category` 값 목록:** `career`

**Indexes**

- `secret_posts_pkey: CREATE UNIQUE INDEX secret_posts_pkey ON public.secret_posts USING btree (id)`

---

## `secret_profiles` (≈1 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| user_id | uuid | N |  |  |
| nickname | text | N |  |  |
| share_count | integer | Y | 0 |  |
| created_at | timestamp with time zone | Y | now() |  |

**Indexes**

- `secret_profiles_nickname_key: CREATE UNIQUE INDEX secret_profiles_nickname_key ON public.secret_profiles USING btree (nickname)`
- `secret_profiles_pkey: CREATE UNIQUE INDEX secret_profiles_pkey ON public.secret_profiles USING btree (id)`
- `secret_profiles_user_id_key: CREATE UNIQUE INDEX secret_profiles_user_id_key ON public.secret_profiles USING btree (user_id)`

---

## `session_submissions` (≈1 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| title | text | N |  |  |
| speaker_name | text | N |  |  |
| email | text | N |  |  |
| duration | text | N |  |  |
| description | text | N |  |  |
| target_audience | text | Y |  |  |
| additional_info | text | Y |  |  |
| created_at | timestamp with time zone | N | now() |  |

**Indexes**

- `session_submissions_pkey: CREATE UNIQUE INDEX session_submissions_pkey ON public.session_submissions USING btree (id)`

---

## `speaker_submissions` (≈21 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| topic | text | N |  |  |
| speaker_name | text | N |  |  |
| email | text | N |  |  |
| bio | text | N |  |  |
| duration | text | N |  |  |
| outline | text | N |  |  |
| portfolio_url | text | Y |  |  |
| additional_info | text | Y |  |  |
| created_at | timestamp with time zone | N | now() |  |
| short_desc | text | Y |  |  |
| event_id | uuid | Y |  |  |
| submission_type | text | Y | 'talk'::text |  |

**`submission_type` 값 목록:** `demo-booth`, `lightning-talk`, `talk`

**Indexes**

- `speaker_submissions_pkey: CREATE UNIQUE INDEX speaker_submissions_pkey ON public.speaker_submissions USING btree (id)`

---

## `sponsor_submissions` (≈4 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| company_name | text | N |  |  |
| contact_name | text | N |  |  |
| email | text | N |  |  |
| phone | text | Y |  |  |
| sponsorship_level | text | N |  |  |
| message | text | Y |  |  |
| created_at | timestamp with time zone | N | now() |  |
| logo_url | text | Y |  |  |
| event_id | uuid | Y |  |  |

**`sponsorship_level` 값 목록:** `Community Partner`, `Gold Sponsor`, `Media Partner`, `Silver Sponsor`

**Indexes**

- `sponsor_submissions_pkey: CREATE UNIQUE INDEX sponsor_submissions_pkey ON public.sponsor_submissions USING btree (id)`

---

## `sponsorship_requests` (≈0 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| name | text | N |  |  |
| email | text | N |  |  |
| organization | text | Y |  |  |
| sponsorship_type | text | N |  |  |
| message | text | Y |  |  |
| created_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |

**Indexes**

- `sponsorship_requests_pkey: CREATE UNIQUE INDEX sponsorship_requests_pkey ON public.sponsorship_requests USING btree (id)`

---

## `squad_applications` (≈2 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| squad_id | uuid | N |  |  |
| user_id | uuid | N |  |  |
| slot_number | integer | N |  |  |
| message | text | Y |  |  |
| status | text | Y | 'pending'::text |  |
| created_at | timestamp with time zone | Y | now() |  |

**Indexes**

- `squad_applications_pkey: CREATE UNIQUE INDEX squad_applications_pkey ON public.squad_applications USING btree (id)`
- `unique_squad_application: CREATE UNIQUE INDEX unique_squad_application ON public.squad_applications USING btree (squad_id, user_id)`

---

## `squads` (≈5 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| leader_id | uuid | N |  |  |
| title | text | N |  |  |
| description | text | Y |  |  |
| project_type | text | Y |  |  |
| reference_url | text | Y |  |  |
| reference_title | text | Y |  |  |
| member_1_id | uuid | Y |  |  |
| member_2_id | uuid | Y |  |  |
| member_3_id | uuid | Y |  |  |
| slot_1_role | text | Y |  |  |
| slot_2_role | text | Y |  |  |
| slot_3_role | text | Y |  |  |
| duration | text | Y | '4weeks'::text |  |
| meeting_type | text | Y | 'none'::text |  |
| ai_services | ARRAY | Y | '{}'::text[] |  |
| tech_stack | ARRAY | Y | '{}'::text[] |  |
| collab_style | text | Y | 'hybrid'::text |  |
| region | text | Y |  |  |
| status | text | Y | 'recruiting'::text |  |
| is_active | boolean | Y | true |  |
| created_at | timestamp with time zone | Y | now() |  |
| updated_at | timestamp with time zone | Y | now() |  |

**`project_type` 값 목록:** `hackathon`, `pseudolab_project`, `side_project`, `startup`, `study_group`

**`slot_1_role` 값 목록:** `ai_ml`, `backend`, `frontend`, `research`

**`slot_2_role` 값 목록:** `ai_ml`, `design`, `frontend`

**`slot_3_role` 값 목록:** `any`, `design`, `pm`

**`meeting_type` 값 목록:** `none`, `offline`, `online`

**`status` 값 목록:** `recruiting`

**Indexes**

- `idx_squads_created_at: CREATE INDEX idx_squads_created_at ON public.squads USING btree (created_at DESC)`
- `idx_squads_is_active: CREATE INDEX idx_squads_is_active ON public.squads USING btree (is_active)`
- `idx_squads_leader_id: CREATE INDEX idx_squads_leader_id ON public.squads USING btree (leader_id)`
- `idx_squads_project_type: CREATE INDEX idx_squads_project_type ON public.squads USING btree (project_type)`
- `idx_squads_status: CREATE INDEX idx_squads_status ON public.squads USING btree (status)`
- `squads_pkey: CREATE UNIQUE INDEX squads_pkey ON public.squads USING btree (id)`
- `unique_squad_leader_title: CREATE UNIQUE INDEX unique_squad_leader_title ON public.squads USING btree (leader_id, title)`

---

## `table` (≈0 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | bigint | N |  |  |
| created_at | timestamp with time zone | N | now() |  |

**Indexes**

- `table_pkey: CREATE UNIQUE INDEX table_pkey ON public."table" USING btree (id)`

---

## `user_badges` (≈14 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| user_id | uuid | N |  |  |
| badge_id | uuid | N |  |  |
| event_id | uuid | Y |  |  |
| verified | boolean | Y | false |  |
| verification_data | jsonb | Y |  |  |
| claimed_at | timestamp with time zone | N | now() |  |

**Indexes**

- `user_badges_pkey: CREATE UNIQUE INDEX user_badges_pkey ON public.user_badges USING btree (id)`
- `user_badges_user_id_badge_id_event_id_key: CREATE UNIQUE INDEX user_badges_user_id_badge_id_event_id_key ON public.user_badges USING btree (user_id, badge_id, event_id)`

---

## `user_follows` (≈37 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| program_id | text | N |  |  |
| follower_email | text | N |  |  |
| following_email | text | N |  |  |
| created_at | timestamp with time zone | N | now() |  |

**Indexes**

- `user_follows_pkey: CREATE UNIQUE INDEX user_follows_pkey ON public.user_follows USING btree (id)`
- `user_follows_program_id_follower_email_following_email_key: CREATE UNIQUE INDEX user_follows_program_id_follower_email_following_email_key ON public.user_follows USING btree (program_id, follower_email, following_email)`

---

## `user_influences` (≈106 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| influenced_by_id | uuid | N |  |  |
| influenced_user_id | uuid | N |  |  |
| context_type | text | N | 'general'::text |  |
| context_id | uuid | Y |  |  |
| message | text | Y |  |  |
| created_at | timestamp with time zone | N | now() |  |

**`context_type` 값 목록:** `community_feed`, `feed_inspired`, `feed_like`, `resource`

**Indexes**

- `idx_user_influences_by: CREATE INDEX idx_user_influences_by ON public.user_influences USING btree (influenced_by_id)`
- `idx_user_influences_context: CREATE INDEX idx_user_influences_context ON public.user_influences USING btree (context_id, context_type)`
- `idx_user_influences_user: CREATE INDEX idx_user_influences_user ON public.user_influences USING btree (influenced_user_id)`
- `user_influences_influenced_by_id_influenced_user_id_context_key: CREATE UNIQUE INDEX user_influences_influenced_by_id_influenced_user_id_context_key ON public.user_influences USING btree (influenced_by_id, influenced_user_id, context_type, context_id)`
- `user_influences_pkey: CREATE UNIQUE INDEX user_influences_pkey ON public.user_influences USING btree (id)`

---

## `user_missions` (≈1 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| user_id | uuid | N |  |  |
| mission_id | uuid | N |  |  |
| completed_at | timestamp with time zone | N | now() |  |
| verification_data | jsonb | Y |  |  |
| verified | boolean | Y | false |  |

**Indexes**

- `user_missions_pkey: CREATE UNIQUE INDEX user_missions_pkey ON public.user_missions USING btree (id)`
- `user_missions_user_id_mission_id_key: CREATE UNIQUE INDEX user_missions_user_id_mission_id_key ON public.user_missions USING btree (user_id, mission_id)`

---

## `user_quests` (≈10 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| user_id | uuid | N |  |  |
| quest_id | uuid | N |  |  |
| completed_at | timestamp with time zone | Y | now() |  |
| created_at | timestamp with time zone | Y | now() |  |

**Indexes**

- `user_quests_pkey: CREATE UNIQUE INDEX user_quests_pkey ON public.user_quests USING btree (id)`

---

## `user_roles` (≈664 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| user_id | uuid | N |  |  |
| role | USER-DEFINED | N |  |  |
| created_at | timestamp with time zone | N | now() |  |

**Indexes**

- `user_roles_pkey: CREATE UNIQUE INDEX user_roles_pkey ON public.user_roles USING btree (id)`
- `user_roles_user_id_role_key: CREATE UNIQUE INDEX user_roles_user_id_role_key ON public.user_roles USING btree (user_id, role)`

---

## `user_which_projects` (≈178 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| name | text | Y |  |  |
| project | text | Y |  |  |

---

## `wiki_articles` (≈0 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| title | text | N |  |  |
| slug | text | N |  |  |
| content | text | N | ''::text |  |
| parent_id | uuid | Y |  |  |
| category | text | Y |  |  |
| created_by | uuid | Y |  |  |
| updated_by | uuid | Y |  |  |
| created_at | timestamp with time zone | N | now() |  |
| updated_at | timestamp with time zone | N | now() |  |
| is_published | boolean | N | true |  |
| view_count | integer | N | 0 |  |
| sort_order | integer | N | 0 |  |

**Indexes**

- `idx_wiki_articles_category: CREATE INDEX idx_wiki_articles_category ON public.wiki_articles USING btree (category)`
- `idx_wiki_articles_parent_id: CREATE INDEX idx_wiki_articles_parent_id ON public.wiki_articles USING btree (parent_id)`
- `idx_wiki_articles_slug: CREATE INDEX idx_wiki_articles_slug ON public.wiki_articles USING btree (slug)`
- `wiki_articles_pkey: CREATE UNIQUE INDEX wiki_articles_pkey ON public.wiki_articles USING btree (id)`
- `wiki_articles_slug_key: CREATE UNIQUE INDEX wiki_articles_slug_key ON public.wiki_articles USING btree (slug)`

---

## `wiki_categories` (≈8 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | extensions.uuid_generate_v4() |  |
| name | text | N |  |  |
| slug | text | N |  |  |
| description | text | Y |  |  |
| icon | text | Y |  |  |
| parent_id | uuid | Y |  |  |
| sort_order | integer | Y | 0 |  |
| created_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |
| updated_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |

**Indexes**

- `wiki_categories_pkey: CREATE UNIQUE INDEX wiki_categories_pkey ON public.wiki_categories USING btree (id)`
- `wiki_categories_slug_key: CREATE UNIQUE INDEX wiki_categories_slug_key ON public.wiki_categories USING btree (slug)`

---

## `wiki_pages` (≈6 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | extensions.uuid_generate_v4() |  |
| category_id | uuid | Y |  |  |
| title | text | N |  |  |
| slug | text | N |  |  |
| content | text | Y |  |  |
| view_count | integer | Y | 0 |  |
| is_published | boolean | Y | false |  |
| created_by | uuid | Y |  |  |
| updated_by | uuid | Y |  |  |
| created_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |
| updated_at | timestamp with time zone | N | timezone('utc'::text, now()) |  |

**Indexes**

- `wiki_pages_pkey: CREATE UNIQUE INDEX wiki_pages_pkey ON public.wiki_pages USING btree (id)`
- `wiki_pages_slug_key: CREATE UNIQUE INDEX wiki_pages_slug_key ON public.wiki_pages USING btree (slug)`

---

## `wiki_revisions` (≈10 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| article_id | uuid | Y |  |  |
| content | text | N |  |  |
| edited_by | uuid | Y |  |  |
| edit_summary | text | Y |  |  |
| created_at | timestamp with time zone | N | now() |  |
| page_id | uuid | Y |  |  |
| author_id | uuid | Y |  |  |
| change_summary | text | Y |  |  |
| status | text | Y | 'pending'::text |  |
| reviewer_id | uuid | Y |  |  |
| review_comment | text | Y |  |  |
| reviewed_at | timestamp with time zone | Y |  |  |

**`status` 값 목록:** `approved`

**Indexes**

- `idx_wiki_revisions_article_id: CREATE INDEX idx_wiki_revisions_article_id ON public.wiki_revisions USING btree (article_id)`
- `wiki_revisions_pkey: CREATE UNIQUE INDEX wiki_revisions_pkey ON public.wiki_revisions USING btree (id)`

---

## `xp_history` (≈439 rows)

| column | type | nullable | default | comment |
| --- | --- | --- | --- | --- |
| id | uuid | N | gen_random_uuid() |  |
| user_id | uuid | N |  |  |
| amount | integer | N |  |  |
| reason | text | N |  |  |
| category | text | Y |  |  |
| created_at | timestamp with time zone | N | now() |  |

**Indexes**

- `idx_xp_history_created_at: CREATE INDEX idx_xp_history_created_at ON public.xp_history USING btree (created_at)`
- `idx_xp_history_user_id: CREATE INDEX idx_xp_history_user_id ON public.xp_history USING btree (user_id)`
- `xp_history_pkey: CREATE UNIQUE INDEX xp_history_pkey ON public.xp_history USING btree (id)`