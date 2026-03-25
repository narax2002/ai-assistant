from pathlib import Path

import pytest

from services.calendar_service import CalendarService, CalendarSetupError


def test_format_event_for_all_day_event_with_location() -> None:
    service = CalendarService("data/credentials.json", "data/token.json")

    formatted = service._format_event(
        {
            "summary": "팀 회의",
            "start": {"date": "2026-03-25"},
            "location": "회의실 A",
        }
    )

    assert formatted == "- 2026-03-25 (종일) | 팀 회의 @ 회의실 A"


def test_format_event_uses_fallbacks_for_missing_fields() -> None:
    service = CalendarService("data/credentials.json", "data/token.json")

    formatted = service._format_event({"start": {}})

    assert formatted == "- 시간 미정 | 제목 없음"


def test_format_event_list_returns_empty_message_for_no_events() -> None:
    service = CalendarService("data/credentials.json", "data/token.json")

    formatted = service._format_event_list([], empty_message="일정 없음")

    assert formatted == "일정 없음"


def test_get_credentials_requires_oauth_client_file(tmp_path: Path) -> None:
    service = CalendarService(
        credentials_path=str(tmp_path / "missing-credentials.json"),
        token_path=str(tmp_path / "token.json"),
    )

    with pytest.raises(CalendarSetupError, match="Google Calendar 인증 파일이 없습니다"):
        service._get_credentials()
