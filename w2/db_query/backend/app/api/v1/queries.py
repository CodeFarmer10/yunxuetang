"""Query execution API endpoints."""

import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from typing import List
from app.database import get_session
from app.models.database import DatabaseConnection
from app.models.query import QuerySource
from app.models.schemas import (
    QueryInput,
    QueryResult,
    QueryHistoryEntry,
    NaturalLanguageInput,
    GeneratedSqlResponse,
    ExportRequest,
    ExportFormatEnum,
    NaturalLanguageQueryAndExportRequest,
)
from app.services.query_wrapper import execute_query_with_service
from app.services.query import get_query_history
from app.services.sql_validator import SqlValidationError, validate_and_transform_sql
from app.services.nl2sql import nl2sql_service
from app.services.metadata import get_cached_metadata
from app.services.export import (
    export_to_csv,
    export_to_json,
    generate_export_filename,
)

router = APIRouter(prefix="/api/v1/dbs", tags=["queries"])


def to_history_entry(history) -> QueryHistoryEntry:
    """Convert QueryHistory to QueryHistoryEntry schema."""
    return QueryHistoryEntry(
        id=history.id,
        databaseName=history.database_name,
        sqlText=history.sql_text,
        executedAt=history.executed_at,
        executionTimeMs=history.execution_time_ms,
        rowCount=history.row_count,
        success=history.success,
        errorMessage=history.error_message,
        querySource=history.query_source.value,
    )


@router.post("/{name}/query", response_model=QueryResult)
async def execute_sql_query(
    name: str,
    input_data: QueryInput,
    session: Session = Depends(get_session),
) -> QueryResult:
    """
    Execute SQL query against a database.

    Args:
        name: Database connection name
        input_data: Query input with SQL
        session: Database session

    Returns:
        Query result with columns and rows
    """
    # Get connection
    statement = select(DatabaseConnection).where(
        DatabaseConnection.name == name
    )
    connection = session.exec(statement).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database connection '{name}' not found",
        )

    # Execute query
    try:
        result = await execute_query_with_service(
            session,
            name,
            connection.db_type,
            connection.url,
            input_data.sql,
            QuerySource.MANUAL,
        )
        return result
    except SqlValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}",
        )


@router.get("/{name}/history", response_model=List[QueryHistoryEntry])
async def get_query_history_for_database(
    name: str,
    limit: int = 50,
    session: Session = Depends(get_session),
) -> List[QueryHistoryEntry]:
    """
    Get query history for a database.

    Args:
        name: Database connection name
        limit: Maximum number of queries to return
        session: Database session

    Returns:
        List of query history entries
    """
    # Verify connection exists
    statement = select(DatabaseConnection).where(
        DatabaseConnection.name == name
    )
    connection = session.exec(statement).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database connection '{name}' not found",
        )

    # Get history
    history_list = await get_query_history(session, name, limit)
    return [to_history_entry(h) for h in history_list]


