-- FindFlix Database Initialization
-- This runs automatically when the PostgreSQL container starts for the first time.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ── Enums ────────────────────────────────────────────────────

CREATE TYPE title_type AS ENUM ('movie', 'tv');
CREATE TYPE provider_type AS ENUM ('flatrate', 'rent', 'buy', 'free');
CREATE TYPE feedback_type AS ENUM ('skip', 'hide', 'not_interested', 'rate', 'mood_signal');

-- ── Users ────────────────────────────────────────────────────

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    display_name    VARCHAR(100),
    avatar_url      TEXT,
    region          VARCHAR(10) DEFAULT 'US',
    language        VARCHAR(10) DEFAULT 'en',
    is_active       BOOLEAN DEFAULT TRUE,
    is_admin        BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);

-- ── Questionnaire Responses ─────────────────────────────────

CREATE TABLE questionnaire_responses (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id              UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    genre_preferences    JSONB DEFAULT '[]',
    mood_preferences     JSONB DEFAULT '[]',
    pacing_preference    FLOAT DEFAULT 0.5,    -- 0 = slow burn, 1 = fast paced
    tone_preference      FLOAT DEFAULT 0.5,    -- 0 = serious, 1 = fun
    intensity_preference FLOAT DEFAULT 0.5,    -- 0 = light, 1 = intense
    runtime_preference   VARCHAR(20) DEFAULT 'no_preference',
    rewatch_tolerance    VARCHAR(20) DEFAULT 'sometimes',
    preferred_providers  JSONB DEFAULT '[]',
    completed_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- ── Taste Embeddings ─────────────────────────────────────────

CREATE TABLE taste_embeddings (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    embedding_vector FLOAT[] NOT NULL,
    model_version    VARCHAR(50) DEFAULT 'v1.0',
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- ── Titles ───────────────────────────────────────────────────

CREATE TABLE titles (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tmdb_id           INTEGER UNIQUE NOT NULL,
    title_type        title_type NOT NULL,
    name              VARCHAR(500) NOT NULL,
    original_name     VARCHAR(500),
    overview          TEXT,
    poster_path       VARCHAR(255),
    backdrop_path     VARCHAR(255),
    release_date      DATE,
    vote_average      FLOAT DEFAULT 0,
    vote_count        INTEGER DEFAULT 0,
    popularity        FLOAT DEFAULT 0,
    runtime           INTEGER,
    genres            JSONB DEFAULT '[]',
    cast_members      JSONB DEFAULT '[]',
    keywords          JSONB DEFAULT '[]',
    original_language VARCHAR(10),
    status            VARCHAR(50),
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_titles_tmdb_id ON titles(tmdb_id);
CREATE INDEX idx_titles_type ON titles(title_type);
CREATE INDEX idx_titles_name_trgm ON titles USING gin(name gin_trgm_ops);
CREATE INDEX idx_titles_genres ON titles USING gin(genres);
CREATE INDEX idx_titles_popularity ON titles(popularity DESC);

-- ── Regional Availability ────────────────────────────────────

CREATE TABLE regional_availability (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title_id          UUID NOT NULL REFERENCES titles(id) ON DELETE CASCADE,
    region            VARCHAR(10) NOT NULL,
    provider_name     VARCHAR(100) NOT NULL,
    provider_type     provider_type NOT NULL,
    provider_logo_path VARCHAR(255),
    link              TEXT,
    updated_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_availability_title ON regional_availability(title_id);
CREATE INDEX idx_availability_region ON regional_availability(region);
CREATE INDEX idx_availability_title_region ON regional_availability(title_id, region);

-- ── Watch History ────────────────────────────────────────────

CREATE TABLE watch_history (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id               UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title_id              UUID NOT NULL REFERENCES titles(id) ON DELETE CASCADE,
    watched_at            TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    rating                FLOAT,
    would_rewatch         BOOLEAN,
    mood_feedback         VARCHAR(50),
    completion_percentage FLOAT DEFAULT 100.0,
    UNIQUE(user_id, title_id, watched_at)
);

CREATE INDEX idx_watch_history_user ON watch_history(user_id);
CREATE INDEX idx_watch_history_user_title ON watch_history(user_id, title_id);

-- ── Watchlist ────────────────────────────────────────────────

CREATE TABLE watchlist_entries (
    id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title_id  UUID NOT NULL REFERENCES titles(id) ON DELETE CASCADE,
    added_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    priority  INTEGER DEFAULT 0,
    notes     TEXT,
    UNIQUE(user_id, title_id)
);

CREATE INDEX idx_watchlist_user ON watchlist_entries(user_id);

-- ── Recommendation Logs ──────────────────────────────────────

CREATE TABLE recommendation_logs (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title_id      UUID NOT NULL REFERENCES titles(id) ON DELETE CASCADE,
    score         FLOAT NOT NULL,
    reason        TEXT,
    model_version VARCHAR(50),
    shown_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    clicked       BOOLEAN DEFAULT FALSE,
    feedback      VARCHAR(50)
);

CREATE INDEX idx_rec_logs_user ON recommendation_logs(user_id);
CREATE INDEX idx_rec_logs_shown ON recommendation_logs(shown_at DESC);

-- ── Search History ───────────────────────────────────────────

CREATE TABLE search_history (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query       TEXT NOT NULL,
    filters     JSONB DEFAULT '{}',
    searched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_search_history_user ON search_history(user_id);

-- ── Feedback Events ──────────────────────────────────────────

CREATE TABLE feedback_events (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title_id   UUID NOT NULL REFERENCES titles(id) ON DELETE CASCADE,
    event_type feedback_type NOT NULL,
    value      JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_feedback_user ON feedback_events(user_id);
CREATE INDEX idx_feedback_title ON feedback_events(title_id);

-- ── Device Sessions ──────────────────────────────────────────

CREATE TABLE device_sessions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_type VARCHAR(50),
    device_name VARCHAR(100),
    last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fcm_token   VARCHAR(255)
);

CREATE INDEX idx_device_sessions_user ON device_sessions(user_id);

-- ── Notification Preferences ─────────────────────────────────

CREATE TABLE notification_preferences (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id               UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    new_recommendations   BOOLEAN DEFAULT TRUE,
    watchlist_available   BOOLEAN DEFAULT TRUE,
    weekly_digest         BOOLEAN DEFAULT FALSE,
    UNIQUE(user_id)
);

-- ── Seed Data: Sample Titles ─────────────────────────────────

INSERT INTO titles (tmdb_id, title_type, name, original_name, overview, poster_path, backdrop_path, release_date, vote_average, vote_count, popularity, runtime, genres, cast_members, original_language, status)
VALUES
(550, 'movie', 'Fight Club', 'Fight Club',
 'A ticking-Loss of insomnia forces an average insomniac to create an underground fight club.',
 '/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg', '/hZkgoQYus5dXo3H8T7Uef6DNknx.jpg',
 '1999-10-15', 8.4, 26000, 61.4, 139,
 '[{"id": 18, "name": "Drama"}, {"id": 53, "name": "Thriller"}]',
 '[{"name": "Brad Pitt", "character": "Tyler Durden"}, {"name": "Edward Norton", "character": "The Narrator"}]',
 'en', 'Released'),

(680, 'movie', 'Pulp Fiction', 'Pulp Fiction',
 'The lives of two mob hitmen, a boxer, a gangster and his wife intertwine in four tales of violence and redemption.',
 '/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg', '/suaEOtk1N1sgg2MTM7oZd2cfVp3.jpg',
 '1994-09-10', 8.5, 25000, 65.2, 154,
 '[{"id": 53, "name": "Thriller"}, {"id": 80, "name": "Crime"}]',
 '[{"name": "John Travolta", "character": "Vincent Vega"}, {"name": "Samuel L. Jackson", "character": "Jules Winnfield"}]',
 'en', 'Released'),

(27205, 'movie', 'Inception', 'Inception',
 'A skilled thief is offered a chance to have his criminal record erased if he can successfully perform inception.',
 '/edv5CZvWj09upOsy2Y6IwDhK8bt.jpg', '/s3TBrRGB1iav7gFOCNx3H31MoES.jpg',
 '2010-07-16', 8.4, 34000, 88.1, 148,
 '[{"id": 28, "name": "Action"}, {"id": 878, "name": "Science Fiction"}, {"id": 12, "name": "Adventure"}]',
 '[{"name": "Leonardo DiCaprio", "character": "Dom Cobb"}, {"name": "Joseph Gordon-Levitt", "character": "Arthur"}]',
 'en', 'Released'),

(1396, 'tv', 'Breaking Bad', 'Breaking Bad',
 'A chemistry teacher diagnosed with lung cancer teams up with a former student to manufacture crystal meth.',
 '/ggFHVNu6YYI5L9pCfOacjizRGt.jpg', '/tsRy63Mu5cu8etL1X7ZLyf7UP1M.jpg',
 '2008-01-20', 8.9, 12000, 95.3, 45,
 '[{"id": 18, "name": "Drama"}, {"id": 80, "name": "Crime"}]',
 '[{"name": "Bryan Cranston", "character": "Walter White"}, {"name": "Aaron Paul", "character": "Jesse Pinkman"}]',
 'en', 'Ended'),

(66732, 'tv', 'Stranger Things', 'Stranger Things',
 'When a young boy vanishes, a small town uncovers a mystery involving secret experiments and supernatural forces.',
 '/49WJfeN0moxb9IPfGn8AIqMGskD.jpg', '/56v2KjBlYj3Ris2WLbUnUDJleYv.jpg',
 '2016-07-15', 8.6, 15000, 82.7, 50,
 '[{"id": 18, "name": "Drama"}, {"id": 9648, "name": "Mystery"}, {"id": 10765, "name": "Sci-Fi & Fantasy"}]',
 '[{"name": "Millie Bobby Brown", "character": "Eleven"}, {"name": "Finn Wolfhard", "character": "Mike Wheeler"}]',
 'en', 'Returning Series'),

(438631, 'movie', 'Dune', 'Dune',
 'Paul Atreides unites with the Fremen while on a warpath of revenge against those who destroyed his family.',
 '/d5NXSklXo0qyIYkgV94XAgMIckC.jpg', '/oBIQDKcqNxKckjugtmzpIIOgoc4.jpg',
 '2021-09-15', 7.8, 9500, 71.5, 155,
 '[{"id": 878, "name": "Science Fiction"}, {"id": 12, "name": "Adventure"}]',
 '[{"name": "Timothée Chalamet", "character": "Paul Atreides"}, {"name": "Zendaya", "character": "Chani"}]',
 'en', 'Released'),

(76341, 'movie', 'Mad Max: Fury Road', 'Mad Max: Fury Road',
 'An apocalyptic story set in the furthest reaches of our planet, in a stark desert landscape.',
 '/8tZYtuWezp8JbcsvHYO0O46tFBO.jpg', '/phszHPFVhPHhMZgo0fWTKBDQsJA.jpg',
 '2015-05-15', 7.6, 19000, 45.2, 120,
 '[{"id": 28, "name": "Action"}, {"id": 12, "name": "Adventure"}, {"id": 878, "name": "Science Fiction"}]',
 '[{"name": "Tom Hardy", "character": "Max Rockatansky"}, {"name": "Charlize Theron", "character": "Furiosa"}]',
 'en', 'Released'),

(85271, 'tv', 'WandaVision', 'WandaVision',
 'Wanda Maximoff and Vision—two super-powered beings living idealized suburban lives—suspect things are not as they seem.',
 '/glKDfE6btIRcVB7uHY8qzonIhMQ.jpg', '/57vVjteucIF3bGnZj6PmaoJRScw.jpg',
 '2021-01-15', 7.9, 11000, 55.1, 35,
 '[{"id": 10765, "name": "Sci-Fi & Fantasy"}, {"id": 9648, "name": "Mystery"}, {"id": 18, "name": "Drama"}]',
 '[{"name": "Elizabeth Olsen", "character": "Wanda Maximoff"}, {"name": "Paul Bettany", "character": "Vision"}]',
 'en', 'Ended');

-- ── Seed Data: Regional Availability ─────────────────────────

INSERT INTO regional_availability (title_id, region, provider_name, provider_type, provider_logo_path)
SELECT t.id, 'US', 'Netflix', 'flatrate', '/t2yyOv40HZeVlLjYsCsPHnWLk4W.jpg'
FROM titles t WHERE t.tmdb_id IN (550, 1396);

INSERT INTO regional_availability (title_id, region, provider_name, provider_type, provider_logo_path)
SELECT t.id, 'US', 'Amazon Prime Video', 'flatrate', '/emthp39XA2YScoYL1p0sdbAH2WA.jpg'
FROM titles t WHERE t.tmdb_id IN (680, 76341);

INSERT INTO regional_availability (title_id, region, provider_name, provider_type, provider_logo_path)
SELECT t.id, 'US', 'HBO Max', 'flatrate', '/Ajqyt5aNxNGjmF9uOfxArGrdf3X.jpg'
FROM titles t WHERE t.tmdb_id IN (27205, 438631);

INSERT INTO regional_availability (title_id, region, provider_name, provider_type, provider_logo_path)
SELECT t.id, 'US', 'Disney+', 'flatrate', '/7rwgEs15tFwyR9NPQ5vpzxTj19Q.jpg'
FROM titles t WHERE t.tmdb_id IN (66732, 85271);

-- ── Seed Data: Sample Admin User ─────────────────────────────
-- Password: admin123 (bcrypt hash)
INSERT INTO users (email, hashed_password, display_name, region, language, is_admin)
VALUES ('admin@findflix.app', '$2b$12$LJ3m4ys4Hz3YexJ/tOPN4.tFDMTkMGBSijb2KwBx8fRdbIJqJDPGu',
        'Admin', 'US', 'en', TRUE);
