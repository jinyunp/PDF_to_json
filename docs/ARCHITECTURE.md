# Architecture Overview — PDF_to_json

## 파이프라인 단계

| # | 단계명 | 함수 | 설명 |
|---|--------|------|------|
| 1 | `stage1_ocr` | `run_stage1_ocr` | PDF → 페이지별 PNG → DeepSeek OCR → `result.mmd` |
| 2 | `stage2_quality` | `run_stage2_quality` | 빈 `result.mmd` 탐지 및 재OCR + `completed_pages.txt` 자동 갱신 |
| 3 | `stage3_structure` | `run_stage2_structure` | `result.mmd` 파싱 → 구조화 JSON 생성 |
| 4 | `stage4_keywords` | `run_stage4_keywords` | mmd 전체 텍스트에서 빈도 기반 단어·구문 추출 |
| - | `check` | `run_check_completed` | OCR 완료 페이지 목록 확인 및 로그 저장 (단독 실행 가능) |

## OCR 진행 출력 제어 (stage1_ocr)

- 기본(`--verbose` 없음): `\r` 기반 단일 줄 progress(`[file.pdf] 3/20 페이지 처리 중...`)만 표시
- transformers·torch 등 라이브러리 로그는 OS 레벨(`os.dup2`)에서 `/dev/null`로 차단
- `--verbose` 지정 시: 모든 라이브러리 로그를 그대로 출력

## 빈 mmd 처리 전략

- `result.mmd` 파일이 없거나 비어 있으면 empty로 간주
- 해당 페이지의 `page_XXXX.png` 기반으로 재OCR 수행
- 재실패 시 `logs/empty_pages_retry_failed.txt`에 기록

## 키워드·구문 추출 전략 (stage4_keywords)

- **단어(word)**: `[A-Za-z][A-Za-z0-9\-]{2,}` 패턴 + 불용어 제거, 소문자 정규화
- **구문(phrase)**: 연속된 2-gram·3-gram 중 구성 단어가 모두 불용어가 아닌 것만 포함
- 결과는 등장 횟수 내림차순으로 정렬, `type: "word" | "phrase"` 필드로 구분
- `top_n`(단어 수)과 `top_n_phrases`(구문 수)를 독립적으로 제어 가능

## 시퀀스 흐름

```
PDF → [stage1_ocr] → result.mmd
              ↓
     [stage2_quality] → 빈 페이지 재OCR
                      → completed_pages.txt (자동 갱신)
              ↓
     [stage3_structure] → texts/tables/images JSON
              ↓
     [stage4_keywords] → keywords.json (단어 + 구문)

[check] → completed_pages.txt  (언제든 단독 실행 가능)
```

## 폴더 구조

```
PDF_to_json/           (저장소 루트, 물리적 폴더명: WP_to_json)
├─ README.md
├─ AGENTS.md
├─ requirements.deepseek.txt
├─ setup.sh
├─ .gitignore
├─ docs/
│  ├─ ARCHITECTURE.md
│  ├─ DATA_CONTRACT.md
│  ├─ PARSING_RULES.md
│  └─ CLI_SPEC.md
├─ docpipe/
│  ├─ __init__.py
│  ├─ __main__.py       # CLI 진입점
│  ├─ ocr.py            # stage1 (verbose/quiet_mode 포함)
│  ├─ quality.py        # stage2 (DeepSeekOCR2Runner, run_check_completed 포함)
│  ├─ structure.py      # stage3 wrapper
│  ├─ keywords.py       # stage4 (단어 + 2/3-gram 구문 추출)
│  └─ stage2_structure/ # 구조화 내부 구현
│     ├─ __init__.py
│     ├─ parsing.py     # mmd 파싱 (헤딩/Figure/Table)
│     ├─ chunking.py    # 텍스트 청킹 + 참조 탐지
│     ├─ builders.py    # figures/tables JSON 빌더
│     ├─ io_utils.py    # JSON 쓰기 / 로그 유틸
│     ├─ pipeline.py    # stage3 파이프라인
│     └─ types.py       # FigureItem, TableItem
├─ tests/
│  └─ test_stage2_structure_pipeline.py
└─ data/
   ├─ pdf/                      # 원본 PDF 입력
   ├─ ocr/                      # OCR 출력 (root_dir)
   │  └─ <pdf_name>/
   │     ├─ page_0001.png
   │     ├─ page_0001/
   │     │  └─ result.mmd
   │     └─ logs/
   │        ├─ empty_pages_quality.txt
   │        ├─ empty_pages_retry_failed.txt
   │        └─ completed_pages.txt       # retry-empty 자동 갱신 / check 단독 실행 가능
   └─ json_output/              # 구조화 JSON 출력
      └─ <pdf_name>/
         ├─ texts_final.json
         ├─ tables_str_final.json
         ├─ images_sum_final.json
         ├─ keywords.json
         └─ empty_pages_structuring.txt
```

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DEEPSEEK_MODEL_ID` | `/workspace/models/DeepSeek-OCR-2` | DeepSeek OCR 모델 경로 |
