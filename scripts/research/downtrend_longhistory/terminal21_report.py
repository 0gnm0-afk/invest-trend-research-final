"""Render the terminal-return addendum from verified, saved counts."""
from pathlib import Path
import json, re, hashlib
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
DOC=ROOT/'docs/research/downtrend-terminal21-2026-10-29'
OLD=ROOT/'docs/research/downtrend-longhistory-2026-10-29'


def pct(x): return f'{100*x:.2f}%'
def ci(r): return f'{100*r.ci95_low:.2f}~{100*r.ci95_high:.2f}%'


def main():
    d=pd.read_csv(DOC/'all81-terminal21.csv')
    old=pd.read_csv(OLD/'evaluate-metrics.csv');old=old[old.period=='primary']
    annual=pd.read_csv(DOC/'annual-terminal21.csv')
    receipt=json.loads((DOC/'verification.json').read_text(encoding='utf-8'))
    text=['# 신호 이후 21거래일 기간말 하락 확률: 한국·미국 TOP5',
          '', '**기존 15년 연구의 원자료로 직접 계산했다.** 평균 수익률이나 −5% 접촉률을 대신 쓰지 않고, 다음 거래일 시가보다 21번째 거래일 종가가 낮은 사례를 셌다. 기존 81개 조건을 모두 비교했으며 새로운 신호나 임계값은 만들지 않았다.',
          '', '**한국 1위는 RSI 약세 다이버전스 58.31%, 미국 1위는 MFI80 하향 이탈 51.00%였다.** 한국에서는 과반이 낮은 가격으로 끝난 패턴이 보였지만, 미국 1위의 95% 구간도 48.16~53.82%로 50%를 포함했다. 미국에서는 이 기준만으로 높은 확신의 하락 신호를 찾았다고 보기 어렵다. 기존 MACD+RSI는 한국 55.59%(8위), 미국 48.77%(9위)였다. 이 순위는 관측된 역사적 비율이며 미래 성능이나 순위 차이의 통계적 확정이 아니다.',
          '', '## 무엇을 계산했나', '',
          '`기간말 하락 비율 = close[t+21] < open[t+1]인 신호 수 / 전체 평가 가능한 신호 수`', '',
          '신호일을 t로 두고, 다음 거래일이 1일째다. 따라서 다음 거래일 시가부터 신호 후 21번째 거래일 종가까지를 비교한다. 신호일 종가와 비교하거나, 진입일 이후 21일을 더 세어 t+22를 사용하는 계산이 아니다. 저장 가격의 원래 정밀도로 엄격한 `<`를 적용했다. 같은 가격은 보합으로 따로 세고 분모에는 남겼다.', '',
          '주 표의 신호일 범위는 **2010-10-01~2025-09-30**다. 기존 가격 경로 연구와 비교하기 위해 과거 65봉·미래 63봉의 연속성 및 당시 관측 변수의 유효성을 만족하는 공통 표본을 그대로 사용했다. 신호가 준비되지 않은 날은 제외한다. 이미 하락한 날만 고르지 않았고, 사후 L1 추세를 이 계산의 조건으로 사용하지 않았다. 공백을 넘어 거래일을 이어 세지 않는다.', '',
          '63일 관측 제한이 필요 없는 독자적인 21일 질문도 확인하기 위해, 같은 규칙에서 미래 관측만 21봉으로 줄인 결과를 보조로 계산했다. 아래 TOP5는 기존 연구와 일치하는 공통 표본 기준이며, 보조 표본의 결과도 뒤에 공개한다.', '',
          '기존 CSV에는 `positive_return`(양수 수익률 비율)이 있었지만 음수 비율은 따로 없었다. **1−양수 비율은 하락+보합 비율**이므로 이를 하락 확률로 제시할 수 없었다. 이번에는 하락·보합·상승의 합이 전체 신호 수와 정확히 일치하도록 직접 집계했다.', '']
    for market, title in [('KR','한국'),('US','미국')]:
        sub=d[d.market==market];top=sub[sub['rank']<=5]
        text += [f'## {title} TOP5', '',
                 '순위는 이 표본에서 관측된 하락 비율 순이다. 95% 구간은 종목과 공통 시기의 연관성을 반영한 **개별 비율의 불확실성**이며, 순위가 확정됐다는 뜻은 아니다.', '',
                 '| 순위 | 신호 | 하락 수 / 전체 신호 수 | 기간말 하락 비율 | 95% 구간 | 보합 수 | 평균 수익률 |',
                 '|---:|---|---:|---:|---|---:|---:|']
        for r in top.itertuples():
            text.append(f'| {r.rank} | {r.label} | {r.negative:,} / {r.signals:,} | **{pct(r.negative_rate)}** | {ci(r)} | {r.zero:,} | {100*r.mean_return:+.2f}% |')
        if market=='KR':
            text += ['', '한국에서는 과열 뒤 약화와 관련된 기존 신호들이 상위에 모였다. 다만 1위인 RSI 다이버전스조차 약 42%는 기간말 하락으로 끝나지 않았다. 1위의 평균 수익률은 −0.38%이고 나머지 TOP5는 +0.15~+0.25%로 양수였다. 하락 횟수의 과반과 매도의 경제적 이익은 같은 말이 아니다. 이 다이버전스는 미래 피벗을 확인하는 지표가 아니라, 직전 20일 종가 최고점과 당시 RSI를 비교하는 기존 일별 패턴이다.']
        else:
            text += ['', '미국에서는 1위를 제외한 TOP5도 하락 비율이 50% 미만이었고, 모두 개별 95% 구간에 50%가 포함됐다. TOP5의 평균 수익률은 모두 양수였다. 이 결과만으로 “신호가 나오면 21일 뒤 가격이 낮을 가능성이 높다”고 일반화하기 어렵다. 다만 이는 비슷한 상태의 비신호일보다 정보가 전혀 없다는 검정 결과는 아니다.']
        text += ['', '**정확한 조건과 반복 집계 방식**', '']
        for r in top.itertuples():
            repeat='조건을 만족하는 날마다 1건으로 센 기존 일별 패턴이다.' if r.kind=='daily_pattern' else '기존 신규 교차·이탈 사건을 센다.'
            formula=r.formula
            if r.id=='rsi_divergence':
                formula='직전 20일 중 종가가 가장 높은 날 j를 정하고, C[t]>C[j] 및 RSI14[t]<RSI14[j]−5를 동시에 만족한다. RSI 차이는 정확히 5가 아닌 5 초과이며, 고점 동률이면 가장 이른 날을 사용한다'
            text.append(f'- **{r.label}** (`{r.id}`): {formula}. {repeat}')
        text += ['', '| 신호 | 종목별 비율 동일가중 | 21일만 요구한 표본의 하락 비율 | 추가 평가 신호 수 | 2011~2024 연도별 범위 |',
                 '|---|---:|---:|---:|---|']
        for r in top.itertuples():
            y=annual[(annual.market==market)&(annual.id==r.id)&annual.year.between(2011,2024)]
            text.append(f'| {r.label} | {pct(r.equal_stock_negative_rate)} | {pct(r.negative_rate_21only)} | {r.signals_21only-r.signals:,} | {pct(y.negative_rate.min())}~{pct(y.negative_rate.max())} |')
        assert sub.sort_values('negative_rate_21only',ascending=False).id.tolist()[:5]==top.id.tolist()
        text += ['', '미래 관측을 21일만 요구해도 이 시장 TOP5의 구성과 순서는 같았다. 종목 동일가중 값은 원래 알림 1건당 확률과 다른 질문에 답하므로 주 순위를 대신하지 않는다.']
        text.append('')
    text += ['## 기존 MACD+RSI의 결과와 무엇이 다른가', '',
             '| 시장 | 신호 | 21일 기간말 하락 비율 | 이번 81조건 순위 | 기존 하락 초입 0~5일 적중률 | 21일 평균 수익률 |',
             '|---|---|---:|---:|---:|---:|']
    for market in ['KR','US']:
        for key in ['macd_rsi60','macd_positive','cci100_up20','rmi70']:
            r=d[(d.market==market)&(d.id==key)].iloc[0]
            o=old[(old.market==market)&(old.id==key)].iloc[0]
            text.append(f'| {market} | {r.label} | {pct(r.negative_rate)} | {int(r["rank"])} | {pct(o.precision)} | {100*r.mean_return:+.2f}% |')
    text += ['', '초입 적중률은 사후 L1로 판정한 “신호일이 하락 시작 후 0~5일이었나”이고, 이번 비율은 “다음 시가보다 21번째 종가가 낮았나”다. 질문과 평가 가능 조건이 다르다. 위 초입 수치는 기존 연구의 분류 표본(미래 126봉 등)에서 가져왔으므로 이번 가격 경로 분모와 같다고 해석하면 안 된다.', '',
             '하락이 더 자주 나타나더라도 소수의 상승 폭이 크면 평균 수익률은 양수일 수 있다. 이 때문에 평균이 낮은 순서와 하락 비율이 높은 순서는 서로 바꿔 쓸 수 없다. 또한 기간 중 −5%를 접촉한 뒤 반등해 21일 종가가 더 높아진 사례는 이번 하락 분자에 들어가지 않는다.', '',
             '## 해석과 한계', '',
             '이 결과는 기존 자료에서 **기간말 하락 횟수의 순위**를 완성한다. “하락 초입을 가장 잘 확인하는 순위”나 “매도하면 가장 이익인 순위”를 새로 확정한 결과는 아니다. 신호 후 어느 시점에든 하락할 확률, 낙폭의 크기, 매도 후 재진입·비용·배당을 반영한 전략 성과도 아니다.', '',
             'TOP5의 구간이 겹치므로 1위가 2위보다 통계적으로 우수하다고 결론 내리지 않는다. 개별 95% 구간 외에 시장별 전체 81개 비율을 한꺼번에 고려한 동시 구간도 CSV에 제공했다. 이번 순위는 이미 살펴본 전체 기간에서 사후 비교했으며 새로운 독립 검증 성과가 아니다. 50%와 비교하는 것만으로 신호의 추가 정보가 입증되지는 않는다. 해당 시장·비슷한 상태의 비신호일과의 차이는 별도의 질문이고, 기존 −5% 접촉률 비교의 유의성을 이번 음수 비율에 옮겨 붙일 수 없다.', '',
             '한국과 미국은 구분해 계산했다. 현재 확보된 저장 목록 전체를 검사했지만 역사상 모든 상장폐지 종목까지 포함한 전수 자료는 아니다. 생존 편향, 과거 가격 수정과 공백 처리의 기존 한계는 유지된다. 2010년과 2025년은 각각 10~12월, 1~9월만 포함하므로 연도별 범위 표에서는 완전한 2011~2024년만 썼다. 종목 동일가중은 해당 신호가 한 번 이상 발생한 종목의 개별 하락 비율을 같은 무게로 평균한 값이다.', '',
             '## 계산 검증과 파일', '',
             f'- 저장 목록 7,483개 중 원자료 캐시 7,293개를 재사용했고, 없는 190개를 0건 성공 또는 실패로 처리하지 않았다. 시장별 주 가격 경로 관측일은 '+', '.join(f'{r["market"]} {r["risk_days"]:,}종목·일' for r in receipt['receipts'])+'이다.',
             '- 162개 시장·조건 조합의 신호 분모와 기존 양수 수익률 건수가 모두 일치했다. 기간말 평균 수익률도 이전 집계와 수치 오차 범위에서 일치했다. 모든 종목·월·조건에서 하락+보합+상승=전체를 확인했다.',
             f'- 거래일 인덱스와 직접 가격 비교의 별도 스칼라 점검은 {receipt["scalar_checks"]:,}건이다. 신뢰구간은 종목 Poisson 가중치와 공통 월 stationary bootstrap을 교차한 1,999회 재표집으로 계산했다. 평균 3·6개월 블록 각각의 구간 중 넓은 경계를 표시한다. 신호일 중첩과 같은 시장 시기 의존성을 무시한 단순 이항 구간을 쓰지 않았다.',
             '- 기존 원자료·신호 산식·연구 결과는 수정하지 않았다. 재계산 코드는 `scripts/research/downtrend_longhistory/terminal21.py`, 문서 생성은 `terminal21_report.py`다.', '',
             '- [전체 81조건 × 한국·미국 CSV](downtrend-terminal21-2026-10-29/all81-terminal21.csv)',
             '- [TOP5 CSV](downtrend-terminal21-2026-10-29/top5-terminal21.csv)',
             '- [연도별 건수와 비율 CSV](downtrend-terminal21-2026-10-29/annual-terminal21.csv)',
             '- [검증 기록](downtrend-terminal21-2026-10-29/verification.json)',
             '- [기존 15년 연구](downtrend-longhistory-2026-10-29.md)', '',
             'CSV의 비율은 0~1 단위다. `negative/zero/positive`는 각각 하락/보합/상승 건수, `signals`는 기존 63일 공통 표본 분모다. `signals_21only`·`negative_21only`·`negative_rate_21only`는 미래 21일만 요구한 보조 표본이다. `ci95_*`는 개별 구간, `simultaneous81_*`는 시장별 81비율 동시 구간이다. 후자는 순위 차이의 구간이 아니다.', '']
    report=DOC.with_suffix('.md');report.write_text('\n'.join(text),encoding='utf-8')
    # Artifact and arithmetic checks, independent of the aggregation producer.
    assert len(d)==162 and set(d.market)=={'KR','US'}
    assert (d.negative+d.zero+d.positive==d.signals).all()
    assert abs(d.negative/d.signals-d.negative_rate).max()<1e-14
    for market,g in d.groupby('market'):
        assert g.id.nunique()==81 and len(g[g['rank']<=5])==5
        assert g.sort_values('negative_rate',ascending=False).id.tolist()[:5]==g[g['rank']<=5].id.tolist()
    for link in re.findall(r'\]\(([^)]+)\)',report.read_text(encoding='utf-8')):
        assert (report.parent/link).exists(),link
    protected=json.loads((ROOT/'runtime/downtrend-longhistory-20261029/frozen-protocol.json').read_bytes())
    for p,sha in protected['original_reports_and_sources'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha,p
    (DOC/'report-verification.json').write_text(json.dumps(dict(status='PASS',rows=162,
        protected_prior_files=len(protected['original_reports_and_sources']),
        report_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),
        csv_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in DOC.glob('*.csv')}),indent=2),encoding='utf-8')
    print('report and verification PASS')


if __name__=='__main__':main()
