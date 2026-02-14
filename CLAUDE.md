# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GitHub Archive Data Platform on Cloudflare — a data catalog and analytics platform for GitHub activity data, built entirely on Cloudflare's edge infrastructure. The project follows Data Mesh principles with domain-driven data ownership.

Primary language for documentation and discussion is Korean.

## Architecture

### Planned Monorepo Structure (Turborepo + uv workspace)

```
domains/
├── github-archive/        # Domain 1: GitHub Archive data
│   ├── ingestion/         #   Python ETL (runs on local/batch server)
│   ├── storage/           #   D1 schema + R2 structure definitions
│   ├── api/               #   Cloudflare Workers API (Hono)
│   └── catalog-meta/      #   Domain metadata definitions
│
├── catalog/               # Domain 2: Data Catalog platform
│   ├── backend/           #   Workers API (schema, glossary, lineage)
│   ├── frontend/          #   Cloudflare Pages (React + Vite)
│   └── ontology/          #   JSON-LD T-Box/A-Box definitions
│
└── shared/                # Shared infrastructure
    ├── auth/              #   Authentication (future multi-tenant)
    ├── config/            #   Cloudflare config (wrangler.toml)
    └── types/             #   Shared TypeScript types
```

### Tech Stack

- **TypeScript packages**: pnpm workspace + Turborepo
- **Python packages**: uv workspace
- **Frontend**: React + Vite + TailwindCSS + Shadcn/ui, deployed to Cloudflare Pages
- **API**: Hono framework on Cloudflare Workers
- **ETL**: Python scripts, optionally orchestrated by Airflow on local machine
- **Upload**: Wrangler CLI for R2/D1 data loading

### Cloudflare Services

| Service | Purpose |
|---------|---------|
| R2 | Raw JSON archive storage (~100MB/year) |
| D1 | Processed events + metadata + catalog (SQLite, ~30K rows/year) |
| KV | Cache layer (search results, popular catalog entries) |
| Pages | Frontend hosting |
| Workers | API endpoints + Cron Triggers |

### Data Flow

```
GitHub Archive (gharchive.org)
  → Python ETL (filter by org/repo, normalize)
  → Wrangler CLI upload
  → R2 (raw JSON) + D1 (processed tables)
  → Workers API (Hono)
  → React frontend (catalog UI)
```

### D1 Core Tables

- `events` — raw GitHub events (type, actor, repo, org, payload)
- `daily_stats` — daily aggregates by org/repo/event_type
- `catalog_datasets` — dataset metadata with JSON-LD schema, glossary, lineage
- `catalog_columns` — column-level metadata with descriptions and PII flags

## Project Status

This project is in the initial planning phase. See `history/001_init.md` for the full project plan including phased development tracks, team composition suggestions, and detailed schema designs.

## Key Design Decisions

- **Free tier first**: All Cloudflare services sized for free tier limits
- **Data Mesh**: Each domain owns its data products with clear boundaries
- **JSON-LD ontology**: Lightweight semantic schema (T-Box for concepts, A-Box for instances)
- **Future expansion**: Designed to add Discord, LinkedIn, and other data sources as new domains
- **Multi-tenant ready**: Architecture supports future public multi-tenant access
