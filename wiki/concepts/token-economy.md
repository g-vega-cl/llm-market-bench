---
tags: [billing, quota, guest-access, llm-spend, tokens]
category: concept
---

# Token Economy

One token buys **one backtest** or **one live bot for 7 calendar days**. It is the single unit that bounds LLM spend on `/build`, replacing the old per-day backtest cap. Accounts refill weekly; logged-out visitors get a one-time guest balance.

## The two lanes

| Lane | Grant | Refill | Identity |
|---|---|---|---|
| Guest | 5 tokens | never | signed httpOnly cookie + hashed `CF-Connecting-IP` |
| Account | 15 tokens | weekly, Monday 09:30 ET | Supabase user id |

A guest balance is one-time, so a returning visitor must sign up to run again — the exhaustion state is the conversion surface, not an error. Anonymous refills were rejected because a rotating IP would make the balance unbounded.

## Enforcement

`supabase/migrations/20261127190000_token_architecture.sql` adds `token_balances`, `token_ledger` (append-only, unique on `(owner_key, kind, ref_id)`, and a second unique index on `(kind, ref_id)` so a ref can never belong to two owners), `guest_sessions`, `guest_budget_daily`, `feedback_requests`, and `strategy_recipes.live_expires_at`. `20261127191000_guest_mint.sql` adds the guest mint.

- `reserve_token(owner, kind, ref)` locks the balance row, refuses at zero, charges the guest daily budget, and is idempotent per ref. A refunded ref is terminal.
- `settle_token(ref, outcome)` refunds a failed or expired backtest exactly once. A paused live week is never refunded. If the balance row is missing it is rebuilt from `sum(delta)`, never from zero.
- `refill_tokens(owner, amount, period)` accepts only the current Monday and 1–15 tokens, sets rather than adds, and ledgers the adjustment so `balance == sum(delta)`.
- `expire_live_bots()` pauses lapsed bots, skipping any bot with a turn whose `COALESCE(heartbeat_at, created_at)` is inside 30 minutes.
- `mint_guest_tokens(token_hash, ip_hash)` resolves a guest from a hashed signed cookie and grants 5 tokens exactly once.
- `start_live_week(user, recipe)` spends a `live_week` token and writes `live_expires_at` in the same transaction; re-enabling an already-live bot is free. `switch_live_schedule` delegates its enable step to it, so a refused token rolls the pause back too. The hourly cycle calls `expire_live_bots`.

Contract tests live in `supabase/tests/` (21 assertions across the ledger and the mint) and run against a throwaway Postgres via `scripts/test_token_rpc.sh`, including a two-session race on the last token.

## Spend path

`apps/web/src/shared/auth/guest-cookie.ts` signs the cookie (HMAC) and hashes it; `clientIpFrom` reads only `CF-Connecting-IP`, never the spoofable leftmost `X-Forwarded-For`. `guest-session.ts` mints and resolves the balance.

`enqueueRecipeJob` spends only after every validation has passed, using the queue row id as the ref, so a refund always names a row that exists; an insert failure refunds immediately. Guest runs use `startGuestBacktestFn` under the sentinel user `00000000-0000-0000-0000-000000000000`, which the queue accepts because `user_id` has no foreign key. The engine refunds in `_record_job_failure`, skipping compile/preview/live-turn rows and returning early when the status write itself failed.

## Accepted non-goals

These are decisions with evidence, not gaps. The next session should not propose them back:

- **No buying tokens.** There is no payment rail, no price, and no entitlement model; the exchange rate is not validated yet.
- **No admin grant UI.** The tokens-exhausted feedback form is an inbox, not a grant path. Manual grants would land on a cookie identity that dies when the cookie clears.
- **No email capture.** Google OAuth is the only sign-in, so a "send me a link" recovery flow has nothing to send to.
- **No IP blocking.** Per-identity limits cannot bound spend against IP rotation; the global 20-backtest / 2-live-week daily budget is the bound that survives.
- **Compiles do not spend tokens.** The 25/day compile cap stays as its own meter, so a signed-in user can burn 25 compiles and zero tokens. Accepted because compiles are cheap relative to a 30–60 call backtest.
- **No per-day cap for accounts.** A user can spend all 15 on day one; burst-then-drought is intentional, and the UI must show the refill date on the control that spends.
- **Live concurrency is unchanged.** `max_live_recipes` (1–3) still gates concurrent bots; a token buys time on a slot, not another slot.

## Before guest tokens can ship

1. **Privacy policy update.** Storing a signed guest cookie, a hashed IP, and a feedback body is a new data category; `wiki/concepts/privacy-policy.md` currently describes IP-derived coarse location only.
2. **Replica probe.** The migration touches `strategy_recipes`, so `deploy_secondary.sh` must re-run and `recipe_public_stats` must be probed live (PGRST205 otherwise).
3. **Backfill order.** `live_expires_at = now() + 7 days` must be written before the `CHECK (is_live = FALSE OR live_expires_at IS NOT NULL)` constraint, or the migration aborts on the existing live bots.
