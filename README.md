# PDF_to_json

DeepSeek-OCR2 기반 PDF → Markdown OCR 후 구조화 JSON 및 키워드/구문을 추출하는 파이프라인입니다.

## 파이프라인 단계

| 단계 | CLI 명령 | 설명 |
|------|----------|------|
| 0a | `pptx2pdf` | `.pptx` → born-digital PDF 변환 (`data/raw/` → `data/pdf/`), Windows 전용 |
| 0b | `pdf-extract` | born-digital PDF → `pdf_extracted.json` (메타데이터 + 페이지별 텍스트·이미지수) |
| 1 | `stage1_ocr` / `ocr` | PDF → DeepSeek OCR → `result.mmd` 생성 |
| 2 | `stage2_quality` / `retry-empty` | 비어 있는 `result.mmd` 탐지 후 재OCR + `completed_pages.txt` 자동 갱신 |
| 3 | `stage3_structure` / `structure` | `result.mmd` → 구조화 JSON |
| 4 | `stage4_keywords` / `keywords` | `texts_final.json` 기반 chunk별 TF-IDF 키워드 추출 → `texts_final.json` 업데이트 + `keywords.json` 생성 |
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

# 0a. PPTX → born-digital PDF 변환 (Windows 전용, PowerPoint 필요)
python -m docpipe pptx2pdf --raw_dir data/raw --pdf_dir data/pdf
# 이미 존재하는 PDF 덮어쓰기: --overwrite 옵션 추가

# 0b. born-digital PDF에서 텍스트·메타데이터 추출 → pdf_extracted.json
python -m docpipe pdf-extract --pdf_dir data/pdf --out_root data/json_output
# 단일 파일: --pdf_file data/pdf/my_file.pdf

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
├─ pdf_extracted.json        # born-digital PDF 직접 추출 (메타데이터 + 페이지별 텍스트·이미지수)
├─ texts_final.json          # 텍스트 청크 (stage4 실행 후 chunk별 keywords 필드 추가됨)
├─ tables_str_final.json     # 표 (HTML 포함)
├─ images_sum_final.json     # 그림 캡션
└─ keywords.json             # TF-IDF 기반 단어·구문 목록 (type: "word"|"phrase", score 포함)

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
--root_dir        (미사용, 하위 호환용) OCR 루트 경로 (기본: data/ocr)
--pdf             PDF 폴더명 (필수)
--out_root        JSON 출력 루트 (기본: data/json_output)
--top_n           chunk별 및 전역 단어 추출 수 (기본: 30)
--top_n_phrases   전역 구문 추출 수 (기본: top_n과 동일)
--min_count       전역 keywords.json 최소 등장 횟수 (기본: 2)
```

### pptx2pdf
```
--raw_dir    .pptx 파일이 있는 디렉토리 (기본: data/raw)
--pdf_dir    PDF 저장 디렉토리 (기본: data/pdf)
--overwrite  이미 존재하는 PDF 덮어쓰기
```
- Windows 전용 (PowerPoint COM 자동화)
- born-digital 설정: 텍스트를 이미지가 아닌 실제 텍스트로 저장, 문서 구조 태그 포함

### pdf-extract
```
--pdf_dir    처리할 .pdf 파일 디렉토리 (--pdf_file과 택1)
--pdf_file   단일 .pdf 파일 경로 (--pdf_dir와 택1)
--out_root   JSON 출력 루트 (기본: data/json_output)
```
- pypdfium2 기반, born-digital PDF에서 최대 정보 추출
- 출력: `<out_root>/<pdf_stem>/pdf_extracted.json`
- 추출 항목: 메타데이터(author, creator, dates 등) + 페이지별 텍스트, 문자수, 이미지수, 경로수, 페이지 크기

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
