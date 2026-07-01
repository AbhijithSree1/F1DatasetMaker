import pandas as pd
import pytest
import requests

from f1dataset.config import OpenF1Settings
from f1dataset.ingestion.openf1_client import OpenF1Client


@pytest.fixture
def settings() -> OpenF1Settings:
    return OpenF1Settings(
        base_url="https://api.openf1.org/v1",
        min_season=2023,
        request_timeout=5,
        max_retries=3,
        retry_backoff_seconds=0,
    )


@pytest.fixture
def client(settings: OpenF1Settings) -> OpenF1Client:
    return OpenF1Client(settings)


def test_get_laps_returns_dataframe(client, requests_mock):
    requests_mock.get(
        "https://api.openf1.org/v1/laps",
        json=[{"session_key": 9158, "driver_number": 1, "lap_number": 1}],
    )

    df = client.get_laps(session_key=9158)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df.iloc[0]["driver_number"] == 1


def test_get_laps_omits_none_params(client, requests_mock):
    requests_mock.get("https://api.openf1.org/v1/laps", json=[])

    client.get_laps(session_key=9158, driver_number=None)

    query = requests_mock.last_request.qs
    assert "session_key" in query
    assert "driver_number" not in query


def test_empty_response_returns_empty_dataframe(client, requests_mock):
    requests_mock.get("https://api.openf1.org/v1/weather", json=[])

    df = client.get_weather(session_key=9158)

    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_retries_on_server_error_then_succeeds(client, requests_mock):
    requests_mock.get(
        "https://api.openf1.org/v1/stints",
        [
            {"status_code": 500, "json": []},
            {"status_code": 200, "json": [{"stint_number": 1}]},
        ],
    )

    df = client.get_stints(session_key=9158)

    assert len(df) == 1
    assert requests_mock.call_count == 2


def test_gives_up_after_max_retries(client, requests_mock):
    requests_mock.get("https://api.openf1.org/v1/pit", status_code=503, json=[])

    with pytest.raises(requests.exceptions.RequestException):
        client.get_pit(session_key=9158)

    assert requests_mock.call_count == client._settings.max_retries
