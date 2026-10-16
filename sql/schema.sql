-- Schema for SQL scenarios 1 and 2 (SQLite 3.25+; window functions required)

-- ---------------------------------------------------------------------------
-- Scenario 1: account transfers
-- Money is stored in integer cents so the "within 10%" boundary is exact
-- (floating-point 0.10 * amount can land a hair above or below the limit).
-- Times are ISO-8601 UTC text ('YYYY-MM-DD HH:MM:SS'), which sorts correctly.
-- ---------------------------------------------------------------------------
CREATE TABLE transactions (
    txn_id        INTEGER PRIMARY KEY,
    from_account  TEXT    NOT NULL,
    to_account    TEXT    NOT NULL,
    amount_cents  INTEGER NOT NULL CHECK (amount_cents > 0),
    txn_time      TEXT    NOT NULL,
    CHECK (from_account <> to_account)
);
CREATE INDEX idx_transactions_pair_time ON transactions (from_account, to_account, txn_time);

-- ---------------------------------------------------------------------------
-- Scenario 2: IPL-style batting data
-- ---------------------------------------------------------------------------
CREATE TABLE players (
    player_id    INTEGER PRIMARY KEY,
    player_name  TEXT NOT NULL,
    team         TEXT NOT NULL
);

CREATE TABLE matches (
    match_id     INTEGER PRIMARY KEY,
    season       INTEGER NOT NULL,
    match_date   TEXT    NOT NULL,      -- 'YYYY-MM-DD'
    team1        TEXT    NOT NULL,
    team2        TEXT    NOT NULL
);

-- One row per player per match in which the player batted.
CREATE TABLE batting_scores (
    match_id     INTEGER NOT NULL REFERENCES matches (match_id),
    player_id    INTEGER NOT NULL REFERENCES players (player_id),
    runs         INTEGER NOT NULL CHECK (runs >= 0),
    PRIMARY KEY (match_id, player_id)
);
