"""Seed script to populate the database with sample data."""

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import (
    Base,
    NotificationPreference,
    ProviderType,
    QuestionnaireResponse,
    RegionalAvailability,
    Title,
    TitleType,
    User,
    WatchHistory,
    WatchlistEntry,
)
from app.db.session import async_session_factory, engine


SAMPLE_USERS = [
    {
        "email": "alice@example.com",
        "password": "password123",
        "display_name": "Alice Johnson",
        "region": "US",
        "language": "en",
        "is_admin": True,
    },
    {
        "email": "bob@example.com",
        "password": "password123",
        "display_name": "Bob Smith",
        "region": "GB",
        "language": "en",
    },
    {
        "email": "carol@example.com",
        "password": "password123",
        "display_name": "Carol Chen",
        "region": "US",
        "language": "en",
    },
]

SAMPLE_TITLES = [
    {
        "tmdb_id": 550,
        "title_type": TitleType.MOVIE,
        "name": "Fight Club",
        "overview": "An insomniac office worker and a devil-may-care soap maker form an underground fight club.",
        "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
        "release_date": "1999-10-15",
        "vote_average": 8.4,
        "vote_count": 26000,
        "popularity": 73.5,
        "runtime": 139,
        "genres": [{"id": 18, "name": "Drama"}, {"id": 53, "name": "Thriller"}],
        "original_language": "en",
        "status": "Released",
    },
    {
        "tmdb_id": 680,
        "title_type": TitleType.MOVIE,
        "name": "Pulp Fiction",
        "overview": "The lives of two mob hitmen, a boxer, a gangster and his wife intertwine in four tales of violence and redemption.",
        "poster_path": "/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg",
        "release_date": "1994-09-10",
        "vote_average": 8.5,
        "vote_count": 25000,
        "popularity": 68.2,
        "runtime": 154,
        "genres": [{"id": 53, "name": "Thriller"}, {"id": 80, "name": "Crime"}],
        "original_language": "en",
        "status": "Released",
    },
    {
        "tmdb_id": 238,
        "title_type": TitleType.MOVIE,
        "name": "The Godfather",
        "overview": "Spanning the years 1945 to 1955, a chronicle of the fictional Italian-American Corleone crime family.",
        "poster_path": "/3bhkrj58Vtu7enYsRolD1fZdja1.jpg",
        "release_date": "1972-03-14",
        "vote_average": 8.7,
        "vote_count": 18000,
        "popularity": 95.3,
        "runtime": 175,
        "genres": [{"id": 18, "name": "Drama"}, {"id": 80, "name": "Crime"}],
        "original_language": "en",
        "status": "Released",
    },
    {
        "tmdb_id": 1396,
        "title_type": TitleType.TV,
        "name": "Breaking Bad",
        "overview": "A high school chemistry teacher diagnosed with inoperable lung cancer turns to manufacturing and selling methamphetamine.",
        "poster_path": "/ggFHVNu6YYI5L9pCfOacjizRGt.jpg",
        "release_date": "2008-01-20",
        "vote_average": 8.9,
        "vote_count": 12000,
        "popularity": 120.0,
        "runtime": 45,
        "genres": [{"id": 18, "name": "Drama"}, {"id": 80, "name": "Crime"}],
        "original_language": "en",
        "status": "Ended",
    },
    {
        "tmdb_id": 1399,
        "title_type": TitleType.TV,
        "name": "Game of Thrones",
        "overview": "Seven noble families fight for control of the mythical land of Westeros.",
        "poster_path": "/u3bZgnGQ9T01sWNhyveQz0wH0Hl.jpg",
        "release_date": "2011-04-17",
        "vote_average": 8.4,
        "vote_count": 20000,
        "popularity": 200.0,
        "runtime": 60,
        "genres": [{"id": 10765, "name": "Sci-Fi & Fantasy"}, {"id": 18, "name": "Drama"}, {"id": 10759, "name": "Action & Adventure"}],
        "original_language": "en",
        "status": "Ended",
    },
]


async def seed_database() -> None:
    """Create sample data in the database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        # Check if already seeded
        existing = await db.execute(select(User).limit(1))
        if existing.scalar_one_or_none() is not None:
            print("Database already seeded. Skipping.")
            return

        # Create users
        users: list[User] = []
        for u_data in SAMPLE_USERS:
            user = User(
                email=u_data["email"],
                hashed_password=hash_password(u_data["password"]),
                display_name=u_data["display_name"],
                region=u_data.get("region", "US"),
                language=u_data.get("language", "en"),
                is_admin=u_data.get("is_admin", False),
            )
            db.add(user)
            users.append(user)

        await db.flush()
        print(f"Created {len(users)} users")

        # Create titles
        titles: list[Title] = []
        for t_data in SAMPLE_TITLES:
            title = Title(**t_data)
            db.add(title)
            titles.append(title)

        await db.flush()
        print(f"Created {len(titles)} titles")

        # Add some availability
        providers = [
            ("Netflix", ProviderType.FLATRATE, "/t2yyOv40HZeVlLjYsCsPHnWLk4W.jpg"),
            ("Amazon Prime Video", ProviderType.FLATRATE, "/emthp39XA2YScoYL1p0sdbAH2WA.jpg"),
            ("Apple TV", ProviderType.RENT, "/peURlLlr8jggOwK53fJ5wdQl05y.jpg"),
        ]
        for title in titles:
            for pname, ptype, logo in providers:
                ra = RegionalAvailability(
                    title_id=title.id,
                    region="US",
                    provider_name=pname,
                    provider_type=ptype,
                    provider_logo_path=logo,
                    link=f"https://www.themoviedb.org/movie/{title.tmdb_id}/watch",
                )
                db.add(ra)

        # Questionnaire for Alice
        qr = QuestionnaireResponse(
            user_id=users[0].id,
            genre_preferences={"Drama": 5, "Thriller": 4, "Comedy": 3, "Sci-Fi": 4},
            mood_preferences={"relaxed": 3, "excited": 4, "thoughtful": 5},
            pacing_preference="moderate",
            tone_preference="dark",
            intensity_preference="high",
            runtime_preference="long",
            rewatch_tolerance="sometimes",
            preferred_providers=["Netflix", "Amazon Prime Video"],
            completed_at=datetime.now(timezone.utc),
        )
        db.add(qr)

        # Watch history for Alice
        for title in titles[:3]:
            wh = WatchHistory(
                user_id=users[0].id,
                title_id=title.id,
                rating=8.5,
                would_rewatch=True,
                mood_feedback="engaged",
            )
            db.add(wh)

        # Watchlist for Bob
        for title in titles[2:]:
            wl = WatchlistEntry(
                user_id=users[1].id,
                title_id=title.id,
                priority=3,
                notes="Recommended by a friend",
            )
            db.add(wl)

        # Notification preferences
        for user in users:
            np = NotificationPreference(user_id=user.id)
            db.add(np)

        await db.commit()
        print("Seed data committed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_database())
