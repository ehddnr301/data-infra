import { SELF, env } from 'cloudflare:test'
import type { Env } from '@pseudolab/shared-types'
import { beforeAll, beforeEach, describe, expect, it } from 'vitest'
import { z } from 'zod'
import { ProblemDetailSchema, apiSuccessSchema, expectJson, expectProblemJson } from '../helpers'

const db = (env as unknown as Env).DB

const ListingOwnerSchema = z.object({
  id: z.string(),
  slug: z.string(),
  display_name: z.string(),
  team_name: z.string().nullable(),
  role_title: z.string().nullable(),
  bio: z.string().nullable(),
  avatar_url: z.string().nullable(),
  contact_email: z.string().nullable(),
  slack_channel: z.string().nullable(),
})

const MarketplaceListingDatasetSchema = z.object({
  id: z.string(),
  domain: z.enum(['github', 'discord', 'linkedin', 'members']),
  slug: z.string(),
  name: z.string(),
  description: z.string(),
  owner: z.string().nullable(),
  tags: z.array(z.string()),
  purpose: z.string().nullable(),
  limitations: z.array(z.string()),
  usage_examples: z.array(z.string()),
  preview_available: z.boolean(),
  has_pii: z.boolean(),
  updated_at: z.string(),
})

const ListingBusinessNeedSchema = z.object({
  id: z.string(),
  title: z.string(),
  summary: z.string(),
  display_order: z.number(),
})

const ListingResourceSchema = z.object({
  id: z.string(),
  type: z.enum(['sql', 'api', 'notebook', 'documentation']),
  title: z.string(),
  summary: z.string().nullable(),
  url: z.string().nullable(),
  content: z.string().nullable(),
  display_order: z.number(),
  related_dataset_ids: z.array(z.string()),
})

const MarketplaceListingSummarySchema = z.object({
  id: z.string(),
  dataset_id: z.string(),
  domain: z.enum(['github', 'discord', 'linkedin', 'members']),
  slug: z.string(),
  title: z.string(),
  subtitle: z.string().nullable(),
  description: z.string(),
  category: z.string(),
  update_frequency: z.string().nullable(),
  coverage_summary: z.string().nullable(),
  documentation_url: z.string().nullable(),
  last_verified_at: z.string().nullable(),
  owner: ListingOwnerSchema,
  business_need_tags: z.array(z.string()),
  preview_available: z.boolean(),
  has_pii: z.boolean(),
})

const MarketplaceListingDetailSchema = MarketplaceListingSummarySchema.extend({
  dataset: MarketplaceListingDatasetSchema,
  business_needs: z.array(ListingBusinessNeedSchema),
  resources: z.array(ListingResourceSchema),
  related_listings: z.array(MarketplaceListingSummarySchema),
})

const MarketplaceDomainSummarySchema = z.object({
  key: z.enum(['github', 'discord', 'linkedin', 'members']),
  label: z.string(),
  description: z.string(),
  listing_count: z.number(),
  featured_listing_slug: z.string().nullable(),
  featured_listing_title: z.string().nullable(),
})

const MarketplaceDomainDetailSchema = MarketplaceDomainSummarySchema.extend({
  listings: z.array(MarketplaceListingSummarySchema),
})

beforeAll(async () => {
  await db.exec(
    'CREATE TABLE IF NOT EXISTS catalog_datasets (id TEXT PRIMARY KEY, domain TEXT NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL, schema_json TEXT, lineage_json TEXT, owner TEXT, tags TEXT, purpose TEXT, limitations TEXT, usage_examples TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);',
  )
  await db.exec(
    'CREATE TABLE IF NOT EXISTS catalog_columns (dataset_id TEXT NOT NULL, column_name TEXT NOT NULL, data_type TEXT NOT NULL, description TEXT, is_pii INTEGER NOT NULL DEFAULT 0, examples TEXT, PRIMARY KEY (dataset_id, column_name));',
  )
  await db.exec(
    'CREATE TABLE IF NOT EXISTS listing_owners (id TEXT PRIMARY KEY, slug TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL, team_name TEXT, role_title TEXT, bio TEXT, avatar_url TEXT, contact_email TEXT, slack_channel TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);',
  )
  await db.exec(
    "CREATE TABLE IF NOT EXISTS marketplace_listings (id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL UNIQUE, domain TEXT NOT NULL CHECK (domain IN ('github', 'discord', 'linkedin', 'members')), slug TEXT NOT NULL, owner_id TEXT NOT NULL, title TEXT NOT NULL, subtitle TEXT, description TEXT NOT NULL, category TEXT NOT NULL, coverage_summary TEXT, update_frequency TEXT, documentation_url TEXT, last_verified_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE (domain, slug));",
  )
  await db.exec(
    'CREATE TABLE IF NOT EXISTS listing_business_needs (id TEXT PRIMARY KEY, listing_id TEXT NOT NULL, title TEXT NOT NULL, summary TEXT NOT NULL, display_order INTEGER NOT NULL DEFAULT 0);',
  )
  await db.exec(
    "CREATE TABLE IF NOT EXISTS listing_resources (id TEXT PRIMARY KEY, listing_id TEXT NOT NULL, dataset_id TEXT, resource_type TEXT NOT NULL, title TEXT NOT NULL, summary TEXT, url TEXT, content TEXT, related_dataset_ids TEXT NOT NULL DEFAULT '[]', display_order INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);",
  )
})

