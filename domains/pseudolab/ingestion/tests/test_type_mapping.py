"""type_mapping 단위 테스트."""

from datetime import datetime, timezone
from uuid import UUID

from pseudolab_etl.type_mapping import convert_value, pg_to_d1_type


class TestPgToD1Type:
    def test_boolean(self):
        assert pg_to_d1_type("boolean") == "INTEGER"

    def test_integer(self):
        assert pg_to_d1_type("integer") == "INTEGER"

    def test_bigint(self):
        assert pg_to_d1_type("bigint") == "INTEGER"

    def test_uuid(self):
        assert pg_to_d1_type("uuid") == "TEXT"

    def test_text(self):
        assert pg_to_d1_type("text") == "TEXT"

    def test_jsonb(self):
        assert pg_to_d1_type("jsonb") == "TEXT"

    def test_timestamp(self):
        assert pg_to_d1_type("timestamp with time zone") == "TEXT"

    def test_array(self):
        assert pg_to_d1_type("ARRAY") == "TEXT"


class TestConvertValue:
    def test_none(self):
        assert convert_value(None, "text") is None

    def test_boolean_true(self):
        assert convert_value(True, "boolean") == 1

    def test_boolean_false(self):
        assert convert_value(False, "boolean") == 0

    def test_integer(self):
        assert convert_value(42, "integer") == 42

    def test_jsonb_dict(self):
        result = convert_value({"key": "value"}, "jsonb")
        assert result == '{"key": "value"}'

    def test_jsonb_string(self):
        assert convert_value('{"a": 1}', "jsonb") == '{"a": 1}'

    def test_array_list(self):
        result = convert_value(["a", "b"], "ARRAY")
        assert result == '["a", "b"]'

    def test_uuid(self):
        u = UUID("12345678-1234-5678-1234-567812345678")
        assert convert_value(u, "uuid") == "12345678-1234-5678-1234-567812345678"

    def test_timestamp(self):
        dt = datetime(2026, 4, 3, 15, 0, 0, tzinfo=timezone.utc)
        result = convert_value(dt, "timestamp with time zone")
        assert "2026-04-03" in result
