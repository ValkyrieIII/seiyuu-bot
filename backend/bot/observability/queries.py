"""Bounded-range aggregate queries for the admin metrics endpoint."""

from dataclasses import dataclass
from datetime import datetime, timedelta
import math
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import case, func

from .events import VALID_STATUSES


@dataclass(frozen=True)
class RangeSpec:
    key: str
    bucket: str
    bucket_count: int


RANGE_SPECS = {
    "24h": RangeSpec("24h", "hour", 24),
    "7d": RangeSpec("7d", "day", 7),
    "30d": RangeSpec("30d", "day", 30),
}


def get_range_spec(range_key: str) -> RangeSpec:
    try:
        return RANGE_SPECS[range_key]
    except KeyError as exc:
        raise ValueError("range must be one of: 24h, 7d, 30d") from exc


def calculate_percentiles(
    values: Iterable[int], percentiles: Sequence[float] = (0.5, 0.95, 0.99)
) -> Dict[str, Optional[int]]:
    """Calculate linearly interpolated percentiles without a heavy dependency."""
    ordered = sorted(int(value) for value in values if value is not None)
    result: Dict[str, Optional[int]] = {}
    for percentile in percentiles:
        key = f"p{int(percentile * 100)}"
        if not ordered:
            result[key] = None
            continue
        position = (len(ordered) - 1) * percentile
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            value = ordered[lower]
        else:
            weight = position - lower
            value = ordered[lower] + (ordered[upper] - ordered[lower]) * weight
        result[key] = int(round(value))
    return result


def _range_bounds(spec: RangeSpec, now: datetime) -> tuple[datetime, List[datetime]]:
    if spec.bucket == "hour":
        end = now.replace(minute=0, second=0, microsecond=0)
        buckets = [end - timedelta(hours=offset) for offset in reversed(range(24))]
    else:
        end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        buckets = [
            end - timedelta(days=offset)
            for offset in reversed(range(spec.bucket_count))
        ]
    return buckets[0], buckets


def _bucket_expression(session, column, spec: RangeSpec):
    dialect = session.get_bind().dialect.name
    if dialect == "sqlite":
        fmt = "%Y-%m-%dT%H:00:00" if spec.bucket == "hour" else "%Y-%m-%dT00:00:00"
        return func.strftime(fmt, column)
    fmt = "%Y-%m-%dT%H:00:00" if spec.bucket == "hour" else "%Y-%m-%dT00:00:00"
    return func.date_format(column, fmt)


def query_metrics(
    range_key: str,
    now: Optional[datetime] = None,
    session_factory: Optional[Callable] = None,
    models: Optional[Tuple[Any, Any]] = None,
) -> Dict[str, Any]:
    if session_factory is None or models is None:
        from bot.plugins.voice_actor.models import RequestLog, VoiceActor, get_session

        session_factory = get_session
        models = (RequestLog, VoiceActor)
    RequestLog, VoiceActor = models

    spec = get_range_spec(range_key)
    current = now or datetime.utcnow()
    since, expected_buckets = _range_bounds(spec, current)
    session = session_factory()
    try:
        base = session.query(RequestLog).filter(RequestLog.created_at >= since)
        total = base.count()
        success = base.filter(RequestLog.status == "success").count()
        success_rate = round((success / total) * 100, 2) if total else 0.0
        active_users = (
            session.query(func.count(func.distinct(RequestLog.user_id)))
            .filter(RequestLog.created_at >= since)
            .scalar()
            or 0
        )
        active_groups = (
            session.query(func.count(func.distinct(RequestLog.group_id)))
            .filter(RequestLog.created_at >= since, RequestLog.group_id.isnot(None))
            .scalar()
            or 0
        )

        duration_values = [
            row[0]
            for row in (
                session.query(RequestLog.response_time_ms)
                .filter(
                    RequestLog.created_at >= since,
                    RequestLog.response_time_ms.isnot(None),
                )
                .all()
            )
        ]

        status_counts = {status: 0 for status in sorted(VALID_STATUSES)}
        for status, count in (
            session.query(RequestLog.status, func.count(RequestLog.id))
            .filter(RequestLog.created_at >= since)
            .group_by(RequestLog.status)
            .all()
        ):
            status_counts[str(status)] = int(count)

        bucket = _bucket_expression(session, RequestLog.created_at, spec)
        rows = (
            session.query(
                bucket.label("bucket"),
                func.count(RequestLog.id),
                func.sum(case((RequestLog.status == "success", 1), else_=0)),
            )
            .filter(RequestLog.created_at >= since)
            .group_by(bucket)
            .order_by(bucket)
            .all()
        )
        row_map = {
            str(bucket_value): {"total": int(count), "success": int(ok_count or 0)}
            for bucket_value, count, ok_count in rows
        }
        time_series = []
        for expected in expected_buckets:
            key = expected.strftime("%Y-%m-%dT%H:00:00" if spec.bucket == "hour" else "%Y-%m-%dT00:00:00")
            counts = row_map.get(key, {"total": 0, "success": 0})
            time_series.append({"bucket": key, **counts})

        top_voice_actors = [
            {"id": actor_id, "name": name, "requests": int(count)}
            for actor_id, name, count in (
                session.query(
                    VoiceActor.id, VoiceActor.name, func.count(RequestLog.id)
                )
                .join(RequestLog, RequestLog.voice_actor_id == VoiceActor.id)
                .filter(RequestLog.created_at >= since)
                .group_by(VoiceActor.id, VoiceActor.name)
                .order_by(func.count(RequestLog.id).desc(), VoiceActor.id.asc())
                .limit(10)
                .all()
            )
        ]

        recent_error_codes = [
            {"error_code": code, "count": int(count), "last_seen_at": last_seen.isoformat()}
            for code, count, last_seen in (
                session.query(
                    RequestLog.error_code,
                    func.count(RequestLog.id),
                    func.max(RequestLog.created_at),
                )
                .filter(
                    RequestLog.created_at >= since,
                    RequestLog.error_code.isnot(None),
                )
                .group_by(RequestLog.error_code)
                .order_by(func.max(RequestLog.created_at).desc())
                .limit(10)
                .all()
            )
        ]

        return {
            "range": spec.key,
            "from": since.isoformat(),
            "to": current.isoformat(),
            "total_requests": int(total),
            "success_rate": success_rate,
            "duration_ms": calculate_percentiles(duration_values),
            "active_users": int(active_users),
            "active_groups": int(active_groups),
            "status_distribution": status_counts,
            "time_series": time_series,
            "top_voice_actors": top_voice_actors,
            "recent_error_codes": recent_error_codes,
        }
    finally:
        session.close()