@router.post("/{name}/query/natural", response_model=GeneratedSqlResponse)
async def natural_language_to_sql(
    name: str,
    input_data: NaturalLanguageInput,
    session: Session = Depends(get_session),
) -> GeneratedSqlResponse:
    """
    Convert natural language to SQL query using OpenAI.

    Args:
        name: Database connection name
        input_data: Natural language prompt
        session: Database session

    Returns:
        Generated SQL query with explanation
    """
    # Get connection
    statement = select(DatabaseConnection).where(DatabaseConnection.name == name)
    connection = session.exec(statement).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database connection '{name}' not found",
        )

    # Get metadata for context
    try:
        metadata_obj = await get_cached_metadata(session, connection.name)
        if not metadata_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Metadata not found for database '{name}'. Please refresh metadata first.",
            )
        metadata = json.loads(metadata_obj.metadata_json)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load metadata: {str(e)}",
        )

    # Generate SQL
    try:
        result = await nl2sql_service.generate_sql(input_data.prompt, metadata, connection.db_type)
        return GeneratedSqlResponse(
            sql=result["sql"],
            explanation=result["explanation"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate SQL: {str(e)}",
        )


def _detect_export_format(prompt: str, explicit_format: str | None) -> str:
    if explicit_format in (ExportFormatEnum.CSV, ExportFormatEnum.JSON):
        return explicit_format

    lower = prompt.lower()
    if "json" in lower:
        return ExportFormatEnum.JSON
    if "csv" in lower:
        return ExportFormatEnum.CSV
    if "导出" in prompt or "下载" in prompt:
        return ExportFormatEnum.CSV
    return ExportFormatEnum.CSV


@router.post("/{name}/query/natural-and-export")
async def natural_language_query_and_export(
    name: str,
    input_data: NaturalLanguageQueryAndExportRequest,
    session: Session = Depends(get_session),
) -> StreamingResponse:
    statement = select(DatabaseConnection).where(DatabaseConnection.name == name)
    connection = session.exec(statement).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database connection '{name}' not found",
        )

    try:
        metadata_obj = await get_cached_metadata(session, connection.name)
        if not metadata_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Metadata not found for database '{name}'. Please refresh metadata first.",
            )
        metadata = json.loads(metadata_obj.metadata_json)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load metadata: {str(e)}",
        )

    format_value = _detect_export_format(input_data.prompt, input_data.format)

    try:
        gen = await nl2sql_service.generate_sql(input_data.prompt, metadata, connection.db_type)
        sql = validate_and_transform_sql(gen["sql"], db_type=connection.db_type)
    except SqlValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate SQL: {str(e)}",
        )

    try:
        result = await execute_query_with_service(
            session,
            name,
            connection.db_type,
            connection.url,
            sql,
            QuerySource.NATURAL_LANGUAGE,
        )
    except SqlValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}",
        )

    columns_dict = [{"name": col.name, "dataType": col.data_type} for col in result.columns]

    if format_value == ExportFormatEnum.CSV:
        content = export_to_csv(columns_dict, result.rows)
        media_type = "text/csv; charset=utf-8-sig"
        content_bytes = content.encode("utf-8-sig")
    else:
        content = export_to_json(columns_dict, result.rows)
        media_type = "application/json; charset=utf-8"
        content_bytes = content.encode("utf-8")

    filename = generate_export_filename(connection.name, format_value)

    return StreamingResponse(
        iter([content_bytes]),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


async def _get_connection_and_execute(
    name: str, sql: str, session: Session
) -> tuple[DatabaseConnection, QueryResult]:
    """获取数据库连接并执行查询，返回连接和结果.

    Args:
        name: 数据库连接名称
        sql: SQL 查询语句
        session: 数据库会话

    Returns:
        (DatabaseConnection, QueryResult) 元组

    Raises:
        HTTPException: 连接不存在或查询执行失败
    """
    # 获取连接
    statement = select(DatabaseConnection).where(DatabaseConnection.name == name)
    connection = session.exec(statement).first()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database connection '{name}' not found",
        )

    # 执行查询
    try:
        result = await execute_query_with_service(
            session,
            name,
            connection.db_type,
            connection.url,
            sql,
            QuerySource.MANUAL,
        )
        return connection, result
    except SqlValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}",
        )


@router.post("/{name}/export")
async def export_query_result(
    name: str,
    input_data: ExportRequest,
    session: Session = Depends(get_session),
) -> StreamingResponse:
    """执行 SQL 查询并导出结果为 CSV 或 JSON 文件.

    Args:
        name: 数据库连接名称
        input_data: 导出请求，包含 sql 和 format
        session: 数据库会话

    Returns:
        文件流响应
    """
    # 校验导出格式
    if input_data.format not in (ExportFormatEnum.CSV, ExportFormatEnum.JSON):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported export format: '{input_data.format}'. Use 'csv' or 'json'.",
        )

    # 执行查询
    connection, result = await _get_connection_and_execute(name, input_data.sql, session)

    # 生成导出内容
    columns_dict = [{"name": col.name, "dataType": col.data_type} for col in result.columns]

    if input_data.format == ExportFormatEnum.CSV:
        content = export_to_csv(columns_dict, result.rows)
        media_type = "text/csv; charset=utf-8-sig"
        # 重新编码为 utf-8-sig（带 BOM）以兼容 Excel
        content_bytes = content.encode("utf-8-sig")
    else:
        content = export_to_json(columns_dict, result.rows)
        media_type = "application/json; charset=utf-8"
        content_bytes = content.encode("utf-8")

    filename = generate_export_filename(connection.name, input_data.format)

    return StreamingResponse(
        iter([content_bytes]),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post("/{name}/query-and-export")
async def query_and_export(
    name: str,
    input_data: ExportRequest,
    session: Session = Depends(get_session),
) -> StreamingResponse:
    """一键完成查询执行 + 结果导出（语义别名，与 /{name}/export 功能一致）.

    Args:
        name: 数据库连接名称
        input_data: 导出请求，包含 sql 和 format
        session: 数据库会话

    Returns:
        文件流响应
    """
    return await export_query_result(name, input_data, session)
