-- Scenario 2: IPL 2024 player performance streaks
-- Players who scored 30+ runs in at least 3 consecutive matches, with the date
-- the streak started.
--
-- Rules (agreed edge cases):
--   * 30+ means runs >= 30 (exactly 30 counts)
--   * "consecutive" = consecutive matches the PLAYER batted in during the 2024
--     season; a team match the player missed does not break the streak
--   * matches from other seasons never join a 2024 streak
--   * a player with two separate streaks gets two rows
--
-- Technique: gaps-and-islands. Number every innings of a player (rn_all), then
-- number only the 30+ innings with a second ROW_NUMBER(). Within a run of
-- consecutive 30+ scores both counters rise together, so their difference
-- (streak_key) is constant for the whole streak and changes after every break.

WITH innings AS (
    SELECT
        p.player_id,
        p.player_name,
        m.match_id,
        m.match_date,
        b.runs,
        ROW_NUMBER() OVER (PARTITION BY p.player_id ORDER BY m.match_date, m.match_id) AS rn_all
    FROM batting_scores AS b
    JOIN matches AS m ON m.match_id  = b.match_id
    JOIN players AS p ON p.player_id = b.player_id
    WHERE m.season = 2024
),
scores_30_plus AS (
    SELECT
        *,
        rn_all - ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY match_date, match_id) AS streak_key
    FROM innings
    WHERE runs >= 30
)
SELECT
    player_name,
    MIN(match_date) AS streak_start_date,
    MAX(match_date) AS streak_end_date,
    COUNT(*)        AS matches_in_streak
FROM scores_30_plus
GROUP BY player_id, player_name, streak_key
HAVING COUNT(*) >= 3
ORDER BY player_name, streak_start_date;
