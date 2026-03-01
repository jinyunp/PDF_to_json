# Architecture Overview — PDF_to_json

## 파이프라인 단계

| # | 단계명 | 함수 | 설명 |
|---|--------|------|------|
| 1 | `stage1_ocr` | `run_stage1_ocr` | PDF → 페이지별 PNG → DeepSeek OCR → `result.mmd` |
| 2 | `stage2_quality` | `run_stage2_quality` | 빈 `result.mmd` 탐지 및 재OCR |
| 3 | `stage3_structure` | `run_stage2_structure` | `result.mmd` 파싱 → 구조화 JSON 생성 |
| 4 | `stage4_keywords` | `run_stage4_keywords` | mmd 전체 텍스트에서 빈도 기반 키워드 추출 |

## 빈 mmd 처리 전략

- `result.mmd` 파일이 없거나 비어 있으면 empty로 간주
- 해당 페이지의 `page_XXXX.png` 기반으로 재OCR 수행
- 재실패 시 `logs/empty_pages_retry_failed.txt`에 기록

## 시퀀스 흐름

```
PDF → [stage1_ocr] → result.mmd
               ↓
      [stage2_quality] → 빈 페이지 재OCR
               ↓
      [stage3_structure] → texts/tables/images JSON
               ↓
      [stage4_keywords] → keywords.json
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
│  ├─ ocr.py            # stage1
│  ├─ quality.py        # stage2 (DeepSeekOCR2Runner 포함)
│  ├─ structure.py      # stage3 wrapper
│  ├─ keywords.py       # stage4
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
   │        └─ empty_pages_retry_failed.txt
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
