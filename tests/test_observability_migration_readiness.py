from pathlib import Path
import asyncio
import sys

from sqlalchemy import BigInteger, Integer, String


BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from bot.observability.migration import request_log_migration_plan
from bot.observability.system import check_database, check_onebot, readiness


def test_migration_plan_is_empty_after_target_schema_exists():
    old_columns = {"user_id": {"type": Integer()}, "group_id": {"type": Integer()}}
    assert len(request_log_migration_plan(old_columns, [])) == 5

    target_columns = {
        "user_id": {"type": BigInteger()},
        "group_id": {"type": BigInteger()},
        "error_code": {"type": String(64)},
    }
    target_indexes = [
        {"name": "idx_request_logs_created_status", "column_names": ["created_at", "status"]},
        {"name": "idx_request_logs_created_command", "column_names": ["created_at", "command"]},
    ]
    assert request_log_migration_plan(target_columns, target_indexes) == []


def test_readiness_degrades_independently_for_database_and_onebot():
    class FailedSession:
        def execute(self, _statement):
            raise RuntimeError("down")
        def close(self):
            pass

    database = check_database(lambda: FailedSession())
    onebot = check_onebot(lambda: {})
    assert database == {"ready": False, "error_code": "DATABASE_UNAVAILABLE"}
    assert onebot["ready"] is False
    assert onebot["error_code"] == "ONEBOT_DISCONNECTED"

    database_down = asyncio.run(readiness(
        database_check=lambda: {"ready": False, "error_code": "DATABASE_UNAVAILABLE"},
        onebot_check=lambda: {"ready": True, "error_code": None, "connected_bots": 1},
    ))
    onebot_down = asyncio.run(readiness(
        database_check=lambda: {"ready": True, "error_code": None},
        onebot_check=lambda: {"ready": False, "error_code": "ONEBOT_DISCONNECTED", "connected_bots": 0},
    ))
    assert database_down["ready"] is False
    assert database_down["onebot"]["ready"] is True
    assert onebot_down["ready"] is False
    assert onebot_down["database"]["ready"] is True
