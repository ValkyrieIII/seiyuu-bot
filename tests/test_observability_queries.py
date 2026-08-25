from datetime import datetime, timedelta
from pathlib import Path
import sys

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from bot.observability.queries import query_metrics


Base = declarative_base()


class Actor(Base):
    __tablename__ = "test_actors"
    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False)


class Log(Base):
    __tablename__ = "test_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    group_id = Column(Integer)
    command = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False)
    voice_actor_id = Column(Integer, ForeignKey("test_actors.id"))
    response_time_ms = Column(Integer)
    error_code = Column(String(64))
    created_at = Column(DateTime, nullable=False)


def test_time_range_aggregation_statuses_and_top_actor():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    now = datetime(2026, 8, 25, 12, 30)
    session = sessions()
    session.add(Actor(id=1, name="测试声优"))
    session.add_all([
        Log(id=1, user_id=1, group_id=10, command="voice_actor", status="success", voice_actor_id=1, response_time_ms=100, created_at=now - timedelta(hours=1)),
        Log(id=2, user_id=2, group_id=10, command="voice_actor", status="error", voice_actor_id=1, response_time_ms=300, error_code="TEST_ERROR", created_at=now - timedelta(hours=2)),
        Log(id=3, user_id=3, group_id=11, command="check_in", status="success", response_time_ms=200, created_at=now - timedelta(days=2)),
    ])
    session.commit()
    session.close()

    metrics_24h = query_metrics("24h", now, sessions, (Log, Actor))
    assert metrics_24h["total_requests"] == 2
    assert metrics_24h["success_rate"] == 50.0
    assert metrics_24h["active_users"] == 2
    assert metrics_24h["active_groups"] == 1
    assert metrics_24h["duration_ms"] == {"p50": 200, "p95": 290, "p99": 298}
    assert metrics_24h["status_distribution"]["file_missing"] == 0
    assert len(metrics_24h["time_series"]) == 24
    assert metrics_24h["top_voice_actors"][0]["requests"] == 2
    assert metrics_24h["recent_error_codes"][0]["error_code"] == "TEST_ERROR"

    metrics_7d = query_metrics("7d", now, sessions, (Log, Actor))
    assert metrics_7d["total_requests"] == 3
    assert len(metrics_7d["time_series"]) == 7
