CREATE TABLE IF NOT EXISTS discord_user_profiles (
    user_id TEXT PRIMARY KEY,
    username TEXT,
    global_name TEXT,
    avatar TEXT,
    banner TEXT,
    accent_color INTEGER,
    bio TEXT,
    pronouns TEXT,
    mutual_guild_count INTEGER NOT NULL DEFAULT 0,
    mutual_friend_count INTEGER NOT NULL DEFAULT 0,
    connected_account_count INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL CHECK (source IN ('users_profile_api')),
    source_endpoint TEXT NOT NULL,
    fetched_at TEXT NOT NULL CHECK (fetched_at GLOB '????-??-??T??:??:??*'),
    raw_payload TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_discord_user_profiles_fetched_at
    ON discord_user_profiles(fetched_at DESC);

CREATE INDEX IF NOT EXISTS idx_discord_user_profiles_global_name
    ON discord_user_profiles(global_name);
