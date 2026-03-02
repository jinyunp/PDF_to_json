# PDF_to_json

DeepSeek-OCR2 기반 PDF → Markdown OCR 후 구조화 JSON 및 키워드/구문을 추출하는 파이프라인입니다.

## 파이프라인 단계

| 단계 | CLI 명령 | 설명 |
|------|----------|------|
| 1 | `stage1_ocr` / `ocr` | PDF → DeepSeek OCR → `result.mmd` 생성 |
| 2 | `stage2_quality` / `retry-empty` | 비어 있는 `result.mmd` 탐지 후 재OCR + `completed_pages.txt` 자동 갱신 |
| 3 | `stage3_structure` / `structure` | `result.mmd` → 구조화 JSON |
| 4 | `stage4_keywords` / `keywords` | mmd 전체에서 자주 등장하는 단어·구문 추출 |
| - | `check` | OCR 완료 페이지 목록 확인 및 로그 저장 (단독 실행 가능) |

## 핵심 경로

- 입력 PDF: `data/pdf/`
- OCR 결과: `data/ocr/`
- 구조화 JSON: `data/json_output/`

## 환경 설정

```bash
bash setup.sh
source .venv/deepseek/bin/activate
```

선택 인자:
- `--method snapshot|git` (기본: `snapshot`)
- `--hf-token <TOKEN>`

모델 경로는 환경변수로 지정:
```bash
export DEEPSEEK_MODEL_ID=/workspace/models/DeepSeek-OCR-2
```

## 빠른 실행

```bash
PDF=<pdf_name>

# 1. OCR (기본: 터미널에 페이지 진행 상황만 표시)
python -m docpipe ocr --pdf_input data/pdf --out_root data/ocr

# 1a. OCR - 상세 로그 출력
python -m docpipe ocr --pdf_input data/pdf --out_root data/ocr --verbose

# 2. 빈 mmd 재OCR (완료 시 completed_pages.txt 자동 갱신)
python -m docpipe retry-empty --root_dir data/ocr --pdf "$PDF"

# 3. 구조화 JSON 생성
python -m docpipe structure --root_dir data/ocr --pdf "$PDF" --out_root data/json_output

# 4. 키워드 및 구문 추출
python -m docpipe keywords --root_dir data/ocr --pdf "$PDF" --out_root data/json_output

# OCR 완료 페이지 확인 (retry-empty 실행 시 자동으로도 실행됨)
python -m docpipe check --root_dir data/ocr --pdf "$PDF"
```

## 출력 파일

```
data/json_output/<pdf_name>/
├─ texts_final.json          # 텍스트 청크
├─ tables_str_final.json     # 표 (HTML 포함)
├─ images_sum_final.json     # 그림 캡션
└─ keywords.json             # 빈도 기반 단어·구문 목록 (type: "word"|"phrase")

data/ocr/<pdf_name>/logs/
├─ empty_pages_quality.txt        # 빈 mmd 페이지 목록
├─ empty_pages_retry_failed.txt   # 재OCR 실패 페이지
└─ completed_pages.txt            # OCR 결과가 있는 페이지 목록 (retry-empty 자동 갱신 / check 단독 실행 가능)
```

## 주요 CLI 옵션

### stage1_ocr / ocr
```
--pdf_input       PDF 파일 또는 폴더 경로 (필수)
--out_root        OCR 출력 루트 (기본: data/ocr)
--start_page      1-based 시작 페이지
--end_page        1-based 종료 페이지
--dpi             렌더링 DPI (기본: 200)
--device          cuda/cpu 강제 지정
--verbose         상세 로그 출력 (기본: 페이지 진행만 표시)
```

### stage2_quality / retry-empty
```
--root_dir    OCR 루트 경로 (기본: data/ocr)
--pdf         PDF 폴더명 (필수)
--max_retry   재시도 횟수 (기본: 1)
--device      cuda/cpu 강제 지정
```

### stage3_structure / structure
```
--root_dir    OCR 루트 경로 (기본: data/ocr)
--pdf         PDF 폴더명 (필수)
--out_root    JSON 출력 루트 (기본: data/json_output)
```

### stage4_keywords / keywords
```
--root_dir        OCR 루트 경로 (기본: data/ocr)
--pdf             PDF 폴더명 (필수)
--out_root        JSON 출력 루트 (기본: data/json_output)
--top_n           추출할 단어 수 (기본: 50)
--top_n_phrases   추출할 구문 수 (기본: top_n과 동일)
--min_count       최소 등장 횟수 (기본: 2)
```

### check
```
--root_dir    OCR 루트 경로 (기본: data/ocr)
--pdf         PDF 폴더명 (필수)
```

## OCR 폴더 구조

```
data/ocr/<pdf_name>/
├─ page_0001.png
├─ page_0001/
│  └─ result.mmd
├─ page_0002.png
├─ page_0002/
│  └─ result.mmd
└─ logs/
   ├─ empty_pages_quality.txt
   ├─ empty_pages_retry_failed.txt
   └─ completed_pages.txt
```

## Troubleshooting

GPU 확인:
```bash
python -c "import torch; print(torch.cuda.is_available()); print(torch.version.cuda)"
```

CUDA 11.8 torch 예시:
```bash
pip uninstall torch torchvision torchaudio -y
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 \
  --index-url https://download.pytorch.org/whl/cu118
```

세부 규칙은 `docs/` 하위 문서를 따릅니다.
