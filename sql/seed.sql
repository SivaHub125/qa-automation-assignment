-- Seed data for SQL scenarios 1 and 2. Synthetic test data, not real match statistics.
-- ---------------------------------------------------------------------------
-- Scenario 1: transactions. Expected round trips are marked MATCH.
-- ---------------------------------------------------------------------------
INSERT INTO transactions (txn_id, from_account, to_account, amount_cents, txn_time) VALUES
    (1,  'ACC-A', 'ACC-B', 100000,  '2024-03-01 10:00:00'),  -- A -> B 1,000.00
    (2,  'ACC-B', 'ACC-A',  95000,  '2024-03-01 18:00:00'),  -- MATCH: back 8h later, 5% less
    (3,  'ACC-C', 'ACC-D', 500000,  '2024-03-02 09:00:00'),
    (4,  'ACC-D', 'ACC-C', 550000,  '2024-03-03 09:00:00'),  -- MATCH boundary: exactly +10%, exactly 24h
    (5,  'ACC-E', 'ACC-F', 200000,  '2024-03-04 12:00:00'),
    (6,  'ACC-F', 'ACC-E', 200000,  '2024-03-05 12:01:00'),  -- no: 24h 1m later
    (7,  'ACC-G', 'ACC-H', 300000,  '2024-03-06 08:00:00'),
    (8,  'ACC-H', 'ACC-G', 269000,  '2024-03-06 09:00:00'),  -- no: 10.33% less
    (9,  'ACC-I', 'ACC-J', 150000,  '2024-03-07 10:00:00'),
    (10, 'ACC-I', 'ACC-J', 150000,  '2024-03-07 11:00:00'),  -- no: same direction, not a return
    (11, 'ACC-M', 'ACC-N',  80000,  '2024-03-09 10:00:00'),
    (12, 'ACC-N', 'ACC-O',  80000,  '2024-03-09 10:30:00'),  -- no: sent on to a third account
    (13, 'ACC-P', 'ACC-Q', 1000000, '2024-03-10 10:00:00'),
    (14, 'ACC-Q', 'ACC-P',  910000, '2024-03-10 20:00:00'),  -- MATCH: 9% less, 10h
    (15, 'ACC-Q', 'ACC-P', 1000000, '2024-03-11 08:00:00'),  -- MATCH: second return for txn 13, 22h
    (16, 'ACC-R', 'ACC-S', 200000,  '2024-03-12 10:00:00'),
    (17, 'ACC-S', 'ACC-R', 180000,  '2024-03-12 12:00:00'),  -- MATCH boundary: exactly -10%
    (18, 'ACC-T', 'ACC-U', 100000,  '2024-03-13 10:00:00'),
    (19, 'ACC-U', 'ACC-T', 100000,  '2024-03-13 10:00:00'),  -- MATCH: same second, reported once (18 -> 19)
    -- Case 1: A -> B, A -> C, B -> A within 24h: only A <-> B is a round trip
    (20, 'ACC-V', 'ACC-W', 300000,  '2024-03-14 10:00:00'),
    (21, 'ACC-V', 'ACC-X', 300000,  '2024-03-14 11:00:00'),  -- no: X never sends back
    (22, 'ACC-W', 'ACC-V', 300000,  '2024-03-14 12:00:00'),  -- MATCH: returns txn 20
    -- Case 2: A -> B, B -> A, B -> A, A -> B within 24h: every qualifying pair is reported
    (23, 'ACC-Y', 'ACC-Z', 400000,  '2024-03-15 10:00:00'),
    (24, 'ACC-Z', 'ACC-Y', 400000,  '2024-03-15 11:00:00'),  -- MATCH: returns txn 23
    (25, 'ACC-Z', 'ACC-Y', 400000,  '2024-03-15 12:00:00'),  -- MATCH: also returns txn 23
    (26, 'ACC-Y', 'ACC-Z', 400000,  '2024-03-15 13:00:00'),  -- MATCH: returns txn 24 and txn 25
    -- Case 3: A -> B, B -> A, B -> A within 24h; A -> B 25.5h after the first
    (27, 'ACC-K', 'ACC-L', 600000,  '2024-03-16 10:00:00'),
    (28, 'ACC-L', 'ACC-K', 600000,  '2024-03-16 11:00:00'),  -- MATCH: returns txn 27
    (29, 'ACC-L', 'ACC-K', 600000,  '2024-03-16 12:00:00'),  -- MATCH: also returns txn 27
    (30, 'ACC-K', 'ACC-L', 600000,  '2024-03-17 11:30:00');  -- MATCH with txn 29 (23.5h); not with 28 (24.5h)

-- ---------------------------------------------------------------------------
-- Scenario 2: IPL-style 2024 season (plus two 2023 matches to test the season filter)
-- ---------------------------------------------------------------------------
INSERT INTO players (player_id, player_name, team) VALUES
    (1, 'Virat Kohli', 'RCB'),
    (2, 'Faf du Plessis', 'RCB'),
    (3, 'Shubman Gill', 'GT'),
    (4, 'Ruturaj Gaikwad', 'CSK'),
    (5, 'Travis Head', 'SRH'),
    (6, 'Sanju Samson', 'RR'),
    (7, 'Rishabh Pant', 'DC'),
    (8, 'KL Rahul', 'LSG'),
    (9, 'Rohit Sharma', 'MI');

