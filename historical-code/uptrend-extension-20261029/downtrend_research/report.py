"""Publish local research tables/figures, no deployment or external publication."""
from run import ROOT,OUT,write,sha
import json,shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

DEST=ROOT/'docs/downtrend-indicators-2026-10-21'
def pct(x):return '—' if pd.isna(x) else f'{100*x:.1f}%'
def pp(x):return '—' if pd.isna(x) else f'{100*x:+.1f}pp'
def table(df,cols):
    return '| '+' | '.join(t for _,t,_ in cols)+' |\n| '+' | '.join('---' for _ in cols)+' |\n'+'\n'.join('| '+' | '.join(fn(r[k]) for k,_,fn in cols)+' |' for _,r in df.iterrows())

def main():
    DEST.mkdir(exist_ok=True);coverage=json.loads((OUT/'coverage.json').read_bytes());inv=json.loads((OUT/'inventory.json').read_bytes())
    v=pd.read_csv(OUT/'validated_candidates.csv',dtype={'group':str,'year':str});allr=pd.read_csv(OUT/'all_results.csv',dtype={'group':str,'year':str})
    main=allr[allr.year=='all'];main.to_csv(DEST/'all-63-indicators.csv.gz',index=False,compression='gzip',encoding='utf-8-sig')
    v.to_csv(DEST/'validated-candidates.csv',index=False,encoding='utf-8-sig')
    yearly=allr[(allr.period=='test')&(allr.year!='all')];yearly.to_csv(DEST/'yearly-results.csv.gz',index=False,compression='gzip',encoding='utf-8-sig')
    for name in ['coverage.json','verification-artifacts.json','verification-synthetic.json','features.json','frozen_candidates.json','event_counts.json','supplemental_sources.json','source-lineage.json']:
        shutil.copyfile(OUT/name,DEST/name)
    shutil.copyfile(Path(__file__).with_name('protocol.json'),DEST/'protocol.json')
    post=v[v.window=='post'].sort_values(['market','group','rank']);lead=v[v.window=='lead'].sort_values(['market','group','rank'])
    formatcols=[('market','시장',str),('group','하락 지속일',str),('label','신호',str),('capture','시작 후1~5일 포착',pct),('baseline','평소 같은5일 창',pct),('signals_per_year','연간 횟수',lambda x:f'{x:.1f}'),('any_precision','신호 중 ≥10일 하락 초입',pct),('median_near_lag','근접 신호 시차 중앙값',lambda x:f'{x:+.0f}일')]
    keycols=[('market','시장',str),('group','하락 지속일',str),('label','신호',str),('precision','해당 기간 하락 초입 적중',pct),('context_difference','같은 상태 대비 증가',pp),('context_simultaneous_low','동시보정 하한',pp),('median_onset_to_nextopen_drop','시작종가→다음시가 이미 내린 폭',pct)]
    font=FontProperties(fname='C:/Windows/Fonts/malgun.ttf');plt.rcParams['font.family']=font.get_name();plt.rcParams['axes.unicode_minus']=False
    chosen=post.drop_duplicates(['market','group'])
    fig,axs=plt.subplots(1,2,figsize=(14,6),layout='constrained')
    labs=[f"{r.market} {r.group}일\n{r.label}" for r in chosen.itertuples()];yy=np.arange(len(chosen))
    axs[0].barh(yy-.17,100*chosen.capture,.32,label='하락 시작 후 1~5일',color='#165b9b');axs[0].barh(yy+.17,100*chosen.baseline,.32,label='동일 종목·연도 평소 5일',color='#a8b9c9')
    axs[0].set_yticks(yy,labs);axs[0].invert_yaxis();axs[0].set_xlim(0,100);axs[0].set_xlabel('해당 창에 신호가 나타난 비율 (%)');axs[0].legend(loc='lower right');axs[0].set_title('TRAIN에서 고른 초기 확인 후보 → TEST')
    axs[1].barh(yy,100*chosen.any_precision,color='#287c70');axs[1].barh(yy,100*(1-chosen.any_precision),left=100*chosen.any_precision,color='#e3ded6')
    for i,r in enumerate(chosen.itertuples()):axs[1].text(100*r.any_precision+1,i,f'{100*r.any_precision:.1f}% 초입 일치',va='center',fontsize=10)
    axs[1].set_yticks(yy,[f'{r.market} {r.group}일 후보' for r in chosen.itertuples()]);axs[1].invert_yaxis();axs[1].set_xlim(0,100);axs[1].set_xlabel('실제 발생한 모든 신호 (%)');axs[1].set_title('신호가 떴다고 항상 새 하락은 아니다\n초입 일치: ≥10일 L1 하락 시작 ±5일')
    fig.savefig(DEST/'capture-versus-precision.png',dpi=160);plt.close(fig)
    counts=pd.DataFrame(coverage['periods']);ct=counts[counts.period=='test'];totalonsets=int(ct.onsets.sum());totalstocks=int(ct.stocks_with_valid_days.sum())
    covrows=[]
    for m,c in coverage['markets'].items():
        t=ct[ct.market==m].iloc[0];covrows.append(dict(market=m,inventory=c['inventory'],history=c['usable_history'],test=int(t.stocks_with_valid_days),onsets=int(t.onsets),bars=c['used_bars'],first=c['earliest']))
    covdf=pd.DataFrame(covrows)
    controls=main[(main.period=='test')&(main.window=='post')&main.id.isin(['price5','price10','price5_up20','requested'])].copy()
    controls.to_csv(DEST/'common-controls-and-requested.csv',index=False,encoding='utf-8-sig')
    comparisons=[]
    for (m,ident),g in main[(main.period=='test')&(main.window=='post')].groupby(['market','id']):
        r=g.iloc[0]
        comparisons.append(dict(market=m,id=ident,label=r.label,family=r.family,
            capture=g.hits.sum()/g.n_onsets.sum(),baseline=np.average(g.baseline,weights=g.matched_onsets),
            signals_per_year=r.signals_per_year,any_precision=r.any_precision,strong_any_precision=r.strong_any_precision))
    comparison=pd.DataFrame(comparisons);comparison.to_csv(DEST/'indicator-comparison.csv',index=False,encoding='utf-8-sig')
    show=comparison[comparison.id.isin(['price5','cci100_up20','macd_positive','rsi60','stoch80','dmi_adx25','low20_volume','cmf_zero'])]
    positivepost=int(((post.simultaneous_low>0)&(post.context_simultaneous_low>0)).sum())
    positivelead=int(((lead.simultaneous_low>0)&(lead.lead_context_simultaneous_low>0)).sum()) if len(lead) else 0
    txt=f'''# 한국·미국 전체 저장 이력에서 하락 추세 초입의 기술적 신호

2026-10-21 · 연구 전용 · 운영 감시·매매 규칙에 적용하지 않음

기존 「백테스트 결과 비판적 재해석」의 마지막 상세해석을 확장했다. **L1 하락의 정의는 유지하고, 전체 저장 종목과 63개 기술적 사건을 비교했다.** TEST에서 실제 비교 가능한 종목은 **{totalstocks:,}개**, 10거래일 이상 완료 하락 시작점은 **{totalonsets:,}개**다. “많이 나타나는 신호”와 “신호가 나타났을 때 실제 초입인 비율”은 별개다.

**새로 추가한 지표에서는 CCI20의 +100 하향 이탈＋20일선 상승이 특히 강한 초기 확인 후보였다.** 한국의2주권·분기권에서는 사전 선정 후보로 검증했고, 미국에서도 기술통계상 증가폭이 컸다. 미국의1개월·분기권은 **MACD 양수권 시그널 데드크로스**가 사전 선정1위였다. 신호가 드물어졌어도 하락 초입과 맞지 않는 경우는 여전히 많아, 단독 매도 신호로 입증된 것은 아니다.

## 1. 먼저 볼 결과

아래는 2016~2021년 TRAIN에서 미리 고른 후보를 2023-04-01~2025-09-30 TEST에 대조한 결과다. 각 시장·기간에서 TRAIN 증가폭 상위2개만 뽑았다. **단순 종가5·10일선 이탈과 5일선 이탈＋20일선 상승은 비교군으로 남기고 후보에서 제외했다.** 모든 후보는 TRAIN 기준 연간12회 이하, 평소5일 창 발생률25% 이하 조건을 통과했다. TEST에서 더 빈번해졌다면 실제 횟수 그대로 표시한다.

{table(post,formatcols)}

‘초입 일치’는 신호일이 **사후 L1 시작점 전5일~후5일**에 있는 경우다. 오른쪽 적중률은 세 기간을 합친 ≥10일 하락이며, 해당 행의 특정 기간을 맞힌 확률은 다음 표에 따로 있다. 같은 신호가 여러 기간 행에 나오면 독립된 다른 전략이 아니다.

미국 CCI＋20일선 상승은 TEST의 세 구간에서70.1~78.5%를 포착했지만, TRAIN 연간 횟수가12.08회로 사전 상한12회를 조금 초과해 위의 사전 선정 검증 후보에서 제외됐다. 경계를 보고 조건을 완화하지 않았다. **미국 CCI는 유망한 탐색 결과로 따로 해석**한다. 순위 기준과 빈도 상한은 연구 가정이며 자연법칙이 아니다.

![포착률과 신호 적중률 비교](downtrend-indicators-2026-10-21/capture-versus-precision.png)

## 2. 평소에도 흔해서 높아 보인 것은 아닌가

동일 종목·같은 분기에서 **20일선 상승 여부, 종가의20일선 위/아래, RSI60 위/아래**가 같은 날을 대조했다. 신호가 없던 날의 초입 비율을 신호 발생 분포에 맞춰 가중했다. 이 비교도 사후 연관성 검사이며 인과·실시간 매도 우위를 뜻하지 않는다.

{table(post,keycols)}

종목과 분기를 함께 재표집한2,000회 부트스트랩을 사용했다. 선행/초기 확인의 전체 선정 후보 수×3개 효과 검사로 보수적으로 Bonferroni 보정했다. **초기 확인 후보 {len(post)}행 중 {positivepost}행**에서 일반빈도 대비 증가와 같은 상태 대비 적중 증가의 보정 하한이 모두0보다 컸다. 이것은 반복된 역사 안의 통계적 연관성이다. 과거 연구에서 이미 본 기간이므로 완전히 새로운 독립 검증이라고 부르지 않는다.

선정된 초기 확인12행은2023·2024·2025년 각각에서도 일반빈도 증가와 같은 상태 대비 적중 증가의 점추정 방향이 모두 양수였다. 해별로 각각 유의성을 입증했다는 뜻은 아니다. 종목 동일가중 확률은CSV의 `equal_stock_precision`에 함께 제공한다.

초입과 일치하지 않은 신호를 전부 “해롭지 않은 조정”으로 부를 수 없다. 이미 오래 하락 중이거나, 시작점에서 멀거나, 10일 미만 하락일 수도 있다. **1−적중률은 이 연구의 목표 초입에 대한 오경보율**이다.

## 3. 시작 전에 알려주는 지표인가

시작 전5일, 당일, 시작 후1~5일, 이후6~10일을 분리했다. 첫 표는 후1~5일의 확인 신호다. 시차 중앙값은 ±20일 안의 가장 가까운 같은 신호 기준이고, 음수는 먼저, 양수는 나중이다. 매도 가능 시점은 신호 종가 다음 연속 유효 거래일 시가로만 비교했다. 사후 시작가격에 팔 수 있었다고 가정하지 않았다.

TRAIN에서 선정된 시작 전 후보는 **{len(lead)}행**이다. 이 중 일반 빈도 증가와 같은 상태 대비 **향후1~5일 새 시작 확률 증가**의 보정 하한이 모두 양수인 것은 **{positivelead}행**이다. 이 별도 검사는 신호 당일/이전에 이미 시작된 하락을 성공으로 세지 않는다. 정확한 증가폭과 동시보정 구간은 후보CSV의 `lead_context_*` 열에 있다.

통과한2행은 **한국의 볼린저 상단 재진입**이다. 종가가20일 평균＋2표준편차 위에 있다가 다시 아래로 들어오는 사건이다. 같은 관측 상태에서 향후5일 안에1개월권 하락이 시작한 비율은 **9.35%→10.74%(+1.40pp)**, 분기권은 **4.82%→5.52%(+0.70pp)**였다. 각각의 보정 증가폭 구간은 **+0.49~+2.31pp**, **+0.06~+1.35pp**다. 가까운 신호 시차 중앙값은 시작1~2일 전이었지만 절대 확률의 증가는 작다. 미국에서는 선정한 선행 후보가 이 보정을 통과하지 못했다. **선행 신호가 전혀 없다고도, 신뢰도 높은 선행 경보를 찾았다고도 말할 수 없다.**

{table(lead,[('market','시장',str),('group','하락 지속일',str),('label','시작 전 선정 후보',str),('capture','시작 전5일 포착',pct),('baseline','평소5일 창',pct),('lead_precision','신호 후5일 내 해당 하락 시작',pct),('signals_per_year','연간 횟수',lambda x:f'{x:.1f}')]) if len(lead) else '고정한 최소 빈도·희소성·증가폭 조건을 동시에 충족한 선행 후보가 없다.'}

**기간별로 많이 보인다는 것과 2주/1개월/분기 하락을 미리 구분한다는 것은 다르다.** 이 연구는 기간별 시작점과의 연관성을 평가했으며, 미래 지속기간 분류기의 성능을 검증한 것이 아니다.

## 4. 분석 범위와 이전 보고서와의 차이

{table(covdf,[('market','시장',str),('inventory','조사 목록',lambda x:f'{x:,}'),('history','계산 가능한 이력',lambda x:f'{x:,}'),('test','TEST 유효 종목',lambda x:f'{x:,}'),('onsets','TEST 하락 시작점',lambda x:f'{x:,}'),('bars','사용 가격봉',lambda x:f'{x:,}'),('first','가장 이른 저장일',str)])}

- 전수 저장소 한국2,604·미국4,843개에서 기존 승인 제외57개를 보존했다. 별도 저장소의 중복되지 않는 과거 한국 이력과 ADR 차트도 조회했다. 종목별 부족·빈 이력·긴 연속 구간 없음은 `coverage.json`에 남겼다.
- 원 장기 보관소의 공통 마지막 날짜는 **2026-09-30**이다. 최초 저장일부터 모든 유효 이력을 계산해 `all` 기술통계도 제공한다. 주요 비교는 기존2016년 이후 구간을 유지한다.
- 이전 보고서는 한국406·미국2,000개, 당시 시총 자격 이후를 추적했다. 이번에는 시총·유동성 필터가 없고 코스닥·중소형주가 포함된다. 이전 보고서의 일부 원천과2026-10-15 끝점도 달라 **변화 전부를 표본 확대 효과라고 해석할 수 없다.** L1 전체 적합 시작점도 저장 최초일로 확장됐다.
- 가격 이상·거래량0·명시된 이력 공백·10일 넘는 달력 공백을 넘어서 지표/추세를 이어 붙이지 않았다. 실제 완료 하락과 자료 끝 미완료 하락을 구분했다. 65개 과거봉과126개 미래봉이 같은 자료 구간 안에 있어야 비교했다.
- 원본은 저장 공급자의 수정주가다. 모든 기업행동과 거래량 조정의 경제적 정합성을 새로 공시까지 감사한 것은 아니다. 주요 목록은 현재 상장 종목 중심이고 일부 한국 과거 이력을 보완했을 뿐, 상장폐지를 모두 포함한 역사 전체 시장은 아니다.

## 5. 추세와 지표의 정확한 의미

대표 지표를 같은 ≥10일 하락 시작점 전체로 묶은 기술통계다. 서로 다른 기간의 포착률은 사건 수로 가중했다. 지표를 추가했다고 모두 좋아진 것은 아니며, 거래량·추세강도 조건은 얼마나 적게 울리는지와 얼마나 많이 놓치는지를 함께 봐야 한다. 이 표 자체는 TEST를 보고 보는 탐색 비교이며 추가 확증 후보 선정에 쓰지 않았다.

{table(show,[('market','시장',str),('label','조건',str),('capture','시작 후1~5일 포착',pct),('baseline','평소5일 창',pct),('signals_per_year','연간 횟수',lambda x:f'{x:.1f}'),('any_precision','신호의 초입 일치율',pct)])}

CCI 조건은 강했던 단기 가격 모멘텀이 약해지지만 중기 평균 기울기는 아직 양수인 상태다. MACD 양수권 데드도 장기 역배열이 완성되기 전 모멘텀 둔화를 본다. 두 조건이 같은 날 발생했을 때의 추가 효과를 위 단일 조건 결과만으로 단정할 수는 없다.

L1은 로그 종가에 대해 `0.5×오차제곱합 + 1.0×2차차분 절댓값합`을 최소화한다. 한 거래일 기울기 `<−0.000001`인 연속 구간을 하락으로 정의하고, 직전 유효 기울기가 하락이 아니었던 첫 지점을 시작으로 삼는다. 평평하거나 상승인 구간을 임의로 연결하지 않는다. 10~20 /21~62 /63+는 서로 겹치지 않는 지속기간이다. **미래 가격을 사용한 사후 기준점이므로 실시간에 알려진 시작일이 아니다.** [원 방법 논문](https://stanford.edu/~boyd/papers/pdf/l1_trend_filter.pdf).

63개는 서로 독립인63개 가설이 아니다. 이동평균 교차·RSI·MACD·DMI/ADX·스토캐스틱·CCI·볼린저·ATR/켈트너·가격 저점/고점 실패·캔들·OBV/CMF/MFI·ROC·Aroon·Vortex·일목·변동성·과거 자료만 사용하는 RSI 약세 다이버전스와 고정 조합을 포함한다. 서로 같은 가격 변화를 다르게 표현하는 지표가 많다. [일반 지표 설명](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/overview), [MFI 설명](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/mfi).

지표는 당일 종가까지의 값만 쓴다. 일목 구름은 오늘 차트에 표시되는26봉 전 계산값, 다이버전스는 이미 지난20일 고점의RSI와 비교한다. 미래 피벗 확인이나 L1 상태를 신호 조건에 넣지 않았다. 결측은 거짓이나0으로 대체하지 않는다. 정확한 계산은 [features.py](../scripts/downtrend_research/features.py), 고정 기준은 [protocol.json](downtrend-indicators-2026-10-21/protocol.json)에 있다.

## 6. 검증·재현 자료

- [63개 전 조건·전체/선정/비교 기간 결과](downtrend-indicators-2026-10-21/all-63-indicators.csv.gz)
- [선정 후보와 군집 신뢰구간](downtrend-indicators-2026-10-21/validated-candidates.csv)
- [연도별 결과](downtrend-indicators-2026-10-21/yearly-results.csv.gz)
- [흔한 비교 신호와 사용자 예시](downtrend-indicators-2026-10-21/common-controls-and-requested.csv)
- [자료 범위](downtrend-indicators-2026-10-21/coverage.json) · [원자료/원장 검증](downtrend-indicators-2026-10-21/verification-artifacts.json) · [합성/미래참조 검사](downtrend-indicators-2026-10-21/verification-synthetic.json)
- 종목별 원장·모든 시작점 날짜·입력 해시는 `runtime/downtrend-indicators-20261021/`에 있다. `onsets.csv.gz`는 기간별로 같은 사건을 반복 포함하므로 `all/train/test`를 합쳐 독립 사건 수로 세면 안 된다.

재현 순서: 격리 의존성SciPy와 기존NumPy/pandas/matplotlib 환경에서 `run.py prepare` → `supplement.py` → `run.py summary` → `audit.py` → `research_stats.py aggregate` → `research_stats.py validate` → `report.py`. 이번 고정 실험의 재개용 코드다. 입력/조건을 바꾸면 같은 캐시를 재사용하지 말고 `run.py`의 `OUT`을 새 연구 폴더로 분리하고 의존성을 준비해야 한다. 원본/운영DB/알림 설정은 변경하지 않았다.

**확인된 것은 특정 정의의 하락 초입과의 통계적 연관성이다. 실제 매도의 이익, 재진입 비용, 순수한 선행 예측력과 같은 의미로 확대하지 않는다.**
'''
    (ROOT/'docs/downtrend-indicators-2026-10-21.md').write_text(txt,encoding='utf-8')
    write(DEST/'artifact-manifest.json',[dict(path=p.name,sha256=sha(p),bytes=p.stat().st_size) for p in sorted(DEST.iterdir()) if p.is_file() and p.name!='artifact-manifest.json'])
    print('report ready',str(ROOT/'docs/downtrend-indicators-2026-10-21.md'),flush=True)

from pathlib import Path
if __name__=='__main__':main()
