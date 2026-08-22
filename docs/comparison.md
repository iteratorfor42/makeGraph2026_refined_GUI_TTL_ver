# 원본(makeGraph2022.exe)과의 비교 검증

이 저장소는 Windows 전용 실행파일(`original/makeGraph2022.exe`)을 직접
실행할 수 없는 환경에서 개발되었다. 아래 절차는 **Windows 환경에서
직접 수행**해야 하는 검증 가이드다.

## 절차

1. `original/makeGraph2022.exe`와 `samples/*.lst`를 Windows PC로 복사한다.
2. 각 `.lst` 파일을 원본 EXE에 드래그&드롭하여 `.htm`을 생성한다.
   - 결과를 `docs/comparison-results/original/예제1.htm` 형태로 저장.
3. 동일한 `.lst`를 재구현판(GUI 또는 CLI)으로 변환한다.
   - GUI: `dist/makegraph.exe` 실행 → 파일 열기
   - CLI: 필요하다면 `src/makegraph.py`를 직접 호출하는 스크립트를 작성해도 된다.
4. 두 HTML을 같은 브라우저에서 열어 아래 항목을 비교하고 표에 기록한다.

| 항목 | 원본 | 재구현 | 일치 여부 | 비고 |
|---|---|---|---|---|
| Normal layout 초기 배치 | | | | |
| Horizontal layout | | | | |
| Vertical layout | | | | |
| Node shape/color | | | | |
| Node icon 표시 (0/1/2) | | | | |
| Hyperlink 클릭 동작 | | | | |
| Relation arrow 스타일 | | | | |
| moving-arrows 애니메이션 | | | | 재구현은 점선으로 근사 |
| sequence 색상/굵기 | | | | |
| Relation label 표시 옵션 (0/1/2/3) | | | | |
| 오류 발생 시 화면 | | | | |

5. 차이가 발견되면 `src/makegraph.py` / `src/ttl_loader.py`를 수정하고
   `tests/test_makegraph.py`에 회귀 테스트를 추가한다.

## 현재까지 알려진 의도적 차이

README.md의 "알려진 한계" 항목 참고. 특히 `moving-arrows`의 애니메이션
재현은 Windows 환경에서 원본 동작을 직접 관찰한 뒤 결정한다.
