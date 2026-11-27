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

`supabase/migrations/20261127190000_token_architecture.sql` adds `token_balances`, `token_ledger` (append-only, unique on `(owner_key, kind, ref_id)`), `guest_sessions`, `guest_budget_daily`, `feedback_requests`, and `strategy_recipes.live_expires_at`.

- `reserve_token(owner, kind, ref)` locks the balance row, refuses at zero, charges the guest daily budget, and is idempotent per ref.
- `settle_token(ref, outcome)` refunds a failed or expired backtest exactly once. A paused live week is never refunded.
- `refill_tokens(owner, amount, period)` sets rather than adds, so a missed cron week cannot stack.
- `expire_live_bots()` pauses lapsed bots and skips any bot with a turn in flight.

Contract tests live in `supabase/tests/000_token_rpc_test.sql` and run against a throwaway Postgres via `scripts/test_token_rpc.sh`, including a two-session race on the last token.

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
