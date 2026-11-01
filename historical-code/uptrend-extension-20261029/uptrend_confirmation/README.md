# Upside onset confirmation research

Offline research; no dashboard/account/alert/order/schedule writes. Original downtrend scripts and results are imported/read, never changed. Use the adjacent engine Python and inherited SciPy directory.

Run from the workbench root with `../invest-agent-engine/.venv/Scripts/python.exe`:

1. `scripts/uptrend_confirmation/verify.py` — independent synthetic/prefix checks.
2. `scripts/uptrend_confirmation/verify.py freeze` — ONCE only, immutable protocol/prior hashes.
3. `scripts/uptrend_confirmation/study.py select --workers 4` then `aggregate-select` — TRAIN only; immutable candidate receipt.
4. `scripts/uptrend_confirmation/study.py evaluate --workers 4` then `aggregate-evaluate` — all candidates, anchors, six follow-ups and maintained-state comparators.
5. `scripts/uptrend_confirmation/endpoint.py` — deterministic40-stock/market endpoint audit.
6. `scripts/uptrend_confirmation/paths.py --workers 4` — all-signal future paths and four matching schemes, no L1 eligibility filter.
7. `scripts/uptrend_confirmation/infer.py classification` and `infer.py paths` —1999 replicates, mean3/6-month blocks, stock multipliers, simultaneous intervals.
8. `scripts/uptrend_confirmation/artifacts.py` — all-signal ledger, distributions, illustrative cases, reconciliations and independent checks.
9. `scripts/uptrend_confirmation/report.py` — readable report, charts, CSV archive.

Output: `runtime/uptrend-confirmation-20261023` and `docs/uptrend-confirmation-2026-10-23*`. Commands resume existing per-stock results. Never silently reuse them after changing feature/label/statistical definitions. Use a separate output folder for a new experiment; do not overwrite the original selection receipt. Saved new feature caches verify both original-cache SHA256 and signal-code SHA256. Output-side source timestamps are not evidence of a fresh market sample.

Key semantics:

- L1 is the inherited log-close lambda1 fit. Positive edge >1e-6; flat includes both ±1e-6 boundaries. A completed up run needs known boundaries at both ends. Duration is number of positive edges. Date of first edge is age0.
- Classification: all known signals with65 prior/126 future contiguous bars and complete labels; before-onset signals are failures, not excluded. Early0..5,late6+,short1..9,other are disjoint. Original source/cache breaks and warmups apply.
- Capture counts episodes once, conditional on all window values known. Delay is first successful signal only, never imputes zero for missed episodes. Price already risen is next-open/onset-close−1. Repeated crossings remain separate precision observations.
- Maintained states count every true day and are explicitly separate from events. They are not selected as winners and their annual count is qualifying days, not independent alerts.
- Future paths: h=5/21/63, base open[t+1], extrema over t+1..t+h, terminal close[t+h]. Common63-bar completeness, independent of L1. `all` and `early_hit` must never be pooled. Favorable excursion is max(0,max-high/open−1); adverse excursion is max(0,1−min-low/open), a positive loss depth. Excursions are not achievable trading returns.
- Matching: exact stock/quarter and causal categorical states. Scheme0 basic;1 adds ATR and r5;2 adds r1;3 adds r20 and MA20 distance. Signal-weighted supported-cell contrast. No matching on future L1. Fixed support/first-order control influence is approximate; report balance and scope.
- CSV ratios use fractions. `*_sum`, `*_n`, and per-stock NPZ sufficient statistics permit reconciliation. `evaluate-metrics.csv`'s `all_*` path columns use the label-evaluable population; the primary no-L1 results are `all-signal-paths.csv`, `matched-paths.csv` and `path-distributions.csv`. Legacy `context_*` fields are not used for conclusions.
- Both TRAIN and TEST were seen in past studies. This is a pre-specified upside analysis of reused history, not untouched prospective verification. All-history overlaps both; never sum those rows as independent data.
- The code imports pandas/NumPy/matplotlib from the existing engine environment, SciPy from the previous research dependencies. No dependency or environment installation is required.