INSERT INTO matches (match_id, season, match_date, team1, team2) VALUES
    (1, 2024, '2024-03-22', 'RCB', 'MI'),
    (2, 2024, '2024-03-23', 'GT', 'LSG'),
    (3, 2024, '2024-03-24', 'CSK', 'DC'),
    (4, 2024, '2024-03-25', 'SRH', 'RR'),
    (5, 2024, '2024-03-26', 'RCB', 'LSG'),
    (6, 2024, '2024-03-27', 'MI', 'DC'),
    (7, 2024, '2024-03-28', 'GT', 'RR'),
    (8, 2024, '2024-03-29', 'CSK', 'SRH'),
    (9, 2024, '2024-03-30', 'RCB', 'DC'),
    (10, 2024, '2024-03-31', 'LSG', 'RR'),
    (11, 2024, '2024-04-01', 'MI', 'SRH'),
    (12, 2024, '2024-04-02', 'GT', 'CSK'),
    (13, 2024, '2024-04-03', 'RCB', 'RR'),
    (14, 2024, '2024-04-04', 'DC', 'SRH'),
    (15, 2024, '2024-04-05', 'LSG', 'CSK'),
    (16, 2024, '2024-04-06', 'MI', 'GT'),
    (17, 2024, '2024-04-07', 'RCB', 'SRH'),
    (18, 2024, '2024-04-08', 'RR', 'CSK'),
    (19, 2024, '2024-04-09', 'DC', 'GT'),
    (20, 2024, '2024-04-10', 'LSG', 'MI'),
    (21, 2024, '2024-04-11', 'RCB', 'CSK'),
    (22, 2024, '2024-04-12', 'SRH', 'GT'),
    (23, 2024, '2024-04-13', 'RR', 'MI'),
    (24, 2024, '2024-04-14', 'DC', 'LSG'),
    (25, 2024, '2024-04-15', 'RCB', 'GT'),
    (26, 2024, '2024-04-16', 'CSK', 'MI'),
    (27, 2024, '2024-04-17', 'SRH', 'LSG'),
    (28, 2024, '2024-04-18', 'RR', 'DC'),
    (101, 2023, '2023-05-18', 'SRH', 'RCB'),
    (102, 2023, '2023-05-21', 'SRH', 'MI');

-- batting_scores grouped by player; runs listed in match order
INSERT INTO batting_scores (match_id, player_id, runs) VALUES
    -- Virat Kohli: streak of 3 starting with his first match (exactly 30 counts)
    (101, 1, 45),
    (1, 1, 45),
    (5, 1, 33),
    (9, 1, 30),
    (13, 1, 12),
    (17, 1, 50),
    (21, 1, 8),
    (25, 1, 19),
    -- Faf du Plessis: streak of 4
    (1, 2, 10),
    (5, 2, 20),
    (9, 2, 64),
    (13, 2, 70),
    (17, 2, 33),
    (21, 2, 41),
    (25, 2, 2),
    -- Shubman Gill: streak of 3 in the middle of the season
    (2, 3, 31),
    (7, 3, 10),
    (12, 3, 40),
    (16, 3, 35),
    (19, 3, 38),
    (22, 3, 5),
    (25, 3, 22),
    -- Ruturaj Gaikwad: never more than 2 in a row: no result
    (3, 4, 30),
    (8, 4, 30),
    (12, 4, 8),
    (15, 4, 30),
    (18, 4, 30),
    (21, 4, 2),
    (26, 4, 30),
    -- Travis Head: 3 in a row only across 2023 -> 2024: no result
    (101, 5, 50),
    (102, 5, 41),
    (4, 5, 40),
    (8, 5, 10),
    (11, 5, 33),
    (14, 5, 12),
    (17, 5, 9),
    (22, 5, 15),
    (27, 5, 28),
    -- Sanju Samson: two separate streaks: two results
    (4, 6, 35),
    (7, 6, 42),
    (10, 6, 31),
    (13, 6, 9),
    (18, 6, 55),
    (23, 6, 61),
    (28, 6, 47),
    -- Rishabh Pant: did not bat in DC's 2nd match; streak counts over matches he played
    (3, 7, 34),
    (9, 7, 39),
    (14, 7, 41),
    (19, 7, 3),
    (24, 7, 20),
    (28, 7, 11),
    -- KL Rahul: 29s break every run: no result
    (2, 8, 29),
    (5, 8, 30),
    (10, 8, 29),
    (15, 8, 45),
    (20, 8, 30),
    (24, 8, 29),
    (27, 8, 60),
    -- Rohit Sharma: 30, 29 then 30, 31, 32: streak starts after the break
    (1, 9, 30),
    (6, 9, 29),
    (11, 9, 30),
    (16, 9, 31),
    (20, 9, 32),
    (23, 9, 0),
    (26, 9, 77);
