"""Validated event model shared by bot commands and the metrics writer."""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
import re
import time
from typing import Any, Dict, Optional


class EventStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    COOLDOWN = "cooldown"
    NOTFOUND = "notfound"
    NO_IMAGE = "no_image"
    FILE_MISSING = "file_missing"


VALID_STATUSES = frozenset(status.value for status in EventStatus)
_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_ERROR_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


def elapsed_ms(start_ns: int, end_ns: Optional[int] = None) -> int:
    """Return monotonic elapsed milliseconds, rounded down and never negative."""
    if end_ns is None:
        end_ns = time.perf_counter_ns()
    return max(0, (end_ns - start_ns) // 1_000_000)


def should_record_notfound(is_explicit_mention: bool) -> bool:
    """Only an explicit mention authorizes recording an unmatched query."""
    return is_explicit_mention


@dataclass(frozen=True)
class ObservabilityEvent:
    command: str
    status: str
    user_id: int
    group_id: Optional[int] = None
    voice_actor_id: Optional[int] = None
    image_id: Optional[int] = None
    duration_ms: Optional[int] = None
    error_code: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not _IDENTIFIER_RE.fullmatch(self.command):
            raise ValueError("command must be a stable snake_case identifier")
        if self.status not in VALID_STATUSES:
            raise ValueError(f"unsupported status: {self.status}")
        if not isinstance(self.user_id, int) or isinstance(self.user_id, bool) or self.user_id <= 0:
            raise ValueError("user_id must be a positive integer")
        for field_name in ("group_id", "voice_actor_id", "image_id"):
            value = getattr(self, field_name)
            if value is not None and (
                not isinstance(value, int) or isinstance(value, bool) or value <= 0
            ):
                raise ValueError(f"{field_name} must be a positive integer or None")
        if self.duration_ms is not None and (
            not isinstance(self.duration_ms, int)
            or isinstance(self.duration_ms, bool)
            or self.duration_ms < 0
        ):
            raise ValueError("duration_ms must be a non-negative integer or None")
        if self.error_code is not None and not _ERROR_CODE_RE.fullmatch(self.error_code):
            raise ValueError("error_code must be a stable upper snake case identifier")
        if not isinstance(self.created_at, datetime):
            raise ValueError("created_at must be a datetime")

    def to_record(self) -> Dict[str, Any]:
        """Map the event to request_logs columns without carrying user message text."""
        record = asdict(self)
        record["response_time_ms"] = record.pop("duration_ms")
        record["error_message"] = None
        return record
