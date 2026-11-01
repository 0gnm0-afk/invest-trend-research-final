# 추가 하락 연구의 논문·산식 검토

2026-10-29 원문을 확인했다. 논문은 연구 설계의 근거이며, 아래 특정 지표가 한국·미국의 0~5일 하락 초입을 잘 찾는다는 증거로 인용하지 않는다. 산식 설명서의 매매 권고도 효과가 검증됐다는 뜻으로 받아들이지 않는다.

| 학술 자료 | 이번 연구에 적용한 판단 |
|---|---|
| Kim, Koh, Boyd & Gorinevsky (2009), SIAM Review, [L1 Trend Filtering](https://stanford.edu/~boyd/papers/pdf/l1_trend_filter.pdf) | 로그가격의 구간별 선형 추세를 평가 정답으로 사용한다. λ=1은 기존 연구의 선택이며 보편적 최적값이 아니다. 미래 가격을 사용하는 추세를 실시간 신호 조건에 넣지 않는다. |
| Lo, Mamaysky & Wang (2000), Journal of Finance, [Foundations of Technical Analysis](https://www.mit.edu/~wangj/pap/LoMamayskyWang00.pdf) | 패턴을 객관적 계산으로 정의하고, 조건부 가격 분포가 평소와 다른지 검토한다. 상태 분류 능력·추가 가격 정보·거래 이익은 각각 다른 주장이다. |
| Sullivan, Timmermann & White (1999), Journal of Finance, [기관 공개 작업논문](https://www.fmg.ac.uk/sites/default/files/2020-11/dp303.pdf) | 후보 전체를 사전 고정하고 모두 보고한다. 시간 의존성을 반영해 여러 비교를 보정한다. 이번 최대통계량 보정은 분류·가격경로 차이에 대한 보정이지 수익 전략의 White Reality Check를 실행했다는 주장은 아니다. |
| Bajgrowicz & Scaillet (2012), Journal of Financial Economics, [저자 공개본](https://scaillet.ch/pdfs/BajSca.pdf) | 과거 우수 규칙의 미래 지속성과 거래비용은 별도 검증 문제다. 이미 본 TEST를 새 검증으로 부르지 않고, 저점까지 낙폭을 회피 가능한 손실로 바꾸지 않는다. |

네 논문의 일반적인 교훈을 적용하되, 서로 다른 목적의 연구를 그대로 복제했다고 주장하지 않는다. 특히 현재 신호 탐색은 거래비용을 포함한 매도·재진입 전략 검증이 아니다.

## 왜 이 지표들을 추가했는가

| 지표군·고정 설정 | 새로 확인할 정보 | 산식 근거·해석의 한계 |
|---|---|---|
| 슈퍼트렌드 ATR10×3 | 변동폭을 반영한 추적선의 하락 전환이 초입 확인에 도움 되는가 | [TradingView 산식](https://www.tradingview.com/support/solutions/43000634738-supertrend/). 종가 시점의 방향 전환. 지연 가능성을 평가에 포함. |
| 파라볼릭 SAR .02/.02/.20 | 시간 경과와 고저점에 따라 추적선이 가속되는 방식이 도움 되는가 | [TradingView 알고리즘](https://www.tradingview.com/support/solutions/43000502597-parabolic-sar-sar/). 초기 방향은 첫 두 종가로 결정; 장중 체결을 가정하지 않음. |
| TRIX18, 신호 EMA9 | 세 번 평활한 모멘텀이 잡음을 줄이는 대신 얼마나 늦어지는가 | [TradingView 설명](https://www.tradingview.com/support/solutions/43000502331-trix/). 0선·신호선 이탈을 별도 사건으로 고정. |
| StochRSI14/14/3/3 | RSI 자체의 최근 범위에서 힘이 약해지는 순간을 더 빨리 확인하는가 | [TradingView 산식](https://www.tradingview.com/support/solutions/43000502333-stochastic-rsi-stoch-rsi/). K80 이탈과 전일 K≥80에서 K/D 교차. RSI 범위0이면 결측. |
| RMI20/5, 70·50 이탈 | 하루 변화 대신 5일 변화를 누적하면 정확성이 개선되는가 | [Infront 산식·기본값](https://infront-portfolio-manager.helpcenter.infront.co/en/pm/latest/relative-momentum-index). 70은 과열 약화, 50은 방향 균형 가설. |
| 체이킨3/10 | 일중 종가 위치와 거래량의 누적 변화가 가격만 보는 신호에 정보를 더하는가 | [TradingView 산식](https://www.tradingview.com/support/solutions/43000501979-chaikin-oscillator/). ADL의 두 EMA 차이; 매수·매도 주체를 직접 관측한 자료는 아님. |
| 분기 고정 VWAP 대용치 | 거래량 가중 기준가격 아래로 내려가는 사건이 의미 있는가 | [TradingView 산식·앵커](https://www.tradingview.com/support/solutions/43000502018-volume-weighted-average-price-vwap/). 일봉 대표가격×거래량을 누적한 대용치; 실제 체결 VWAP가 아님. 사후 고점 앵커 금지. |
| 거래량 오실레이터5/20+하락일 | 거래량 증가가 동반된 약화에 추가 정보가 있는가 | [Fidelity 설명](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/volume-oscillator). 거래량 자체에는 방향이 없으므로 음의 당일 수익률을 함께 요구. |
| 확정 5봉 저점 프랙탈 이탈 | 최근의 확정 지지 저점 붕괴가 고정 기간 저가 이탈과 다른가 | [TradingView 설명](https://www.tradingview.com/support/solutions/43000591663-williams-fractal-indicator/). 중앙 저가가 양옆 두 봉보다 엄격히 낮아야 하며, 오른쪽2봉 이후에만 사용. 피벗 날짜로 신호를 소급하지 않음. |

앱과 같은 이름이어도 초기화·가격 수정·거래량 수정·동률 처리에 따라 표시가 다를 수 있다. 이번 코드는 위 고정 정의를 검증한다.

## 제외한 후보

매물대와 실제 장중 VWAP는 일봉만으로 정확히 복원할 수 없다. 엔벨로프·이격도·가격 오실레이터·%B·모멘텀은 기존 MA·MACD·밴드·ROC 조건과 겹치는 부분이 커서 우선순위를 낮췄다. 윌리엄스 %R은 동일 기간의 원시 스토캐스틱 위치와 같은 정보를 다른 척도로 표현한다. 메스 인덱스는 고저가 범위 확대를 다루는 비방향 지표이므로 별도 방향 조건을 더해 탐색 범위를 늘리지 않았다. AD 라인은 이번 체이킨의 구성요소다. 이 제외는 ‘효과 없음’의 실험 결과가 아니다.
