# AGENTS.md

## Codex 작업 원칙

1. DATA_CONTRACT.md의 스키마를 절대 변경하지 말 것
2. Table은 반드시 HTML 본문 포함
3. 빈 mmd는 반드시 로그 기록
4. Windows/Git Bash 경로 호환성 고려
5. 테스트 코드 최소 1개 포함

## 금지 사항

- JSON 스키마 임의 변경
- 표 제목만 저장하고 HTML 누락
- multi_data 필드 누락

## 테스트 기준

- 샘플 mmd 입력 시 JSON 정상 생성
- 빈 mmd 발생 시 로그 기록 확인

## 프로젝트 개요

- 프로젝트명: `PDF_to_json`
- 파이프라인: pptx2pdf (선택) → OCR → retry-empty (→ completed_pages.txt 자동 갱신) → structure → keywords
- 번역 단계 없음

## 사용 예시

```bash
PDF="sample_book"

# PPTX → born-digital PDF (Windows 전용, PowerPoint 필요)
python -m docpipe pptx2pdf --raw_dir data/raw --pdf_dir data/pdf

python -m docpipe ocr --pdf_input data/pdf --out_root data/ocr
python -m docpipe retry-empty --root_dir data/ocr --pdf "$PDF"
python -m docpipe structure --root_dir data/ocr --pdf "$PDF" --out_root data/json_output
python -m docpipe keywords --root_dir data/ocr --pdf "$PDF" --out_root data/json_output
```
