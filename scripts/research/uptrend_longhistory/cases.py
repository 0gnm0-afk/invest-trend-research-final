"""Deterministic typical successful/unsuccessful confirmation examples.

Cases are selected nearest the lower median 21-bar terminal return within each
fixed market/condition/hit class. This is explanatory sampling after evaluation,
not a success-rate estimate, extreme best/worst selection or a trading strategy.
"""
from paths import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

KEYS = ['rmi30', 'macd_rsi40', 'cci_recovery', 'supertrend']
DOC = ROOT / 'docs/research/uptrend-longhistory-2026-10-29'


def source_file(rec):
    return Path(rec.get('cache_path', rec.get('research_cache',
        str(OLD / 'cache' / f"{rec['market']}_{rec['symbol']}.npz"))))


def price_source(rec):
    with np.load(source_file(rec), allow_pickle=False) as q:
        return {key: q[key] for key in ['date', 'open', 'high', 'low', 'close', 'full', 'segment']}


def choose():
    rr = sorted(records(), key=lambda r: (r['market'], r['symbol']))
    populations = {(m, key, hit): [] for m in ['KR', 'US'] for key in KEYS for hit in [0, 1]}
    for si, rec in enumerate(rr):
        path = OUT / 'paths' / f"{rec['market']}_{rec['symbol']}.npz"
        if not path.exists():
            continue
        with np.load(path, allow_pickle=False) as q:
            ledger = q['ledger_index']; ids = q['ids'].tolist()
        keep = np.isin(ledger[:, 0], [ids.index(key) for key in KEYS]) & (ledger[:, 3] >= 0)
        ledger = ledger[keep]
        if not len(ledger):
            continue
        z = price_source(rec)
        for key in KEYS:
            for is_hit in [0, 1]:
                ts = ledger[(ledger[:, 0] == ids.index(key)) & (ledger[:, 2] == is_hit), 1]
                returns = z['close'][ts + 21] / z['open'][ts + 1] - 1
                populations[(rec['market'], key, is_hit)].append(
                    np.column_stack([np.full(len(ts), si), ts, returns]))
        if si % 1000 == 999:
            print('case population', si + 1, '/', len(rr), flush=True)
    rows = []
    for (m, key, is_hit), parts in populations.items():
        if not parts:
            continue
        a = np.concatenate(parts); order = np.lexsort((a[:, 1], a[:, 0], a[:, 2]))
        rank = (len(order) - 1) // 2; si, t, ret = a[order[rank]]
        rec = rr[int(si)]; t = int(t); z = price_source(rec); lab = labels(z['full'], z['segment'])
        origin = int(lab['origin'][t]); entry = float(z['open'][t + 1]); pa = forward(z)
        row = dict(market=m, id=key, early_hit=is_hit, symbol=rec['symbol'],
                   stock_name=rec.get('name', rec['symbol']), signal_index=t,
                   signal_date=str(z['date'][t]), next_open_date=str(z['date'][t + 1]),
                   next_open=entry, signal_close=float(z['close'][t]),
                   label_class=int(lab['cls'][t]), age=int(lab['age'][t]),
                   duration=int(lab['duration'][t]),
                   rise_onset_to_next_open=entry / z['close'][origin] - 1 if is_hit else np.nan,
                   population_count=len(a), median_rank_1based=rank + 1,
                   selection='lower median21 terminal return; ties market-symbol/date; known label only')
        for h in HORIZONS:
            row.update({f'return{h}': float(pa[h][t, 0]),
                        f'favorable{h}': float(max(0, pa[h][t, 2])),
                        f'adverse{h}': float(max(0, -pa[h][t, 1]))})
        assert np.isclose(row['return21'], ret)
        assert bool(lab['cls'][t] == 1) == bool(is_hit)
        rows.append(row)
    DOC.mkdir(parents=True, exist_ok=True)
    result = pd.DataFrame(rows)
    result.to_csv(OUT / 'representative-cases.csv', index=False, encoding='utf-8-sig')
    result.to_csv(DOC / 'representative-cases.csv', index=False, encoding='utf-8-sig')
    return result, rr