beforeEach(async () => {
  await db.exec('DELETE FROM listing_resources;')
  await db.exec('DELETE FROM listing_business_needs;')
  await db.exec('DELETE FROM marketplace_listings;')
  await db.exec('DELETE FROM listing_owners;')
  await db.exec('DELETE FROM catalog_columns;')
  await db.exec('DELETE FROM catalog_datasets;')

  const datasetInsert = db.prepare(
    'INSERT INTO catalog_datasets (id, domain, name, description, schema_json, lineage_json, owner, tags, purpose, limitations, usage_examples, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
  )
  for (const dataset of [
    [
      'discord.messages.v1',
      'discord',
      'Discord Messages',
      'Community messages dataset',
      null,
      null,
      'qa',
      '["discord","community"]',
      'Moderation triage and engagement review',
      '["Content can contain PII"]',
      '["Review recent moderation spikes"]',
      '2025-01-01T00:00:00.000Z',
      '2025-01-10T00:00:00.000Z',
    ],
    [
      'discord.watermarks.v1',
      'discord',
      'Discord Watermarks',
      'Collector progress dataset',
      null,
      null,
      'qa',
      '["discord","operations"]',
      'Collector recovery and freshness checks',
      '["No preview source mapped"]',
      '["Check lagging channels first"]',
      '2025-01-01T00:00:00.000Z',
      '2025-01-09T00:00:00.000Z',
    ],
    [
      'github.push-events.v1',
      'github',
      'dl_push_events',
      'Daily engineering activity feed',
      null,
      null,
      'qa',
      '["github","engineering"]',
      'Track release cadence and maintainer throughput across PseudoLab repositories',
      '["Derived from gharchive.org and REST API activity only"]',
      '["Compare push cadence by repository and release windows"]',
      '2025-01-01T00:00:00.000Z',
      '2025-01-08T00:00:00.000Z',
    ],
    [
      'github.create-events.v1',
      'github',
      'GitHub Project Builders',
      'Builder and project-start signal',
      null,
      null,
      'qa',
      '["github","builders"]',
      'Identify who launched new study and project repositories',
      '["Builder interpretation is limited to repository creation rows"]',
      '["Find builders who created new repositories this week"]',
      '2025-01-01T00:00:00.000Z',
      '2025-01-12T00:00:00.000Z',
    ],
    [
      'github.watch-events.v1',
      'github',
      'dl_watch_events',
      'Support and interest signal',
      null,
      null,
      'qa',
      '["github","community","support"]',
      'Measure support around study projects with internal vs external weighting',
      '["Internal interest uses repo membership or prior code contribution heuristic"]',
      '["Rank repositories by weighted internal and external interest"]',
      '2025-01-01T00:00:00.000Z',
      '2025-01-11T00:00:00.000Z',
    ],
    [
      'ds.github.repo.v1',
      'github',
      'GitHub Repository Inventory',
      'Repository inventory and portfolio map',
      null,
      null,
      'qa',
      '["github","inventory"]',
      'Audit the active study and research repository portfolio',
      '["Inventory snapshots may lag live GitHub state"]',
      '["Review project ownership and portfolio coverage"]',
      '2025-01-01T00:00:00.000Z',
      '2025-01-07T00:00:00.000Z',
    ],
  ]) {
    await datasetInsert.bind(...dataset).run()
  }

  await db.exec(
    "INSERT INTO catalog_columns (dataset_id, column_name, data_type, description, is_pii, examples) VALUES ('discord.messages.v1', 'content', 'TEXT', 'message body', 1, NULL), ('discord.watermarks.v1', 'last_message_id', 'TEXT', 'cursor', 0, NULL), ('github.push-events.v1', 'repo_name', 'TEXT', 'repository name', 0, NULL), ('github.create-events.v1', 'is_repo_creation', 'INTEGER', 'repository creation flag', 0, NULL), ('github.watch-events.v1', 'user_login', 'TEXT', 'watch actor login', 0, NULL), ('ds.github.repo.v1', 'repo_id', 'TEXT', 'repository id', 0, NULL);",
  )

  const ownerInsert = db.prepare(
    'INSERT INTO listing_owners (id, slug, display_name, team_name, role_title, bio, avatar_url, contact_email, slack_channel, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
  )
  for (const owner of [
    [
      'owner-discord',
      'discord-marketplace',
      'Discord Data Team',
      'Data Platform',
      'Marketplace Owner',
      'Discord marketplace owners',
      null,
      'discord@pseudolab.org',
      '#discord-data',
      '2025-01-01T00:00:00.000Z',
      '2025-01-01T00:00:00.000Z',
    ],
    [
      'owner-github',
      'github-marketplace',
      'GitHub Data Team',
      'Data Platform',
      'Marketplace Owner',
      'GitHub marketplace owners',
      null,
      'github@pseudolab.org',
      '#github-data',
      '2025-01-01T00:00:00.000Z',
      '2025-01-01T00:00:00.000Z',
    ],
  ]) {
    await ownerInsert.bind(...owner).run()
  }

  const listingInsert = db.prepare(
    'INSERT INTO marketplace_listings (id, dataset_id, domain, slug, owner_id, title, subtitle, description, category, coverage_summary, update_frequency, documentation_url, last_verified_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
  )
  for (const listing of [
    [
      'listing-discord-messages',
      'discord.messages.v1',
      'discord',
      'messages.v1',
      'owner-discord',
      'Discord Messages',
      'Privacy-aware community message archive',
      '공지/스터디 채널 중심의 Discord 메시지를 배치 수집해 moderation과 engagement 변화를 privacy-aware 범위에서 검토합니다.',
      'community',
      'Discord Bot/API batch collection → R2 raw JSON + D1 discord_messages, DM은 수집 대상에서 제외합니다.',
      'daily_or_weekly',
      '/api/catalog/datasets/discord.messages.v1',
      '2025-01-10T00:00:00.000Z',
      '2025-01-01T00:00:00.000Z',
      '2025-01-10T00:00:00.000Z',
    ],
    [
      'listing-discord-watermarks',
      'discord.watermarks.v1',
      'discord',
      'watermarks.v1',
      'owner-discord',
      'Discord Collector Watermarks',
      'Collector freshness and recovery ledger',
      '채널별 watermark와 scan cursor를 기반으로 Discord 배치 수집 상태와 recovery 대상을 추적합니다.',
      'operations',
      'Discord batch collector watermark table로 채널별 last_message_id와 scan cursor를 관리합니다.',
      'daily_or_weekly',
      '/api/catalog/datasets/discord.watermarks.v1',
      '2025-01-09T00:00:00.000Z',
      '2025-01-01T00:00:00.000Z',
      '2025-01-09T00:00:00.000Z',
    ],
    [
      'listing-github-push-events',
      'github.push-events.v1',
      'github',
      'push-events.v1',
      'owner-github',
      'dl_push_events',
      'Daily engineering activity feed',
      'PseudoLab GitHub org와 산하 프로젝트의 push 활동을 일 배치로 적재해 릴리즈 cadence와 maintainer throughput을 추적합니다.',
      'engineering',
      'gharchive.org + REST API → org/repo filter → R2 raw + D1 dl_push_events',
      'daily',
      '/api/catalog/datasets/github.push-events.v1',
      '2025-01-08T00:00:00.000Z',
      '2025-01-01T00:00:00.000Z',
      '2025-01-08T00:00:00.000Z',
    ],
    [
      'listing-github-create-events',
      'github.create-events.v1',
      'github',
      'create-events.v1',
      'owner-github',
      'GitHub Project Builders',
      'Builder and project-start signal',
      '조직 저장소의 repository creation 이벤트를 기반으로 누가 새 스터디/프로젝트 저장소를 시작했는지 추적하는 builder 신호입니다.',
      'builders',
      'D1 dl_create_events 중 organization repository creation 행만 builder 신호로 해석하며 branch/tag create는 제외합니다.',
      'daily',
      '/api/catalog/datasets/github.create-events.v1',
      '2025-01-12T00:00:00.000Z',
      '2025-01-01T00:00:00.000Z',
      '2025-01-12T00:00:00.000Z',
    ],
    [
      'listing-github-watch-events',
      'github.watch-events.v1',
      'github',
      'watch-events.v1',
      'owner-github',
      'dl_watch_events',
      'Support and interest signal',
      'Watch/star 이벤트를 기반으로 어떤 스터디/프로젝트가 관심과 응원을 받는지 파악하는 support 신호입니다.',
      'community',
      'D1 dl_watch_events 기반 관심 신호이며 내부는 repo membership 또는 prior code contribution evidence로 분리합니다.',
      'daily',
      '/api/catalog/datasets/github.watch-events.v1',
      '2025-01-11T00:00:00.000Z',
      '2025-01-01T00:00:00.000Z',
      '2025-01-11T00:00:00.000Z',
    ],
    [
      'listing-github-repo',
      'ds.github.repo.v1',
      'github',
      'ds.github.repo.v1',
      'owner-github',
      'GitHub Repository Inventory',
      'Repository inventory and portfolio map',
      'PseudoLab 메인 org와 산하 프로젝트 저장소를 inventory 관점에서 정리해 프로젝트 포트폴리오와 ownership을 파악합니다.',
      'inventory',
      'Repository inventory snapshots로 study/research 포트폴리오, ownership, 운영 범위를 파악합니다.',
      'periodic',
      '/api/catalog/datasets/ds.github.repo.v1',
      '2025-01-07T00:00:00.000Z',
      '2025-01-01T00:00:00.000Z',
      '2025-01-07T00:00:00.000Z',
    ],
  ]) {
    await listingInsert.bind(...listing).run()
  }

  const needInsert = db.prepare(
    'INSERT INTO listing_business_needs (id, listing_id, title, summary, display_order) VALUES (?, ?, ?, ?, ?)',
  )
  for (const need of [
    [
      'need-discord-messages-1',
      'listing-discord-messages',
      'Moderation and engagement review',
      '공지와 스터디 채널 활동을 privacy-aware 범위에서 함께 검토합니다.',
      1,
    ],
    [
      'need-discord-messages-2',
      'listing-discord-messages',
      'Privacy-aware collection policy',
      'DM 제외와 public study channel 우선 원칙을 함께 설명합니다.',
      2,
    ],
    [
      'need-discord-watermarks-1',
      'listing-discord-watermarks',
      'Collector freshness review',
      '수집이 지연되거나 멈춘 채널을 빠르게 복구합니다.',
      1,
    ],
    [
      'need-github-push-1',
      'listing-github-push-events',
      'Release cadence monitoring',
      '스터디/프로젝트 저장소의 코드 흐름과 maintainer activity를 일 단위로 검토합니다.',
      1,
    ],
    [
      'need-github-create-1',
      'listing-github-create-events',
      'Community builder detection',
      '새 스터디/프로젝트 저장소가 언제, 누가 시작했는지 builder 신호로 확인합니다.',
      1,
    ],
    [
      'need-github-watch-1',
      'listing-github-watch-events',
      'Support signal review',
      '프로젝트별 관심/응원을 내부와 외부 반응으로 나눠 해석합니다.',
      1,
    ],
    [
      'need-github-repo-1',
      'listing-github-repo',
      'Portfolio inventory audit',
      '현재 운영 중인 저장소 포트폴리오와 ownership 현황을 감사합니다.',
      1,
    ],
  ]) {
    await needInsert.bind(...need).run()
  }

  const resourceInsert = db.prepare(
    'INSERT INTO listing_resources (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
  )
  for (const resource of [
    [
      'resource-discord-messages-preview',
      'listing-discord-messages',
      'discord.messages.v1',
      'api',
      'Preview API',
      '최근 community message preview를 바로 확인합니다.',
      '/api/catalog/datasets/discord.messages.v1/preview',
      null,
      '["discord.messages.v1"]',
      1,
      '2025-01-01T00:00:00.000Z',
      '2025-01-01T00:00:00.000Z',
    ],
    [
      'resource-discord-messages-sql',
      'listing-discord-messages',
      'discord.messages.v1',
      'sql',
      'Recent channel activity SQL',
      '최근 community activity를 SQL로 살펴봅니다.',
      null,
      'SELECT channel_name, author_username, created_at FROM discord_messages ORDER BY created_at DESC LIMIT 20;',
      '["discord.messages.v1"]',
      2,
      '2025-01-01T00:00:00.000Z',
      '2025-01-01T00:00:00.000Z',
    ],
    [
      'resource-github-push-api',
      'listing-github-push-events',
      'github.push-events.v1',
      'api',
      'Dataset API',
      'Catalog metadata와 최신 검증 시점을 확인합니다.',
      '/api/catalog/datasets/github.push-events.v1',
      null,
      '["github.push-events.v1"]',
      1,
      '2025-01-01T00:00:00.000Z',
      '2025-01-01T00:00:00.000Z',
    ],
    [
      'resource-github-push-sql',
      'listing-github-push-events',
      'github.push-events.v1',
      'sql',
      'Release cadence SQL',
      '프로젝트별 push cadence를 빠르게 확인합니다.',
      null,
      `SELECT base_date, repo_name, COUNT(DISTINCT event_id) AS push_events FROM dl_push_events WHERE organization = 'pseudolab' GROUP BY base_date, repo_name ORDER BY base_date DESC, push_events DESC LIMIT 30;`,
      '["github.push-events.v1"]',
      2,
      '2025-01-01T00:00:00.000Z',
      '2025-01-01T00:00:00.000Z',
    ],
    [
      'resource-github-create-api',
      'listing-github-create-events',
      'github.create-events.v1',
      'api',
      'Dataset API',
      'Builder signal metadata와 최신 검증 시점을 확인합니다.',
      '/api/catalog/datasets/github.create-events.v1',
      null,
      '["github.create-events.v1"]',
      1,
      '2025-01-01T00:00:00.000Z',
      '2025-01-01T00:00:00.000Z',
    ],
    [
      'resource-github-create-sql',
      'listing-github-create-events',
      'github.create-events.v1',
      'sql',
      'Builder launch SQL',
      'repository creation만 골라 builder launch를 확인합니다.',
      null,
      `SELECT base_date, repo_name, user_login FROM dl_create_events WHERE organization = 'pseudolab' AND is_repo_creation = 1 ORDER BY base_date DESC LIMIT 30;`,
      '["github.create-events.v1"]',
      2,
      '2025-01-01T00:00:00.000Z',
      '2025-01-01T00:00:00.000Z',
    ],
    [
      'resource-github-watch-api',
      'listing-github-watch-events',
      'github.watch-events.v1',
      'api',
      'Dataset API',
      'Support signal metadata와 최신 검증 시점을 확인합니다.',
      '/api/catalog/datasets/github.watch-events.v1',
      null,
      '["github.watch-events.v1"]',
      1,
      '2025-01-01T00:00:00.000Z',
      '2025-01-01T00:00:00.000Z',
    ],
    [
      'resource-github-watch-sql',
      'listing-github-watch-events',
      'github.watch-events.v1',
      'sql',
      'Weighted interest SQL',
      '내부/외부 관심을 가중치로 분리해 확인합니다.',
      null,
      `WITH internal_logins AS ( SELECT member_login AS user_login FROM dl_member_events WHERE is_member_added = 1 AND member_login IS NOT NULL UNION SELECT user_login FROM dl_push_events UNION SELECT user_login FROM dl_pull_request_events UNION SELECT pr_author_login AS user_login FROM dl_pull_request_events WHERE pr_author_login IS NOT NULL UNION SELECT reviewer_login AS user_login FROM dl_pull_request_review_events WHERE reviewer_login IS NOT NULL UNION SELECT commenter_login AS user_login FROM dl_pull_request_review_comment_events WHERE commenter_login IS NOT NULL ) SELECT w.repo_name, COUNT(*) FILTER (WHERE i.user_login IS NOT NULL) AS internal_watch_count, COUNT(*) FILTER (WHERE i.user_login IS NULL) AS external_watch_count, COUNT(*) FILTER (WHERE i.user_login IS NOT NULL) * 2 + COUNT(*) FILTER (WHERE i.user_login IS NULL) AS weighted_interest_score FROM dl_watch_events w LEFT JOIN internal_logins i ON i.user_login = w.user_login WHERE w.organization = 'pseudolab' GROUP BY w.repo_name ORDER BY weighted_interest_score DESC, w.repo_name ASC LIMIT 30;`,
      '["github.watch-events.v1"]',
      2,
      '2025-01-01T00:00:00.000Z',
      '2025-01-01T00:00:00.000Z',
    ],
    [
      'resource-github-repo-api',
      'listing-github-repo',
      'ds.github.repo.v1',
      'api',
      'Dataset API',
      'Catalog metadata와 최신 검증 시점을 확인합니다.',
      '/api/catalog/datasets/ds.github.repo.v1',
      null,
      '["ds.github.repo.v1"]',
      1,
      '2025-01-01T00:00:00.000Z',
      '2025-01-01T00:00:00.000Z',
    ],
    [
      'resource-github-repo-guide',
      'listing-github-repo',
      'ds.github.repo.v1',
      'documentation',
      'Ownership audit guide',
      '프로젝트 포트폴리오와 ownership 검토 지침입니다.',
      null,
      'Review repository inventory for study/research portfolio scope, ownership, and coverage.',
      '["ds.github.repo.v1"]',
      2,
      '2025-01-01T00:00:00.000Z',
      '2025-01-01T00:00:00.000Z',
    ],
  ]) {
    await resourceInsert.bind(...resource).run()
  }
})

