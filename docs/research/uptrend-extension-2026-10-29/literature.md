# Method and indicator sources — additional uptrend research

Reviewed before market-result calculation on 2026-10-29. This wave reuses the prior study's academic review and exact retrospective labels. Formula documentation is implementation evidence, not evidence that a trading rule works. No source establishes the specific six-day confirmation claim being tested here.

## Academic methods retained

| Source | Decision affected in this study |
|---|---|
| Kim, Koh, Boyd & Gorinevsky (2009), [L1 Trend Filtering, author PDF](https://stanford.edu/~boyd/papers/pdf/l1_trend_filter.pdf) | Keep the existing log-price, lambda=1 cached fits and slope boundaries. A fitted trend uses future observations: it is an evaluation label, never a live signal input. Reuse the earlier endpoint-revision audit because neither these inputs nor the label changed. |
| Lo, Mamaysky & Wang (2000), [Foundations of Technical Analysis, author PDF](https://www.mit.edu/~wangj/pap/LoMamayskyWang00.pdf) | Reuse the prior original-text review: technical patterns can be studied as conditional information. Separate classification, conditional future-price distributions, and implementable trading profitability. Compare all signals with contemporaneous observable-state controls. |
| Sullivan, Timmermann & White (1999), [author/institution working version, LSE FMG DP303](https://www.fmg.ac.uk/sites/default/files/2020-11/dp303.pdf) | Reading the abstract and discussion of data reuse supports freezing the entire candidate family and reporting all candidates, not only the winner. Apply dependent resampling and family-adjusted intervals. The wave-specific correction does not remove selection from earlier research or turn reused TEST years into fresh validation. |
| Bajgrowicz & Scaillet (2012), [author PDF](https://scaillet.ch/pdfs/BajSca.pdf) | Retain the earlier separation between in-sample discovery, persistence, false discoveries and costs. No transaction-cost-free maximum excursion will be described as obtainable profit. A high confirmation rate does not establish ex ante profitability. |

Long-horizon momentum profitability does not directly establish short-horizon confirmation at ages 0–5. We therefore do not use momentum papers as proof that these particular indicators succeed. Earlier academic notes remain available in the protected `prior/docs/uptrend-confirmation-2026-10-23` and `prior/docs/downtrend-closure-2026-10-22` runtime copies.

## Formula sources checked and resulting fixed choices

| Family | Reliable formula source | Implemented choice and limits |
|---|---|---|
| Supertrend | [TradingView documentation](https://www.tradingview.com/support/solutions/43000634738-supertrend/) | HL midpoint, Wilder ATR10, multiplier3, recursive upper/lower bands and a bearish-to-bullish switch. Direction initializes bearish at first valid ATR; the shared 65-bar warmup applies. |
| Parabolic SAR | [TradingView documentation](https://www.tradingview.com/support/solutions/43000502597-parabolic-sar-sar/) | Acceleration .02, increment .02, cap .20; first two closes initialize direction. Project SAR, test strict high/low penetration, reverse to the old extreme or clamp to the prior two bars. Detect only at completed close. |
| TRIX | [TradingView documentation](https://www.tradingview.com/support/solutions/43000502331-trix/) | One-day percentage change of triple EMA18. Evaluate a zero cross and an EMA9 signal-line cross separately. EMA9 is a fixed research parameter. |
| Stochastic RSI | [TradingView documentation](https://www.tradingview.com/support/solutions/43000502333-stochastic-rsi-stoch-rsi/) | RSI14 normalized within its past14 values, SMA3 K and SMA3 D. K20 recovery and low K/D cross are distinct events. A zero RSI range is unknown, not an invented neutral oscillator reading. |
| RMI | [Infront Portfolio Manager documentation](https://infront-portfolio-manager.helpcenter.infront.co/en/pm/latest/relative-momentum-index) | Wilder20 averages of positive/negative five-day close changes. Cross30 tests recovery; cross50 tests direction. No threshold sweep. |
| Chaikin oscillator | [TradingView documentation](https://www.tradingview.com/support/solutions/43000501979-chaikin-oscillator/) | Cumulative accumulation/distribution from close location in each daily range and volume; EMA3 minus EMA10 crosses zero. Zero-range bars contribute zero. |
| Anchored VWAP | [Anchored VWAP](https://www.tradingview.com/support/solutions/43000669764-anchored-vwap-drawing-tool/), [VWAP calculation](https://www.tradingview.com/support/solutions/43000502018-volume-weighted-average-price-vwap/) | Calendar-quarter anchor fixed without hindsight, reset at segment start if needed; cumulative daily typical-price times volume divided by volume. Require five previous anchor bars. This is a **daily proxy**, not transaction VWAP or an anchor selected at a subsequently known low. |
| Volume oscillator | [Fidelity indicator guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/volume-oscillator) | SMA5(volume)/SMA20(volume)-1 crossing zero, plus positive close-to-close return because volume expansion alone has no direction. Periods5/20 and the direction condition are research choices. |

These are transparent research definitions; exact equality with the user's app, rounding, initialization and adjusted-volume convention is not claimed.

## Candidates deliberately deferred before seeing results

- Volume profile and true intraday VWAP need intraday price/volume data; daily OHLCV cannot reveal the actual volume at each price.
- Mass Index is non-directional range expansion. Adding an arbitrary directional rule would expand the search without a distinct pre-specified hypothesis.
- Envelope and disparity repeat moving-average distance; Williams %R and unsmoothed stochastic are affine counterparts; %B repeats band position; momentum/price oscillators overlap earlier ROC/MACD tests. This is a priority decision, not evidence of ineffectiveness.
- AD Line is represented through its Chaikin derivative here. Existing single-indicator and combination results are retained as benchmarks rather than re-optimized.

All 11 new events receive equal evaluation alongside five unchanged benchmark events. No additional simultaneous, ordered or persistence filters will be added after their outcomes are seen. This bounded extension ends with its report even if no candidate improves the established tradeoff.
