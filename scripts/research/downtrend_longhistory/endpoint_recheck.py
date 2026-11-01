"""Reclassify existing direction-neutral prefix fits for DOWN endpoint risk.

No solver is imported or called. The previous 40-stock hash-selected sample
and its three prefix fits are reused read-only; no UP classification statistic
is an input. A scalar DOWN run classifier is reconciled with this study's code.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import csv
import hashlib
import json
import numpy as np
import study

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / 'docs/research/downtrend-longhistory-2026-10-29'
SOURCE = ROOT / 'runtime/uptrend-longhistory-20261029/endpoint-audit'
PROTOCOL = ROOT / 'docs/research/uptrend-longhistory-2026-10-29/endpoint-audit-protocol.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scalar_labels(fit, segment):
    slope = np.r_[np.diff(fit), np.nan]
    slope[np.r_[segment[1:] != segment[:-1], True]] = np.nan
    known = np.isfinite(slope) & (slope >= -1e-6)
    cls = np.full(len(fit), -1, np.int8); cls[known] = 0
    starts, ends = [], []; t = 0
    while t < len(slope):
        if not np.isfinite(slope[t]) or slope[t] >= -1e-6:
            t += 1; continue
        start = t
        while t < len(slope) and np.isfinite(slope[t]) and slope[t] < -1e-6:
            t += 1
        if start > 0 and np.isfinite(slope[start - 1]) and t < len(slope) and np.isfinite(slope[t]):
            starts.append(start); ends.append(t); known[start:t] = True
            if t - start < 10:
                cls[start:t] = 3
            else:
                cls[start:start + 6] = 1; cls[start + 6:t] = 2
    return dict(slope=slope, known=known, cls=cls, starts=np.array(starts, int), ends=np.array(ends, int))


def start_matches(prefix, final):
    candidates = sorted((abs(int(a) - int(b)), int(a), int(b))
                        for a in prefix for b in final if abs(int(a) - int(b)) <= 5)
    pa, fa, shifts = set(), set(), []
    for distance, a, b in candidates:
        if a not in pa and b not in fa:
            pa.add(a); fa.add(b); shifts.append(distance)
    return len(shifts), sum(x == 0 for x in shifts), sum(shifts)


def save_json(name, value):
    (DOC / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def save_csv(name, rows):
    with (DOC / name).open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def main():
    DOC.mkdir(parents=True, exist_ok=True)
    protocol = json.loads(PROTOCOL.read_bytes())
    up_code = ROOT / 'scripts/research/uptrend_longhistory/endpoint_audit.py'
    assert sha(up_code) == protocol['code_sha256']
    inventory_path = ROOT / 'runtime/downtrend-longhistory-20261029/inventory.json'
    inv = json.loads(inventory_path.read_bytes())
    records = {(r['market'], r['symbol']): r for r in inv['stocks']}
    selected = protocol['selected']; assert len(selected) == 40
    assert Counter(r['market'] for r in selected) == {'KR': 20, 'US': 20}
    assert Counter((r['market'], r['group']) for r in selected) == {
        ('KR', 'inherited'): 18, ('KR', 'supplemental'): 2,
        ('US', 'inherited'): 18, ('US', 'supplemental'): 2}
    protected = {str(p.relative_to(ROOT)): sha(p) for p in [PROTOCOL, up_code, inventory_path]}
    rows = []; checks = 0; cells_checked = 0; prefixes = 0
    for sample in selected:
        market, symbol = sample['market'], sample['symbol']; rec = records[market, symbol]
        source = ROOT / rec['cache_path']; source_hash = sha(source)
        assert source_hash == json.loads(source.with_suffix('.json').read_bytes())['cache_sha256']
        protected[str(source.relative_to(ROOT))] = source_hash
        with np.load(source, allow_pickle=False) as q:
            z = {key: q[key] for key in ['date', 'segment', 'full']}
        final = scalar_labels(z['full'], z['segment'])
        produced = study.labels(z['full'], z['segment'])
        for key in ['cls', 'starts', 'ends', 'known']:
            assert np.array_equal(final[key], produced[key]), (market, symbol, key)
        checks += 1; cells_checked += len(z['date'])
        for cutoff in protocol['cutoffs']:
            path = SOURCE / f'{market}_{symbol}_{cutoff}.npz'
            protected[str(path.relative_to(ROOT))] = sha(path)
            with np.load(path, allow_pickle=False) as q:
                ds, segment, fit = q['date'], q['segment'], q['prefix_fit']
            n = int((z['date'] <= cutoff).sum())
            assert len(ds) == n and np.array_equal(ds, z['date'][:n])
            assert np.array_equal(segment, z['segment'][:n])
            prefix = scalar_labels(fit, segment); produced = study.labels(fit, segment)
            for key in ['cls', 'starts', 'ends', 'known']:
                assert np.array_equal(prefix[key], produced[key]), (market, symbol, cutoff, key)
            prefixes += 1; checks += 1; cells_checked += n
            hist = np.zeros(n, bool); fut = np.zeros(n, bool)
            if n > 65: hist[65:] = segment[65:] == segment[:-65]
            if n > 126: fut[:-126] = (segment[126:] == segment[:-126]) & np.isfinite(fit[126:])
            base = (ds >= protocol['comparison_start']) & hist & np.isfinite(prefix['slope']) & np.isfinite(final['slope'][:n])
            tail = np.zeros(n, bool); tail[max(0, n - 126):] = True
            for arm, scope in [('mature', base & fut), ('last126', base & tail)]:
                pc = prefix['cls']; fc = final['cls'][:n]; common = scope & (pc >= 0) & (fc >= 0)
                ps = prefix['starts'][(prefix['ends'] - prefix['starts'] >= 10) & scope[prefix['starts']]]
                fs = final['starts'][(final['starts'] < n) & (final['ends'] - final['starts'] >= 10)]
                fs = fs[scope[fs]]; matched, exact, shifts = start_matches(ps, fs)
                row = dict(market=market, symbol=symbol, sample_group=sample['group'], cutoff=cutoff, arm=arm,
                    comparison_days=int(scope.sum()), common_known_days=int(common.sum()),
                    prefix_unknown_final_known=int((scope & (pc < 0) & (fc >= 0)).sum()),
                    prefix_known_final_unknown=int((scope & (pc >= 0) & (fc < 0)).sum()),
                    class_equal_including_unknown=int((scope & (pc == fc)).sum()),
                    class_equal_common=int((common & (pc == fc)).sum()),
                    early_equal_common=int((common & ((pc == 1) == (fc == 1))).sum()),
                    prefix_early_common=int((common & (pc == 1)).sum()), final_early_common=int((common & (fc == 1)).sum()),
                    early_both_common=int((common & (pc == 1) & (fc == 1)).sum()),
                    early_union_common=int((common & ((pc == 1) | (fc == 1))).sum()),
                    prefix_completed_starts=len(ps), final_completed_starts=len(fs),
                    starts_matched_within5=matched, starts_matched_exact=exact, matched_absolute_shift_sum=shifts,
                    source_cache_sha256=source_hash, prefix_fit_sha256=protected[str(path.relative_to(ROOT))])
                for i in [-1, 0, 1, 2, 3]:
                    for j in [-1, 0, 1, 2, 3]:
                        row[f'confusion_{i}_{j}'] = int((scope & (pc == i) & (fc == j)).sum())
                assert sum(v for k, v in row.items() if k.startswith('confusion_')) == row['comparison_days']
                rows.append(row)
    summaries = []
    non_numeric = {'market', 'symbol', 'sample_group', 'cutoff', 'arm', 'source_cache_sha256', 'prefix_fit_sha256'}
    for market in ['KR', 'US']:
        for cutoff in protocol['cutoffs']:
            for arm in ['mature', 'last126']:
                part = [r for r in rows if (r['market'], r['cutoff'], r['arm']) == (market, cutoff, arm)]
                assert len(part) == 20
                s = dict(market=market, cutoff=cutoff, arm=arm, stocks=len(part),
                         **{k: sum(r[k] for r in part) for k in rows[0] if k not in non_numeric})
                for name, numerator, denominator in [
                    ('class_agreement_including_unknown', 'class_equal_including_unknown', 'comparison_days'),
                    ('class_agreement_common', 'class_equal_common', 'common_known_days'),
                    ('early_agreement_common', 'early_equal_common', 'common_known_days'),
                    ('early_jaccard_common', 'early_both_common', 'early_union_common'),
                    ('prefix_early_retained', 'early_both_common', 'prefix_early_common'),
                    ('final_early_recovered', 'early_both_common', 'final_early_common')]:
                    s[name] = s[numerator] / s[denominator] if s[denominator] else None
                summaries.append(s)
    for rel, digest in protected.items(): assert sha(ROOT / rel) == digest, rel
    assert prefixes == 120 and checks == 160 and len(rows) == 240
    rows.sort(key=lambda r: (r['market'], r['symbol'], r['cutoff'], r['arm']))
    save_csv('endpoint-recheck.csv', rows); save_csv('endpoint-recheck-summary.csv', summaries)
    save_json('endpoint-recheck-summary.json', dict(
        source_protocol=str(PROTOCOL.relative_to(ROOT)), sample_selection=protocol['selection_rule'],
        scope='Read-only reuse of40stocks/120prefix fits; DOWN labels recalculated; no L1 solver call',
        summary=summaries, limitations=[
            'Long-history hash-selected40stocks are not representative of every listing or discontinuous history.',
            'Common-known agreement excludes censored unknown labels; explicit transition/confusion counts remain.',
            'No real-time signal uses L1; this only diagnoses retrospective evaluation label revision.']))
    save_json('endpoint-recheck-validation.json', dict(
        status='PASS', prefix_files=prefixes, source_cache_files=40, independent_scalar_vs_production_arrays=checks,
        label_cells=cells_checked, confusion_tables=240, protected_files_unchanged=len(protected),
        source_hashes=protected, code_sha256=sha(Path(__file__)), fresh_fits=0,
        finished_utc=datetime.now(timezone.utc).isoformat()))
    text = ['# 장기 하락 정답표의 종료일 민감도 재점검\n',
        '기존 상승 장기 감사에서 미리 고정한 40종목(한국20·미국20)의 가격·L1 prefix 결과를 읽기만 하고, **하락 상태를 새로 계산**했다. 상승 판정 통계를 복사하거나 L1을 다시 적합하지 않았다. 각 시장의 기존 종목18개·추가 보조 종목2개, 총120개 종료일별 추세 배열을 최종2026-09-30 배열과 비교했다.\n',
        '종료일은2015-09-30·2020-09-30·2025-09-30이다. 성숙 구간은 그 종료일 안에서 과거65봉·미래126봉이 같은 유효 구간에 있는 날짜다. 마지막126봉은 미래 완충을 일부러 적용하지 않은 비교다. 둘 다2010-10-01 이후이며 양쪽 기울기가 계산되는 날짜를 사용했다.\n',
        '|시장|종료일|성숙 공통확정일|성숙 상태 일치(미확정 포함)|성숙 초입 Jaccard|마지막126봉 상태 일치(미확정 포함)|마지막126봉 초입 Jaccard|',
        '|---|---|---:|---:|---:|---:|---:|']
    for market in ['KR', 'US']:
        for cutoff in protocol['cutoffs']:
            a = next(s for s in summaries if (s['market'], s['cutoff'], s['arm']) == (market, cutoff, 'mature'))
            b = next(s for s in summaries if (s['market'], s['cutoff'], s['arm']) == (market, cutoff, 'last126'))
            text.append(f"|{market}|{cutoff}|{a['common_known_days']:,}|{a['class_agreement_including_unknown']:.4%}|{a['early_jaccard_common']:.2%}|{b['class_agreement_including_unknown']:.2%}|{b['early_jaccard_common']:.2%}|")
    text += ['\nJaccard는 두 정답표 중 어느 한쪽에서 초입이었던 날짜의 합집합을 분모로, 양쪽 모두 초입인 날짜의 교집합을 분자로 삼는다. 평소 날짜가 많아 전체 일치율만 높아지는 문제를 보완한다. 다만 위 Jaccard는 양쪽 상태가 확정된 날짜만 비교하므로, 미완료가 나중에 확정된 날짜는 별도 항목으로 반드시 함께 보아야 한다.\n',
        '성숙 구간의 미확정→확정 변화 및 ≥10일 하락 시작점 수:\n',
        '|시장|종료일|미확정→확정 일수|prefix 시작점|최종 시작점|동일 날짜 시작점|±5봉 안 일치|',
        '|---|---|---:|---:|---:|---:|---:|']
    for s in summaries:
        if s['arm'] == 'mature':
            text.append(f"|{s['market']}|{s['cutoff']}|{s['prefix_unknown_final_known']}|{s['prefix_completed_starts']}|{s['final_completed_starts']}|{s['starts_matched_exact']}|{s['starts_matched_within5']}|")
    text += ['\n이 감사는 126봉 완충과 미완료 구간 제외를 유지할 근거를 점검한다. 40종목의 높은 일치율이 모든 종목·모든 시기에서 시작점 수정을 막는다는 보장은 아니다. 표본은2014년 말 이전부터2025년9월까지 이력이 있는 종목에 한정돼 새 상장·짧은 이력의 수정 위험을 대표하지 못한다. L1은 계속 사후 정답표이며 당시 매도 신호로 쓸 수 없다는 해석을 유지한다.\n',
        '직접 계산한 하락 분류와 본 연구 분류의160개 배열,240개 혼동표,120개 prefix의 날짜·구간을 대조했다. 원본 가격·추세 파일과 근거 파일의 전후 해시를 확인했고 변경은 없었다. `endpoint-recheck.csv`, `endpoint-recheck-summary.csv`, `endpoint-recheck-validation.json`에 상세 계산과 해시를 남겼다.\n']
    (DOC / 'endpoint-recheck.md').write_text('\n'.join(text), encoding='utf-8')
    print(json.dumps([{k: s[k] for k in ['market', 'cutoff', 'arm', 'common_known_days', 'class_agreement_including_unknown',
        'early_jaccard_common', 'prefix_unknown_final_known', 'prefix_completed_starts', 'final_completed_starts']} for s in summaries], ensure_ascii=False), flush=True)


if __name__ == '__main__': main()
