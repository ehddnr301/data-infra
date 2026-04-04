"""table_registry 단위 테스트."""

from pseudolab_etl.table_registry import (
    ALL_TABLES,
    INCREMENTAL_TABLES,
    SNAPSHOT_TABLES,
)


class TestTableCounts:
    def test_total(self):
        assert len(ALL_TABLES) == 79

    def test_snapshot(self):
        assert len(SNAPSHOT_TABLES) == 44

    def test_incremental(self):
        assert len(INCREMENTAL_TABLES) == 35

    def test_no_overlap(self):
        s = set(SNAPSHOT_TABLES.keys())
        i = set(INCREMENTAL_TABLES.keys())
        assert s.isdisjoint(i)

    def test_union(self):
        assert set(ALL_TABLES.keys()) == set(SNAPSHOT_TABLES.keys()) | set(INCREMENTAL_TABLES.keys())


class TestSpecialCases:
    def test_page_views_timestamp(self):
        t = ALL_TABLES["page_views"]
        assert t.timestamp_column == "viewed_at"
        assert t.mode == "incremental"

    def test_user_which_projects_no_timestamp(self):
        t = ALL_TABLES["user_which_projects"]
        assert t.timestamp_column is None
        assert t.mode == "snapshot"

    def test_user_badges_claimed_at(self):
        t = ALL_TABLES["user_badges"]
        assert t.timestamp_column == "claimed_at"
        assert t.mode == "incremental"

    def test_follows_incremental(self):
        assert ALL_TABLES["follows"].mode == "incremental"
        assert ALL_TABLES["user_follows"].mode == "incremental"

    def test_notifications_incremental(self):
        assert ALL_TABLES["notifications"].mode == "incremental"

    def test_legacy_members_incremental(self):
        assert ALL_TABLES["legacy_members"].mode == "incremental"


class TestDlName:
    def test_prefix(self):
        assert ALL_TABLES["profiles"].dl_name == "dl_profiles"
        assert ALL_TABLES["page_views"].dl_name == "dl_page_views"


class TestPiiAssignment:
    def test_profiles_pii(self):
        t = ALL_TABLES["profiles"]
        assert "email" in t.pii_columns
        assert "name" in t.pii_columns
        assert "name_en" in t.pii_columns
        assert "name_kr" in t.pii_columns

    def test_no_pii_table(self):
        t = ALL_TABLES["badges"]
        assert len(t.pii_columns) == 0

    def test_table_excluded_reserved(self):
        assert "table" not in ALL_TABLES
