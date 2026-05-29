---
name: add-to-watchlist
description: Add one or more symbols to the user's TradingView watchlist through the open Chrome browser. Use when the user asks to add tickers, futures, crypto, forex, or other TradingView symbols to a named watchlist such as the US watchlist, especially when they want the repeatable UI flow.
---

# add-to-watchlist

Add symbols to a TradingView watchlist using the user's logged-in Chrome session and Computer Use.

## Inputs To Extract

- Symbols to add, in order. Support one or many symbols.
- Target watchlist name. Default to `US` if the user says "US watchlist" or does not specify a different TradingView watchlist.
- Optional disambiguation such as exchange, asset type, or full TradingView symbol (`CME:MES1!`, `NASDAQ:MU`, `BTCUSD`, etc.).

## Standard Flow

1. Use the `computer-use:computer-use` skill and operate `Google Chrome`.
2. Open a new Chrome tab with this stable TradingView chart URL unless the user explicitly says to use the current tab:

```text
https://www.tradingview.com/chart/5JanKmS6/?symbol=NASDAQ%3AMU
```

3. In the right panel, confirm the watchlist dropdown/header shows the target watchlist, usually `US`.
4. If the wrong watchlist is selected, click the watchlist dropdown/header and choose the requested watchlist before adding anything.
5. Click `Add symbol` (`+`) in the watchlist panel.
6. For each symbol:
   - Type the symbol into the `Symbol, ISIN, or CUSIP` search field.
   - Choose the exact intended result by symbol, description, exchange, and asset type.
   - Click that row's `Add to Watchlist` (`+`) icon.
   - Verify the icon changes to `Remove from Watchlist` or the symbol appears in the watchlist.
   - Clear the search field and repeat for the next symbol.
7. Close the add-symbol dialog when finished.
8. If you opened a new tab only for this task, close that tab and leave the user's original tabs alone.
9. Report the added symbols and any display aliases TradingView used.

## Result Selection Rules

- Prefer exact symbol matches over partial matches.
- If the user supplies an exchange or asset type, require it in the result.
- If the symbol is ambiguous and the user did not provide enough detail, use common TradingView conventions only when the intended result is obvious from the request.
- Do not add a similarly named stock/index/fund when the user asked for a futures, forex, crypto, or specific exchange symbol.
- If the correct result is not visible, click the appropriate tab (`Futures`, `Stocks`, `Crypto`, etc.) or refine the search with the exchange prefix if useful.

## Known TradingView Aliases

- `MES` for Micro E-mini S&P 500 Index Futures is the CME futures result. After adding it, TradingView may show it in the watchlist as `MES1!`.
- For continuous futures, TradingView often displays the continuous contract with a `1!` suffix even when the search query was the root symbol.

## Multiple Symbols

When adding multiple symbols, keep the add-symbol dialog open. Add symbols one by one:

```text
search first symbol -> click correct + -> verify added -> clear search -> next symbol
```

If a symbol is already in the watchlist, its row usually shows a remove/trash icon instead of `+`. Treat it as already added, do not click remove, and continue.
