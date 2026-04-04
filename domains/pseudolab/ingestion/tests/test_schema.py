"""schema DDL 생성 테스트."""

from pseudolab_etl.schema import generate_all_ddl, generate_create_index, generate_create_table
from pseudolab_etl.table_registry import ALL_TABLES


class TestGenerateCreateTable:
    def test_badges(self):
        t = ALL_TABLES["badges"]
        ddl = generate_create_table(t)
        assert "CREATE TABLE IF NOT EXISTS dl_badges" in ddl
        assert "id TEXT NOT NULL" in ddl
        assert "name TEXT NOT NULL" in ddl
        assert "points INTEGER" in ddl
        assert "base_date TEXT NOT NULL" in ddl
        assert "load_dt TEXT NOT NULL" in ddl

    def test_boolean_mapped_to_integer(self):
        t = ALL_TABLES["builder_onboarding"]
        ddl = generate_create_table(t)
        assert "linkedin_post INTEGER NOT NULL" in ddl

    def test_user_which_projects_all_nullable(self):
        t = ALL_TABLES["user_which_projects"]
        ddl = generate_create_table(t)
        assert "name TEXT," in ddl or "name TEXT\n" in ddl


class TestGenerateIndex:
    def test_index(self):
        t = ALL_TABLES["profiles"]
        idx = generate_create_index(t)
        assert "CREATE INDEX IF NOT EXISTS" in idx
        assert "dl_profiles" in idx
        assert "base_date" in idx


class TestGenerateAllDdl:
    def test_all_79_tables(self):
        ddl = generate_all_ddl()
        for table in ALL_TABLES.values():
            assert table.dl_name in ddl
