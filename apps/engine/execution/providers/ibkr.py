"""IBKR implementation of FinancialProvider."""

import asyncio
import xml.etree.ElementTree as ET
import logging
import math
from typing import Optional, List, Dict

from ib_async import IB, Stock, util
from .base import FinancialProvider, TickerData
from core.config import logger, IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID


class IBKRProvider(FinancialProvider):
    """Provider for Interactive Brokers API via ib-async."""

    async def _get_ib_client(self) -> IB:
        """Helper to create and connect an IB client."""
        util.patchAsyncio()
        
        # Suppress verbose ib_async internal logs (positions, account info)
        ib_logger = logging.getLogger('ib_async')
        ib_logger.setLevel(logging.WARNING)

        ib = IB()
        await ib.connectAsync(IBKR_HOST, IBKR_PORT, clientId=IBKR_CLIENT_ID, readonly=True)

        # Set market data type to 3 (Delayed) and 4 (Delayed Frozen)
        # to ensure we get data even without real-time subscriptions.
        # This is especially important for paper accounts or after-hours data.
        ib.reqMarketDataType(3)
        ib.reqMarketDataType(4)

        return ib

    async def get_ticker_data(self, ticker: str) -> Optional[TickerData]:
        """Fetch stock quote and market cap from IBKR."""
        ib = await self._get_ib_client()
        try:
            contract = Stock(ticker, "SMART", "USD")
            qualified = await ib.qualifyContractsAsync(contract)
            if not qualified:
                logger.warning(f"Ticker {ticker} not found or could not be qualified on IBKR.")
                return None
            
            contract = qualified[0]

            # 1. Fetch Price
            tickers = await ib.reqTickersAsync(contract)
            if not tickers:
                logger.warning(f"No ticker data found for {ticker} on IBKR.")
                return None
            
            t = tickers[0]
            
            # Key fix: math.isnan() check is crucial because NaN is truthy in Python.
            # We explicitly check for None or NaN at each step.
            price = t.marketPrice()
            if price is None or math.isnan(price) or price <= 0:
                price = t.last
            
            if price is None or math.isnan(price) or price <= 0:
                price = t.close
            
            if price is None or math.isnan(price) or price <= 0:
                price = t.bid
                
            if price is None or math.isnan(price) or price <= 0:
                price = t.ask
            
            if price is None or math.isnan(price) or price <= 0:
                logger.warning(f"Could not find a valid price for {ticker} on IBKR. marketPrice={t.marketPrice()}, last={t.last}, close={t.close}")
                return None

            # 2. Fetch Market Cap (Fundamental Data)
            market_cap = 0.0
            try:
                # reqFundamentalData returns an XML string
                fundamental_xml = await ib.reqFundamentalDataAsync(contract, "ReportSnapshot")
                if fundamental_xml:
                    root = ET.fromstring(fundamental_xml)
                    # Look for MarketCap in the XML
                    # Typical path: FinancialSummary/Ratios/Ratio[@type='MKTCAP']
                    # Or similar. Let's try to find any 'Ratio' with 'MKTCAP'
                    for ratio in root.findall(".//Ratio"):
                        if ratio.get("FieldName") == "MKTCAP":
                            market_cap = float(ratio.text) * 1e6 # IBKR usually returns in millions
                            break
                    
                    if market_cap == 0.0:
                        # Backup: Look for CompanyProfile/MarketCap
                        mkt_cap_node = root.find(".//MarketCap")
                        if mkt_cap_node is not None:
                            market_cap = float(mkt_cap_node.text)
            except Exception as e:
                logger.warning(f"Error fetching fundamental data for {ticker} from IBKR: {e}")

            if market_cap is None or math.isnan(market_cap):
                market_cap = 0.0

            return TickerData(
                ticker=ticker,
                price=float(price),
                market_cap=float(market_cap),
                exists=True,
                currency="USD",
                exchange=contract.exchange
            )

        except Exception as e:
            logger.error(f"Unexpected error fetching data from IBKR for {ticker}: {e}")
            return None
        finally:
            ib.disconnect()

    async def get_history(self, ticker: str, days: int = 14) -> List[Dict]:
        """Fetch historical price data from IBKR."""
        ib = await self._get_ib_client()
        try:
            contract = Stock(ticker, "SMART", "USD")
            qualified = await ib.qualifyContractsAsync(contract)
            if not qualified:
                return []
            
            contract = qualified[0]
            
            duration = f"{days} D"
            bars = await ib.reqHistoricalDataAsync(
                contract,
                endDateTime="",
                durationStr=duration,
                barSizeSetting="1 day",
                whatToShow="TRADES",
                useRTH=True
            )
            
            if not bars:
                return []
            
            results = []
            for bar in bars:
                results.append({
                    "price": float(bar.close),
                    "fetched_at": bar.date.isoformat() if hasattr(bar.date, "isoformat") else str(bar.date)
                })
            
            # Sort latest first
            results.reverse()
            return results

        except Exception as e:
            logger.error(f"Error fetching history from IBKR for {ticker}: {e}")
            return []
        finally:
            ib.disconnect()
