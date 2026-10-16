"""Assert each SQL scenario returns exactly the rows the seed data was designed to produce."""

import pytest

from sql.sql_runner import connect, run

pytestmark = pytest.mark.sql


@pytest.fixture(scope="module")
def db():
    connection = connect()
    yield connection
    connection.close()


@pytest.fixture(scope="module")
def round_trips(db) -> list[dict]:
    """Scenario 1 result rows as {column: value}, queried once for all tests."""
    columns, rows = run(db, "scenario1_round_trip")
    return [dict(zip(columns, row)) for row in rows]


@pytest.fixture(scope="module")
def pairs(round_trips) -> list[tuple[int, int]]:
    return [(t["sent_txn_id"], t["return_txn_id"]) for t in round_trips]


def test_round_trips_match_exactly_the_designed_pairs(pairs):
    assert pairs == [
        (1, 2), (3, 4), (13, 14), (13, 15), (16, 17), (18, 19),
        (20, 22),                              # case 1
        (23, 24), (23, 25), (24, 26), (25, 26),  # case 2
        (27, 28), (27, 29), (29, 30),          # case 3
    ]


@pytest.mark.parametrize(
    "sent, back, reason",
    [
        (5, 6, "returned 24h 1m later"),
        (7, 8, "10.33% difference"),
        (9, 10, "same direction"),
        (11, 12, "sent on to a third account"),
        (19, 18, "same-second pair is reported once, with the lower txn_id as the original"),
        (28, 30, "24.5h apart: the window is measured between the two transactions of each pair"),
    ],
)
def test_round_trip_exclusions(pairs, sent, back, reason):
    assert (sent, back) not in pairs, reason


def test_transfer_to_a_third_account_is_never_a_round_trip(pairs):
    assert 21 not in {txn for pair in pairs for txn in pair}  # case 1: V -> X, X never sends back


def test_one_transaction_can_appear_in_several_pairs(pairs):
    sent, returned = [p[0] for p in pairs], [p[1] for p in pairs]
    assert sent.count(23) == 2 and returned.count(26) == 2  # case 2
    assert 24 in sent and 24 in returned  # a return in one pair, the original in another


def test_round_trip_boundaries_are_inclusive(round_trips):
    by_pair = {(t["sent_txn_id"], t["return_txn_id"]): t for t in round_trips}
    assert by_pair[(3, 4)]["hours_between"] == 24.0
    assert by_pair[(3, 4)]["pct_difference"] == 10.0
    assert by_pair[(16, 17)]["pct_difference"] == 10.0
    assert by_pair[(18, 19)]["hours_between"] == 0.0


def test_ipl_streaks(db):
    _, rows = run(db, "scenario2_ipl_streaks")
    assert [(name, start, length) for name, start, _end, length in rows] == [
        ("Faf du Plessis", "2024-03-30", 4),
        ("Rishabh Pant", "2024-03-24", 3),
        ("Rohit Sharma", "2024-04-01", 3),
        ("Sanju Samson", "2024-03-25", 3),
        ("Sanju Samson", "2024-04-08", 3),
        ("Shubman Gill", "2024-04-02", 3),
        ("Virat Kohli", "2024-03-22", 3),
    ]


@pytest.mark.parametrize(
    "player, reason",
    [
        ("Ruturaj Gaikwad", "never more than 2 in a row"),
        ("KL Rahul", "29 runs breaks the streak"),
        ("Travis Head", "3 in a row only when 2023 matches are included"),
    ],
)
def test_ipl_streak_exclusions(db, player, reason):
    _, rows = run(db, "scenario2_ipl_streaks")
    assert player not in {r[0] for r in rows}, reason
