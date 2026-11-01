"""Readable Korean long-history report, assembled only from completed result tables.

No selection, fitting, optimization, or new signal logic belongs in this file.
The fixed eighteen focal rules are shown regardless of their long-window result.
"""
from pathlib import Path
import json
import argparse
import numpy as np
import pandas as pd
from study import ROOT, OUT
import figures

DOC=ROOT/'docs/research/downtrend-longhistory-2026-10-29'
REPORT=DOC.with_suffix('.md')
FOCAL=figures.FOCAL
SMALL=['rmi70','psar','stochrsi80','macd_rsi60','macd_positive','cci100_up20']
MARKET={'KR':'한국','US':'미국'}


def pct(x,d=1):return f'{100*x:.{d}f}' if pd.notna(x) and np.isfinite(x) else '평가 불가'
def number(x):return f'{int(x):,}' if pd.notna(x) and np.isfinite(x) else '평가 불가'
def value(x,d=2):return f'{x:.{d}f}' if pd.notna(x) and np.isfinite(x) else '평가 불가'
def signed(x,d=2):return f'{100*x:+.{d}f}' if pd.notna(x) and np.isfinite(x) else '평가 불가'
def esc(x):return str(x).replace('|',' / ').replace('\n',' ')
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(esc(x) for x in row)+' |' for row in rows])+'\n'
def link(name,label=None):return f'[{label or name}](downtrend-longhistory-2026-10-29/{name})'
def image(name,alt):return f'\n![{alt}](downtrend-longhistory-2026-10-29/{name}.png)\n'
def read(name):
    path=OUT/(name+'.csv')
    if not path.exists():raise FileNotFoundError(f'Final result required before report: {path}')
    return pd.read_csv(path,keep_default_na=False,na_values=[''])
def interval(lo,hi,percent=True):
    f=pct if percent else value
    return f'[{f(lo)}, {f(hi)}]'


def load_results():
    raw=read('evaluate-metrics')
    primary=raw[raw.period=='primary'].copy()
    assert len(primary)==162 and not primary.duplicated(['market','id']).any()
    base=read('base-rates')
    b=base.groupby(['market','id','state'],as_index=False).agg(
        base_rate=('base_rate','first'),difference=('difference','first'),lift=('lift','first'),
        precision_low=('precision_low','min'),precision_high=('precision_high','max'),
        sim_low=('difference_sim_low','min'),sim_high=('difference_sim_high','max'),adjusted_p=('adjusted_p','max'))
    e=b[b.state=='early0_5'].rename(columns={'base_rate':'early_base'})
    primary=primary.merge(e[['market','id','early_base','precision_low','precision_high','lift']],on=['market','id'],validate='one_to_one')
    ci=read('classification-intervals').groupby(['market','id','metric'],as_index=False).agg(
        low=('low','min'),high=('high','max'),sim_low=('sim_low','min'),sim_high=('sim_high','max'),adjusted_p=('adjusted_p','max'))
    cap=ci[ci.metric=='capture'].rename(columns={'low':'capture_low','high':'capture_high'})
    primary=primary.merge(cap[['market','id','capture_low','capture_high']],on=['market','id'],validate='one_to_one')
    risk=read('matched-paths').groupby(['market','id','scheme','horizon','outcome'],as_index=False).agg(
        all_signals=('all_signals','first'),matched_signals=('matched_signals','first'),support=('support','first'),
        signal=('signal','first'),control=('control','first'),difference=('difference','first'),
        sim_low=('sim_low','min'),sim_high=('sim_high','max'),adjusted_p=('adjusted_p','max'))
    balance=read('balance')
    balance['abs_smd']=balance.standardized_difference.abs()
    bal=balance.groupby(['market','id','scheme'],as_index=False).agg(max_abs_smd=('abs_smd','max'),control_effective_n=('control_effective_n','first'))
    risk=risk.merge(bal,on=['market','id','scheme'],validate='many_to_one')
    paired=read('paired-benchmarks').groupby(['market','id','benchmark','metric'],as_index=False).agg(
        difference=('difference','first'),sim_low=('sim_low','min'),sim_high=('sim_high','max'),adjusted_p=('adjusted_p','max'))
    return dict(raw=raw,primary=primary,base=b,ci=ci,risk=risk,paired=paired,balance=balance,
        eras=read('classification-eras'),yearly=read('classification-yearly'),equal=read('equal-stock'),
        sensitivity=read('evaluate-sensitivity'),duration=read('evaluate-duration'),paths=read('path-distributions'),
        all_paths=read('all81-path-summary'),coverage=json.loads((DOC/'coverage-summary.json').read_bytes()))


def label_map():
    return {r.id:r.label for r in read('KR-signal-definitions').itertuples()}


def rmi_conclusion(data,names):
    p=data['primary'].set_index(['market','id']);pair=data['paired'];out=[]
    for m in ['KR','US']:
        r=p.loc[(m,'rmi70')];b=p.loc[(m,'macd_rsi60')];c=p.loc[(m,'cci100_up20')]
        q=pair[(pair.market==m)&(pair.id=='rmi70')&(pair.benchmark=='macd_rsi60')&(pair.metric=='precision')].iloc[0]
        if q.sim_high<0:assessment='RMI70의 적중률이 더 낮다는 차이는 이번 다중비교 보정 후에도 남았다.'
        elif q.sim_low>0:assessment='RMI70의 적중률이 더 높다는 차이는 이번 다중비교 보정 후에도 남았다. 포착·지연의 대가도 함께 보아야 한다.'
        else:assessment='차이 구간이 0을 포함해, 적중률의 확실한 우열까지는 결론 내리기 어렵다.'
        out.append(f"- **{MARKET[m]}:** RMI70 적중률 **{pct(r.precision)}%**, 포착률 {pct(r.capture)}%, 성공한 첫 확인까지 {value(r.mean_delay)}일이다. 기존 MACD+RSI는 **{pct(b.precision)}%**, {pct(b.capture)}%, {value(b.mean_delay)}일이었다. 적중률 차이는 {signed(q.difference)}%p, 동시 보정95% 구간 [{signed(q.sim_low)}, {signed(q.sim_high)}]%p다. {assessment} 기존 CCI100·상승 MA20은 적중률 {pct(c.precision)}%로 하락의 {pct(c.capture)}%를 평균 {value(c.mean_delay)}일에 포착했다.")
    return '\n'.join(out)+'\n'


