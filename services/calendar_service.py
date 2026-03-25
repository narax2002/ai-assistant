from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from config import Settings

READONLY_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
SCOPES = [READONLY_SCOPE]


class CalendarSetupError(RuntimeError):
    """Raised when Google Calendar is not configured correctly."""


class CalendarRequestError(RuntimeError):
    """Raised when Google Calendar cannot return events."""


class CalendarService:
    def __init__(
        self,
        credentials_path: str,
        token_path: str,
        calendar_id: str = "primary",
    ) -> None:
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.calendar_id = calendar_id

    @classmethod
    def from_settings(cls, settings: Settings) -> "CalendarService":
        return cls(
            credentials_path=settings.google_calendar_credentials_path,
            token_path=settings.google_calendar_token_path,
            calendar_id=settings.google_calendar_id,
        )

    def format_upcoming_events(self, max_results: int = 5) -> str:
        events = self.get_upcoming_events(max_results=max_results)
        return self._format_event_list(
            events,
            empty_message="다가오는 일정이 없습니다.",
        )

    def format_today_events(self, max_results: int = 10) -> str:
        events = self.get_today_events(max_results=max_results)
        return self._format_event_list(
            events,
            empty_message="오늘 일정이 없습니다.",
        )

    def get_upcoming_events(self, max_results: int = 5) -> list[dict[str, Any]]:
        return self._list_events(
            time_min=datetime.now(timezone.utc),
            time_max=None,
            max_results=max_results,
        )

    def get_today_events(self, max_results: int = 10) -> list[dict[str, Any]]:
        local_now = datetime.now().astimezone()
        start_of_day = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        return self._list_events(
            time_min=start_of_day.astimezone(timezone.utc),
            time_max=end_of_day.astimezone(timezone.utc),
            max_results=max_results,
        )

    def _list_events(
        self,
        time_min: datetime,
        time_max: datetime | None,
        max_results: int,
    ) -> list[dict[str, Any]]:
        service = self._build_service()
        params: dict[str, Any] = {
            "calendarId": self.calendar_id,
            "timeMin": time_min.astimezone(timezone.utc).isoformat(),
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if time_max is not None:
            params["timeMax"] = time_max.astimezone(timezone.utc).isoformat()

        try:
            result = service.events().list(**params).execute()
        except Exception as exc:
            raise CalendarRequestError("Google Calendar 일정을 불러오지 못했습니다.") from exc

        items = result.get("items", [])
        return [item for item in items if isinstance(item, dict)]

    def _build_service(self) -> Any:
        _, _, _, build = _load_google_calendar_dependencies()
        credentials = self._get_credentials()
        try:
            return build("calendar", "v3", credentials=credentials)
        except Exception as exc:
            raise CalendarRequestError(
                "Google Calendar 클라이언트를 초기화하지 못했습니다."
            ) from exc

    def _get_credentials(self) -> Any:
        Request, Credentials, InstalledAppFlow, _ = _load_google_calendar_dependencies()
        credentials = None

        if self.token_path.exists():
            try:
                credentials = Credentials.from_authorized_user_file(
                    str(self.token_path),
                    SCOPES,
                )
            except Exception as exc:
                raise CalendarSetupError(
                    f"Google Calendar token file을 읽지 못했습니다: {self.token_path}"
                ) from exc

        if credentials and credentials.valid:
            return credentials

        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except Exception as exc:
                raise CalendarSetupError("Google Calendar token 갱신에 실패했습니다.") from exc
        else:
            if not self.credentials_path.exists():
                raise CalendarSetupError(
                    "Google Calendar 인증 파일이 없습니다. "
                    f"{self.credentials_path} 에 OAuth client JSON을 두세요."
                )

            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path),
                    SCOPES,
                )
                credentials = flow.run_local_server(port=0)
            except Exception as exc:
                raise CalendarSetupError("Google Calendar 인증을 완료하지 못했습니다.") from exc

        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.token_path.write_text(credentials.to_json(), encoding="utf-8")
        except OSError as exc:
            raise CalendarSetupError(
                f"Google Calendar token file을 저장하지 못했습니다: {self.token_path}"
            ) from exc

        return credentials

    def _format_event_list(
        self,
        events: list[dict[str, Any]],
        *,
        empty_message: str,
    ) -> str:
        if not events:
            return empty_message
        return "\n".join(self._format_event(event) for event in events)

    def _format_event(self, event: dict[str, Any]) -> str:
        summary = event.get("summary") or "제목 없음"
        start_text = self._format_start(event.get("start", {}))
        location = event.get("location")
        if location:
            return f"- {start_text} | {summary} @ {location}"
        return f"- {start_text} | {summary}"

    def _format_start(self, start: dict[str, Any]) -> str:
        date_time = start.get("dateTime")
        if date_time:
            try:
                parsed = datetime.fromisoformat(date_time.replace("Z", "+00:00"))
            except ValueError:
                return str(date_time)
            return parsed.astimezone().strftime("%Y-%m-%d %H:%M")

        date = start.get("date")
        if date:
            return f"{date} (종일)"
        return "시간 미정"


def _load_google_calendar_dependencies() -> tuple[Any, Any, Any, Any]:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise CalendarSetupError(
            "Google Calendar 의존성이 없습니다. "
            "`pip install -r requirements.txt`를 다시 실행하세요."
        ) from exc

    return Request, Credentials, InstalledAppFlow, build
