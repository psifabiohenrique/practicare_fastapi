from datetime import date, timedelta
from http import HTTPStatus

import pytest

pytestmark = pytest.mark.asyncio


async def test_get_dashboard_statistics_default(session_client):
    client, user = session_client
    response = client.get("/dashboard/statistics")

    assert response.status_code == HTTPStatus.OK
    data = response.json()

    assert "total_input_tokens" in data
    assert "total_output_tokens" in data
    assert "total_transcriptions" in data
    assert "active_treatments_count" in data
    assert "start_date" in data
    assert "end_date" in data

    today = date.today().isoformat()
    thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()

    assert data["end_date"] == today
    assert data["start_date"] == thirty_days_ago


async def test_get_dashboard_statistics_with_dates(session_client):
    client, user = session_client
    start_date = "2024-01-01"
    end_date = "2024-01-31"

    response = client.get(
        f"/dashboard/statistics?start_date={start_date}&end_date={end_date}"
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()

    assert data["start_date"] == start_date
    assert data["end_date"] == end_date
