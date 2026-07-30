"""导出服务单元测试."""

import json
import pytest
from app.services.export import export_to_csv, export_to_json, generate_export_filename


class TestExportToCsv:
    """CSV 导出测试."""

    def test_basic_csv(self):
        """基本 CSV 导出：验证列名和数据行."""
        columns = [
            {"name": "id", "dataType": "integer"},
            {"name": "name", "dataType": "text"},
        ]
        rows = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
        result = export_to_csv(columns, rows)

        lines = result.strip().split("\n")
        # 第一行是列名
        assert lines[0] == "id,name"
        assert lines[1] == "1,Alice"
        assert lines[2] == "2,Bob"

    def test_csv_null_values(self):
        """CSV 导出：NULL 值转为空字符串."""
        columns = [{"name": "col1", "dataType": "text"}, {"name": "col2", "dataType": "text"}]
        rows = [{"col1": None, "col2": "data"}]
        result = export_to_csv(columns, rows)

        lines = result.strip().split("\n")
        assert lines[1] == ",data"

    def test_csv_special_characters(self):
        """CSV 导出：含逗号的字段用双引号包裹."""
        columns = [{"name": "text", "dataType": "text"}]
        rows = [{"text": "hello, world"}]
        result = export_to_csv(columns, rows)

        lines = result.strip().split("\n")
        # csv.writer 自动转义：'hello, world' -> '"hello, world"'
        assert '"hello, world"' in lines[1]

    def test_csv_double_quote_escape(self):
        """CSV 导出：双引号转义."""
        columns = [{"name": "text", "dataType": "text"}]
        rows = [{"text": 'she said "hi"'}]
        result = export_to_csv(columns, rows)

        lines = result.strip().split("\n")
        # csv.writer 自动转义内部双引号
        assert '"she said ""hi"""' in lines[1]

    def test_csv_newline_handling(self):
        """CSV 导出：含换行符的字段用双引号包裹."""
        columns = [{"name": "text", "dataType": "text"}]
        rows = [{"text": "line1\nline2"}]
        result = export_to_csv(columns, rows)

        lines = result.strip().split("\n")
        assert '"line1' in lines[1]

    def test_csv_empty_rows(self):
        """CSV 导出：空数据只有表头."""
        columns = [{"name": "a", "dataType": "int"}, {"name": "b", "dataType": "int"}]
        rows = []
        result = export_to_csv(columns, rows)

        lines = result.strip().split("\n")
        assert len(lines) == 1
        assert lines[0] == "a,b"

    def test_csv_missing_column_in_row(self):
        """CSV 导出：行中缺失字段按空字符串处理."""
        columns = [{"name": "a", "dataType": "int"}, {"name": "b", "dataType": "int"}]
        rows = [{"a": 1}]  # 缺少 b
        result = export_to_csv(columns, rows)

        lines = result.strip().split("\n")
        assert lines[1] == "1,"


class TestExportToJson:
    """JSON 导出测试."""

    def test_basic_json(self):
        """基本 JSON 导出."""
        columns = [
            {"name": "id", "dataType": "integer"},
            {"name": "name", "dataType": "text"},
        ]
        rows = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
        result = export_to_json(columns, rows)
        parsed = json.loads(result)

        assert len(parsed) == 2
        assert parsed[0] == {"id": 1, "name": "Alice"}
        assert parsed[1] == {"id": 2, "name": "Bob"}

    def test_json_null_values(self):
        """JSON 导出：null 值保留."""
        columns = [{"name": "col1", "dataType": "text"}, {"name": "col2", "dataType": "text"}]
        rows = [{"col1": None, "col2": "data"}]
        result = export_to_json(columns, rows)
        parsed = json.loads(result)

        assert parsed[0]["col1"] is None
        assert parsed[0]["col2"] == "data"

    def test_json_indent(self):
        """JSON 导出：带缩进美化."""
        columns = [{"name": "id", "dataType": "int"}]
        rows = [{"id": 1}]
        result = export_to_json(columns, rows)

        # 应该包含缩进（换行 + 空格）
        assert "\n" in result
        assert "  " in result

    def test_json_chinese_text(self):
        """JSON 导出：中文正常显示不转义."""
        columns = [{"name": "名称", "dataType": "text"}]
        rows = [{"名称": "张三"}]
        result = export_to_json(columns, rows)
        parsed = json.loads(result)

        assert parsed[0]["名称"] == "张三"
        # ensure_ascii=False，中文应直接显示
        assert "张三" in result

    def test_json_empty_rows(self):
        """JSON 导出：空数据返回空数组."""
        columns = [{"name": "a", "dataType": "int"}]
        rows = []
        result = export_to_json(columns, rows)
        parsed = json.loads(result)

        assert parsed == []

    def test_json_extra_fields_excluded(self):
        """JSON 导出：行中多余字段不包含在结果中."""
        columns = [{"name": "id", "dataType": "int"}]
        rows = [{"id": 1, "extra": "should_not_appear"}]
        result = export_to_json(columns, rows)
        parsed = json.loads(result)

        assert "extra" not in parsed[0]


class TestGenerateExportFilename:
    """文件名生成测试."""

    def test_csv_filename(self):
        """CSV 文件名格式."""
        name = generate_export_filename("mydb", "csv")
        assert name.startswith("mydb_")
        assert name.endswith(".csv")

    def test_json_filename(self):
        """JSON 文件名格式."""
        name = generate_export_filename("test-db", "json")
        assert name.startswith("test-db_")
        assert name.endswith(".json")

    def test_filename_timestamp_format(self):
        """文件名时间戳格式正确（YYYYMMDD_HHMMSS）."""
        name = generate_export_filename("mydb", "csv")
        # 提取时间戳部分: mydb_20260729_153000.csv
        basename = name.replace("mydb_", "").replace(".csv", "")
        assert len(basename) == 15  # YYYYMMDD_HHMMSS = 15 chars
        assert basename[8] == "_"