def main(make_figures=True):
    DOC.mkdir(parents=True,exist_ok=True)
    d=load_results();p=d['primary'];names=label_map();cov=d['coverage'];base=d['base'];risk=d['risk']
    for m in ['KR','US']:
        assert len(p[p.market==m])==81 and set(FOCAL)<=set(p[p.market==m].id)
    if make_figures:figures.generate(p,d['eras'],risk)
    text=['# 한국·미국 전체 저장 종목으로 다시 본 하락 초입 확인: 15년 주 분석과 최초 이력 분석\n',
      'DOWNTREND-LONGHISTORY-20261029 · 기존 정의·조건 유지 · 새로운 최적화 없음\n',
      '**주 분석을 2010-10-01~2025-09-30의 15년으로 넓혀 다시 계산했다.** 15년 이력이 없는 종목도 탈락시키지 않고 이 창 안의 최초 평가 가능일부터 포함했다. 또한 **전체 이력 보조 분석에서는 종목별 가장 이른 평가 가능일부터** 계산해,2010년 이전의 자료와 주 분석 뒤의 성숙 구간도 사용했다. 여기서 백테스트는 “신호 발생 후 실제로 이미 시작된 하락의 초입이었는가”와 이후 가격경로의 역사적 검증이다. 매도·재진입·비용을 정한 실행 전략의 수익률 검증은 아니다.\n',
      rmi_conclusion(d,names)]
    interpretation=DOC/'interpretation.md'
    if interpretation.exists():text.append(interpretation.read_text(encoding='utf-8'))
    if (DOC/'interpretation-classification.md').exists():
        text.append('신규12조건 각각의 역할, 기존2.5년 결과와의 차이, 기간·종목 가중치에 따른 변화는 '+link('interpretation-classification.md','분류 결과 상세 해설')+'에서 이어서 볼 수 있다.\n')
    text.append('용어가 낯설다면 '+link('reading-guide.md','쉬운 뜻 → 비유 → 실제 수치로 읽는 통계 안내')+'를 함께 읽으면 된다.\n')
    text.append('이 비교는 “평소보다 초입에 집중되는가”, “알림을 받았을 때 실제 초입일 가능성이 높은가”, “얼마나 늦고 얼마나 놓치는가”를 함께 읽어야 한다. 아래 모든 주요 표는 고정한 신규12·기존6조건을 그대로 공개하며, 전체81조건은 마지막 부록과 CSV에 남겼다. 긴 역사를 다시 사용해도 이미 살펴본 기간과 과거 후보 선정의 영향은 남는다. **새로운 독립 검증 표본이라고 부르지 않는다.**\n')

    text.append('\n## 1. 정말 15년인가, 정말 전체 종목인가\n')
    rows=[]
    for m,v in cov['markets'].items():
        rows.append([MARKET[m],number(v['inventory']),number(v['status_counts']['ok']),number(v['windows']['fifteen']['stocks']),number(v['source_span_ge_15y']),number(v['evaluable_span_ge_15y']),number(v['at_least_one_contiguous_evaluable_15y_run'])])
    text.append(table(['시장','점검한 전체 목록','가격 계산 가능','주15년 평가 종목','가격 첫~끝 ≥15년','평가 첫~끝 ≥15년','연속 평가 ≥15년'],rows))
    text.append('전체 목록은 **7,483개**, 가격·L1 공용 계산이 가능한 것은 **7,293개**다. 가격 계산 가능과 실제 신호 평가 가능은 다르다. 오래된 상장 종목만 남기는15년 필터는 사용하지 않았다. 공통 평가에도 과거65봉·미래126봉·완료된 추세 경계가 필요하고, 지표별 준비 기간이 더해지면 각 분모는 추가로 줄어든다. “처음과 마지막 날짜가15년 떨어졌다”는 사실과 “빠진 날 없이15년 평가했다”는 사실도 구별했다.\n')
    rows=[]
    for m,v in cov['markets'].items():
        rows.append([MARKET[m],v['source_first'],v['source_last'],v['first_evaluable'],v['last_evaluable'],number(v['windows']['fifteen']['evaluable_days']),number(v['windows']['all']['evaluable_days'])])
    text.append(table(['시장','최초 저장 가격','가격 상한','최초 평가일','최종 성숙 평가일','15년 공통 평가일 수','최초 이력 공통 평가일 수'],rows))
    text.append('일 수는 종목별 거래일을 합친 값이다. 주15년 창은 종목 간 비교와 세 개5년 구간을 고정하기 위해 사용했다. 그 뒤까지 확보된 성숙 이력은 `period=all` 보조 결과에 포함했다. 신호를 계산할 때2010년에서 지표를 초기화하지 않고, 그 이전 저장 자료도 준비 기간으로 사용했다.\n')
    rows=[]
    for m,v in cov['markets'].items():
        for reason,n in v['status_counts'].items():
            if reason!='ok':rows.append([MARKET[m],{'too_short':'가격 이력 부족','no_long_segment':'유효한 연속 구간 부족','empty':'빈 자료'}.get(reason,reason),number(n)])
    text.append(table(['시장','가격 계산 제외 사유','종목 수'],rows))
    text.append('저장된 운영 제외57종목도 연구용으로 시도해 데이터 유무를 남겼다. **BP·NVO·TSM은 저장된 차트 이력이2016년부터여서 그 시점부터 사용했다.** 이는 상장일이2016년이라는 뜻이 아니다. 실제 확보 범위와 종목별 제외 사유는 '+link('coverage-stocks.csv')+'·'+link('coverage-excluded.csv')+'에 있다.\n')
    text.append('“전체”는 보유한 현재·저장 종목 목록 전체라는 뜻이다. 역사상 상장폐지된 모든 주식을 복원한 무편향 상장 종목 전수는 아니다. 과거 한국 공급자 날짜와 거래달력 차이, 미국 이력 공백, 가격·거래량 수정 기준의 한계를 보존했고 공백을 임의로 메우지 않았다. 자료의 시작이 곧 균일한 품질의 시작이라는 뜻도 아니다.\n')
    text.append(image('report-coverage','연도별 확보 종목과 공통 평가 가능 종목 수'))
    text.append('회색과 청록선의 차이는 저장 자료가 있어도 평가에 못 쓰는 부분이다. 오래된 시기에 종목 수가 적으므로 전체기간 평균이 모든 시기에서 같은 정도로 뒷받침된다고 해석하지 않는다.\n')

    text.append('\n## 2. 유지한 하락 정의와 발생 시점\n')
    text.append('로그종가 L1 추세의 목적함수는 `0.5×Σ(log C−x)² + 1×Σ|Δ²x|`다. `x[t+1]−x[t] < −0.000001`이면 하락, `> +0.000001`이면 상승, 두 경계를 포함한 사이는 횡보다.20거래일 가격변화 경계는 약 **−0.00199998% / +0.00200002%**다. 미래 자료까지 본 L1은 평가용 정답표이며 신호 조건과 위험 비교 표본에는 넣지 않는다.\n')
    text.append('양쪽 경계가 관측된 완료 하락 중 **10거래일 이상**을 주 대상으로 했다. 첫 음의 기울기 구간의 왼쪽 날짜가 시작 당일이며, **0~5일은 당일 포함 총6일**이다. 시작 전 신호도 전체 분모에 남고 성공으로 세지 않는다. 미완료 추세나 관측 부족을 실패·짧은 하락으로 위장하지 않는다. 횡보·가격 공백을 넘어 하락 구간을 이어 붙이지 않는다.\n')
    text.append('신규 교차·이탈·반전은 발생 사건을 센다. 기존63개 중 갭·음봉 장악·긴 위꼬리·ATR급락과 거래량·RSI 다이버전스의5개 패턴은 원래 정의대로 조건을 만족한 날마다 센다. 같은 조건이 계속 유지된 경우와 새로운 교차를 혼동하지 않도록 `kind`를 함께 공개했다. 후속 확인 조건의 신호일은 모든 조건을 그날까지 확인한 날이며 첫 신호일로 소급하지 않는다.\n')
    defs=read('KR-signal-definitions').set_index('id')
    text.append(table(['고정한 주요 신호','정확한 산식·발생 조건'],[[names[k],defs.loc[k,'formula']] for k in FOCAL]))
    text.append('표의 기존 조건 약어를 풀면, `macd_signal`은 `EMA12(종가)−EMA26(종가)`가 자기 `EMA9`를 신규 하향 교차한 날이다. **MACD+RSI60은 그 교차가 오늘 발생하면서 Wilder RSI14의60 하향 이탈이 오늘·어제·그제 중 한번 발생한 경우**다. 양수 MACD는 같은 교차일에 MACD>0을 요구한다. `cci100`은 대표가격 `(고가+저가+종가)/3`의20일 평균 대비 차이를 `0.015×20일 평균절대편차`로 나눈 CCI20이100을 신규 하향 이탈한 경우다. CCI·상승20일선 조건은 여기에 `SMA20[t]>SMA20[t−5]`를 함께 요구한다.\n')
    text.append('분기 VWAP는 일봉 대표가격과 거래량으로 만든 대용치이며 실제 체결 VWAP가 아니다. 프랙탈 저점은 오른쪽 두 봉이 완료된 뒤에만 알려진 것으로 처리했다.81개 전체 조건은 '+link('KR-signal-definitions.csv','한국 정의')+'·'+link('US-signal-definitions.csv','미국 정의')+'에 있다.\n')

    text.append('\n## 3. 15년 주 결과: 모든 신호에서 출발한 적중률\n')
    text.append('적중률 = 초입에 발생한 신호 / 평가 가능한 모든 신호. 포착률 = 초입 신호가 한 번이라도 있었던 하락 구간 / 초입6일 전체를 평가할 수 있었던 하락 구간. 기저율 = 해당 지표의 평가 가능 거래일 중 초입일 비율이다. 대괄호는 종목·공통 시기의 의존성을 반영한 **주변95% 구간**이며, 직접 차이에 대한 다중비교 보정 구간과 구별한다.\n')
    for m in ['KR','US']:
        q=figures.ordered(p,m);text.append(f'\n### {MARKET[m]}\n')
        text.append(table(['신호','전체 신호 수','초입 적중률 % [95%]','기저율 %','기저율 대비','포착률 %'],[[names[r.id],number(r.signals),f'{pct(r.precision)} {interval(r.precision_low,r.precision_high)}',pct(r.early_base),value(r.lift)+'배',pct(r.capture)] for r in q.itertuples()]))
        text.append(image('report-'+m+'-tradeoff',MARKET[m]+' 주요18조건 적중률과 포착률'))
        text.append('작은 주황선보다 높으면 해당 표본의 초입 기저율보다 알림 적중률이 높다. 그러나 “기저율보다 높다”와 “대부분의 알림을 믿어도 된다”는 다르다. 오른쪽 포착률과 아래 지연·빈도를 같이 봐야 한다.95% 구간끼리 겹치는지만으로 두 신호 차이의 유의성을 판단하지 않는다.\n')
        text.append(table(['신호','놓친 하락 %','첫 성공 지연(일)','252평가일당 횟수','확인까지 이미 하락 %','늦은 신호 비중 %'],[[names[r.id],pct(1-r.capture),value(r.mean_delay),value(r.annual),pct(r.first_drop),pct(r.late/r.signals)] for r in q.itertuples()]))
    text.append('첫 확인 지연과 이미 내린 폭은 **초입 확인에 성공한 하락 구간의 첫 신호**에만 해당한다. 이미 내린 폭은 `1−신호 다음 연속 유효 시가/사후 시작일 종가`다. 당시 고점에서 팔 수 있었다는 뜻이 아니며, 놓친 사례까지 평균 지연에 포함된 것도 아니다.\n')
    text.append(image('report-timing','확인 속도·적중률·포착률 관계'))
    text.append('왼쪽일수록 빠르고 위일수록 정확하며 큰 점일수록 많은 하락을 포착했다. 하나의 축만 좋은 지표를 전체적으로 우수하다고 판단하지 않는다.\n')
    pairs=d['paired'];rows=[]
    for m in ['KR','US']:
        for key,bench in [('rmi70','macd_rsi60'),('psar','cci100_up20'),('stochrsi80','cci100_up20')]:
            for met in ['precision','capture']:
                r=pairs[(pairs.market==m)&(pairs.id==key)&(pairs.benchmark==bench)&(pairs.metric==met)].iloc[0]
                rows.append([MARKET[m],names[key]+' − '+names[bench],{'precision':'적중률','capture':'포착률'}[met],signed(r.difference),f'[{signed(r.sim_low)}, {signed(r.sim_high)}]',value(r.adjusted_p,4)])
    text.append(table(['시장','고정 직접 비교','항목','차이 %p','동시 보정95% 구간 %p','보정 p'],rows))
    text.append('신규12개와 기존6개를 두 시장에서 비교한288개 대비 전체를 함께 보정했다. 양수는 앞 지표가 더 높다는 뜻이며, 포착률의 증가는 적중률 하락을 자동으로 상쇄하지 않는다. 전체 비교는 '+link('paired-benchmarks.csv')+'에 있다.\n')

    text.append('\n## 4. 평소에도 흔한가, 초입에 집중되는가\n')
    rows=[]
    for m in ['KR','US']:
        for r in figures.ordered(p,m).itertuples():
            rows.append([MARKET[m],names[r.id],pct(r.ordinary_rate),pct(r.early_rate),pct(r.late_rate),signed(r.rate_difference),value(r.rate_ratio)+'배'])
    text.append(table(['시장','신호','상승·횡보 발생 %','초입 발생 %','중후반 발생 %','초입−평소 %p','초입/평소'],rows))
    text.append('모든 발생률은 **해당 상태의 평가 가능일 하루 단위**다.6일 창에서 한번이라도 발생할 확률과 평소 하루 발생률을 비교하지 않았다. 빈도 차이의 동시 보정 구간과 검정은 '+link('classification-intervals.csv')+'의 `rate_difference` 행에서 볼 수 있다.\n')
    for m in ['KR','US']:text.append(image('report-'+m+'-frequency',MARKET[m]+' 평소·초입·중후반의 일별 발생률'))
    text.append('경보기가 요리할 때도 울리는지 보는 것이 평소 발생률이다. 실제 불이 났을 때 얼마나 울렸는지는 포착률이고, 울렸을 때 실제 불인 비율은 적중률이다. 이 셋은 서로 대신할 수 없다.\n')
    rows=[]
    for m in ['KR','US']:
        for r in figures.ordered(p,m).itertuples():
            rows.append([MARKET[m],names[r.id],pct(r.context_precision),pct(r.context_baseline),signed(r.context_difference),pct(r.context_support)])
    text.append(table(['시장','신호','상태 비교 신호일 초입 %','비신호일 초입 %','차이 %p','비교 유지 %'],rows))
    text.append('이 보조 비교는 동일 종목·같은 달·당시 MA20의 상승 여부·가격 위치·RSI60 상태를 맞췄다. 결과를 보고 하락 중이었던 날만 고른 비교가 아니다. 관측 상태를 거칠게 맞춘 기술통계이므로 남은 연속 상태 차이와 뉴스 등 미관측 차이는 남는다. 더 엄격한 이후 위험 비교는 다음 절에서 따로 평가했다.\n')

    text.append('\n## 5. 하락 초입과 하락 기간 전체는 다른 질문이다\n')
    rows=[]
    for m in ['KR','US']:
        for r in figures.ordered(p,m).itertuples():
            w=base[(base.market==m)&(base.id==r.id)&(base.state=='whole_down_ge10')].iloc[0]
            rows.append([MARKET[m],names[r.id],pct(r.precision),pct((r.early+r.late)/r.signals),pct(w.base_rate),pct(r.late/r.signals),pct(r.short/r.signals),pct(r.other/r.signals)])
    text.append(table(['시장','신호','초입 적중 %','≥10일 하락 전체 %','전체 하락 기저율 %','늦은 확인 %','짧은 하락 %','그 밖 %'],rows))
    text.append('초입+늦은 확인=완료된 ≥10일 하락 전체다. 초입+늦은 확인+짧은 하락+그 밖은100%다. 시작 전5일 발생은 “그 밖”의 일부로 남는다. 당일과1~5일, 전체 하락과 짧은 하락까지 포함한 상태의 별도 수치는 '+link('evaluate-metrics.csv')+'·'+link('base-rates.csv')+'에 있다. 전체 하락 상태를 잘 분류하는 지표가 초입도 잘 잡는다고 바꾸어 말하지 않는다.\n')
    text.append(table(['시장','주요 신호','시작 당일 %','시작 후1~5일 %','시작 전5일 %'],[[MARKET[r.market],names[r.id],pct(r.day0/r.signals),pct(r.day1_5/r.signals),pct(r.before5/r.signals)] for r in p[p.id.isin(SMALL)].itertuples()]))
    text.append('이 표의 분모도 모든 평가 가능한 신호다. 앞 두 열만 초입 성공에 더하고, 시작 전5일 열은 실패 분류에 남긴다. 미리 경고하는 능력을 이번 목적의 성공으로 바꾸지 않았다.\n')

    text.append('\n## 6. 신호 뒤 가격 경로와 비슷한 비신호일의 추가 하락 위험\n')
    paths=d['paths'];rows=[]
    for m in ['KR','US']:
        for key in FOCAL:
            q=paths[(paths.market==m)&(paths.id==key)&(paths.population=='all')&(paths.horizon==21)].set_index('outcome')
            rows.append([MARKET[m],names[key],number(q.loc['return','n']),pct(q.loc['loss05','mean']),pct(q.loc['gain05','mean']),pct(q.loc['adverse','mean']),signed(q.loc['return','mean']),signed(q.loc['return','median'])])
    text.append(table(['시장','신호','전체 경로 신호 수','−5% 접촉 %','+5% 접촉 %','최대 추가하락 평균 %','21일 종가 평균 %','중앙값 %'],rows))
    text.append('기준은 **신호 다음 연속 유효 거래일 시가**다. 그날을1번째 봉으로5·21·63개 봉의 고저가와 마지막 종가를 본다. 같은 경로가 상승·하락 양쪽에 닿을 수 있다. 최대 추가하락·반등은 경로의 범위이며 실제 확보 수익이나 회피 손실이 아니다. 전체81조건 경로는 '+link('all81-path-summary.csv')+', 주요18조건의10·50·90백분위와5/63일 결과는 '+link('path-distributions.csv')+'에 있다.\n')
    rows=[]
    for m in ['KR','US']:
        for key in ['rmi70','macd_rsi60','cci100_up20']:
            q=paths[(paths.market==m)&(paths.id==key)&(paths.population=='early_hit')&(paths.horizon==21)].set_index('outcome')
            rows.append([MARKET[m],names[key],number(q.loc['return','n']),pct(q.loc['loss05','mean']),pct(q.loc['gain05','mean']),signed(q.loc['return','median'])])
    text.append('\n사후 초입 확인에 성공한 신호만 따로 보면:\n')
    text.append(table(['시장','신호','성공 경로 수','−5% 접촉 %','+5% 접촉 %','21일 종가 중앙값 %'],rows))
    text.append('이 하위표는 성공한 사례를 설명한다. 신호 당시에는 성공 여부를 몰랐으므로, 실제 알림의 이후 정보는 전체 신호와 비신호일 비교에서 판단해야 한다. 경로 표본에는65봉 과거·63봉 미래와 관측 상태를 요구하고, 성공 진단에만 분류용126봉 조건을 추가한다. 서로 다른 분모를 섞지 않았다.\n')
    drop_rows=[]
    for m in ['KR','US']:
        for key in ['rmi70','macd_rsi60','cci100_up20']:
            z=paths[(paths.market==m)&(paths.id==key)&(paths.horizon==0)]
            if len(z):
                r=z.iloc[0]
                drop_rows.append([MARKET[m],names[key],number(r.n),pct(r['mean']),pct(r['median']),pct(r.q10),pct(r.q90)])
    if drop_rows:
        text.append(table(['시장','신호','성공 신호 수','이미 하락 평균 %','중앙값 %','10백분위 %','90백분위 %'],drop_rows))
        text.append('이 분포는 경로 표본에서 초입 확인에 성공한 모든 신호의 다음 시가와 사후 시작일 종가를 비교한다. 앞 절의 “하락 구간별 첫 확인” 평균과 표본·집계 단위가 다르다. 평균만 보면 큰 낙폭의 영향을 받을 수 있어 중앙값과 분포를 함께 제시했다. 음수는 다음 시가가 시작일 종가보다 높았다는 뜻이다.\n')
    rows=[]
    q=risk[(risk.scheme==3)&(risk.horizon==21)&(risk.outcome=='loss05')]
    for m in ['KR','US']:
        for r in q[q.market==m].set_index('id').loc[FOCAL].reset_index().itertuples():
            rows.append([MARKET[m],names[r.id],number(r.matched_signals),pct(r.support),pct(r.signal),pct(r.control),f'{signed(r.difference)} [{signed(r.sim_low)}, {signed(r.sim_high)}]',value(r.max_abs_smd),number(r.control_effective_n)])
    text.append(table(['시장','신호','비교 가능 신호','전체 중 유지 %','신호 −5%접촉 %','비신호 %','차이 %p [보정95%]','잔여 SMD 최대','대조 유효수'],rows))
    text.append('동일 종목·같은 분기에서 MA/RSI 상태, ATR/가격, 당일·5일·20일 수익률, MA20과 거리를 사전에 정한 구간으로 맞춘 가장 엄격한 비교(scheme3)다. **사후 L1 상태나 미래 지속기간으로 표본을 제한하지 않았다.** 같은 분기의 비신호일은 신호 전후 모두 가능하므로 인과효과나 실시간 대조군 선택 절차로 해석하지 않는다.\n')
    text.append('유지율은 비교할 비신호일이 남은 신호의 비율이다. SMD는 맞춘 뒤에도 남은 관측 상태의 차이이고, 대조 유효수는 같은 대조일을 반복 사용한 정도를 반영한다. 유지율이 낮고 잔여 차이가 크면 전체 알림으로 일반화하기 어렵다. 구간이0 위에 있더라도 기업 뉴스·실적 등 관측하지 않은 차이는 남는다.\n')
    for m in ['KR','US']:text.append(image('report-'+m+'-risk',MARKET[m]+' 비슷한 비신호일 대비 5·21·63일 추가하락 접촉 차이'))
    text.append('세 패널은 같은 기준 시가에서5·21·63일을 비교한다.0을 가로지르는 구간은 그 비교에서 차이가 불확실하다는 뜻이며, 추가 정보가 없다고 입증한 것은 아니다. 느슨한 비교부터 엄격한 비교까지 scheme0~3 전체는 '+link('matched-paths.csv')+'·'+link('balance.csv')+'에 있다.\n')
    text.append('장기 자료에서 달라진 MACD의 근거, 신규12조건 각각의 위험 정보, 잔여 상태 차이·시기별 변화·양수인 평균 수익률까지 연결한 설명은 '+link('interpretation-paths.md','가격 경로 상세 해설')+'에서 확인할 수 있다.\n')

    text.append('\n## 7. 기존 후속 확인 조건은 무엇을 얻고 무엇을 잃었는가\n')
    rows=[]
    for m in ['KR','US']:
        pp=p[p.market==m].set_index('id')
        for bkey in ['macd_rsi60','macd_positive']:
            b=pp.loc[bkey]
            for tag,label in [('and20','같은 날 20일선 아래'),('then20','이후5일 안에 20일선 이탈'),('persist3','약화3일 지속 확인')]:
                r=pp.loc[bkey+'__'+tag]
                rows.append([MARKET[m],names[bkey],label,pct(r.precision),signed(r.precision-b.precision),pct(r.capture),signed(r.capture-b.capture),value(r.mean_delay),value(r.mean_delay-b.mean_delay)])
    text.append(table(['시장','기준 신호','기존 추가 확인','적중 %','기준 대비 %p','포착 %','기준 대비 %p','성공 지연(일)','지연 차이(일)'],rows))
    text.append('이6조건은 이번 장기 결과를 보고 새로 만든 조합이 아니다. 동시 조건은 그날, 순서·지속 조건은 실제로 두 번째 조건 또는 지속을 확인한 날에 신호를 기록한다. 확인 속도의 차이는 서로 포착한 하락 집합이 달라서 생기는 효과도 포함하므로 동일 하락에서의 순수 추가 대기시간이라고 단정하지 않는다.\n')

    text.append('\n## 8. 장기 평균은 시기·종목·하락 길이에 따라 달라지는가\n')
    for m in ['KR','US']:text.append(image('report-'+m+'-eras',MARKET[m]+' 세 개5년 구간의 적중률과 포착률'))
    text.append('각 칸의 숫자를 가로로 읽으면 같은 조건의 시기별 변화가 보인다. 짙은 색 하나를 골라 새 기준을 만들지 않았다. 시기별 기저율·종목 수와 함께 봐야 하며, 구간별 값에 전체기간 신뢰구간을 붙이지 않는다. 자세한 기저율·포착·지연은 '+link('classification-eras.csv')+'·'+link('classification-yearly.csv')+'에 있다.\n')
    rows=[]
    eq=d['equal'].set_index(['market','id'])
    for m in ['KR','US']:
        for key in SMALL:
            r=p[(p.market==m)&(p.id==key)].iloc[0];e=eq.loc[(m,key)]
            rows.append([MARKET[m],names[key],pct(r.precision),pct(e.early_precision),pct(e.early_base_equal_signal_stocks),number(e.stocks_with_signals)])
    text.append(table(['시장','신호','신호 건수 가중 적중 %','종목 동일가중 적중 %','같은 종목 기저율 %','신호 발생 종목 수'],rows))
    text.append('동일가중은 알림이 많은 몇 종목이 결과를 끌고 가는지 확인한다. 알림이 없는 종목의 적중률을0으로 넣지 않고, 신호가 있었던 종목의 적중률을 하나씩 같은 무게로 평균했다. 비교 기저율도 같은 종목으로 맞췄다.\n')
    rows=[]
    dur=d['duration'];dur=dur[(dur.period=='primary')&(dur.duration!='all')&dur.id.isin(['rmi70','macd_rsi60','cci100_up20'])]
    for r in dur.itertuples():rows.append([MARKET[r.market],names[r.id],r.duration,number(r.episodes),pct(r.capture),value(r.mean_delay),pct(r.first_drop)])
    text.append(table(['시장','신호','사후 지속기간','하락 수','포착 %','첫 성공 지연','이미 하락 %'],rows))
    text.append('이 구분은 오래 이어지는 하락을 특히 놓쳤는지 보는 사후 보조 분석이다. 신호 당시 앞으로10일·60일 이상 이어질지 알아냈다는 뜻은 아니다.\n')
    sens=d['sensitivity'];sens=sens[(sens.period=='primary')&sens.id.isin(['rmi70','macd_rsi60','cci100_up20'])]
    text.append(table(['시장','신호','초입 범위','적중 %','포착 %'],[[MARKET[r.market],names[r.id],r.window,pct(r.precision),pct(r.capture)] for r in sens.itertuples()]))
    text.append('0~3일은 더 엄격한 빠른 확인,0~10일은 더 기다린 확인이다. 창을 넓혀 얻은 포착을0~5일의 성능 개선으로 바꾸어 말하지 않는다. 이 보조 창에 주 기준의 직접 비교 신뢰구간을 재사용하지 않았다.\n')

    text.append('\n## 9. 실제 성공·실패·늦은 확인 사례\n')
    case_images=[]
    for m in ['KR','US']:
        if (DOC/(m+'-cases.png')).exists():case_images.append(image(m+'-cases',MARKET[m]+' 실제 성공·실패·늦은 확인 사례'))
    if case_images:
        text.extend(case_images)
        text.append('가격·사후 L1·초입 영역·실제 신호일·다음 시가 이후 경로를 함께 보았다. 예시는 각 집단의21일 종가 경로 중앙값에 가까운 고정 후보의 사례이며, 무작위 대표 표본이나 성능 증명이 아니다. 신호 뒤 가격이 내렸다고 반드시 초입 확인에 성공한 것도, 초입 확인에 실패했다고 반드시 이후 가격이 오른 것도 아니다. 날짜·가격은 '+link('illustrated-cases.csv')+'에서 확인할 수 있다.\n')
    else:
        text.append('사례 그림은 별도 사례 생성 단계의 검증 후 이 절에 연결된다. 집계 성능은 사례 선택에 의존하지 않는다.\n')

    text.append('\n## 10. 논문에서 가져온 점과 남은 불확실성\n')
    text.append(table(['연구 근거','이번 분석에서의 적용·한계'],[
      ['[Kim, Koh, Boyd & Gorinevsky (2009), L1 Trend Filtering](https://stanford.edu/~boyd/papers/pdf/l1_trend_filter.pdf)','구간별 선형 추세를 사후 정답으로 사용한다. λ=1은 기존 연구를 유지한 선택이며 보편적 최적값이 아니다. 사후 시작점을 그날 알았던 것처럼 신호에 넣지 않는다.'],
      ['[Lo, Mamaysky & Wang (2000)](https://www.mit.edu/~wangj/pap/LoMamayskyWang00.pdf)','패턴을 객관적으로 계산하고 조건부 가격 분포를 비교한다. 상태 분류·추가 가격 정보·실현 거래 이익은 서로 다른 주장이다.'],
      ['[Sullivan, Timmermann & White (1999), 기관 공개 작업논문](https://www.fmg.ac.uk/sites/default/files/2020-11/dp303.pdf)','다수 규칙의 우연한 우승과 시간 의존성을 고려한다. 이번 대비의 최대통계량 보정은 분류/경로 차이에 대한 것으로, 매도 전략 수익의 White Reality Check를 수행했다는 주장이 아니다.'],
      ['[Bajgrowicz & Scaillet (2012)](https://scaillet.ch/pdfs/BajSca.pdf)','과거의 우수한 규칙이 미래에도 유지되는지와 거래비용의 영향을 따로 검증해야 한다.15년 재평가를 새 독립 표본이나 비용 차감 매도 성과로 부르지 않는다.']]))
    text.append('비유하면 L1은 경기 뒤 영상을 돌려본 판정이고 신호는 경기 중의 판단이다. 같은 날 많은 주식이 함께 움직이므로 사건 수가 많다는 이유만으로 독립적인 증거가 늘었다고 볼 수 없다. 이번에는 종목 재표집과 공통3/6개월 시간 블록을 함께 사용했고1,999회 계산했다. 두 설정의 넓은 구간을 사용했다.\n')
    text.append('많은 사람에게 동전 던지기를 시키면 우연한 연승자가 생기듯, 많은 규칙을 비교할수록 보기 좋은 결과가 나올 수 있다. 이번에는486개 상태 대비,162개 발생률 대비,288개 직접 비교,3,456개 가격경로 대비를 각 고정 집합 안에서 보정했다. 그러나 이전 연구부터 이어진 적응적 탐색 전체를 지우지는 못한다.\n')
    text.append('매칭은 고정된 셀·지지 표본을 사용하고, 비신호일 평균의1차 불확실성을 실제 대조일의 월에 배분했다. 매 반복마다 대조군을 새로 구성한 완전한 재매칭은 아니다. 세부 구간을 나눈다고 연속 상태가 완전히 같아지는 것도 아니다. 새 기간의 관측, 생존편향 없는 역사 종목군, 시점별 가격 수정본까지 확보한 검증은 여전히 별도다.\n')
    text.append('종료일 민감도는 한국20·미국20종목에 대해2015·2020·2025년9월 종료 추세와 최종 추세를 비교해 하락 정답을 다시 계산했다.126봉 완충 뒤 양쪽에서 확정된 날짜의 하락 상태·초입은 모두 일치했다. 다만 미국2015년에는 미완료였던21일이 나중에 확정되면서 시작점이181개에서182개로 늘었다. 완충을 적용하지 않은 마지막126봉의 상태 일치율은 한국76.5~94.2%, 미국59.1~88.1%였다. **완충이 종료점 위험을 줄이지만 정답 불변을 보장하지는 않는다.**40종목 표본의 결과를 모든 신규 상장·짧은 이력에 일반화할 수 없다. 상세는 '+link('endpoint-recheck.md','종료일 민감도 감사')+'에 있다.\n')

    text.append('\n## 11. 전체81조건: 15년과 최초 확보 이력 비교\n')
    allp=d['raw'][d['raw'].period=='all'].set_index(['market','id'])
    text.append('아래 전체 이력은 종목별 최초 평가 가능일부터 시작한다. 오래된 자료의 품질·종목 구성이 다르고 주15년과 겹치므로 별도의 독립 검증이 아니다. 짧은 이력도 포함했으며, 모든 조건에 공통으로15년치 관측을 만들어 넣지 않았다.\n')
    for m in ['KR','US']:
        text.append(f'\n### {MARKET[m]} 전체 조건\n');rows=[]
        for r in p[p.market==m].itertuples():
            a=allp.loc[(m,r.id)]
            rows.append([names[r.id],{'event':'사건','daily_pattern':'일별 패턴'}.get(r.kind,r.kind),number(r.signals),pct(r.precision),pct(r.capture),number(a.signals),pct(a.precision),pct(a.capture)])
        text.append(table(['조건','집계 유형','15년 신호 수','15년 적중 %','15년 포착 %','최초 이력 신호 수','최초 이력 적중 %','최초 이력 포착 %'],rows))
    text.append('신호 수가 많아도 신뢰도는 기간·종목 의존성에 따라 달라진다. 표의 점추정 순위만으로 새로운 우승자를 고르지 않았고, 값이 없는 항목은0이 아닌 평가 불가다.\n')

    text.append('\n## 12. 확인된 사실, 남은 불확실성, 활용 범위\n')
    text.append(table(['구분','이번 연구가 말할 수 있는 내용'],[
        ['확인된 사실','고정81조건의 장기 재평가에서도 MACD+RSI의 상대적으로 높은 초입 적중률과 CCI의 빠르고 넓은 포착이 유지됐다. 신규12조건이 이를 대체할 근거는 찾지 못했다. MACD의21/63일 추가 하락 차이는 비교 가능한 일부 상태에서 보정 후 남았다.'],
        ['아직 불확실','비교되지 않은 대부분 알림으로의 일반화, 새로운 기간의 재현성, 생존편향·과거 가격 처리·L1 종료점 위험은 남는다. 추가 하락이 관측됐다는 사실만으로 매도했을 때 이익이 늘었는지는 알 수 없다.'],
        ['실전 활용 범위','MACD+RSI는 약화와 가격 위험을 다시 점검할 근거, CCI는 빠르고 넓은 점검 후보로 이해할 수 있다. 단독 신호로 초입을 확정하거나 자동 전량 매도를 정당화할 수준은 아니다. 보유 가설·기업 정보·비용·재진입을 포함한 판단이 별도로 필요하다.']]))
    text.append('이 연구의 주 질문에 답하기 위해 같은 과거 자료에서 지표·임계값을 더 늘릴 필요는 낮다. 현재 조건을 고정한 새 기간의 관측이 다음 신뢰성 검증에 가깝다. 매도 성과가 궁금해질 때는 진입·매도·재진입·비용을 먼저 정한 별도 연구로 구분해야 한다. 이번에는 그 범위로 확장하지 않았다.\n')
    text.append('\n## 계산 결과와 재현 자료\n')
    text.append('주 결과는 '+link('evaluate-metrics.csv')+'·'+link('base-rates.csv')+', 불확실성은 '+link('classification-intervals.csv')+', 이후 경로는 '+link('path-distributions.csv')+'·'+link('matched-paths.csv')+'에 있다. 기간별 '+link('classification-eras.csv','5년 구간')+'·'+link('classification-yearly.csv','연도')+'·'+link('equal-stock.csv','종목 동일가중')+'·'+link('evaluate-duration.csv','하락 지속기간')+'도 함께 제공한다. 각 그림에는 동일 이름의 `-data.csv`가 있어 화면의 값과 계산을 대조할 수 있다.\n')
    text.append('전체 CSV 묶음: '+link('results-csv.zip','다운로드')+'. 재현 코드는 [연구 실행 안내](../../scripts/research/downtrend_longhistory/README.md)에 있다. 미완료 추세·평가 제외는 '+link('evaluate-coverage.csv')+'·'+link('coverage-summary.json')+'에서 확인할 수 있다. 원자료·운영 감시·계좌·매매 조건은 바꾸지 않았다.\n')
    text.append('실전에서는 확인 신호를 보유 가설·기업 변화·가격 위험을 다시 점검할 계기로 쓸 수 있다. 초입 적중률이나 미래 저점까지의 낙폭만으로 전량 매도 효과를 확정할 수는 없다. 후속 연구를 한다면 같은 과거 자료에서 임계값을 더 찾기보다, 조건을 고정한 새 기간의 관측이나 명시적인 매도·재진입·비용 규칙을 검증하는 다른 질문으로 구분하는 편이 타당하다.\n')
    REPORT.write_text('\n'.join(text),encoding='utf-8')
    print(json.dumps({'report':str(REPORT),'markets':2,'conditions_per_market':81,'focal_per_market':18,'case_images':len(case_images)},ensure_ascii=False),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--no-figures',action='store_true');args=ap.parse_args()
    main(not args.no_figures)
