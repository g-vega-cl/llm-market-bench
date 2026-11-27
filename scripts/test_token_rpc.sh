#!/usr/bin/env bash
# Applies the token migration to a throwaway Postgres 16 and runs the RPC
# contract tests, including a real two-session race on the last token.
#
# Usage: scripts/test_token_rpc.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MIGRATION="$ROOT/supabase/migrations/20261127190000_token_architecture.sql"
MINT_MIGRATION="$ROOT/supabase/migrations/20261127191000_guest_mint.sql"
STUB="$ROOT/supabase/tests/000_stub_schema.sql"
CONTRACTS="$ROOT/supabase/tests/000_token_rpc_test.sql"
MINT_CONTRACTS="$ROOT/supabase/tests/001_guest_mint_test.sql"
CID="bfy-token-test-$$"
TMP="$(mktemp -d)"
PASS="token_test"

cleanup() {
    docker rm -f "$CID" >/dev/null 2>&1 || true
    rm -rf "$TMP"
}
trap cleanup EXIT

if [[ ! -f "$MIGRATION" || ! -f "$MINT_MIGRATION" ]]; then
    echo "FAIL: migration not found: $MIGRATION / $MINT_MIGRATION" >&2
    exit 1
fi

docker run -d --name "$CID" -e POSTGRES_PASSWORD="$PASS" -e POSTGRES_DB=token_test postgres:16 >/dev/null

READY=0
for _ in $(seq 1 60); do
    if docker exec "$CID" psql -U postgres -d token_test -c 'SELECT 1' >/dev/null 2>&1; then
        READY=1
        break
    fi
    sleep 1
done

if [[ "$READY" != "1" ]]; then
    echo "FAIL: Postgres never became ready (unit under test did not start)" >&2
    exit 1
fi

psql_() { docker exec -i "$CID" psql -U postgres -d token_test -v ON_ERROR_STOP=1 "$@"; }

psql_ -q -f - < "$STUB"
psql_ -q -f - < "$MIGRATION"
psql_ -q -f - < "$MINT_MIGRATION"
if [[ "${APPLY_TWICE:-0}" == "1" ]]; then
    psql_ -q -f - < "$MIGRATION"
    psql_ -q -f - < "$MINT_MIGRATION"
fi
psql_ -q -f - < "$CONTRACTS"
psql_ -q -f - < "$MINT_CONTRACTS"

# Two sessions, one token: the second must block on the row lock and then
# find the balance empty. Exactly one reservation may succeed.
psql_ -q -c "DELETE FROM public.token_ledger; DELETE FROM public.token_balances;
             INSERT INTO public.token_balances (owner_key, tier, balance, period_start)
             VALUES ('user:z','account',1,CURRENT_DATE);"

( psql_ -tA -c "BEGIN;
                SELECT ok FROM public.reserve_token('user:z','backtest','55555555-5555-5555-5555-555555555555');
                SELECT pg_sleep(2);
                COMMIT;" > "$TMP/a.out" 2>&1 ) &
A_PID=$!

sleep 0.5
psql_ -tA -c "SELECT ok FROM public.reserve_token('user:z','backtest','66666666-6666-6666-6666-666666666666');" > "$TMP/b.out" 2>&1
wait "$A_PID"

A_OK=$(grep -c '^t$' "$TMP/a.out" || true)
B_OK=$(grep -c '^t$' "$TMP/b.out" || true)
LEDGER=$(psql_ -tA -c "SELECT count(*) FROM public.token_ledger WHERE owner_key='user:z';")
BALANCE=$(psql_ -tA -c "SELECT balance FROM public.token_balances WHERE owner_key='user:z';")

if [[ "$A_OK" != "1" || "$B_OK" != "0" || "$LEDGER" != "1" || "$BALANCE" != "0" ]]; then
    echo "FAIL: concurrent last token (a_ok=$A_OK b_ok=$B_OK ledger=$LEDGER balance=$BALANCE)" >&2
    cat "$TMP/a.out" "$TMP/b.out" >&2
    exit 1
fi

echo "PASS 17 concurrent last token: one winner, one refusal"
echo "ALL TOKEN RPC CONTRACTS PASSED"
