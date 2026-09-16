# MakeGraph — 온톨로지 네트워크 그래프 뷰어

한국학중앙연구원 디지털인문학연구소의 `makeGraph2022.exe`를 윈도우11 환경에서
사용할 수 있도록 재구현한 프로그램입니다.
기존 실행파일 경우 윈도우11에서는 열리지 않아서 만들었습니다.

`.lst`(MakeGraph2022 온톨로지 스크립트) 또는 `.ttl`(RDF/Turtle 온톨로지) 파일을 열면,
Vis.js 기반 네트워크 그래프 HTML을 생성해 브라우저로 보여줍니다.
필자는 .ttl로 작업했고, 작업 원본 캡처는 다음과 같습니다.

![MakeGraph GUI로 .ttl 파일을 열어 생성한 네트워크 그래프 예시]
(docs/images/visualization-example.png)

(구현 가능성을 보이기 위해 이 작업을 했을 뿐,
링크 연결 및 가시성 측면에서 html에 직접 작업한 자료가 훨씬 사용자 친화적[user-friendly]입니다.)

또한 이번 개선본은 제가 처음 만든 버전처럼 커맨드라인이 아니라 **더블클릭으로 실행되는 GUI 창**에서
"파일 열기"로 온톨로지 파일을 불러오는 방식입니다. (Protégé와 비슷한 사용성).

> 본 프로젝트는 공개된 사용 설명서(매뉴얼)에 기술된 입력 문법과 동작
> 규칙만을 근거로 한 클린룸(clean-room) 재구현입니다.
> `original/`의  원본 실행파일은 비교 검증용 참고 자료로만 보관하며,
> 코드를 그대로 이식하지 않았습니다.
>
> ⚠️ **중요한 구분**
> - `run.bat` / `python src/gui.py` → **앱을 실행만** 합니다 (exe 생성 X)
> - `build.bat` / `python src/build_exe.py` → **`dist/makegraph.exe`를 생성**합니다
>
> "실행"과 "빌드"는 서로 다른 별개의 작업입니다.

---

## 저장소 구조

```text
makegraph/
│
├─ README.md
├─ requirements.txt
├─ run.bat                     # 더블클릭 → 앱 실행 (exe 생성 안 함)
├─ build.bat                   # 더블클릭 → dist/makegraph.exe 생성
│
├─ original/
│  └─ makeGraph2022.exe        # 원본 보관 (수정하지 않음, 비교 검증용)
│
├─ src/
│  ├─ gui.py                   # 진입점 — 더블클릭으로 실행되는 GUI 앱
│  ├─ makegraph.py             # .lst 파서 + Vis.js HTML 렌더러 (핵심 엔진)
│  ├─ ttl_loader.py            # .ttl → makegraph 데이터 구조 변환
│  └─ build_exe.py             # Windows용 makegraph.exe 빌드 스크립트
│
├─ samples/
│  ├─ example.lst              # 매뉴얼 "전체 예제"
│  ├─ example-icons.lst        # 아이콘 / sequence / 표시옵션 예제
│  ├─ example-error.lst        # 오류 검증 테스트용
│  └─ example.ttl              # TTL 예제 (example.lst와 동일한 내용)
│
├─ tests/
│  └─ test_makegraph.py        # 파서 · TTL 매핑 회귀 테스트
│
└─ docs/
   ├─ comparison.md            # 원본 EXE와의 비교 검증 절차 (Windows 필요)
   └─ images/
      └─ visualization-example.png   # 실제 .ttl 작업 화면 캡처
```

---

## 1) 그냥 실행만 해보기 (exe 없이)

Windows에서 저장소 루트의 **`run.bat`을 더블클릭**하면 필요한 패키지를
자동 설치하고 GUI 창을 띄운다.

또는 터미널에서:

```powershell
pip install -r requirements.txt
python src/gui.py
```

창이 뜨면 **파일 열기**로 `samples/example.lst` 또는 `samples/example.ttl`을 선택한다.
그래프 HTML이 생성되고 자동으로 기본 브라우저에서 열린다.

`.ttl`을 열었는데 rdflib이 없다는 팝업이 뜨면, **"예"를 누르면 자동으로 설치**된다 (인터넷 연결 필요).
설치가 안 되면 터미널에서
`pip install rdflib`을 직접 실행해도 된다.

---

## 2) Windows 실행파일(exe)로 빌드하기

PyInstaller는 크로스 컴파일을 지원하지 않으므로 **반드시 Windows에서** 빌드해야 한다.

Windows에서 저장소 루트의 **`build.bat`을 더블클릭**하면 자동으로 빌드된다.

또는 터미널에서 다음의 코드를 치면 된다.:

```powershell
cd src
python build_exe.py
```

- PyInstaller / rdflib이 없으면 자동 설치
- 결과물: 저장소 루트의 `dist/makegraph.exe` (콘솔창 없는 단일 GUI 실행파일,
  rdflib이 exe 안에 내장되어 있어 별도 설치 없이 TTL도 바로 열림)
