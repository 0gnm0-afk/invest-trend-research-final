# Long-history upward confirmation reassessment

Research only. Prior outputs and operational collection, accounts, alerts and orders are untouched.

Primary dates: 2010-10-01–2025-09-30 (180 months). All available history is supplementary; stocks with shorter histories enter at their first eligible date. The source cutoff is 2026-09-30. All72 fixed conditions are evaluated separately in KR and US. See `protocol.json`, frozen before results, and the durable report under `docs/research/uptrend-longhistory-2026-10-29.md`.

Run from the workbench root with the sibling engine environment:

```powershell
$py = '../invest-agent-engine/.venv/Scripts/python.exe'
& $py scripts/research/uptrend_longhistory/supplemental_cache.py
& $py scripts/research/uptrend_longhistory/coverage_audit.py
& $py scripts/research/uptrend_longhistory/study.py evaluate --workers 6
& $py scripts/research/uptrend_longhistory/study.py aggregate-evaluate
& $py scripts/research/uptrend_longhistory/paths.py --workers 3
$env:OPENBLAS_NUM_THREADS = '4'
& $py scripts/research/uptrend_longhistory/infer.py classification
& $py scripts/research/uptrend_longhistory/infer.py paths
& $py scripts/research/uptrend_longhistory/verify.py preliminary
& $py scripts/research/uptrend_longhistory/verify.py final
& $py scripts/research/uptrend_longhistory/cases.py
& $py scripts/research/uptrend_longhistory/distributions.py --rebuild-spool
& $py scripts/research/uptrend_longhistory/artifacts.py
& $py scripts/research/uptrend_longhistory/package.py copy
& $py scripts/research/uptrend_longhistory/report.py
& $py scripts/research/uptrend_longhistory/package.py
```

The first two commands require the preserved raw-source inventory on this machine. The original7,426 inventory/cache input is reused in place under `runtime/uptrend-extension-20261029/input/`; the additional57 research-only records are attempted in the new supplemental folder. Runtime data are private and are not committed. The source manifest identifies every file and hash needed for reproduction.

`old_signals.py` preserves original upward definitions (only the numerical-helper import points to the preserved `legacy.py`); `new_signals.py` preserves all extension definitions. `prepare.py` records how the separate runner was initially derived; ordinary reproduction runs the committed runner directly, without regenerating it. `followups.py` preserves the actual causal confirmation clock. No long-history outcome selects a candidate or changes a parameter.

All conclusions concern retrospective label confirmation and conditional price paths. They are not a backtested executable portfolio or net return after trading costs. The expanded historical period has previously inspected portions and is not a new independent holdout.

Inspect the nine rendered PNGs before treating delivery as visually verified. `cleanup_distribution_spool.py` may reclaim only this run's temporary, hash-verified float32 quantile spool after its verification passes. The source caches, feature caches, per-stock evaluation/path statistics, CSVs and receipts are preserved. `distributions.py --rebuild-spool` regenerates that temporary spool. `export_events.py --id macd_rsi40 --market KR` can produce an inspectable private event CSV.gz; its classification-population rows must not be confused with the independent future-path population.
