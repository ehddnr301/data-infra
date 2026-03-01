CREATE TABLE IF NOT EXISTS glossary_terms (
  id TEXT PRIMARY KEY,
  domain TEXT NOT NULL CHECK (domain IN ('github', 'discord', 'linkedin', 'members')),
  term TEXT NOT NULL,
  definition TEXT NOT NULL,
  related_terms TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(related_terms) AND json_type(related_terms) = 'array'),
  created_at TEXT NOT NULL CHECK (created_at GLOB '????-??-??T??:??:??*'),
  updated_at TEXT NOT NULL CHECK (updated_at GLOB '????-??-??T??:??:??*')
);