- 실행: `dist/makegraph.exe` 더블클릭 → 파일 열기
- 탐색기에서 `.lst`/`.ttl` 파일을 `makegraph.exe`에 드래그해도 바로 열린다
  (원본처럼 drag & drop 실행 방식 지원)

---

## 지원 파일 형식

### 1. `.lst` — MakeGraph2022 온톨로지 스크립트 (원본과 동일 문법)

```text
#Project
h1 나의 첫번째 네트워크 그래프

#Class
사람 blue circle
동물 red box
음식 green ellipse

#Relation
likes 좋아한다 arrow
loves 사랑한다 moving-arrows
isCloseTo 친하다 both

#Nodes
철수 사람 철수
영이 사람 영이
보미 동물 보미
커피 음식 커피
크림 음식 아이스크림

#Links
철수 크림 likes
영이 커피 likes
영이 보미 isCloseTo
철수 영이 loves

#End
```

지원 기능:
- Class 색상 / node shape (`box`, `circle`, `ellipse`, `star`, `triangle`,
  `square`, `dot`, `text`)
- Relation 설명(다른 이름) / 화살표 모양
  (`arrow`, `inverse`, `both`, `moving-arrows`, `line`, `sequence`)
- Relation 표시 옵션 `0/1/2/3` (이름 숨김 / 이름 / 설명 / 이름+설명)
- Node hyperlink, icon, 표시 옵션 `0/1/2` (hover 아이콘 / 아이콘 / 원형 아이콘)
- Normal / Horizontal / Vertical 레이아웃 전환 버튼
- 섹션 미정의, Class/Relation/Node 참조 무결성, UTF-8 인코딩, 홑따옴표(`'`)
  금지 등 검증 → 오류를 네트워크 그래프 형태로 표시

### 2. `.ttl` — Turtle RDF/OWL 온톨로지

RDF에는 `.lst`처럼 명시적인 Class/Relation 섹션이 없으므로
다음 규칙으로 자동 매핑한다 (`src/ttl_loader.py`):

| `.lst` 개념 | TTL에서의 대응 |
|---|---|
| Class | `rdf:type`의 목적어로 쓰인 리소스 (색상/모양은 자동 배정) |
| Node | `rdf:type`을 가진 개체(individual) |
| Node 라벨 | `rdfs:label` 있으면 사용, 없으면 URI 로컬 이름 |
| Node 하이퍼링크 | 개체의 URI (클릭 시 이동) |
| Relation / Link | 개체-개체를 잇는 predicate (`rdf:type`, `rdfs:label`,
  `rdfs:comment`, `owl:sameAs` 등은 제외) |

리터럴 값을 갖는 datatype property(문자열/숫자 속성)는 현재 그래프에 노드로 표시하지 않는다.
개체(ABox)가 없고 클래스 정의(TBox)만 있는 파일은 오류로 안내한다.

위 캡처는 실제 `.ttl` 파일(Class 5개, Relation 5개, Node 136개, Link 166개)을
GUI에서 열어 생성한 결과다. 개체 수가 많을 경우 물리 엔진 레이아웃이 위 이미지처럼
다소 복잡하게 배치될 수 있으며, 우측 하단의 Normal/Horizontal/Vertical 버튼으로
레이아웃을 바꿔가며 확인하는 것을 권장한다.

---

## 테스트

```powershell
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

`.lst` 파서의 4대 오류 검증(잘못된 섹션명 / 미정의 Class / 미정의 Relation / 미정의 Node)과
TTL 매핑 로직을 함께 검증한다.

---

## 2022년 원본과의 차이

- Vis.js 버전 차이로 인한 물리 엔진/레이아웃 미세 차이
- `moving-arrows`는 원본의 애니메이션 대신 점선(dashed) 화살표로 근사 구현
- HTML/CSS 마크업 구조는 원본과 동일하지 않음
- 오류 메시지 문구는 원본과 다를 수 있음 (기능적으로는 동일한 오류 유형을 검증)
- TTL 지원은 원본에 없던 신규 기능이며, 매핑 규칙은 휴리스틱임 (위 표 참고)

원본 EXE와 나란히 비교하는 절차는 `docs/comparison.md`를 참고한다
(Windows 환경 필요).

---

## 라이선스 및 출처

본 프로젝트는 MakeGraph2022의 공개된 사용법과 입력 형식을 참고한 호환 구현이다.
원본 MakeGraph2022는 한국학중앙연구원 디지털인문학연구소에서 개발되었으며,
원본 안내에 따라 이 도구로 제작한 그래프를 사용할 경우
Vis.js 및 디지털인문학연구소의 온톨로지 스크립트 변환기 출처를 표시할 것을 권장한다.
원본 프로그램 및 Vis.js의 라이선스·저작권 조건을 확인한 후 배포 범위를 결정해야 한다.
