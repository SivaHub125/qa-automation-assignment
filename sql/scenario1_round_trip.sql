-- Scenario 1: round-trip transfers
-- Account A sends money to account B, and B sends a similar amount (within 10%)
-- back to A within 24 hours.
--
-- Rules (agreed edge cases):
--   * "within 10%" is measured against the original amount A sent: |back - sent| <= 10% of sent
--   * exactly 10% counts; exactly 24 hours counts (both bounds inclusive)
--   * the 24-hour window is measured between the two transactions of each pair
--   * the original is the earlier transaction; two transactions at the same second
--     also count, and the lower txn_id is treated as the original (so the pair is
--     reported once, not twice)
--   * EVERY qualifying pair is reported (detection use case: hide no link), so one
--     transaction can appear in more than one pair, and can be a return in one pair
--     and the original in another
--
-- Amounts are integer cents, so "* 10 <= sent" is exact integer arithmetic.

SELECT
    sent.txn_id                                         AS sent_txn_id,
    sent.from_account                                   AS account_a,
    sent.to_account                                     AS account_b,
    printf('%.2f', sent.amount_cents / 100.0)           AS amount_sent,
    sent.txn_time                                       AS sent_at,
    back.txn_id                                         AS return_txn_id,
    printf('%.2f', back.amount_cents / 100.0)           AS amount_returned,
    back.txn_time                                       AS returned_at,
    ROUND((julianday(back.txn_time) - julianday(sent.txn_time)) * 24, 2) AS hours_between,
    ROUND(ABS(back.amount_cents - sent.amount_cents) * 100.0 / sent.amount_cents, 2) AS pct_difference
FROM transactions AS sent
JOIN transactions AS back
  ON  back.from_account = sent.to_account
  AND back.to_account   = sent.from_account
  AND (back.txn_time > sent.txn_time
       OR (back.txn_time = sent.txn_time AND back.txn_id > sent.txn_id))
  AND back.txn_time     <= datetime(sent.txn_time, '+24 hours')
  AND ABS(back.amount_cents - sent.amount_cents) * 10 <= sent.amount_cents
ORDER BY sent.txn_time, back.txn_time;
