import pytest
from datetime import datetime, timezone
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from app.main import app
from app.database import get_session
from app.models.database import DatabaseConnection, ConnectionStatus
from app.models.metadata import DatabaseMetadata
from app.models.schemas import QueryResult, QueryColumn
import json


@pytest.fixture
def test_session():
    from app.models.database import DatabaseConnection
    from app.models.metadata import DatabaseMetadata
    from app.models.query import QueryHistory

    engine = create_engine(
        "sqlite:///file:test_db_export?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False, "uri": True},
    )
    SQLModel.metadata.create_all(engine)
    session = Session(engine, expire_on_commit=False)
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def client(test_session):
    def get_test_session():
        return test_session

    app.dependency_overrides[get_session] = get_test_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_connection(test_session):
    conn = DatabaseConnection(
        name="test_db",
        url="postgresql://user:pass@localhost/testdb",
        description="Test database",
        status=ConnectionStatus.ACTIVE,
        last_connected_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    test_session.add(conn)
    test_session.commit()
    test_session.refresh(conn)
    return conn


@pytest.fixture
def sample_metadata(test_session):
    metadata_dict = {
        "tables": [
            {
                "name": "app_judge_result",
                "type": "table",
                "schemaName": "public",
                "rowCount": 100,
                "columns": [
                    {
                        "name": "id",
                        "dataType": "integer",
                        "nullable": False,
                        "primaryKey": True,
                        "unique": False,
                        "defaultValue": None,
                    }
                ],
            }
        ],
        "views": [],
    }
    cached = DatabaseMetadata(
        database_name="test_db",
        metadata_json=json.dumps(metadata_dict),
        fetched_at=datetime.now(timezone.utc).replace(tzinfo=None),
        table_count=1,
    )
    test_session.add(cached)
    test_session.commit()
    return metadata_dict


class TestNaturalLanguageQueryAndExport:
    @patch("app.api.v1.queries.execute_query_with_service")
    @patch("app.api.v1.queries.nl2sql_service.generate_sql")
    def test_export_csv_by_prompt(
        self,
        mock_generate,
        mock_execute,
        client,
        sample_connection,
        sample_metadata,
    ):
        mock_generate.return_value = {
            "sql": "SELECT COUNT(*) AS total FROM public.app_judge_result",
            "explanation": "Generated",
        }

        mock_execute.return_value = QueryResult(
            columns=[QueryColumn(name="total", dataType="bigint")],
            rows=[{"total": 123}],
            rowCount=1,
            executionTimeMs=10,
            sql="SELECT COUNT(*) AS total FROM public.app_judge_result",
        )

        response = client.post(
            "/api/v1/dbs/test_db/query/natural-and-export",
            json={"prompt": "查询 app_judge_result 表有多少条数据 并将结果导出成csv格式"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "content-disposition" in response.headers
        assert response.content[:3] == b"\xef\xbb\xbf"
        assert b"total" in response.content

    @patch("app.api.v1.queries.execute_query_with_service")
    @patch("app.api.v1.queries.nl2sql_service.generate_sql")
    def test_export_json_by_prompt(
        self,
        mock_generate,
        mock_execute,
        client,
        sample_connection,
        sample_metadata,
    ):
        mock_generate.return_value = {
            "sql": "SELECT COUNT(*) AS total FROM public.app_judge_result",
            "explanation": "Generated",
        }

        mock_execute.return_value = QueryResult(
            columns=[QueryColumn(name="total", dataType="bigint")],
            rows=[{"total": 123}],
            rowCount=1,
            executionTimeMs=10,
            sql="SELECT COUNT(*) AS total FROM public.app_judge_result",
        )

        response = client.post(
            "/api/v1/dbs/test_db/query/natural-and-export",
            json={"prompt": "查询 app_judge_result 表有多少条数据 并导出 json"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        parsed = json.loads(response.content.decode("utf-8"))
        assert parsed == [{"total": 123}]

