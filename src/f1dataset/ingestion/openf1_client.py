"""Thin client for the OpenF1 REST API (https://openf1.org).

OpenF1 exposes real-time and historical F1 data (from the 2023 season onward)
as flat JSON collections: sessions, laps, car telemetry, car/driver position,
pit stops, tire stints, weather, race control messages, and team radio.

Every method returns a pandas DataFrame (empty DataFrame if the endpoint has
no rows for the given filters), so callers don't need to think about JSON.
"""

from __future__ import annotations

import logging

import pandas as pd
import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from f1dataset.config import OpenF1Settings

logger = logging.getLogger(__name__)


class OpenF1Client:
    def __init__(self, settings: OpenF1Settings, session: requests.Session | None = None):
        self._settings = settings
        self._session = session or requests.Session()

    def _get(self, endpoint: str, **params) -> pd.DataFrame:
        clean_params = {k: v for k, v in params.items() if v is not None}
        payload = self._get_with_retry(endpoint, clean_params)
        return pd.DataFrame(payload)

    def _get_with_retry(self, endpoint: str, params: dict) -> list[dict]:
        @retry(
            stop=stop_after_attempt(self._settings.max_retries),
            wait=wait_exponential(multiplier=self._settings.retry_backoff_seconds, max=60),
            retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout, _RetryableStatus)),
            reraise=True,
        )
        def _do_request() -> list[dict]:
            url = f"{self._settings.base_url}/{endpoint}"
            resp = self._session.get(url, params=params, timeout=self._settings.request_timeout)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise _RetryableStatus(f"{resp.status_code} from {url}")
            resp.raise_for_status()
            return resp.json()

        return _do_request()

    # -- Reference data -----------------------------------------------------

    def get_meetings(self, year: int | None = None, meeting_key: int | None = None) -> pd.DataFrame:
        return self._get("meetings", year=year, meeting_key=meeting_key)

    def get_sessions(
        self,
        year: int | None = None,
        meeting_key: int | None = None,
        session_key: int | None = None,
    ) -> pd.DataFrame:
        return self._get(
            "sessions", year=year, meeting_key=meeting_key, session_key=session_key
        )

    def get_drivers(self, session_key: int | None = None, meeting_key: int | None = None) -> pd.DataFrame:
        return self._get("drivers", session_key=session_key, meeting_key=meeting_key)

    # -- Timing / telemetry ---------------------------------------------------

    def get_laps(self, session_key: int, driver_number: int | None = None) -> pd.DataFrame:
        return self._get("laps", session_key=session_key, driver_number=driver_number)

    def get_car_data(self, session_key: int, driver_number: int | None = None) -> pd.DataFrame:
        return self._get("car_data", session_key=session_key, driver_number=driver_number)

    def get_position(self, session_key: int, driver_number: int | None = None) -> pd.DataFrame:
        return self._get("position", session_key=session_key, driver_number=driver_number)

    def get_location(self, session_key: int, driver_number: int | None = None) -> pd.DataFrame:
        return self._get("location", session_key=session_key, driver_number=driver_number)

    def get_intervals(self, session_key: int, driver_number: int | None = None) -> pd.DataFrame:
        return self._get("intervals", session_key=session_key, driver_number=driver_number)

    # -- Strategy / stints ---------------------------------------------------

    def get_pit(self, session_key: int, driver_number: int | None = None) -> pd.DataFrame:
        return self._get("pit", session_key=session_key, driver_number=driver_number)

    def get_stints(self, session_key: int, driver_number: int | None = None) -> pd.DataFrame:
        return self._get("stints", session_key=session_key, driver_number=driver_number)

    # -- Context ---------------------------------------------------------------

    def get_weather(self, session_key: int) -> pd.DataFrame:
        return self._get("weather", session_key=session_key)

    def get_race_control(self, session_key: int) -> pd.DataFrame:
        return self._get("race_control", session_key=session_key)

    def get_team_radio(self, session_key: int, driver_number: int | None = None) -> pd.DataFrame:
        return self._get("team_radio", session_key=session_key, driver_number=driver_number)


class _RetryableStatus(requests.exceptions.RequestException):
    """Raised internally to trigger a retry on 429/5xx responses."""