def plots(df, rr):
    lookup = {(r['market'], r['symbol']): r for r in rr}
    classes = {0: 'other (down/flat)', 1: 'early 0-5', 2: 'late uptrend', 3: 'short rise'}
    outputs = []
    for key in KEYS:
        fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharey=False)
        for mi, market in enumerate(['KR', 'US']):
            for ci, is_hit in enumerate([1, 0]):
                ax = axes[mi, ci]
                rows = df[(df.market == market) & (df.id == key) & (df.early_hit == is_hit)]
                if rows.empty:
                    ax.axis('off'); continue
                row = rows.iloc[0]; rec = lookup[(market, row.symbol)]
                z = price_source(rec); t = int(row.signal_index); n = len(z['date'])
                same = np.flatnonzero(z['segment'] == z['segment'][t])
                lo = max(int(same[0]), t - 40); hi = min(int(same[-1]) + 1, t + 65)
                xx = np.arange(lo, hi) - (t + 1); entry = row.next_open
                ax.plot(xx, z['close'][lo:hi] / entry - 1, color='#273443', lw=1.6, label='Daily close / next open - 1')
                ax.plot(xx, np.exp(z['full'][lo:hi]) / entry - 1, color='#299c86', lw=1.5, label='Retrospective L1 trend')
                lab = labels(z['full'], z['segment'])
                for a, b in zip(lab['starts'], lab['ends']):
                    if b - a >= 10 and a <= hi and a + 5 >= lo:
                        ax.axvspan(max(lo, a) - (t + 1), min(hi, a + 6) - (t + 1), color='#7dd3bd', alpha=.22)
                ax.axvline(-1, color='#9a506b', ls='--', lw=1, label='Signal close')
                ax.axvline(0, color='#738294', ls=':', lw=1, label='Next-open reference')
                ax.axhline(0, color='#a7b0ba', lw=.8)
                ax.scatter([20], [row.return21], color='#c46b1b', s=35, zorder=4)
                status = 'early hit' if is_hit else 'early-confirmation miss'
                ax.set_title(f"{market} {row.symbol} | {status}\n{row.signal_date}; {classes[int(row.label_class)]}; 21-bar end {row.return21:+.1%}", fontsize=10)
                ax.yaxis.set_major_formatter(PercentFormatter(1))
                ax.grid(alpha=.2); ax.set_xlabel('Trading bars relative to next-open reference')
        handles, labels_ = axes[0, 0].get_legend_handles_labels()
        fig.legend(handles, labels_, loc='lower center', ncol=2, fontsize=8, bbox_to_anchor=(.5, .03))
        title={'rmi30':'RMI30','macd_rsi40':'MACD + recent RSI40','cci_recovery':'CCI recovery / falling MA20','supertrend':'Supertrend'}[key]
        fig.suptitle(f'{title}: median-return early hits and misses', fontsize=14, y=.99)
        fig.text(.5, .005, 'Each case is the lower median 21-bar terminal return in its class. Green shade: retrospective early window. Excursions are not realized profit.',
                 ha='center', fontsize=8)
        fig.tight_layout(rect=(0, .11, 1, .95))
        output = DOC / f'cases-{key}.png'; fig.savefig(output, dpi=160); plt.close(fig); outputs.append(str(output))
    write(OUT / 'cases-verification.json', dict(cases=len(df), plots=outputs,
          fixed_conditions=KEYS, selection='Lower median21 by known-label early-hit/miss; no extreme cases',
          path_basis='open[t+1], close[t+21], high/low t+1..t+h inclusive',
          code_sha256=sha(Path(__file__))))


def main():
    df, rr = choose(); plots(df, rr)
    print('Cases and figures', len(df), flush=True)


if __name__ == '__main__':
    main()
