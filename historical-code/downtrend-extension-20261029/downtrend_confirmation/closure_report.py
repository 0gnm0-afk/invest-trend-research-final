"""Readable Korean closure report and fixed scientific figures."""
from closure import *
import shutil,zipfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

NAMES=dict(zip(IDS,['MACD+RSI','양수권 MACD','CCI100·20일선 상승','RSI60 이탈','스토캐스틱80 이탈','종가5일선 이탈(비교)']))

def pct(x):return f'{100*x:.1f}%'
def pp(x):return f'{100*x:+.2f}%p'
def interval(lo,hi):return f'[{100*lo:+.2f}, {100*hi:+.2f}]'
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])

def main():
    for p in DEST.glob('*.csv'):shutil.copyfile(p,DOC/p.name)
    for name in ['verification.json','inference-receipt.json','compute-receipt.json','protocol-amendment.json']:shutil.copyfile(DEST/name,DOC/name)
    b=pd.read_csv(DEST/'base-rates.csv');r=pd.read_csv(DEST/'matched-risk.csv');balance=pd.read_csv(DEST/'balance.csv');year=pd.read_csv(DEST/'yearly.csv');eq=pd.read_csv(DEST/'equal-stock.csv')
    old=pd.read_csv(ROOT/'docs/downtrend-confirmation-2026-10-21/all-signals-test.csv').set_index(['market','id'])
    def br(m,i,state):
        a=b[(b.market==m)&(b.id==i)&(b.state==state)];q=a.iloc[0].to_dict()
        q.update(precision_low=a.precision_low.min(),precision_high=a.precision_high.max(),difference_sim_low=a.difference_sim_low.min(),difference_sim_high=a.difference_sim_high.max(),adjusted_p=a.adjusted_p.max())
        return q
    def rr(m,i,scheme=2,h=21,o='loss05'):
        a=r[(r.market==m)&(r.id==i)&(r.scheme==scheme)&(r.horizon==h)&(r.outcome==o)];q=a.iloc[0].to_dict();q.update(sim_low=a.sim_low.min(),sim_high=a.sim_high.max(),ci_low=a.ci_low.min(),ci_high=a.ci_high.max(),adjusted_p=a.adjusted_p.max());return q
    plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':10,'figure.dpi':130})
    for m in ['KR','US']:
        fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained');yy=np.arange(6)
        for ax,state,title in zip(axes,['early0_5','whole_down_ge10'],['하락 초입 0~5일','전체 하락 기간 (10일 이상 지속)']):
            dat=[br(m,i,state) for i in IDS];x=np.array([q['precision'] for q in dat]);lo=np.array([q['precision_low'] for q in dat]);hi=np.array([q['precision_high'] for q in dat]);bas=np.array([q['base_rate'] for q in dat])
            ax.errorbar(x,yy,xerr=np.stack([x-lo,hi-x]),fmt='o',color='#12677a',capsize=3,label='신호 적중률·95% 구간')
            ax.scatter(bas,yy,marker='D',color='#bb693a',label='같은 평가 날짜의 기저율');ax.set_yticks(yy,[NAMES[i] for i in IDS]);ax.invert_yaxis();ax.xaxis.set_major_formatter(PercentFormatter(1));ax.set_xlim(0,.8);ax.set_title(title);ax.grid(axis='x',alpha=.2)
        axes[1].legend(loc='upper center',bbox_to_anchor=(.5,-.08),ncol=2,fontsize=8);fig.suptitle(m+' | 초입 집중도와 전체 하락 판별력은 다르다');fig.savefig(DOC/f'{m}-base-rates.png');plt.close(fig)
        fig,axes=plt.subplots(1,3,figsize=(13,4.9),layout='constrained')
        for ax,h in zip(axes,HORIZONS):
            dat=[rr(m,i,h=h) for i in IDS];x=np.array([q['difference'] for q in dat]);lo=np.array([q['sim_low'] for q in dat]);hi=np.array([q['sim_high'] for q in dat])
            assert min(lo)>-.06 and max(hi)<.14
            ax.errorbar(x,yy,xerr=np.stack([x-lo,hi-x]),fmt='o',color='#12677a',capsize=3);ax.axvline(0,color='#bb693a',ls='--');ax.set_yticks(yy,[NAMES[i] for i in IDS] if h==5 else []);ax.invert_yaxis();ax.set_xlim(-.06,.14);ax.xaxis.set_major_formatter(PercentFormatter(1));ax.set_xlabel('확률 차이 (%p)');ax.set_title(f'이후 {h}거래일');ax.grid(axis='x',alpha=.2)
        fig.suptitle(m+' | 비슷한 비신호일 대비 5% 추가 하락 확률 차이\n변동성·5일 및 당일 수익률까지 대응 / 432비교·시간블록 민감도 반영',fontsize=12);fig.savefig(DOC/f'{m}-matched-risk.png');plt.close(fig)
    text=['# 하락추세 확인 연구 — 학술 검토와 종료 보완',
          '기준: 2026-10-22 · 기존 신호·λ·가격을 유지한 탐색적 보완 · 매매전략 수익성 검증 아님',
          '**최종 판단: 하락 초입의 흔적을 찾는 연구는 여기서 종료할 수 있다. MACD+RSI는 드문 초입에 집중되지만, 알림만으로 초입을 확정하거나 매도를 결정할 만큼 정확하지 않다. 전체 하락 여부를 맞히는 능력은 초입 집중도와 다르며, 추가 하락 위험의 차이도 시장·관측 기간·비교 상태에 따라 판단해야 한다.**',
          '[이전 상세 보고서](downtrend-confirmation-2026-10-21.md)와 63개 신호·6개 후속 조건 결과는 그대로 보존했다. 이번에는 거기서 이미 제시한 대표6개만 고정했다. 새 지표, 임계값 조정, 후보 재선정, 대규모 최적화는 없다. [학술논문 원문 비교](downtrend-closure-2026-10-22/literature.md) · [전체 CSV 묶음](downtrend-closure-2026-10-22/results-csv.zip).',
          '## 1. 무엇을 구분했는가',
          '초입 적중률은 신호일 중 **완료된 10거래일 이상 하락의 시작일부터 5거래일 뒤까지, 총6일**에 속한 비율이다. 전체 하락 적중률은 같은 분모에서 해당 하락의 모든 날짜에 속한 비율이다. 초입 전 신호도 분모에 남는다. 전체 하락이라고 할 때 10일 미만 하락까지 넣은 보조 결과도 CSV에 `whole_down_any`로 제공한다.',
          '기저율은 각 신호를 계산할 수 있는 전체 평가 날짜 중 해당 상태인 날짜의 비율이다. **하락일만 뽑은 적중률이 아니다.** 초입은 날짜가 적고 전체 하락은 날짜가 많으므로 두 적중률의 숫자만 직접 비교하면 안 된다. 비 오는 날이 절반인 곳에서 55% 맞히는 예보와, 드문 폭풍을 35% 맞히는 예보는 서로 다른 문제다.',
          '사후 정답표는 기존과 같이 로그종가에 ½Σ(log C−x)²+λΣ|Δ²x|, λ=1을 적용한다. 하루 기울기 x[t+1]−x[t]가 <−0.000001이면 하락, >+0.000001이면 상승, 그 사이는 경계 포함 횡보다. 20일 환산 경계는 각각 −0.00199998%, +0.00200002%다. 이 정의는 고정한 평가 기준이며 실시간에 확정되는 객관적 진실은 아니다.',
          '## 2. 학술 검토에서 실제로 보완한 부분',
          'Kim 등(2009)의 목적함수와 현재 L1 구현을 대조했다. Lo 등(2000)의 조건부·평소 분포 구분을 따라 기저율과 비신호일 이후 경로를 비교했다. Sullivan 등(1999)의 데이터 탐색과 시간 의존성 문제를 반영해 고정 비교 전체의 동시 구간과 연속 월 블록 민감도를 추가했다. Bajgrowicz·Scaillet(2012)의 성과 지속성과 거래비용 문제에 따라 정보성·위험 경보와 매도 수익성을 구분했다. 상세 서지·원문·현재 연구와의 차이는 [논문 비교표](downtrend-closure-2026-10-22/literature.md)에 있다.',
          '기존의 TRAIN 후보 고정, 선정용 L1에서 TEST 미래 가격 제외, 다중검정, 종목·시간 군집, 지연·포착률, 끝점 민감도는 유지한다. 새로운 TEST를 얻은 것은 아니다. 거래비용을 포함한 매도·재진입 전략이나 White Reality Check를 수행했다고 주장하지 않는다.',
          '## 3. 초입과 전체 하락: 적중률을 기저율과 함께 읽기']
    for m in ['KR','US']:
        early=br(m,'macd_rsi60','early0_5');down=br(m,'macd_rsi60','whole_down_ge10')
        text += [f'### {m}: '+('한국' if m=='KR' else '미국'),
                 f"동일한 평가 날짜에서 초입 기저율은 **{pct(early['base_rate'])}**, 전체 하락 기저율은 **{pct(down['base_rate'])}**다. MACD+RSI는 초입 적중률 {pct(early['precision'])}로 기저율의 {early['lift']:.2f}배지만, 전체 하락 적중률은 {pct(down['precision'])}로 기저율보다 {pp(down['difference'])} 높을 뿐이다. 전체 하락 차이의 보정 구간은 {interval(down['difference_sim_low'],down['difference_sim_high'])}%p다."]
        rows=[]
        for i in IDS:
            a=br(m,i,'early0_5');d=br(m,i,'whole_down_ge10');rows.append([NAMES[i],f"{a['signals']:,.0f}",f"{pct(a['precision'])} [{100*a['precision_low']:.1f}, {100*a['precision_high']:.1f}]",f"{pp(a['difference'])} / {a['lift']:.2f}배",f"{pct(d['precision'])} [{100*d['precision_low']:.1f}, {100*d['precision_high']:.1f}]",f"{pp(d['difference'])} / {d['lift']:.2f}배"])
        text += [table(['신호','전체 신호 수','초입 적중률 [95%]','초입 기저율 대비','전체 하락 적중률 [95%]','전체 하락 기저율 대비'],rows),f'![{m} 기저율 비교](downtrend-closure-2026-10-22/{m}-base-rates.png)',
                 '그림에서 파란 점과 주황 마름모의 거리를 본다. 왼쪽의 큰 간격은 초입 집중도를 뜻한다. 오른쪽에서 간격이 작거나 반대로 바뀌면 전체 하락 판별력이 좋다고 해석할 수 없다. 신호 적중률 구간은 개별95% 구간이며, 차이의 다중검정 구간은 CSV의 `difference_sim_low/high`다. 모두 3개월·6개월 블록 결과를 감싸는 범위로 표시했다.']
    text += ['초입 집중도와 전체 하락 판별력이 다른 이유도 조건에서 찾을 수 있다. RSI60·CCI100 신규 이탈은 높은 지표가 처음 약해지는 때 발생한다. 이미 오래 하락해 지표가 낮아진 기간에는 새로 이탈할 기회가 적다. 전체 하락일 기저율은 긴 하락의 날짜를 모두 포함한다. 따라서 초입 포착 신호의 전체 하락 적중이 낮다고 초입 결과까지 부정하거나, 초입 집중도가 높다고 전체 하락 판별력을 인정해서는 안 된다. 또한 여기의 무조건부 기저율과 이전의 동일 상태 비신호일 기준(한국 MACD+RSI 초입 약13.5%, 미국11.3%)은 서로 다른 비교다.',
             '## 4. 신호 뒤 실제 추가 하락 위험은 더 컸는가',
             '이 부분은 **신호가 맞았던 사례만 고르지 않는다. L1 상태·지속기간·추세 완결 여부를 전혀 조건으로 쓰지 않는다.** 신호와 비교 상태를 계산할 수 있고, 이전65봉·이후63봉이 같은 유효 가격 구간에 있는 모든 TEST 날짜를 사용한다. 따라서 사후 정답을 알아야 평가 가능한 앞 표와 분모가 조금 다르다. 원래 표본에 대해서는 기존 5·21·63일 수익률/저가 합계와 별도로 일치 검증했다.',
             '각 신호마다 같은 종목·같은 달력 분기 안에서 ① 20일선 상승 여부 ② 종가가20일선 위인지 ③ RSI≥60인지가 같은 비신호일을 대응시킨다(기본 대응·scheme0). scheme1은 ATR14/종가 구간 <2%, 2~4%, ≥4%와 최근5일 수익률 구간 <−5%, −5~0%, 0~5%, ≥5%를 더한다. 이 둘은 결과 확인 전에 고정했다.',
             '**필요해서 추가한 단 한 번의 보완:** 첫 결과의 상태 균형을 확인하니 MACD+RSI 신호일의 당일 수익률 표준화 차이가 한국−0.469·미국−0.455로 남았다. 그래서 scheme2에 당일 수익률 구간 <−3%, −3~−1%, −1~0%, 0~1%, 1~3%, ≥3%를 추가했다. 이는 결과·균형을 본 뒤의 사후 보완이며 독립검증이 아니다. 새 비교 계산 전에 [변경 프로토콜](downtrend-closure-2026-10-22/protocol-amendment.json)을 저장했고, 모든6신호와 세 대응법을 결과와 관계없이 보존했다. 아래 핵심 표는 더 엄격한 scheme2다. 신호 산식은 바뀌지 않았다.',
             '신호일과 같은 셀의 비신호일 평균을 비교하고, 신호 한 건마다 같은 가중치를 준다. 비교일이 없는 신호는 대응 분석에서만 제외하고 비율을 공개한다. 비교일은 같은 분기 내 앞·뒤 날짜를 모두 쓸 수 있으며, 한 비신호일이 여러 신호의 비교 대상으로 쓰일 수 있다. 이것은 과거 자료의 상태 비교이며 당시 실시간 비교일 선택 전략이 아니다. **엄격한 대응은 MACD+RSI 신호의 약 절반만 남긴다. 결과를 전체 신호로 일반화할 수 없고, 신호마다 남는 표본도 달라 위험 차이의 크기만으로 순위를 정할 수 없다.**',
             '**가격 기준:** 신호 다음 연속 유효 거래일 시가에서 시작한다. 이후 h=5·21·63거래일의 저가 최솟값이 기준 시가보다 5%/10% 이상 낮았는지, 최대 불리한 이동 `max(0, 1−최저가/기준시가)`, h번째 종가 수익률을 계산한다. 이 저가를 실제 매수·매도할 수 있었다거나 전부 피할 손실이라고 해석하지 않는다. 기간 중 하락했다가 반등한 경로도 하락 확률에 포함된다.']
    for m in ['KR','US']:
        text += [f'### {m}: 21거래일 안에 추가로 5% 이상 하락할 확률']
        rows=[]
        for i in IDS:
            q=rr(m,i);rows.append([NAMES[i],f"{q['matched_signals']:,.0f}/{q['all_signals']:,.0f} ({pct(q['support'])})",pct(q['signal']),pct(q['control']),pp(q['difference']),interval(q['sim_low'],q['sim_high']),f"{q['adjusted_p']:.4f}"])
        text += [table(['신호','대응 가능/전체 신호','신호일','비슷한 비신호일','차이','동시95% 구간(%p)','보정 p'],rows),f'![{m} 위험 차이](downtrend-closure-2026-10-22/{m}-matched-risk.png)',
                 '점이 0 오른쪽이면 신호 뒤의 추가 하락 확률이 더 높았다. 가로 구간 전체가 0 오른쪽에 있어야 이번 다중비교·시간블록 검증에서 양의 차이가 남았다고 부른다. 0을 걸치면 차이가 없다고 증명된 것이 아니라, 증가를 확실히 구별하지 못했다는 뜻이다. 큰 발생 건수가 독립적인 실험 횟수는 아니다.']
        q=rr(m,'macd_rsi60');raw=rr(m,'macd_rsi60',scheme=0);mid=rr(m,'macd_rsi60',scheme=1)
        if q['sim_low']>0:verdict='양의 차이가 동시 구간에서도 남았다'
        elif q['sim_high']<0:verdict='오히려 음의 차이가 동시 구간에서 남았다'
        else:verdict='동시 구간이 0을 포함해 추가 위험 증가를 확정하지 못했다'
        text += [f"MACD+RSI의 기본 대응 차이는 {pp(raw['difference'])}, 변동성과5일 수익률 추가 대응은 {pp(mid['difference'])}, 당일 수익률까지 추가하면 {pp(q['difference'])}다. 마지막 비교에서 **{verdict}**. 대응 가능한 표본도 바뀌므로 차이의 변화 전부를 당일 수익률 통제의 효과라고 단정하지 않는다. 이 비교는 현재 보유 종목의 매도 수익률을 측정한 것이 아니다."]
    text += ['### MACD+RSI: 위험과 기간말 결과를 구분',
             '아래는 보강 대응에서 신호 평균 / 비신호 평균 / 차이다. 평균 불리한 이동은 양수일수록 더 깊은 하락이고, 기간말 수익률은 양수일수록 높은 가격이다. 서로 부호의 의미가 다르다.']
    rows=[]
    for m in ['KR','US']:
        for h in HORIZONS:
            vals=[]
            for o in OUTCOMES:
                q=rr(m,'macd_rsi60',h=h,o=o);vals.append(f"{pct(q['signal'])} / {pct(q['control'])} / {pp(q['difference'])}")
            rows.append([m,str(h)]+vals)
    text += [table(['시장','기간','5% 하락 확률','10% 하락 확률','평균 불리한 이동','기간말 평균 수익률'],rows),
             '기간말 평균 수익률은 극단적인 상승값에 민감하며 거래비용·배당·세금·현금 수익을 포함하지 않는다. 전체 분포와 중간 경로는 이전 [신호별 가격 경로 CSV](downtrend-confirmation-2026-10-21/selected-price-paths.csv)도 함께 확인할 수 있다. 이번 보완의 위험 판정은 평균 수익률 하나에 의존하지 않는다.',
             '## 5. 비교 대상과 통계가 얼마나 믿을 만한가',
             '보강 대응도 상태를 완전히 같게 만들지는 못한다. 아래는 ATR%, 당일·5일·20일 수익률, 종가/MA20 거리 중 절댓값이 가장 큰 표준화 평균 차이다. 0에 가까울수록 비교 그룹이 비슷하다. 0.1은 통상 점검용 기준일 뿐 합격선으로 최적화하지 않았다. 차이가 크게 남으면 신호 자체의 독립 효과로 읽을 수 없다.']
    rows=[]
    for m in ['KR','US']:
        for i in ['macd_rsi60','macd_positive','cci100_up20']:
            a=balance[(balance.market==m)&(balance.id==i)&(balance.scheme==2)];k=a.standardized_difference.abs().idxmax();q=a.loc[k];label=dict(atr_pct='ATR/종가',return1='당일 수익률',return5='5일 수익률',return20='20일 수익률',distance_ma20='종가/20일선 거리')[q.covariate];rows.append([m,NAMES[i],label,f'{q.standardized_difference:+.3f}',f'{q.control_days:,.0f}',f'{q.control_effective_n:,.0f}'])
    text += [table(['시장','신호','가장 남은 상태 차이','표준화 차이','서로 다른 비교일','가중치 유효 비교일 수'],rows),
             '같은 종목을 함께 재가중하고, 양 시장에 공통인 달력 월의 연속 블록을 재추출했다. 1,999회, 평균 블록3개월과6개월을 모두 계산한다. 위험 차이는 6신호×2시장×3대응법×3기간×4결과=432개를 함께 고려한 최대 표준화 편차 구간이다. 상태 적중률−기저율은 6×2×3상태=36개를 별도로 보정했다. 본문은 두 블록 길이 구간의 합집합과 더 큰 p값을 사용해 어느 한 설정에서 좋은 결과만 고르지 않았다.',
             '**여전히 근사 추론이다.** 시간 표본은30개월뿐이다. 대응 셀과 지원 범위는 고정하되, 비교일 평균이 추정값이라는 불확실성도 1차 영향함수로 반영했다. 구체적으로 비교일 월에 `(셀 신호 수/비신호 수)×(개별 결과−셀 비교일 평균)`을 배분한다. 합은0이어서 점추정은 유지되고, 같은 비교일 재사용과 시간 재추출에 따른 평균 변화가 구간에 반영된다. 신호일과 비교일을 모두 실제 발생 월로 재가중하는 근사이며, 매 재표집에서 대응을 처음부터 재구성하는 완전한 계산은 아니다. 겹치는 미래 경로의 영향을 종목·연속월 블록으로 반영하려 했지만 완전히 제거했다고 주장하지 않는다. 과거 누적 탐색 편향도 이번432개 보정만으로 해결되지 않는다.',
             '### 연도·종목 가중치 확인',
             '2023년은4월부터, 2025년은9월까지다. 아래 위험 차이는 보강 대응의21일5% 하락 확률 차이이며 연도별 단독 유의성 검정은 하지 않았다.']
    a=year[year.id=='macd_rsi60'];rows=[[q.market,str(q.year),pct(q.early),pct(q.early_base),pct(q.down),pct(q.down_base),pp(q.risk21_fine_delta)] for q in a.itertuples()]
    text += [table(['시장','연도','초입 적중','초입 기저','전체 하락 적중','전체 하락 기저','이후 위험 차이'],rows)]
    rows=[[q.market,NAMES[q.id],pct(q.early_precision),pct(q.whole_down_precision),pp(q.risk21_fine_delta),f'{q.risk_stocks:,}'] for q in eq[eq.id=='macd_rsi60'].itertuples()]
    text += [table(['시장','신호','종목 동일가중 초입 적중','전체 하락 적중','이후 위험 차이','위험 비교 종목 수'],rows),
             '주 결과는 신호 건수 가중이다. 위 표는 신호가 있는 종목의 적중률, 대응 가능한 종목의 위험 차이에 각각 동일 가중치를 준다. 분모가 다르므로 앞 표의 전체 날짜 기저율과 이 동일가중 적중률을 섞어 비교하지 않는다.',
             '## 6. 확인된 사실·남은 불확실성·실전 활용 범위',
             '**확인된 사실.** 정해 둔 L1 기준과 과거 표본에서는 MACD+RSI가 평소보다 초입에 집중된다. 그러나 초입 적중은 한국37.2%·미국32.5%이고 하락 사건 포착률은 약31%다. 맞은 사건도 평균 약3.8~3.9거래일 뒤 확인했고, 그 다음 시가까지 평균 약6.8%·7.6% 이미 내려 있었다. CCI 등은 더 일찍 더 많이 잡는 대신 적중률이 낮았다. 이 수치는 이전 결과를 그대로 유지한다. 하락 전체 적중률을 기저율과 비교하면 초입 집중도만으로 전체 하락 판별력이 좋다고 말할 수 없다.',
             '**남은 불확실성.** 현재 보유한 종목 이력 중심이라 상장폐지 등을 완전하게 포함한 당시 전체 시장이 아니다. 이전에 살펴본 TEST라 새 표본 검증이 아니다. λ와 기울기 경계에 따른 사후 분류이며, 최근 끝점의 L1 판정은 수정될 수 있다. 비신호일 대응 후에도 현재 수익률 등 차이가 남고 통계 구간은 근사적이다. 미래의 시장 국면에서 같은 성능이 유지되는지, 특정 보유 종목에서 얼마나 작동하는지는 이 표로 확정할 수 없다.',
             '**실전 활용 가능 범위.** MACD+RSI 등을 “최근 상승 동력이 약해져 하락 초입일 가능성을 점검할 이유”로 사용할 수 있다. 포지션을 보유했다면 보유 가설의 변화, 감수할 손실, 기존 대응 계획을 다시 확인하는 보조 정보다. 신호만으로 초입 확정·전량 매도·정해진 손실 회피를 정당화할 증거는 아니다. 추가 하락 확률 차이가 통계적으로 남아도 비용과 반등 기회비용을 고려한 매도 우위는 별도 문제다.',
             '**연구 종료 판단.** 이 질문에 답하기 위해 지표를 더 늘리거나 같은 TEST에서 조건을 더 맞출 필요는 없다. 정보성과 한계가 드러났으므로 현재의 탐색 연구는 종료한다. 실제 매도 규칙을 채택하려는 별도 목적이 생길 때에만 신호·매도량·재진입·비용을 사전에 고정하고 새로운 기간에서 보유 대비 순성과를 검증할 필요가 있다. 그 조건부 후속 과제를 이번 연구의 미완료 항목이나 자동 실행 계획으로 만들지 않는다.',
             '## 7. 정확한 신호·파일·재현 및 검증',
             table(['신호','기존 발생 조건'],[
                 ['MACD+RSI','MACD(EMA12−EMA26)가 EMA9 시그널선을 신규 하향 교차하고, 오늘 포함 최근3일 안에 RSI14가60을 신규 하향 돌파.'],
                 ['양수권 MACD','같은 MACD 신규 하향 교차이며 당일 MACD>0.'],
                 ['CCI100·20일선 상승','CCI20이+100을 신규 하향 돌파하며 SMA20>5거래일 전 SMA20.'],
                 ['RSI60 이탈','Wilder RSI14가60을 신규 하향 돌파.'],
                 ['스토캐스틱80 이탈','스토캐스틱(14,3,3) K가80을 신규 하향 돌파.'],
                 ['종가5일선 이탈','종가가 SMA5를 신규 하향 이탈. 빈번한 비교 기준으로만 유지.']]),
             '이전 구현의 교차 허용오차·결측 처리·구간 초기화도 동일하다. 조건 유지일을 매일 새 신호로 세지 않으며, 재교차는 별도 발생으로 센다. 세부 산식은 [원래63개 정의](downtrend-confirmation-2026-10-21/signal-definitions.csv)와 기존 `features.py`에 고정돼 있다.',
             table(['파일','내용'],[[f'[{name}.csv](downtrend-closure-2026-10-22/{name}.csv)',desc] for name,desc in [
                 ('base-rates','초입/전체≥10일/짧은 하락 포함: 건수·기저율·적중률·차이·배수·구간, 두 블록 길이'),
                 ('matched-risk','모든6신호·세 대응법·3기간·4가격 결과·지원율·동시구간·보정 p'),
                 ('balance','관찰 가능한5개 상태 변수의 균형과 비교일 유효 표본 수'),
                 ('yearly','2023~2025 부분연도 포함 결과'),('equal-stock','종목 동일가중 결과')]]),
             'CSV 비율은 0~1 원값이며 본문에서만 %로 표시한다. scheme0은 기본 대응, scheme1은 변동성·5일 수익률 추가 대응, scheme2는 당일 수익률까지 추가 대응이다. `adverse`는 최대 불리한 이동, `return`은 기간말 수익률이다. `matched_signals/all_signals`가 비교 가능한 범위를 보여준다. 통계적으로 유의하지 않은 행도 모두 남겼다. `yearly/equal-stock`의 `risk21_fine_*`는 최종 scheme2다.',
             '입력은 기존 `runtime/downtrend-indicators-20261021/cache`의 검증된 가격·신호·L1 배열이다. 캐시 해시를 읽을 때마다 검증한다. 원장 재구성에 필요한 종목/월 충분통계와 감사용 대응 날짜는 `runtime/downtrend-closure-20261022/cells-dayreturn`, 비교일 영향함수는 `control-influence`에 있다. 최초 두 대응법 계산은 같은 상위 경로의 `cells`와 `initial-results`에 보존했다. 별도 시장 수집이나 운영 데이터 수정은 하지 않았다.',
             '재현: 기존 Python 환경에서 `scripts/downtrend_confirmation/closure.py compute`, `influence`, `infer`, `verify` 순서로 실행한 뒤 `closure_report.py`를 실행한다. `freeze`는 최초 한 번만 실행하며 기존 동결 파일이 있으면 덮어쓰지 않는다. 프로토콜과 후속 변경 영수증을 함께 사용한다. 새 결과를 재생하려면 먼저 해당 파생 결과 경로를 별도로 보존해야 한다. 이전 연구 결과는 수정 대상이 아니다.']
    v=json.loads((DEST/'verification.json').read_bytes())
    headline=[]
    for m in ['KR','US']:
        a=br(m,'macd_rsi60','early0_5');d=br(m,'macd_rsi60','whole_down_ge10');q=rr(m,'macd_rsi60')
        headline.append([m,f"{pct(a['precision'])} / {pct(a['base_rate'])}",f"{pct(d['precision'])} / {pct(d['base_rate'])}",f"{pct(q['signal'])} / {pct(q['control'])}",f"{pp(q['difference'])} {interval(q['sim_low'],q['sim_high'])}"])
    text.insert(3,table(['MACD+RSI','초입 적중 / 기저율','전체 하락 적중 / 기저율','21일5%하락: 신호 / 비교일','위험 차이 [보정 구간, %p]'],headline))
    text.insert(4,'마지막 두 열은 당일 수익률까지 맞춘 비교로, 전체 신호의 한국49.7%·미국53.4%에서만 가능했다. 이 범위에서는 추가 하락 위험 차이가 보정 후에도 남지만, 전체 신호나 매도 수익성에 그대로 일반화할 수 없다.')
    ix=next(i for i,s in enumerate(text) if s.startswith('**남은 불확실성.**'))
    text.insert(ix,'**추가로 확인한 가격 위험.** MACD+RSI의 엄격한 대응 표본에서 21일 안에 5% 더 하락할 확률은 한국63.8% 대57.8%, 미국60.4% 대54.8%였다. 차이는 각각+6.00%p·+5.51%p이며 두 시간블록 설정·432개 비교 보정 후에도 양수였다. 기본·변동성 보강 대응에서도 방향이 같았다. 다만 비교 가능한 신호가 약 절반이고 당일·20일 수익률 등의 차이가 완전히 없어지지 않아, 신호의 순수한 인과효과로는 해석하지 않는다. CCI·스토캐스틱 등 초입 포착에 유용했던 후보가 이후 위험 증가까지 일관되게 보여주는 것은 아니었다. 종목 동일가중과 2023~2025년별 MACD+RSI 위험 차이의 방향도 확인했지만 미래 성능을 보장하지 않는다.')
    text += [f"검증 PASS: 12개 시장·신호 조합의 신호 수·초입 수와 6개 가격 합계를 이전 결과와 대조했다. 대응 날짜의 비신호 여부·동일 상태·분기·변동성/수익률 구간 및 {v['scalar_signal_control_paths']:,}개 날짜의 5·21·63일 가격 경로를 독립적인 직접 계산으로 확인했다. 합성5범주(분모·기저율, 대응 차이, 가격 기간/공백, 시간블록 수, 비교일 평균 영향함수)와 기존 핵심 파일 해시 보존을 확인했다. [검증 영수증](downtrend-closure-2026-10-22/verification.json) · [동결 프로토콜](downtrend-closure-2026-10-22/protocol.json)."]
    report=ROOT/'docs/downtrend-closure-2026-10-22.md';report.write_text('\n\n'.join(text)+'\n',encoding='utf-8',newline='\n')
    with zipfile.ZipFile(DOC/'results-csv.zip','w',zipfile.ZIP_DEFLATED) as zz:
        for p in sorted(DOC.glob('*.csv')):zz.write(p,p.name)
    manifests=[report]+[p for p in DOC.iterdir() if p.name!='artifact-manifest.json']
    write(DOC/'artifact-manifest.json',dict(files={str(p.relative_to(ROOT)):sha(p) for p in manifests},source_code={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'scripts/downtrend_confirmation/closure.py',Path(__file__)]}))
    print('report',report,'artifacts',len(manifests),flush=True)

if __name__=='__main__':main()
