# 전체 저장 이력의 하락 초입 지표 연구

2026-10-21 사용자 요청의 재현 코드. 운영 대시보드와 연결되지 않는다.

1. `verify.py`: L1 선형계의 dense/scalar 대조, 목적함수, 지표 prefix, RSI/밴드 독립 검산.
2. `run.py prepare --workers 4`: 입력 목록/원본 해시를 고정하고 전체 저장 가격의 지표·L1 적합을 계산한다.
3. `supplement.py`: 이전 세션의 고유 KR 역사 이력 및 저장 ADR 차트를 더한다. 중복 종목은 전수 보관소 원본을 우선한다.
4. `run.py summary --workers 4`: 모든 시작점과 모든 신호일의 충분통계를 만든다.
5. `audit.py`: 전 종목 캐시·원장 불변식, 분산 표본의 원가격/사건을 확인하고 CSV 시작점 원장을 쓴다.
6. `research_stats.py aggregate`: 전체 결과를 집계하고 TRAIN 후보를 동결한다.
7. `research_stats.py validate`: 선정 후보의 TEST 군집 신뢰구간과 엄격한 미래 시작 비교를 계산한다.
8. `report.py`: 보고서·CSV·그림을 `docs/`에 저장한다.

고정 연구 폴더는 `runtime/downtrend-indicators-20261021`이다. 필요한 SciPy는 그 아래 `dependencies/`에 격리 설치하며, 기존 엔진 Python 환경의 NumPy/pandas/matplotlib/exchange_calendars를 사용한다. 실제 실행은 Python3.12, SciPy1.18.1을 사용했다. 모형이나 입력을 바꾸면 새 연구 폴더로 분리해야 한다. 기존 캐시는 동일 입력의 재개 전용이다.

`protocol.json`은 전체 결과 순위를 보기 전 정한 규약이다. 입력 조사 중 발견한 추가 이력33+3개와, 선행/초기 확인을 혼동하지 않기 위한 엄격한 미래1~5일 비교를 결과 열람 전에 명시했다. 이 연구의 TRAIN/TEST 기간은 이전 연구에서도 본 역사이므로 미사용 미래 데이터라는 주장을 하지 않는다.

숫자 적합은 이전 세션의 `l1_solver.py` 목적함수와 알고리즘을 재사용한다. 반복 선형계만 SciPy의 대역 Cholesky로 가속했고 원 scalar 풀이를 검증용으로 남겼다. 지표 계산/모든 입력은 과거까지지만 L1 정답 라벨은 미래를 사용한다.

초기 실행 중 겹친 준비 작업이 생성 JSON2개를 쓰는 동안 읽은 충돌은 재검사로 해소했다. 최초 실패 기록은 runtime에 보존했다. JSON과NPZ는 원자적으로 공개하도록 수정했으며 전체 입력7426건의 후속 준비 재검증은 실패0이었다. 재현은 위 순서로 한 단계씩 실행한다.

표에서 `all`, `train`, `test`는 별도 집계다. 같은 시작점이 `all`과 다른 기간에 중복되므로 합쳐서 독립 사건 수를 늘리면 안 된다. 결측 신호는−1이다. `all-63-indicators.csv.gz`의 각 window 포착률을 더해서 전체 포착률로 만들지 않는다.
