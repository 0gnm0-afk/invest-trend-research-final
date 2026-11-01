# UPTREND-EXTENSION-20261029

Offline research only. Eleven fixed new events in eight indicator families, five unchanged benchmarks. Existing L1 labels, prices, periods, denominators and future-path framework are reused. No market collection, operational database, account, order or alert writes.

## Lineage

Prior workbench source commit: `a8fa907`. Private archive repository: `PRIVATE_PRIOR_ARCHIVE`, archive commit `120dd467e7667063f6974a52006a44d218d694fd`, release `research-2026-10-21-23`. Original source and documentation copies live only under the new runtime's `prior/` tree. The four `downtrend-indicators-20261021-part*.zip` release assets supply identical immutable price/L1 caches. See `restore.py` for exact hashes and safe extraction scope and the report's restore receipt for execution evidence.

`legacy.py` extracts the original numeric helpers and L1 run segmentation without a dependency on operational modules or a new L1 solver. `study.py`, `paths.py`, `infer.py`, and `artifacts.py` adapt the earlier uptrend workflow. Changes are isolated paths/imports, the fixed new candidate family, common-eligible episode comparisons, paired benchmark uncertainty, and additional verification. `signals.py` is the new causal formula layer. Historical source-cache SHA256s are checked on every load.

## Reproduction order

Use Python with numpy, pandas and matplotlib; the workbench's sibling engine virtualenv was used. The original cached L1 fits avoid a new optimizer dependency.

1. Restore the `prior/` files from the stated Git commit (listed in the protocol receipt); download the four release assets into `runtime/uptrend-extension-20261029/downloads/`, then run `restore.py`.
2. Run `verify.py` for synthetic prefix/formula checks, then `verify.py freeze` **once before market calculations**. A repeat freeze deliberately fails; preserve the original receipt.
3. `study.py select --workers 4`, then `study.py aggregate-select`.
4. `study.py evaluate --workers 4`, then `study.py aggregate-evaluate`.
5. `paths.py --workers 4`, `infer.py classification`, then `infer.py paths`.
6. `artifacts.py` reconciles all signal ledgers, scalar price paths, labels, matched samples and protected input hashes. Then run `summarize.py`, `verify_formulas.py`, `figures.py`, `report.py`, and `package.py`, in that order. Inspect the six PNGs before recording visual acceptance. The completed run used4 workers for selection and6 for evaluation/path computation; this does not change the definitions.

Outputs are under `runtime/uptrend-extension-20261029/`; inspectable report tables and receipts are copied to `docs/research/uptrend-extension-2026-10-29/`. Runtime files contain the full compressed per-signal ledger and per-stock sufficient statistics. A cache's existence is not evidence of completion: use final receipts and the report.

The same TEST years were examined before. This is a pre-specified **exploratory extension**, not new independent validation. The fixed definitions are in `protocol.json`; sources and decision consequences are in the report's `literature.md`.
