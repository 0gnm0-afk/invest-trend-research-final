"""Korean report assembled from reviewed CSVs; no result-changing computation."""
from study import *
DOC=ROOT/'docs/research/downtrend-extension-2026-10-29'
REPORT=DOC.with_suffix('.md')
NAMES={b['id']:b['label'] for b in BASE}
FOCUS=['rmi70','rmi50','psar','stochrsi80','supertrend','trix_zero','fractal_break','macd_rsi60','cci100_up20']
def pct(x):return f'{100*x:.1f}'
def num(x):return f'{int(x):,}'
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,r))+' |' for r in rows])+'\n'
def image(name,caption):return f'\n![{caption}](downtrend-extension-2026-10-29/{name})\n\n'
def link(name,label=None):return f'[{label or name}](downtrend-extension-2026-10-29/{name})'

def main():
    s=pd.read_csv(DOC/'primary-summary.csv');raw=pd.read_csv(DOC/'evaluate-metrics.csv');raw=raw[raw.period=='test']
    p=pd.read_csv(DOC/'path-distributions.csv');mt=pd.read_csv(DOC/'matched-summary21.csv');strict=mt[mt.scheme==3]
    base=pd.read_csv(DOC/'base-rates.csv');year=pd.read_csv(DOC/'classification-yearly.csv');eq=pd.read_csv(DOC/'equal-stock.csv')
    v=json.loads((DOC/'verification-final.json').read_bytes());vv=json.loads((DOC/'verification-extension.json').read_bytes())
    coverage=pd.read_csv(DOC/'evaluate-coverage.csv');coverage=coverage[coverage.period=='test']
    text=['# 미사용 기술적 지표를 더하면 하락 초입을 더 믿을 만하게 확인할 수 있는가?\n',
      '추가 연구 DOWNTREND-EXTENSION-20261029 · 한국/미국 별도 · 연구 완료 2026-10-29\n',
      (DOC/'conclusion.md').read_text(encoding='utf-8'),
      '\n## 무엇을 어떻게 비교했는가\n',
      '기존 연구에 없던 **9개 지표군의 12개 사건 신호**와, 조건을 바꾸지 않은 기존 6개 신호를 비교했다. 계산 전 후보·설정을 고정했고, 결과를 보고 기간이나 임계값을 다시 조정하지 않았다. 과거 선정 기간에서는 한국 RMI70, 미국 RMI70·SAR가 보고서의 우선 검토 대상으로 정해졌다. 나머지 후보도 모두 평가·공개했다.\n',
      '공통 입력은 7,426개 목록 중 사용 가능한 **7,237종목(KR 2,584·US 4,653)**의 저장 이력이다. 나머지 189개는 짧은 이력160·충분한 연속 유효 구간 부재27·빈 자료2개다. 모든 종목이 모든 지표·기간의 통계에 기여하는 것은 아니다. 원자료 종료는 늦어도 2026-09-30이며, 보유 이력 전부의 기술통계와 기간별 결과를 CSV에 담았다. 아래 주 결과는 2023-04-01~2025-09-30이다. **이미 검토했던 TEST를 다시 사용한 추가 탐색이며, 새 독립 검증이 아니다.** 현재 상장 중심 자료의 생존편향도 남는다.\n',
      '하락 정의는 기존 로그종가 L1 추세 필터·λ=1을 그대로 유지했다. 하루 로그기울기 `x[t+1]−x[t] < −0.000001`이면 하락, `> +0.000001`이면 상승, 양 경계를 포함한 사이는 횡보다. 20거래일 가격변화로 환산하면 경계는 약 **−0.00199998% / +0.00200002%**다. 사후 완성된 ≥10거래일 하락의 **시작 당일~5거래일 뒤, 총6일**을 초입으로 평가했다. L1은 사후 정답표이며 신호 계산에는 들어가지 않는다.\n',
      '발생 사건을 센다. 하락 상태가 5일 유지됐다고 5번 세지 않고, 새 교차·새 반전·재이탈 때 다시 센다. MACD+RSI는 MACD가 하향 교차하는 날에 최근3일의 RSI60 이탈 여부를 확인한다. 프랙탈은 중앙 저가의 오른쪽 두 봉이 완료된 뒤에만 사용할 수 있다. 상세 산식은 '+link('KR-signal-definitions.csv','신호 정의 CSV')+'와 '+link('literature.md','논문·산식 검토')+'에 있다.\n',
      '\n## 한국·미국 핵심 결과\n',
      '적중률은 **초입에 발생한 신호 / 평가 가능한 모든 신호**다. 시작 전 신호·늦은 신호도 분모에 남는다. 기저율은 같은 지표를 평가할 수 있었던 전체 거래일 중 초입 거래일의 비율이다. 포착률은 실제 하락 구간 중 초입 신호가 한 번이라도 발생한 비율이다. 대괄호는 종목·공통 시기 의존성을 반영한 주변95% 구간이며, 신호 간 차이의 다중비교 보정 구간과 구별한다.\n']
    for m,title in [('KR','한국'),('US','미국')]:
        d=s[s.market==m];text.append(f'\n### {title}\n')
        rows=[]
        for _,r in d.iterrows():rows.append([NAMES[r.id]+(' (기존)' if not r['new'] else ''),num(r.signals),f'{pct(r.precision)} [{pct(r.precision_low)}, {pct(r.precision_high)}]',pct(r.early_base),f'{r.early_lift:.2f}배',pct(r.capture)])
        text.append(table(['신호','전체 신호 수','초입 적중률 % [95%]','기저율 %','기저율 대비','포착률 %'],rows))
        text.append(image(m+'-tradeoff.png',title+' 정확성·포착률·지연 비교'))
        text.append('왼쪽은 모든 알림 중 실제 초입의 비율, 오른쪽은 실제 하락을 발견한 비율이다. 작은 세로 표시는 각 신호의 기저율이다. 높고 넓은 포착만으로 좋은 신호를 정하지 말고, 함께 적힌 지연·빈도를 보아야 한다. 개별 구간이 겹치는지만으로 신호 간 우열의 유의성을 판단할 수는 없다. 직접 비교는 '+link('paired-benchmarks.csv','보정된 차이 CSV')+'에 있다.\n')
        rows=[]
        for _,r in d[d.id.isin(FOCUS)].iterrows():rows.append([NAMES[r.id],pct(r.missed),f'{r.mean_delay:.2f}',f'{r.annual:.2f}',pct(r.first_drop)])
        text.append(table(['주요 신호','놓친 하락 %','평균 확인 지연(거래일)','종목·252일당 발생','확인까지 이미 내린 폭 %'],rows))
    text.append('지연과 이미 내린 폭은 **초입 확인에 성공한 구간의 첫 신호만**을 대상으로 한다. 놓친 하락·늦은 신호까지 평균 지연에 들어가는 것은 아니다. 이미 내린 폭은 `1−신호 다음 연속 유효 거래일 시가/사후 하락 시작일 종가`다. 당시 알 수 없었던 고점에서 팔 수 있었다는 뜻이 아니다.\n')
    text.append(image('timing-tradeoff.png','확인 속도·적중률·포착률의 관계'))
    text.append('왼쪽일수록 빨리, 위일수록 정확하게 확인했고, 점이 클수록 많은 하락을 찾았다. 빠른 신호와 정확한 신호 사이의 대가를 읽는 그림이다. 조건부 평균 지연이 작다는 사실만으로 실전에서 안전한 알림이라고 해석하지 않는다.\n')
    text.append('\n## 평소에도 흔한가, 초입에 집중되는가\n')
    rows=[]
    for m in ['KR','US']:
        for _,r in raw[(raw.market==m)&raw.id.isin(FOCUS)].iterrows():rows.append([m,NAMES[r.id],pct(r.ordinary_rate),pct(r.early_rate),f'{100*r.rate_difference:+.2f}',f'{r.rate_ratio:.2f}배',f'{100*r.context_difference:+.2f}',pct(r.context_support)])
    text.append(table(['시장','신호','상승·횡보일 발생 %','하락 초입일 발생 %','차이 %p','발생 배수','비슷한 상태 대비 초입확률 차이 %p','비교 유지 %'],rows))
    text.append('발생률은 모두 **하루 단위**다. 뒤 두 열은 동일 종목·같은 달·당시의 MA20 기울기/가격 위치/RSI 상태를 맞춘 신호일과 비신호일의 기술통계다. 비교 대상을 맞추기 전 적중률과 분모가 다르고, 남은 연속 상태 차이는 제거하지 못한다. 이 차이 자체를 인과효과로 읽지 않는다. 이후 가격에 대한 더 엄격한 비교는 아래에서 따로 수행했다.\n')
    for m in ['KR','US']:text.append(image(m+'-frequency.png',m+' 평소·초입·중후반의 일별 발생률'))
    text.append('세 색 막대는 모두 같은 길이의 관측 단위를 사용한다. 초입 막대가 평소보다 높으면 집중된 것이지만, 중후반에서도 자주 울릴 수 있다. 따라서 이 그림은 “울렸을 때 초입일 확률” 표를 대신하지 않는다.\n')
    text.append('\n## 초입과 하락 기간 전체는 다른 질문이다\n')
    rows=[]
    for m in ['KR','US']:
        for _,r in s[(s.market==m)&s.id.isin(FOCUS)].iterrows():rows.append([m,NAMES[r.id],pct(r.precision),pct(r.whole_precision),pct(r.whole_base),pct(r.late),pct(r.short),pct(r.other)])
    text.append(table(['시장','신호','초입 %','전체 ≥10일 하락 %','전체 하락 기저율 %','늦은 확인 %','짧은 하락 %','그 밖 %'],rows))
    text.append('초입+늦은 확인=전체 ≥10일 하락 적중률이다. 초입+늦은 확인+짧은 하락+그 밖은 100%다. 시작 전5일의 발생은 성공에서 제외되어 “그 밖”에 남는다. 시작 당일·1~5일·시작 전의 별도 비율과 전체 하락 기저율 대비 검정은 '+link('primary-summary.csv')+'·'+link('base-rates.csv')+'에서 확인할 수 있다. 하락 전체 적중률이 높아도 대부분 늦었다면 이번 초입 질문의 우수 신호가 아니다.\n')
    text.append('\n## 신호 뒤에도 더 내렸는가\n')
    def pathrow(m,key,pop='all'):
        a=p[(p.market==m)&(p.id==key)&(p.population==pop)&(p.horizon==21)].set_index('outcome')
        return [num(a.loc['return','n']),pct(a.loc['loss05','mean']),pct(a.loc['gain05','mean']),pct(a.loc['adverse','mean']),f"{100*a.loc['return','mean']:+.2f}",f"{100*a.loc['return','median']:+.2f}"]
    rows=[]
    for m in ['KR','US']:
        for key in FOCUS:rows.append([m,NAMES[key],*pathrow(m,key)])
    text.append(table(['시장','신호','전체 경로 신호 수','−5% 접촉 %','+5% 접촉 %','최대 추가하락 평균 %','21일 종가 평균 %','중앙값 %'],rows))
    text.append('기준은 **신호 다음 연속 유효 거래일 시가**, 관측은 그날부터21개 봉이다. 하락·반등 접촉에는 그 기간의 저가·고가, 종가 수익률에는21번째 봉 종가를 쓴다. 한 경로에서 양쪽에 모두 닿을 수 있다. 최대 추가하락은 경로상의 최저가까지 깊이이며 실제 피할 수 있었던 손실·실현수익이 아니다. 5/63일 및 분포의10·90백분위는 '+link('path-distributions.csv')+'에 포함했다.\n')
    rows=[]
    for m in ['KR','US']:
        for key in ['rmi70','macd_rsi60','cci100_up20']:rows.append([m,NAMES[key],*pathrow(m,key,'early_hit')])
    text.append('\n초입 확인에 실제 성공한 경우만 따로 보면:\n')
    text.append(table(['시장','신호','성공 경로 수','−5% 접촉 %','+5% 접촉 %','최대 추가하락 평균 %','21일 종가 평균 %','중앙값 %'],rows))
    text.append('이 하위표는 사후에 성공한 사례의 설명이다. 당시에는 성공 여부를 몰랐으므로 실전 알림의 미래 정보는 위 전체 신호와 아래 비신호일 비교로 판단해야 한다.\n')
    text.append('\n### 비슷한 상태의 비신호일과 비교\n')
    rows=[]
    for m in ['KR','US']:
        for _,r in strict[(strict.market==m)&strict.id.isin(FOCUS)].iterrows():rows.append([m,NAMES[r.id],num(r.matched_signals),pct(r.support),pct(r.loss05_signal),pct(r.loss05_control),f'{100*r.loss05_difference:+.2f} [{100*r.loss05_sim_low:+.2f}, {100*r.loss05_sim_high:+.2f}]',f'{r.max_abs_smd:.2f}'])
    text.append(table(['시장','신호','비교 가능 신호 수','전체 중 유지 %','−5% 접촉 신호 %','비신호 %','차이 %p [다중보정95%]','최대 잔여 SMD'],rows))
    text.append('동일 종목·같은 분기에서 MA/RSI 상태, 변동폭, 당일·5일·20일 수익률, MA20과 거리를 미리 고정한 구간으로 맞췄다(가장 엄격한 scheme3). **사후 L1 하락일만 고르지 않았다.** 차이 구간이0 위에 있으면 이 비교 범위에서 추가 하락 접촉이 더 잦다는 근거다. 비교 가능한 신호만 남으므로 유지율이 낮거나 SMD(남아 있는 상태 차이)가 크면 전체 알림으로 일반화하기 어렵다. SMD가 작아도 뉴스·실적 등 관측하지 않은 차이는 남는다. 비교 조건을 완화한 scheme0~2도 '+link('matched-summary21.csv')+'에 전부 공개했다.\n')
    for m in ['KR','US']:text.append(image(m+'-matched.png',m+' 비슷한 비신호일 대비 이후 경로 차이'))
    text.append('0선을 기준으로 추가 하락·반등·종가 변화가 어느 방향인지 함께 본다. 선은 이번 고정된3,456개 비교를 보정한 구간이며, 3/6개월 블록 설정의 넓은 쪽 경계를 사용했다. 양의 하락 차이가 있어도 매도 후 언제 재진입할지·얼마를 팔지·비용이 어떤지는 이 그림이 알려주지 않는다.\n')
    text.append('\n## 성공과 실패의 실제 가격 경로\n')
    for m in ['KR','US']:text.append(image(m+'-cases.png',m+' 실제 성공·실패·늦은 확인 사례'))
    text.append('빨간 세로선이 신호 종가일이고, 빨간 점이 다음 시가 기준100이다. 파란선은 종가, 노란선은 사후 L1, 옅은 영역은 ≥10일 하락의0~5일 구간이다. 성공·하락 밖의 실패·늦은 확인을 각각 표시했다. 예시는 각 집단의21일 종가 경로 중앙값에 가까운 사례로 골랐으므로 무작위 대표 표본이나 성능의 증명은 아니다. 사후 실패 신호 뒤에도 실제 가격은 내려갈 수 있다. 정확한 종목·날짜·가격은 '+link('illustrated-cases.csv')+'에 있다.\n')
    text.append('\n## 보조 분석: 기간·연도·가중치에 따라 달라지는가\n')
    dur=pd.read_csv(DOC/'evaluate-duration.csv');rows=[]
    for _,r in dur[(dur.period=='test')&(dur.duration!='all')&dur.id.isin(['rmi70','psar','macd_rsi60','cci100_up20'])].iterrows():rows.append([r.market,NAMES[r.id],r.duration,num(r.episodes),pct(r.capture),f'{r.mean_delay:.2f}',pct(r.first_drop)])
    text.append(table(['시장','신호','사후 지속기간','하락 구간 수','포착 %','지연','이미 하락 %'],rows))
    text.append('오래 이어질 하락을 당시 구별할 수 있었다는 뜻은 아니다. 주 결론은 전체 ≥10일 하락을 기준으로 유지한다. 0~3/0~10일로 창을 바꾼 결과는 '+link('evaluate-sensitivity.csv')+'에 있으며 창이 넓어지면 맞힌 비율이 기계적으로 높아질 수 있다.\n')
    sens=pd.read_csv(DOC/'evaluate-sensitivity.csv');rows=[]
    for _,r in sens[(sens.period=='test')&sens.id.isin(['rmi70','macd_rsi60','cci100_up20'])].iterrows():rows.append([r.market,NAMES[r.id],r.window,pct(r.precision),pct(r.capture)])
    text.append(table(['시장','신호','확인 범위','적중률 %','포착률 %'],rows))
    text.append('0~10일의 RMI70 포착은 MACD+RSI보다 높다. 그러나 기다리는 기간을 늘린 다른 질문이며, 본문의0~5일 비교용 신뢰구간을 그대로 붙일 수 없다.0~3일로 줄이면 MACD+RSI 적중률은11.9%/11.4%로 낮아져,4~5일 확인이 주 결과에 크게 기여함도 드러난다.\n')
    rows=[]
    for m in ['KR','US']:
        for key in ['rmi70','psar','macd_rsi60','cci100_up20']:
            a=year[(year.market==m)&(year.id==key)].set_index('year');e=eq[(eq.market==m)&(eq.id==key)].iloc[0]
            rows.append([m,NAMES[key],*[pct(a.loc[y,'early_precision']) for y in [2023,2024,2025]],pct(e.early_precision),pct(e.early_base_equal_signal_stocks)])
    text.append(table(['시장','신호','2023 적중 %','2024 적중 %','2025 적중 %','종목 동일가중 %','같은 종목 기저율 %'],rows))
    text.append('2023·2025는 평가 기간에 포함된 일부 월이다. 동일가중은 알림이 발생한 종목 각각의 적중률을 평균하며, 신호 건수 가중과 질문이 다르다. 비교 기저율도 같은 종목으로 맞췄다. 이후 위험의 연도·동일가중 결과는 '+link('path-yearly.csv')+'·'+link('path-equal-stock.csv')+'에 있다.\n')
    text.append('\n## 통계 항목을 어떻게 읽으면 되는가\n')
    text.append('평소 발생률은 경보기가 요리할 때도 얼마나 자주 울리는지에 해당한다. 포착률은 실제 화재 중 경보를 울린 비율, 적중률은 경보가 울렸을 때 진짜 화재였던 비율이다. 많이 울리면 포착은 높아질 수 있지만 적중이 좋아지는 것은 아니다. 확인 지연은 불이 얼마나 번진 뒤 알려주는지이며, 여기서는 성공한 첫 신호까지 며칠인지와 이미 하락한 폭을 함께 봤다.\n')
    text.append('비슷한 상태의 비교는 같은 환경에서 경보가 울린 날과 안 울린 날을 비교하는 것이다. 이미 많이 내린 날·변동성이 큰 날이라는 사실을 넘어 신호에 정보가 남는지 묻는다. 신뢰구간은 이 자료로 추정한 값의 흔들림 범위이지, 다음 알림이 맞을 확률의 범위가 아니다. 같은 날 여러 주식이 함께 움직이므로 종목 수만 많다고 구간이 좁아져서는 안 된다.\n')
    text.append('여러 사람에게 동전을 던지게 하면 우연히 연승하는 사람이 생기듯, 지표를 많이 비교하면 우연한 우승자가 생긴다. 이번에는 후보를 고정하고 여러 비교를 함께 보정했지만 과거부터 이어진 탐색 이력까지 완전히 지운 것은 아니다. 이미 풀어 본 시험지를 다시 푼 것과 새 시험 성적은 구별해야 한다. 사후 L1은 경기가 끝난 뒤 영상을 돌려본 판정, 신호는 경기 중 알 수 있는 정보에 대응한다.\n')
    text.append('\n## 평가 제외·검증·계산 자료\n')
    text.append(table(['시장','기간 안 거래일','과거65봉 부족','미래126봉/추세자료 부족','미완료 하락','공통 평가 가능일'],[[r.market,num(r.dated),num(r.history_short),num(r.future_short),num(r.censored_down),num(r.valid)] for _,r in coverage.iterrows()]))
    text.append('위 제외 사유는 공통 평가 틀의 집계다. 지표별 준비 기간·StochRSI 범위0·VWAP 앵커 초기는 별도 결측이어서 지표별 분모가 추가로 다르다. 관측 부족·미완료 추세를 실패 또는 짧은 하락으로 바꾸지 않았다. 가격경로는63봉 및 관측 상태 조건을 쓰므로 신호 수가 위 분류 표와 다를 수 있으며 불일치를 개별 마스크로 대조했다. 초입 성공 사례 중에서는 한국 SAR·종가5일선 이탈에서 각각1건이 관측 상태 결측 때문에 가격경로 표에서 빠졌고, 나머지 신호의 성공 건수는 일치했다.\n')
    text.append(f"기존 신호 {num(v['original_benchmark_flag_cells'])}개 종목-날짜-조건 값과 기존 요약 {num(vv['benchmark_numeric_cells'])}개 수치가 일치했다. 전체 신호 경로 {num(v['ledger_rows'])}건을 집계와 대조했고, 독립 가격경로·매칭 검사는 {num(v['scalar_horizon_checks']+v['matched_horizon_checks'])}개 기간 계산을 확인했다. 이는 가격 원자료 전체를 새로 외부 검증했다는 뜻은 아니다. 기존80종목 종료일 민감도 감사는 가격·L1 정의가 같아 재사용했고, 새 지표의 미래정보 누출 여부는 별도로 검사했다.\n")
    text.append('계산 전체: '+link('results-csv.zip','CSV 묶음')+' · '+link('primary-summary.csv','주 결과')+' · '+link('matched-paths.csv','상태 비교 가격경로')+' · '+link('episode-overlap.csv','기존 신호가 놓친 하락 포착')+' · '+link('methods.md','상세 방법')+' · '+link('verification-final.json','검증 기록')+'.\n')
    text.append('기존 신호가 놓친 구간을 새 지표가 추가로 찾았다는 사실은 OR 결합 알림의 적중률을 검증했다는 뜻이 아니다. 이번에는 결과를 본 뒤 조합을 덧붙이지 않았다. 재현 코드는 [연구 실행 안내](../../scripts/research/downtrend_extension/README.md)에 있으며, 원자료·운영 감시·계좌·매매 조건은 변경하지 않았다.\n')
    REPORT.write_text('\n'.join(text),encoding='utf-8');print(REPORT,flush=True)

if __name__=='__main__':main()
