"""Read-only census of inherited uptrend research coverage; no provider calls.

Raw date span is not continuous coverage. Evaluation-day counts apply the
inherited 65-history/126-future contiguous-bar and completed-UP-run rules,
before indicator-specific availability. Cached input hashes were checked by
the preceding uptrend-extension run; this audit does not rehash large NPZs.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import date
import json
from pathlib import Path
import sqlite3

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "runtime/uptrend-extension-20261029/input/runtime/downtrend-indicators-20261021"
OUT = ROOT / "docs/research/uptrend-longhistory-2026-10-29"
COMBINED = ROOT / "runtime/uptrend-longhistory-20261029/inventory.json"
WINDOWS = {"fifteen": ("2010-10-01", "2025-09-30"),
           "recent_fifteen": ("2011-04-01", "2026-03-31"),
           "all": ("1900-01-01", "2026-09-30")}


def read(path):
    return json.loads(Path(path).read_bytes())


def fifteen(first, last):
    if not first or not last:
        return False
    a, b = date.fromisoformat(first), date.fromisoformat(last)
    try:
        anniversary = a.replace(year=a.year + 15)
    except ValueError:
        anniversary = a.replace(year=a.year + 15, day=28)
    return b >= anniversary


def years(first, last):
    return round((date.fromisoformat(last) - date.fromisoformat(first)).days / 365.2425, 4) if first and last else 0


def label_known(fit, seg):
    slope = np.r_[np.diff(fit), np.nan]
    slope[np.r_[seg[1:] != seg[:-1], True]] = np.nan
    up = np.isfinite(slope) & (slope > 1e-6)
    starts = np.flatnonzero(up & ~np.r_[False, up[:-1]])
    ends = np.flatnonzero(up & ~np.r_[up[1:], False]) + 1
    completed = (starts > 0) & np.isfinite(slope[np.maximum(starts - 1, 0)]) & np.isfinite(slope[np.minimum(ends, len(slope) - 1)])
    known = np.isfinite(slope) & (slope <= 1e-6)
    for a, b in zip(starts[completed], ends[completed]):
        known[a:b] = True
    return slope, known


def one(args):
    rec, raw = args
    stem = rec["market"] + "_" + rec["symbol"]
    p = ROOT / rec["cache_path"] if rec.get("cache_path") else SOURCE / "cache" / (stem + ".npz")
    meta = read(p.with_suffix(".json"))
    source = str(rec.get("source", ""))
    category = "active_toss" if "2026-10-01-toss" in source else "supplementary"
    r = dict(market=rec["market"], symbol=rec["symbol"], exchange=rec.get("exchange"),
             source_category=category, status=meta.get("status"),
             source_first=meta.get("source_first", raw.get("first", "")),
             source_last=meta.get("source_last", raw.get("last", "")),
             stored_bars=meta.get("stored_bars", raw.get("bars", 0)),
             used_bars=meta.get("used_bars", 0), invalid_or_zero_volume=meta.get("invalid_or_zero_volume", ""),
             source_missing_sessions=len(raw.get("missing_sessions", [])) if raw else "",
             source_non_sessions=len(raw.get("non_sessions", [])) if raw else "",
             source_invalid_ohlc=len(raw.get("invalid_ohlc", [])) if raw else "",
             provider_end_reached=raw.get("provider_end_reached", ""),
             usable_first="", usable_last="", segments=0, longest_segment_bars=0,
             longest_segment_years=0, segments_span_ge_15y=0,
             first_evaluable="", last_evaluable="", all_evaluable_days=0,
             after_2010_segments=0, longest_evaluable_run_bars=0,
             longest_evaluable_run_years=0, contiguous_evaluable_span_ge_15y=False,
             research_source_group=rec.get("research_source_group","inherited"))
    r["source_span_years"] = years(r["source_first"], r["source_last"])
    r["source_span_ge_15y"] = fifteen(r["source_first"], r["source_last"])
    annual = []
    if p.exists():
        with np.load(p, allow_pickle=False) as z:
            ds, seg, fit = z["date"], z["segment"], z["full"]
        n = len(ds)
        r.update(usable_first=str(ds[0]), usable_last=str(ds[-1]), used_bars=n)
        starts = np.r_[0, np.flatnonzero(seg[1:] != seg[:-1]) + 1]
        ends = np.r_[starts[1:], n]
        spans = [years(str(ds[a]), str(ds[b-1])) for a, b in zip(starts, ends)]
        r.update(segments=len(starts), longest_segment_bars=int(max(ends-starts)),
                 longest_segment_years=max(spans),
                 segments_span_ge_15y=sum(fifteen(str(ds[a]), str(ds[b-1])) for a,b in zip(starts, ends)),
                 after_2010_segments=sum(bool(ds[b-1] >= "2010-10-01") for a,b in zip(starts,ends)))
        hist, fut, future_fit = np.zeros(n,bool), np.zeros(n,bool), np.zeros(n,bool)
        if n > 65:
            hist[65:] = seg[65:] == seg[:-65]
        if n > 126:
            fut[:-126] = seg[126:] == seg[:-126]
            future_fit[:-126] = np.isfinite(fit[126:])
        slope, known = label_known(fit, seg)
        base = hist & fut & future_fit & np.isfinite(slope)
        valid = base & known
        if valid.any():
            r.update(first_evaluable=str(ds[valid][0]), last_evaluable=str(ds[valid][-1]), all_evaluable_days=int(valid.sum()))
            vs=np.flatnonzero(valid&~np.r_[False,valid[:-1]])
            ve=np.flatnonzero(valid&~np.r_[valid[1:],False])+1
            r.update(longest_evaluable_run_bars=int(max(ve-vs)),
                     longest_evaluable_run_years=max(years(str(ds[a]),str(ds[b-1])) for a,b in zip(vs,ve)),
                     contiguous_evaluable_span_ge_15y=any(fifteen(str(ds[a]),str(ds[b-1])) for a,b in zip(vs,ve)))
        for name,(lo,hi) in WINDOWS.items():
            d = (ds >= lo) & (ds <= hi)
            r[name+"_usable_bars"] = int(d.sum())
            r[name+"_evaluable_days"] = int((valid & d).sum())
            r[name+"_warmup_unavailable"] = int((d & ~hist).sum())
            r[name+"_future_unavailable"] = int((d & hist & ~(fut & future_fit)).sum())
            r[name+"_censored_up_days"] = int((d & base & ~known).sum())
        yy = np.array([int(x[:4]) for x in ds])
        for y in np.unique(yy):
            m = yy == y
            annual.append(dict(market=r["market"], symbol=r["symbol"], year=int(y), usable_bars=int(m.sum()), evaluable_days=int((m&valid).sum())))
    else:
        for name in WINDOWS:
            for field in ["usable_bars", "evaluable_days", "warmup_unavailable", "future_unavailable", "censored_up_days"]:
                r[name+"_"+field] = 0
    r["evaluable_span_years"] = years(r["first_evaluable"],r["last_evaluable"])
    r["evaluable_span_ge_15y"] = fifteen(r["first_evaluable"],r["last_evaluable"])
    return r, annual


def csv_write(path, rows):
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--workers",type=int,default=4);args=ap.parse_args()
    inv = read(COMBINED if COMBINED.exists() else SOURCE / "inventory.json")
    raw = {}
    universes = {}
    for market in ["KR","US"]:
        folder=ROOT/"runtime"/(market.lower()+"-history")/"2026-10-01-toss"
        raw.update({(market,x["symbol"]):x for x in read(folder/"coverage.json")})
        universes[market]=read(folder/"universe.json")["data"]["rows"]
    rows, annual = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i,(r,a) in enumerate(pool.map(one,[(r,raw.get((r["market"],r["symbol"]),{})) for r in inv["stocks"]])):
            rows.append(r);annual.extend(a)
            if (i+1)%1000==0: print(f"Audited {i+1} / {len(inv['stocks'])}",flush=True)
    agg=defaultdict(lambda: dict(usable_stock_years=0,evaluable_stocks=0,usable_bars=0,evaluable_days=0))
    for r in annual:
        a=agg[(r["market"],r["year"])];a["usable_stock_years"]+=1;a["evaluable_stocks"]+=r["evaluable_days"]>0;a["usable_bars"]+=r["usable_bars"];a["evaluable_days"]+=r["evaluable_days"]
    annual_rows=[dict(market=m,year=y,**v) for (m,y),v in sorted(agg.items())]
    chart=[]
    con=sqlite3.connect(f"file:{(ROOT/'runtime/chart-history.sqlite3').as_posix()}?mode=ro",uri=True)
    chart_payloads=con.execute("SELECT payload FROM history").fetchall();con.close()
    for (payload,) in chart_payloads:
        p=json.loads(payload)
        if "series" in p:
            s=p["series"];bars=s["bars"]
            chart.append(dict(market=s["market"],symbol=s["symbol"],first=bars[0]["date"],last=bars[-1]["date"],bars=len(bars),in_inventory=any(r["market"]==s["market"] and r["symbol"]==s["symbol"] for r in rows)))
    summary=dict(audit_scope=f"All {len(inv['stocks']):,} research inventory entries; no provider requests, no operational writes", source=str(SOURCE.relative_to(ROOT)), combined_inventory=str(COMBINED.relative_to(ROOT)) if COMBINED.exists() else None, windows=WINDOWS,
                 eligibility="65 prior and 126 future contiguous observations, finite future L1 fit, current finite slope, completed UP boundaries; before signal-specific feature availability", hash_policy="Source hashes already verified in preceding uptrend-extension restoration and per-stock load; this coverage pass does not rehash large NPZ files", markets={},
                 chart_cache=dict(total_rows=len(chart_payloads),successful_payloads=len(chart),unique_symbols=sorted({x["market"]+":"+x["symbol"] for x in chart}),additional_inventory_symbols=sorted({x["market"]+":"+x["symbol"] for x in chart if not x["in_inventory"]})),
                 limitations=["Current/saved stock inventory is not a survivorship-free historical listing census.","A 15-year first-to-last span does not imply 15 contiguous years or full daily coverage.","Short-history stocks remain included from their earliest evaluable observations; no minimum 15-year stock screen.","Former operational exclusions are attempted in this research only; operational policies remain unchanged.","Raw early KR provider dates include historical calendar discrepancies. Inherited segment breaks are retained.","Latest mature eligibility depends on gaps, completed trend boundaries, and indicator warmup; no tail-label shortcut is used.","Contiguous evaluable span is generic label eligibility before signal-specific availability; volume indicators can have fewer available days."])
    for m in ["KR","US"]:
        rr=[r for r in rows if r["market"]==m];u={r["symbol"] for r in universes[m]};s={r["symbol"] for r in rr};ex={r["symbol"] for r in inv["excluded"] if r["market"]==m}
        valid=[r for r in rr if r["all_evaluable_days"]]
        summary["markets"][m]=dict(inventory=len(rr),active_universe=len(u),excluded=len(ex),supplementary_inventory_symbols=sorted(s-u),active_universe_unaccounted=sorted(u-(s|ex)),status_counts=dict(Counter(r["status"] for r in rr)),source_span_ge_15y=sum(r["source_span_ge_15y"] for r in rr),source_span_lt_15y=sum(not r["source_span_ge_15y"] for r in rr),evaluable_span_ge_15y=sum(r["evaluable_span_ge_15y"] for r in rr),at_least_one_contiguous_15y_segment=sum(r["segments_span_ge_15y"]>0 for r in rr),all_evaluable_stocks=len(valid),source_first=min(r["source_first"] for r in rr if r["source_first"]),source_last=max(r["source_last"] for r in rr if r["source_last"]),first_evaluable=min(r["first_evaluable"] for r in valid),last_evaluable=max(r["last_evaluable"] for r in valid),stocks_with_multiple_segments=sum(r["segments"]>1 for r in rr),stocks_with_multiple_segments_after_2010=sum(r["after_2010_segments"]>1 for r in rr),source_missing_sessions=sum(r["source_missing_sessions"] for r in rr if r["source_missing_sessions"]!=""),source_non_sessions=sum(r["source_non_sessions"] for r in rr if r["source_non_sessions"]!=""),last_evaluable_date_counts=dict(Counter(r["last_evaluable"] for r in valid).most_common(10)),windows={k:dict(stocks=sum(r[k+"_evaluable_days"]>0 for r in rr),evaluable_days=sum(r[k+"_evaluable_days"] for r in rr),usable_bars=sum(r[k+"_usable_bars"] for r in rr),warmup_unavailable=sum(r[k+"_warmup_unavailable"] for r in rr),future_unavailable=sum(r[k+"_future_unavailable"] for r in rr),censored_up_days=sum(r[k+"_censored_up_days"] for r in rr)) for k in WINDOWS})
        summary["markets"][m]["at_least_one_contiguous_evaluable_15y_run"]=sum(r["contiguous_evaluable_span_ge_15y"] for r in rr)
        summary["markets"][m]["former_exclusions_attempted"]=sum(r["research_source_group"]=="prior_operational_exclusion_research_only" for r in rr)
    OUT.mkdir(parents=True,exist_ok=True)
    csv_write(OUT/"coverage-stocks.csv",rows)
    csv_write(OUT/"coverage-years.csv",annual_rows)
    csv_write(OUT/"coverage-chart-cache.csv",chart)
    excluded=[dict(market=r["market"],symbol=r["symbol"],exchange=r.get("exchange"),isin=r.get("isin"),reason=r.get("reason"),research_attempted=COMBINED.exists()) for r in inv.get("historical_operational_exclusions",inv["excluded"])]
    csv_write(OUT/"coverage-excluded.csv",excluded)
    (OUT/"coverage-summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
