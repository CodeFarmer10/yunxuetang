"""查询结果导出服务，支持 CSV 和 JSON 格式."""

import csv
import json
import io
from datetime import datetime
from typing import Any


def generate_export_filename(db_name: str, format: str) -> str:
    """生成导出文件名，包含数据库名和时间戳.

    Args:
        db_name: 数据库连接名称
        format: 导出格式 (csv / json)

    Returns:
        文件名，如 'mydb_20260729_153000.csv'
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{db_name}_{timestamp}.{format}"


def export_to_csv(columns: list[dict[str, str]], rows: list[dict[str, Any]]) -> str:
    """将查询结果转换为 CSV 字符串.

    CSV 格式说明：
    - 第一行为列名
    - 后续行为数据行
    - csv.writer 自动处理逗号/引号转义

    Args:
        columns: 列定义列表，每项含 name / dataType
        rows: 数据行列表

    Returns:
        CSV 格式字符串
    """
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")

    # 写入表头
    col_names = [col["name"] for col in columns]
    writer.writerow(col_names)

    # 写入数据行（csv.writer 自动处理转义，无需额外 escape）
    for row in rows:
        writer.writerow([row.get(col_name) for col_name in col_names])

    return output.getvalue()


def export_to_json(
    columns: list[dict[str, str]], rows: list[dict[str, Any]]
) -> str:
    """将查询结果转换为 JSON 字符串.

    JSON 格式说明：
    - 数组格式 [{col1: val1, col2: val2}, ...]
    - indent=2 美化输出
    - ensure_ascii=False 保证中文正常显示

    Args:
        columns: 列定义列表
        rows: 数据行列表

    Returns:
        JSON 格式字符串
    """
    col_names = [col["name"] for col in columns]
    # 只保留查询结果中存在的列，按列定义顺序输出
    result = [{col_name: row.get(col_name) for col_name in col_names} for row in rows]
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)