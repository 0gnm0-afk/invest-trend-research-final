# DOWNTREND-EXTENSION-20261029

Additional bearish confirmation research: 12 frozen new events, 6 original benchmarks. No operational data or alerts are changed. The first goal metadata said uptrend by mistake; the user explicitly confirmed downtrend onset research through the scope question. Every artifact here concerns downtrends. The separate completed uptrend extension remains unchanged.

Original source/report reference: workbench Git `94afaef`. Existing immutable input caches are reused from `runtime/uptrend-extension-20261029/input/runtime/downtrend-indicators-20261021`. That restore is documented in the uptrend extension's README and restore receipt; it retrieved the archived original caches, not newly collected market data. Runtime `prior/` contains relevant original downtrend source and result copies. `signals.py` also imports the pre-existing audited indicator formulas and original features source explicitly; their hashes are in the frozen receipt.

Run with the sibling engine Python environment (numpy, pandas, matplotlib):

1. `verify.py`, `verify_formulas.py`, then `verify.py freeze` once before market-result calculations.
2. `study.py select --workers 6`, `study.py aggregate-select`.
3. `study.py evaluate --workers 6`, `study.py aggregate-evaluate`.
4. `paths.py --workers 6`, `infer.py classification`, `infer.py paths`.
5. `artifacts.py`, `summarize.py`, `figures.py`, `report.py`, then `package.py`.

All denominator, label, matching, bootstrap and stop choices are fixed in `protocol.json`. Crossing is an occurrence, not every day a bearish state persists. All conditions use only current/past daily OHLCV. L1 labels are retrospective. Classification uses the original 126-future-bar evaluation mask; prospective price information is evaluated on all signals without conditioning on L1 state. Reused TEST years are exploratory, even with a predeclared current family and dependent multiple-testing adjustment.

Classification context comparisons in this extension use calendar **months** so their sufficient statistics align with monthly resampling; the original 2026-10-21 comparison used quarters. These descriptive context values are deliberately excluded from exact benchmark reconciliation. Future-path matching uses calendar **quarters**, with four predeclared levels of observable-state detail and actual control-month first-order uncertainty.

Research artifacts are under `docs/research/downtrend-extension-2026-10-29/`; full per-stock caches and compressed event ledger stay in its runtime directory. Never infer completion from a cache alone: use final receipts, report and Git checkpoint.