describe('marketplace routes', () => {
  it('returns dataset-centric listing summaries', async () => {
    const res = await SELF.fetch('http://example.com/api/marketplace/listings')

    expect(res.status).toBe(200)
    expectJson(res)

    const parsed = apiSuccessSchema(z.array(MarketplaceListingSummarySchema)).safeParse(
      await res.json(),
    )
    expect(parsed.success).toBe(true)
    if (!parsed.success) {
      return
    }

    const listing = parsed.data.data.find((item) => item.dataset_id === 'discord.messages.v1')
    expect(listing?.slug).toBe('messages.v1')
    expect(listing?.domain).toBe('discord')
    expect(listing?.preview_available).toBe(true)
    expect(listing?.has_pii).toBe(true)
    expect(listing?.update_frequency).toBe('daily_or_weekly')
    expect(listing?.business_need_tags).toEqual([
      'Moderation and engagement review',
      'Privacy-aware collection policy',
    ])
  })

  it('returns listing detail with singular dataset payload and related listings', async () => {
    const res = await SELF.fetch('http://example.com/api/marketplace/listings/discord/messages.v1')

    expect(res.status).toBe(200)
    expectJson(res)

    const parsed = apiSuccessSchema(MarketplaceListingDetailSchema).safeParse(await res.json())
    expect(parsed.success).toBe(true)
    if (!parsed.success) {
      return
    }

    expect(parsed.data.data.dataset.id).toBe('discord.messages.v1')
    expect(parsed.data.data.dataset.slug).toBe('messages.v1')
    expect(parsed.data.data.dataset.limitations).toEqual(['Content can contain PII'])
    expect(parsed.data.data.dataset.usage_examples).toEqual(['Review recent moderation spikes'])
    expect(parsed.data.data.business_needs).toHaveLength(2)
    expect(parsed.data.data.resources).toHaveLength(2)
    expect(parsed.data.data.related_listings[0]?.dataset_id).toBe('discord.watermarks.v1')
    expect(parsed.data.data.related_listings[0]?.slug).toBe('watermarks.v1')
  })

  it('marks unmapped datasets as preview unavailable', async () => {
    const res = await SELF.fetch(
      'http://example.com/api/marketplace/listings/discord/watermarks.v1',
    )

    expect(res.status).toBe(200)
    expectJson(res)

    const parsed = apiSuccessSchema(MarketplaceListingDetailSchema).safeParse(await res.json())
    expect(parsed.success).toBe(true)
    if (!parsed.success) {
      return
    }

    expect(parsed.data.data.preview_available).toBe(false)
    expect(parsed.data.data.dataset.preview_available).toBe(false)
  })

  it('returns builder semantics for GitHub create-event listings', async () => {
    const res = await SELF.fetch(
      'http://example.com/api/marketplace/listings/github/create-events.v1',
    )

    expect(res.status).toBe(200)
    expectJson(res)

    const parsed = apiSuccessSchema(MarketplaceListingDetailSchema).safeParse(await res.json())
    expect(parsed.success).toBe(true)
    if (!parsed.success) {
      return
    }

    expect(parsed.data.data.title).toBe('GitHub Project Builders')
    expect(parsed.data.data.description).toContain('새 스터디/프로젝트 저장소')
    expect(parsed.data.data.coverage_summary).toContain('repository creation')
    expect(parsed.data.data.coverage_summary).toContain('branch/tag create는 제외')
    expect(parsed.data.data.business_needs[0]?.title).toBe('Community builder detection')
    expect(parsed.data.data.resources[1]?.content).toContain('is_repo_creation = 1')
  })

  it('returns weighted support semantics for GitHub watch-event listings', async () => {
    const res = await SELF.fetch(
      'http://example.com/api/marketplace/listings/github/watch-events.v1',
    )

    expect(res.status).toBe(200)
    expectJson(res)

    const parsed = apiSuccessSchema(MarketplaceListingDetailSchema).safeParse(await res.json())
    expect(parsed.success).toBe(true)
    if (!parsed.success) {
      return
    }

    expect(parsed.data.data.title).toBe('dl_watch_events')
    expect(parsed.data.data.description).toContain('관심과 응원')
    expect(parsed.data.data.coverage_summary).toContain('prior code contribution')
    expect(parsed.data.data.business_needs[0]?.title).toBe('Support signal review')
    expect(parsed.data.data.resources[1]?.content).toContain('weighted_interest_score')
    expect(parsed.data.data.resources[1]?.content).toContain('dl_member_events')
  })

  it('returns marketplace domain summaries', async () => {
    const res = await SELF.fetch('http://example.com/api/marketplace/domains')

    expect(res.status).toBe(200)
    expectJson(res)

    const parsed = apiSuccessSchema(z.array(MarketplaceDomainSummarySchema)).safeParse(
      await res.json(),
    )
    expect(parsed.success).toBe(true)
    if (!parsed.success) {
      return
    }

    const github = parsed.data.data.find((item) => item.key === 'github')
    const discord = parsed.data.data.find((item) => item.key === 'discord')
    expect(github?.description).toBe(
      'gharchive.org and GitHub REST API daily batches for repository activity, builder launches, and community interest across PseudoLab projects.',
    )
    expect(github?.listing_count).toBe(4)
    expect(github?.featured_listing_slug).toBe('create-events.v1')
    expect(discord?.listing_count).toBe(2)
    expect(discord?.description).toBe(
      'Privacy-aware Discord Bot/API batches for community messages and collector health, focused on public study channels and excluding DMs.',
    )
    expect(discord?.featured_listing_title).toBe('Discord Messages')
  })

  it('returns marketplace domain detail', async () => {
    const res = await SELF.fetch('http://example.com/api/marketplace/domains/github')

    expect(res.status).toBe(200)
    expectJson(res)

    const parsed = apiSuccessSchema(MarketplaceDomainDetailSchema).safeParse(await res.json())
    expect(parsed.success).toBe(true)
    if (!parsed.success) {
      return
    }

    expect(parsed.data.data.key).toBe('github')
    expect(parsed.data.data.description).toBe(
      'gharchive.org and GitHub REST API daily batches for repository activity, builder launches, and community interest across PseudoLab projects.',
    )
    expect(parsed.data.data.listings).toHaveLength(4)
    expect(parsed.data.data.listings.map((item) => item.slug)).toEqual([
      'create-events.v1',
      'watch-events.v1',
      'push-events.v1',
      'ds.github.repo.v1',
    ])
  })

  it('returns 404 for unknown listing detail', async () => {
    const res = await SELF.fetch(
      'http://example.com/api/marketplace/listings/github/does-not-exist',
    )

    expect(res.status).toBe(404)
    expectProblemJson(res)

    const parsed = ProblemDetailSchema.safeParse(await res.json())
    expect(parsed.success).toBe(true)
  })

  it('returns validation error for invalid domain detail', async () => {
    const res = await SELF.fetch('http://example.com/api/marketplace/domains/not-a-domain')

    expect(res.status).toBe(400)
    expectProblemJson(res)
  })
})
