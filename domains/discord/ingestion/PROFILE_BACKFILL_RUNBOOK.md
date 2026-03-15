# Discord Profile Backfill Runbook

## Start detached worker

```bash
nohup uv run --project domains/discord/ingestion python domains/discord/ingestion/profile_backfill_worker.py \
  --config domains/discord/ingestion/config.backfill-053.yaml \
  --success-interval-sec 60 \
  --default-429-wait-sec 1200 \
  --error-wait-sec 1800 \
  > domains/discord/ingestion/data/profile_backfill_worker.log 2>&1 &
```

## Check worker process

```bash
ps -ef | grep profile_backfill_worker.py | grep -v grep
```

## Check logs

```bash
tail -f domains/discord/ingestion/data/profile_backfill_worker.log
```

## Check remaining targets

```bash
npx --yes wrangler d1 execute pseudolab-main --remote --config domains/catalog/storage/wrangler.toml --command "SELECT COUNT(DISTINCT m.author_id) AS missing_targets FROM discord_messages m LEFT JOIN discord_user_profiles p ON p.user_id = m.author_id WHERE m.author_id != '' AND p.user_id IS NULL;"
```

## Stop worker

```bash
pkill -f profile_backfill_worker.py
```
