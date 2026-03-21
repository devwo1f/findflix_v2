# FindFlix

A premium movie and TV recommendation platform that reduces decision fatigue. Built with Flutter, FastAPI, and TensorFlow Recommenders.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Flutter App (iOS/Android/Web)             │
│  Riverpod · GoRouter · Firebase Auth · Dark Cinematic UI    │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────────┐
│                    FastAPI Backend (:8000)                   │
│  Auth · Questionnaire · Titles · Recommendations · Admin    │
│  Celery Workers · TMDb Sync · Provider Abstraction          │
└────────┬──────────────┬──────────────────┬──────────────────┘
         │              │                  │
    ┌────▼────┐   ┌─────▼─────┐   ┌───────▼───────┐
    │PostgreSQL│   │   Redis   │   │  ML Service   │
    │  :5432   │   │   :6379   │   │    :8001      │
    │          │   │ Cache/    │   │ Two-Tower     │
    │ Users    │   │ Sessions/ │   │ Retrieval +   │
    │ Titles   │   │ Celery    │   │ Transformer   │
    │ History  │   │ Broker    │   │ Reranker      │
    └──────────┘   └───────────┘   └───────────────┘
```

### Recommendation Pipeline

```
User Request
    │
    ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Stage 1:        │     │  Stage 2:        │     │  Post-process:   │
│  Two-Tower       │────▶│  Transformer     │────▶│  Diversity +     │
│  Retrieval       │     │  Reranker        │     │  Explain +       │
│  (Top 100)       │     │  (Top 20)        │     │  Filter          │
└──────────────────┘     └──────────────────┘     └──────────────────┘
    │                                                     │
    │  User Tower:                                        ▼
    │  - Questionnaire                              Final 5-10
    │  - Watch history                              recommendations
    │  - Mood, pacing, tone                         with reasons
    │  - Implicit signals
    │
    │  Item Tower:
    │  - TMDb metadata
    │  - Genres, cast, plot
    │  - Availability
    │  - Popularity
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Flutter (iOS, Android, Web) |
| State Management | Riverpod |
| Navigation | GoRouter |
| Backend API | FastAPI (Python 3.11) |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Auth | Firebase Authentication + JWT |
| ML Retrieval | TensorFlow Recommenders (Two-Tower) |
| ML Ranking | Transformer Reranker |
| Background Jobs | Celery + Redis |
| Metadata Source | TMDb API |
| Containerization | Docker + Docker Compose |

## Project Structure

```
findflix_v2/
├── app/                          # Flutter application
│   ├── lib/
│   │   ├── main.dart
│   │   ├── core/
│   │   │   ├── theme/            # Dark cinematic theme
│   │   │   ├── router/           # GoRouter config
│   │   │   ├── constants/        # API endpoints
│   │   │   └── network/          # Dio API client
│   │   ├── models/               # Data models
│   │   ├── providers/            # Riverpod providers
│   │   ├── screens/              # All app screens
│   │   │   ├── splash_screen.dart
│   │   │   ├── auth/
│   │   │   ├── onboarding/
│   │   │   ├── home/
│   │   │   ├── recommendations/
│   │   │   ├── titles/
│   │   │   ├── search/
│   │   │   ├── watchlist/
│   │   │   ├── profile/
│   │   │   ├── settings/
│   │   │   └── admin/
│   │   └── widgets/              # Reusable components
│   └── pubspec.yaml
│
├── backend/                      # FastAPI backend
│   ├── app/
│   │   ├── main.py
│   │   ├── core/                 # Config, security, deps
│   │   ├── db/                   # Models, session, seeds
│   │   ├── schemas/              # Pydantic schemas
│   │   ├── api/                  # Route handlers
│   │   ├── services/             # Business logic
│   │   └── tasks/                # Celery background tasks
│   ├── alembic/                  # DB migrations
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
│
├── ml_service/                   # ML recommendation service
│   ├── models/                   # TF model definitions
│   │   ├── two_tower.py          # Two-tower retrieval
│   │   ├── reranker.py           # Transformer reranker
│   │   └── fallback.py           # Popularity fallback
│   ├── features/                 # Feature engineering
│   ├── pipeline/                 # Retrieval + ranking
│   ├── training/                 # Training scripts
│   ├── app.py                    # ML FastAPI service
│   ├── Dockerfile
│   └── requirements.txt
│
├── scripts/
│   └── init_db.sql               # Database schema + seed data
│
├── docker-compose.yml            # Production compose
├── docker-compose.dev.yml        # Dev overrides
├── .env.example                  # Environment template
└── README.md
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Flutter SDK (3.x)
- Python 3.11+
- A TMDb API key ([get one free](https://www.themoviedb.org/settings/api))

### 1. Clone and Configure

```bash
git clone <repo-url> findflix_v2
cd findflix_v2
cp .env.example .env
# Edit .env and add your TMDB_API_KEY and JWT_SECRET_KEY
```

### 2. Start Infrastructure

```bash
# Start all services (Postgres, Redis, Backend, ML Service, Celery)
docker compose up -d

# For development with hot-reload:
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### 3. Run the Flutter App

```bash
cd app
flutter pub get
flutter run -d chrome     # Web
flutter run -d ios        # iOS simulator
flutter run -d android    # Android emulator
```

