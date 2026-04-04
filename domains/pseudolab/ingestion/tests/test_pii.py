"""PII 해싱 단위 테스트."""

from pseudolab_etl.pii import PII_COLUMNS, apply_pii_hashing, hash_pii


class TestHashPii:
    def test_none_returns_none(self):
        assert hash_pii(None, "salt") is None

    def test_deterministic(self):
        h1 = hash_pii("test@example.com", "salt123")
        h2 = hash_pii("test@example.com", "salt123")
        assert h1 == h2

    def test_different_salt(self):
        h1 = hash_pii("test@example.com", "salt1")
        h2 = hash_pii("test@example.com", "salt2")
        assert h1 != h2

    def test_strip_lower(self):
        h1 = hash_pii("Test@Example.com", "salt")
        h2 = hash_pii("  test@example.com  ", "salt")
        assert h1 == h2

    def test_returns_hex_string(self):
        result = hash_pii("hello", "salt")
        assert result is not None
        assert len(result) == 64  # SHA-256 hex


class TestApplyPiiHashing:
    def test_no_pii_table(self):
        rows = [{"id": "1", "title": "test"}]
        result = apply_pii_hashing(rows, "badges", "salt")
        assert result[0]["title"] == "test"

    def test_pii_table(self):
        rows = [{"id": "1", "email": "user@test.com", "name": "John"}]
        apply_pii_hashing(rows, "event_committee", "salt")
        assert rows[0]["email"] != "user@test.com"
        assert rows[0]["name"] != "John"
        assert len(rows[0]["email"]) == 64

    def test_null_pii_preserved(self):
        rows = [{"id": "1", "email": None, "name": "John"}]
        apply_pii_hashing(rows, "event_committee", "salt")
        assert rows[0]["email"] is None
        assert rows[0]["name"] != "John"


class TestPiiColumns:
    def test_24_tables(self):
        assert len(PII_COLUMNS) == 24

    def test_profiles_columns(self):
        assert PII_COLUMNS["profiles"] == frozenset({"email", "name", "name_en", "name_kr"})
