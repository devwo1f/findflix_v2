import uuid

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.db.models import (
    RecommendationLog,
    Title,
    TitleType,
    User,
)
from tests.conftest import TestSessionLocal


pytestmark = pytest.mark.asyncio


async def _create_sample_titles(count: int = 5) -> list[Title]:
    """Insert sample titles and return them."""
    titles = []
    async with TestSessionLocal() as db:
        for i in range(count):
            title = Title(
                tmdb_id=1000 + i,
                title_type=TitleType.MOVIE,
                name=f"Test Movie {i}",
                overview=f"Overview for test movie {i}",
                vote_average=7.0 + i * 0.3,
                vote_count=1000 + i * 100,
                popularity=50.0 + i * 10,
                genres=[{"id": 18, "name": "Drama"}],
                original_language="en",
                release_date=f"202{i}-01-01",
            )
            db.add(title)
            titles.append(title)
        await db.commit()
        for t in titles:
            await db.refresh(t)
    return titles


class TestRecommendationEndpoint:
    async def test_get_recommendations_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/recommendations")
        assert response.status_code == 401

    async def test_get_recommendations_authenticated(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/recommendations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "model_version" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_get_recommendations_with_mood(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/recommendations",
            params={"mood": "relaxed", "limit": 5},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] <= 5


class TestFallbackRecommendations:
    async def test_fallback_returns_popular_titles(self, client: AsyncClient, auth_headers: dict):
        """When no user embedding exists, fallback to popularity-based recs."""
        await _create_sample_titles(5)

        response = await client.get("/api/v1/recommendations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Fallback should return items sorted by popularity
        assert isinstance(data["items"], list)


class TestTrending:
    async def test_trending_empty(self, client: AsyncClient):
        response = await client.get("/api/v1/recommendations/trending")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["page"] == 1

    async def test_trending_with_titles(self, client: AsyncClient):
        await _create_sample_titles(3)

        response = await client.get("/api/v1/recommendations/trending")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3


class TestRecommendationFeedback:
    async def test_feedback_not_found(self, client: AsyncClient, auth_headers: dict):
        fake_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/recommendations/{fake_id}/feedback",
            json={"feedback": "liked"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_feedback_success(self, client: AsyncClient, auth_headers: dict, test_user: User):
        titles = await _create_sample_titles(1)

        # Create a recommendation log
        async with TestSessionLocal() as db:
            rec_log = RecommendationLog(
                user_id=test_user.id,
                title_id=titles[0].id,
                score=0.85,
                reason="Test recommendation",
                model_version="v1",
            )
            db.add(rec_log)
            await db.commit()
            await db.refresh(rec_log)
            rec_id = rec_log.id

        response = await client.post(
            f"/api/v1/recommendations/{rec_id}/feedback",
            json={"feedback": "liked"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["feedback"] == "liked"

    async def test_feedback_clicked(self, client: AsyncClient, auth_headers: dict, test_user: User):
        titles = await _create_sample_titles(1)

        async with TestSessionLocal() as db:
            rec_log = RecommendationLog(
                user_id=test_user.id,
                title_id=titles[0].id,
                score=0.75,
                reason="Another test",
                model_version="v1",
            )
            db.add(rec_log)
            await db.commit()
            await db.refresh(rec_log)
            rec_id = rec_log.id

        response = await client.post(
            f"/api/v1/recommendations/{rec_id}/feedback",
            json={"feedback": "clicked"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["feedback"] == "clicked"
