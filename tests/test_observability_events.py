from datetime import datetime
from pathlib import Path
import sys

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from bot.observability.events import (
    ObservabilityEvent,
    elapsed_ms,
    should_record_notfound,
)
from bot.observability.queries import calculate_percentiles, get_range_spec


def test_elapsed_uses_monotonic_nanoseconds_and_percentiles_are_stable():
    assert elapsed_ms(10_000_000, 13_999_999) == 3
    assert elapsed_ms(20, 10) == 0
    assert calculate_percentiles([10, 20, 30, 40, 50]) == {
        "p50": 30,
        "p95": 48,
        "p99": 50,
    }
    assert calculate_percentiles([]) == {"p50": None, "p95": None, "p99": None}


def test_event_validation_and_storage_mapping_exclude_message_text():
    event = ObservabilityEvent(
        command="voice_actor",
        status="file_missing",
        user_id=4_012_345_678,
        group_id=9_012_345_678,
        voice_actor_id=1,
        image_id=2,
        duration_ms=15,
        error_code="IMAGE_FILE_MISSING",
        created_at=datetime(2026, 8, 25, 10, 0),
    )
    record = event.to_record()
    assert record["response_time_ms"] == 15
    assert record["error_message"] is None
    assert "duration_ms" not in record

    with pytest.raises(ValueError):
        ObservabilityEvent(command="voice_actor", status="unknown", user_id=1)
    with pytest.raises(ValueError):
        ObservabilityEvent(
            command="voice_actor", status="error", user_id=1, error_code="raw message"
        )


def test_unmatched_ordinary_group_message_is_not_recordable():
    assert should_record_notfound(False) is False
    assert should_record_notfound(True) is True


def test_only_supported_metric_ranges_are_accepted():
    assert get_range_spec("24h").bucket_count == 24
    assert get_range_spec("7d").bucket_count == 7
    assert get_range_spec("30d").bucket_count == 30
    with pytest.raises(ValueError):
        get_range_spec("90d")
