# 하락 초입 장기 재검증

기존 하락 신호63개, 과거 고정 후속6개, 추가12개를 한국·미국 각각 평가한다.
공통15년은2010-10-01~2025-09-30이며 짧은 종목도 최초 평가 가능일부터 포함한다.
모든 보유 이력은 보조 결과다. 운영 데이터·다른 상승 연구는 읽기만 한다.

입력 정본은 `runtime/downtrend-longhistory-20261029/inventory.json`의 `cache_path`이다.
기존7,426개와 연구용 추가57개를 모두 시도한7483개 목록이며, 가격/L1캐시는
기존 복원 자료와 `uptrend-longhistory-20261029/supplemental`을 원위치에서 재사용한다.
원시 가격 이력을 복제하거나 새로 수집하지 않는다. 이전 계산의 수정가격·결측 처리를 유지한다.

재현 환경은 인접 엔진 `.venv/Scripts/python.exe`(numpy/pandas/matplotlib)다.
`prepare.py`는 최초 파생 기록이며 일반 재현 때 실행하지 않는다. 커밋된 runner를 사용한다.
`coverage_audit.py` → `verify_features.py` → `study.py evaluate --workers 3` →
`study.py aggregate-evaluate` → `infer.py classification --stock-chunk 8` →
`verify_results.py` → `paths.py --workers 3` → `infer.py paths --stock-chunk 8` →
`verify_paths.py --real` → `cases.py` → `report.py` → `package.py` 순서다.
`cases.py --reconcile-only`는 이미 생성한 분포를 전체81조건 경로 평균과 다시 대조한다.
`endpoint_recheck.py`는 기존40종목의3개 종료일 L1 계산을 읽어 하락 정답의 수정 정도를 검사한다.
추론 실행에는 `OPENBLAS_NUM_THREADS=4`를 사용했다. 숫자·그림·링크·ZIP 검증 영수증은 결과 폴더에 있다.

저장 공간 때문에 분류 추론과 전체 검증을 마친 뒤 이번에 만든 `evaluate/*.npz`7293개만
`release_classification_cache.py`로 해시를 남기고 제거했다. 원자료·이전 연구·결과CSV·가격경로
캐시는 보존한다. 분류 추론/종목별 검증을 다시 실행하려면 먼저 `study.py evaluate`로 해당
파생 캐시를 재생성해야 한다. 이 정리 스크립트는 재현에 필요한 필수 단계가 아니다.
`prepare.py`를 재실행하거나 다른 상승 연구의 파일을 수정할 필요는 없다.

가격경로 추론 완료 후에는 `release_path_cache.py --target-free-gb 1.5`로 필요한 저장
여유만 확보했다. 처리한 파일의 정확한 신호 원장 4배열은 `ledgers`에 바이트 대조해
보존하고, 나머지 종목의 전체 `paths` 캐시는 유지했다. 두 폴더를 합쳐 7,293개 종목이
그대로 남으며 `cases.py`는 혼합 입력을 지원한다. 경로 추론을 다시 실행할 때는 먼저
`paths.py`로 빠진 월별 배열을 재생성한다. 원자료·과거 결과는 이 정리 대상이 아니다.

L1은 사후 평가표다. 신호·가격경로 대조군에 넣지 않는다. 이미 보았던 과거의 범위 확대이며
독립 새 검증이나 실행 가능한 매도 전략 수익률로 해석하지 않는다.
월별 분류 캐시에는 중복 가격경로 통계열을 저장하지 않고 연도별 통계를 미리 합산하여
같은 충분통계와 float64 정밀도를 유지하면서 저장 공간을 줄인다.
