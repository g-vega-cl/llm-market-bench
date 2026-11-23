"""In-memory fixtures for the Daily Stock Picker Arena (sys-picks-*) portfolio tests.

Kept out of ``test_stock_picks_trading.py`` so the test module stays under the
LOC ceiling; the fakes hold no assertions of their own.
"""

from uuid import uuid4

from execution.portfolio import Portfolio
from execution.stock_picks_trading import PICKS_MODEL_TRACKS

SESSION = "2026-11-19"
LONG_TICKERS = ["AAA", "BBB", "CCC"]
SHORT_TICKERS = ["DDD", "EEE", "FFF"]


class _Response:
    def __init__(self, data):
        self.data = data


class _Query:
    """Minimal PostgREST-style query builder over an in-memory table store."""

    def __init__(self, store, table):
        self.store = store
        self.table = table
        self.filters = []
        self.action = "select"
        self.payload = None
        self.conflict = None

    def select(self, *_args, **_kwargs):
        self.action = "select"
        return self

    def insert(self, payload):
        self.action = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.action = "update"
        self.payload = payload
        return self

    def upsert(self, payload, on_conflict=None):
        self.action = "upsert"
        self.payload = payload
        self.conflict = on_conflict
        return self

    def delete(self):
        self.action = "delete"
        return self

    def eq(self, column, value):
        self.filters.append(("eq", column, value))
        return self

    def in_(self, column, values):
        self.filters.append(("in", column, set(values)))
        return self

    def is_(self, column, value):
        self.filters.append(("is", column, value))
        return self

    def match(self, mapping):
        for key, value in mapping.items():
            self.filters.append(("eq", key, value))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def _matches(self, row):
        for op, column, value in self.filters:
            cell = row.get(column)
            if op == "eq" and str(cell) != str(value):
                return False
            if op == "in" and cell not in value:
                return False
            if op == "is" and str(value).lower() == "null" and cell is not None:
                return False
        return True

    def execute(self):
        rows = self.store.rows.setdefault(self.table, [])
        if self.action == "select":
            return _Response([dict(r) for r in rows if self._matches(r)])
        if self.action == "insert":
            items = self.payload if isinstance(self.payload, list) else [self.payload]
            inserted = []
            for item in items:
                row = dict(item)
                row.setdefault("id", str(uuid4()))
                rows.append(row)
                inserted.append(dict(row))
            return _Response(inserted)
        if self.action == "update":
            updated = []
            for row in rows:
                if self._matches(row):
                    row.update(self.payload)
                    updated.append(dict(row))
            return _Response(updated)
        if self.action == "upsert":
            items = self.payload if isinstance(self.payload, list) else [self.payload]
            keys = [k.strip() for k in (self.conflict or "id").split(",")]
            stored = []
            for item in items:
                match = next((r for r in rows if all(str(r.get(k)) == str(item.get(k)) for k in keys)), None)
                if match is not None:
                    match.update(item)
                    stored.append(dict(match))
                else:
                    row = dict(item)
                    row.setdefault("id", str(uuid4()))
                    rows.append(row)
                    stored.append(dict(row))
            return _Response(stored)
        if self.action == "delete":
            removed = [dict(r) for r in rows if self._matches(r)]
            self.store.rows[self.table] = [r for r in rows if not self._matches(r)]
            return _Response(removed)
        raise AssertionError(f"unsupported action {self.action}")


class FakeSupabase:
    def __init__(self, rows=None):
        self.rows = {name: [dict(r) for r in data] for name, data in (rows or {}).items()}

    def table(self, name):
        return _Query(self, name)

    def count(self, name, **filters):
        return len([r for r in self.rows.get(name, []) if all(str(r.get(k)) == str(v) for k, v in filters.items())])


class StubPortfolio(Portfolio):
    """In-memory stand-in that keeps the real derived-property semantics.

    Subclassing ``Portfolio`` (instead of duck-typing a writable ``total_equity``)
    is deliberate: assigning to the derived property must fail in tests the same
    way it fails against Supabase-backed portfolios.
    """

    def __init__(self, owner_id, pid, cash=10000.0):
        super().__init__(owner_id)
        self.id = pid
        self.cash_balance = cash
        self.calculate_reg_t_metrics({})  # mirrors a DB row already marked at cash


def seed_session(store, session=SESSION, models=PICKS_MODEL_TRACKS):
    baskets = store.rows.setdefault("daily_stock_baskets", [])
    picks = store.rows.setdefault("daily_stock_picks", [])
    for index, model in enumerate(models):
        basket_id = f"basket-{index}"
        baskets.append({"id": basket_id, "target_date": session, "model_name": model, "status": "pending"})
        for rank, ticker in enumerate(LONG_TICKERS, start=1):
            picks.append(
                {
                    "id": f"pick-{index}-up-{rank}",
                    "basket_id": basket_id,
                    "target_date": session,
                    "model_name": model,
                    "ticker": ticker,
                    "direction": "UP",
                    "rank": rank,
                    "confidence": 70.0,
                    "status": "pending",
                }
            )
        for rank, ticker in enumerate(SHORT_TICKERS, start=1):
            picks.append(
                {
                    "id": f"pick-{index}-down-{rank}",
                    "basket_id": basket_id,
                    "target_date": session,
                    "model_name": model,
                    "ticker": ticker,
                    "direction": "DOWN",
                    "rank": rank,
                    "confidence": 70.0,
                    "status": "pending",
                }
            )
    return store


def portfolio_getter():
    created: dict[str, StubPortfolio] = {}

    async def _get(owner_id: str) -> StubPortfolio:
        if owner_id not in created:
            created[owner_id] = StubPortfolio(owner_id, f"pf-{len(created)}")
        return created[owner_id]

    return created, _get


def open_price_map(price=100.0, tickers=None):
    return {t: price for t in (tickers or LONG_TICKERS + SHORT_TICKERS)}


def stored_portfolio_getter(store, cash=10000.0):
    """Portfolio getter whose objects are mirrored into the fake `portfolios` table.

    ``execute_picks_exits`` persists equity with an ``update`` on that table, so tests
    that assert the written payload need the row to exist rather than only the object.
    """
    created: dict[str, StubPortfolio] = {}
    rows = store.rows.setdefault("portfolios", [])

    async def _get(owner_id: str) -> StubPortfolio:
        if owner_id not in created:
            portfolio = StubPortfolio(owner_id, f"pf-{len(created)}", cash)
            created[owner_id] = portfolio
            rows.append(
                {
                    "id": portfolio.id,
                    "owner_id": owner_id,
                    "cash_balance": cash,
                    "total_equity": cash,
                    "buying_power": cash,
                    "excess_liquidity": cash,
                    "sma": 0.0,
                    "realized": cash,
                }
            )
        return created[owner_id]

    return created, _get