### 4. Verify Services

```bash
# Backend health check
curl http://localhost:8000/health

# ML service health check
curl http://localhost:8001/health

# API docs (Swagger UI)
open http://localhost:8000/docs
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/signup` | Create account |
| POST | `/api/v1/auth/login` | Login |
| POST | `/api/v1/auth/refresh` | Refresh token |
| POST | `/api/v1/auth/password-reset` | Request password reset |
| POST | `/api/v1/auth/firebase` | Exchange Firebase token |
| GET | `/api/v1/auth/me` | Current user |

### Questionnaire
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/questionnaire` | Submit questionnaire |
| GET | `/api/v1/questionnaire` | Get current answers |
| PUT | `/api/v1/questionnaire` | Update answers |

### Titles
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/titles/search` | Search titles |
| GET | `/api/v1/titles/{id}` | Title detail |
| GET | `/api/v1/titles/{id}/availability` | Regional availability |
| GET | `/api/v1/titles/{id}/similar` | Similar titles |

### Recommendations
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/recommendations` | Get recommendations |
| POST | `/api/v1/recommendations/{id}/feedback` | Submit feedback |
| GET | `/api/v1/recommendations/trending` | Trending titles |

### User
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/users/profile` | Get profile |
| PUT | `/api/v1/users/profile` | Update profile |
| GET | `/api/v1/users/dashboard` | Dashboard stats |
| POST | `/api/v1/users/watch-history` | Log watch |
| GET | `/api/v1/users/watch-history` | Watch history |
| POST | `/api/v1/users/watchlist` | Add to watchlist |
| GET | `/api/v1/users/watchlist` | Get watchlist |
| DELETE | `/api/v1/users/watchlist/{id}` | Remove from watchlist |
| POST | `/api/v1/users/feedback` | Submit feedback |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/stats` | System statistics |
| GET | `/api/v1/admin/users` | List all users |
| GET | `/api/v1/admin/recommendations/logs` | Rec logs |
| GET | `/api/v1/admin/model/info` | ML model info |
| POST | `/api/v1/admin/sync/tmdb` | Trigger TMDb sync |

## Database Schema

The schema includes 12 tables:

- **users** — Accounts with region/language preferences
- **questionnaire_responses** — Taste profile from onboarding
- **taste_embeddings** — ML-generated user embeddings
- **titles** — Movie/TV metadata from TMDb
- **regional_availability** — Where each title streams by region
- **watch_history** — What users watched, with ratings and rewatch intent
- **watchlist_entries** — Saved-for-later titles
- **recommendation_logs** — Every recommendation shown with feedback
- **search_history** — Search queries for implicit signals
- **feedback_events** — Skip, hide, not-interested, rate signals
- **device_sessions** — Multi-device support
- **notification_preferences** — Per-user notification settings

## ML Models

### Two-Tower Retrieval
- User tower: questionnaire features + watch history + implicit signals -> 128-dim embedding
- Item tower: TMDb metadata + genres + cast + availability -> 128-dim embedding
- Training: in-batch negatives with factorized top-K retrieval
- Serves top-100 candidates per request

### Transformer Reranker
- 2-layer, 4-head self-attention over user's interaction sequence
- Cross-attention between user history and candidate features
- Outputs relevance scores with diversity penalty (MMR)
- Novelty bonus for underexplored genres

### Fallback Recommender
- Popularity-based for cold start
- Editorial curated picks
- Content-based filtering using questionnaire cosine similarity

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `REDIS_URL` | Yes | - | Redis connection string |
| `TMDB_API_KEY` | Yes | - | TMDb API key |
| `JWT_SECRET_KEY` | Yes | - | JWT signing secret |
| `FIREBASE_PROJECT_ID` | Yes | - | Firebase project ID |
| `ML_SERVICE_URL` | No | `http://localhost:8001` | ML service URL |
| `ENVIRONMENT` | No | `development` | App environment |
| `DEBUG` | No | `false` | Debug mode |
| `EMBEDDING_DIM` | No | `128` | Embedding dimension |
| `TOP_K` | No | `100` | Retrieval candidate count |
| `CELERY_BROKER_URL` | No | `redis://localhost:6379/1` | Celery broker |

## Testing

```bash
# Backend tests
cd backend && pytest -v

# ML service tests
cd ml_service && pytest -v

# Flutter tests
cd app && flutter test
```

## Deployment

### Local Development
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Staging
```bash
ENVIRONMENT=staging docker compose up -d
```

### Production
```bash
# Use production .env with real secrets
ENVIRONMENT=production docker compose up -d
```

## Roadmap

- [ ] Social authentication (Google, Apple Sign-In)
- [ ] Push notifications for new recommendations
- [ ] Collaborative filtering signals
- [ ] A/B testing framework for recommendation models
- [ ] Offline mode for Flutter app
- [ ] Watch party / social features
- [ ] Advanced analytics dashboard with charts
- [ ] Model retraining pipeline with Airflow
- [ ] Multi-language UI support (i18n)
- [ ] Rate limiting and API throttling
- [ ] CDN for poster image caching
- [ ] WebSocket for real-time recommendation updates
- [ ] Integration with more streaming providers (JustWatch API)
- [ ] User taste drift detection and auto-questionnaire refresh
