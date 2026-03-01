CREATE UNIQUE INDEX IF NOT EXISTS idx_glossary_terms_domain_term
  ON glossary_terms(domain, term);

CREATE INDEX IF NOT EXISTS idx_glossary_terms_domain_updated_at
  ON glossary_terms(domain, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_glossary_terms_term
  ON glossary_terms(term);
