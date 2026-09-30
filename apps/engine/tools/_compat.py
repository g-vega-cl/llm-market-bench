"""Compatibility bridge ensuring unittest.mock.patch('core.llm.tools.*') or upstream modules continue to intercept calls in domain modules."""

from unittest.mock import Mock

import core.db as _cdb
import execution.market_data as _emd
import memory.embeddings as _me


def get_supabase_client():
    """Retrieve Supabase client, respecting mocks applied to core.llm.tools or core.db."""
    import core.llm.tools as bt

    tools_fn = getattr(bt, "get_supabase_client", None)
    db_fn = getattr(_cdb, "get_supabase_client", None)

    if isinstance(tools_fn, Mock):
        return tools_fn()
    if isinstance(db_fn, Mock):
        return db_fn()
    if tools_fn is not None and tools_fn is not db_fn:
        return tools_fn()
    if db_fn is not None:
        return db_fn()
    return None


def get_async_supabase_client():
    """Retrieve async Supabase client, respecting mocks applied to core.llm.tools or core.db."""
    import core.llm.tools as bt

    tools_fn = getattr(bt, "get_async_supabase_client", None)
    db_fn = getattr(_cdb, "get_async_supabase_client", None)

    if isinstance(tools_fn, Mock):
        return tools_fn()
    if isinstance(db_fn, Mock):
        return db_fn()
    if tools_fn is not None and tools_fn is not db_fn:
        return tools_fn()
    if db_fn is not None:
        return db_fn()
    return None


def get_embedding(*args, **kwargs):
    """Generate embedding vector, respecting mocks applied to core.llm.tools or memory.embeddings."""
    import core.llm.tools as bt

    tools_fn = getattr(bt, "get_embedding", None)
    me_fn = getattr(_me, "get_embedding", None)

    if isinstance(tools_fn, Mock):
        return tools_fn(*args, **kwargs)
    if isinstance(me_fn, Mock):
        return me_fn(*args, **kwargs)
    if tools_fn is not None and tools_fn is not me_fn:
        return tools_fn(*args, **kwargs)
    if me_fn is not None:
        return me_fn(*args, **kwargs)
    return None


class MarketDataManager:
    """Proxy class that resolves to core.llm.tools.MarketDataManager or execution.market_data.MarketDataManager."""

    def __new__(cls, *args, **kwargs):
        import core.llm.tools as bt

        tools_cls = getattr(bt, "MarketDataManager", None)
        emd_cls = getattr(_emd, "MarketDataManager", None)

        if isinstance(tools_cls, Mock):
            return tools_cls(*args, **kwargs)
        if isinstance(emd_cls, Mock):
            return emd_cls(*args, **kwargs)
        if tools_cls is not None and tools_cls is not emd_cls:
            return tools_cls(*args, **kwargs)
        if emd_cls is not None:
            return emd_cls(*args, **kwargs)
        return super().__new__(cls)
