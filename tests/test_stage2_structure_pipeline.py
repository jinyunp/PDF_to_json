from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from docpipe.structure import run_stage2_structure


class Stage2StructurePipelineTest(unittest.TestCase):
    def test_structure_generates_json_and_logs_empty_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root_dir = tmp_path / "data" / "ocr"
            pdf_name = "sample_book"

            page1_dir = root_dir / pdf_name / "page_0001"
            page2_dir = root_dir / pdf_name / "page_0002"
            page1_dir.mkdir(parents=True, exist_ok=True)
            page2_dir.mkdir(parents=True, exist_ok=True)

            mmd = """# 1. Intro
This section references Figure 1 and Table 1.

Figure 1: Blast furnace overview
![f1](images/fig_1.png)

Table 1
Main composition
<table>
  <tbody>
    <tr><td>Fe</td><td>98%</td></tr>
  </tbody>
</table>
"""
            (page1_dir / "result.mmd").write_text(mmd, encoding="utf-8")
            (page2_dir / "result.mmd").write_text("", encoding="utf-8")

            out_root = tmp_path / "data" / "json_output"
            run_stage2_structure(root_dir=root_dir, pdf_folder_name=pdf_name, out_root=out_root)

            out_dir = out_root / pdf_name
            texts = json.loads((out_dir / "texts_final.json").read_text(encoding="utf-8"))
            tables = json.loads((out_dir / "tables_str_final.json").read_text(encoding="utf-8"))
            images = json.loads((out_dir / "images_sum_final.json").read_text(encoding="utf-8"))

            self.assertGreaterEqual(len(texts), 1)
            self.assertEqual(len(tables), 1)
            self.assertEqual(len(images), 1)

            first_text = texts[0]
            self.assertIn("multi_data_list", first_text)
            self.assertIn("multi_data_path", first_text)
            self.assertIn("fig_1", first_text["multi_data_list"])
            self.assertIn("table_1", first_text["multi_data_list"])

            table = tables[0]
            self.assertIn("<table>", table["original"])
            self.assertIn("</table>", table["original"])
            self.assertEqual(table["component_type"], "table")

            empty_log = (out_dir / "empty_pages_structuring.txt").read_text(encoding="utf-8")
            self.assertIn("page_0002", empty_log)


if __name__ == "__main__":
    unittest.main()
