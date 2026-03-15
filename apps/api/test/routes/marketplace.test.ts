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
      'Push Events',
      'Repository push activity dataset',
      null,
      null,
      'qa',
      '["github"]',
      'Release and throughput monitoring',
      '["Does not include private repos"]',
      '["Compare push spikes with incidents"]',
      '2025-01-01T00:00:00.000Z',
      '2025-01-08T00:00:00.000Z',
    ],
    [
      'ds.github.repo.v1',
      'github',
      'GitHub Repo Dataset',
      'Repository inventory dataset',
      null,
      null,
      'qa',
      '["github","inventory"]',
      'Repository inventory reporting',
      '["Snapshots are periodic"]',
      '["Audit repository ownership"]',
      '2025-01-01T00:00:00.000Z',
      '2025-01-07T00:00:00.000Z',
    ],
  ]) {
    await datasetInsert.bind(...dataset).run()
  }

  await db.exec(
    "INSERT INTO catalog_columns (dataset_id, column_name, data_type, description, is_pii, examples) VALUES ('discord.messages.v1', 'content', 'TEXT', 'message body', 1, NULL), ('discord.watermarks.v1', 'last_message_id', 'TEXT', 'cursor', 0, NULL), ('github.push-events.v1', 'repo_name', 'TEXT', 'repository name', 0, NULL), ('ds.github.repo.v1', 'repo_id', 'TEXT', 'repository id', 0, NULL);",
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
      'Discord dataset product',
      'Moderation triage and engagement review',
      'community',
      'Community messages dataset',
      'internal',
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
      'Discord Watermarks',
      'Discord dataset product',
      'Collector recovery and freshness checks',
      'operations',
      'Collector progress dataset',
      'internal',
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
      'Push Events',
      'GitHub dataset product',
      'Release and throughput monitoring',
      'engineering',
      'Repository push activity dataset',
      'internal',
      '/api/catalog/datasets/github.push-events.v1',
      '2025-01-08T00:00:00.000Z',
      '2025-01-01T00:00:00.000Z',
      '2025-01-08T00:00:00.000Z',
    ],
    [
      'listing-github-repo',
      'ds.github.repo.v1',
      'github',
      'ds.github.repo.v1',
      'owner-github',
      'GitHub Repo Dataset',
      'GitHub dataset product',
      'Repository inventory reporting',
      'engineering',
      'Repository inventory dataset',
      'internal',
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
      'Moderation triage',
      'Identify message anomalies quickly.',
      1,
    ],
    [
      'need-discord-messages-2',
      'listing-discord-messages',
      'Engagement review',
      'Track healthy participation signals.',
      2,
    ],
    [
      'need-discord-watermarks-1',
      'listing-discord-watermarks',
      'Collector recovery',
      'Recover stuck channels and scans.',
      1,
    ],
    [
      'need-github-push-1',
      'listing-github-push-events',
      'Release monitoring',
      'Track push volume around releases.',
      1,
    ],
    [
      'need-github-repo-1',
      'listing-github-repo',
      'Inventory audit',
      'Review repository ownership and metadata.',
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
      'Open the preview endpoint.',
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
      'Recent moderation query',
      'Inspect recent community activity.',
      null,
      'SELECT channel_id, content FROM discord_messages ORDER BY created_at DESC LIMIT 20;',
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
      'Open the dataset endpoint.',
      '/api/catalog/datasets/github.push-events.v1',
      null,
      '["github.push-events.v1"]',
      1,
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
    expect(listing?.business_need_tags).toEqual(['Moderation triage', 'Engagement review'])
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
    expect(github?.listing_count).toBe(2)
    expect(github?.featured_listing_slug).toBe('push-events.v1')
    expect(discord?.listing_count).toBe(2)
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
    expect(parsed.data.data.listings).toHaveLength(2)
    expect(parsed.data.data.listings.map((item) => item.slug)).toEqual([
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
