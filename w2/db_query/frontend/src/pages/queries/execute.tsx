/** Query execution page with SQL editor, result table, and export functionality. */

import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Card, Button, Space, Spin, Alert, List, Typography, Dropdown } from "antd";
import {
  ReloadOutlined,
  DownloadOutlined,
  FileTextOutlined,
  FileOutlined,
  DownOutlined,
} from "@ant-design/icons";
import { apiClient, exportData } from "../../services/api";
import { QueryResult, QueryHistoryEntry, QueryInput, ExportFormat } from "../../types/query";
import { SqlEditor } from "../../components/SqlEditor";
import { ResultTable } from "../../components/ResultTable";

const { Text } = Typography;

export const QueryExecute: React.FC = () => {
  const { databaseName } = useParams<{ databaseName: string }>();
  const [sql, setSql] = useState("SELECT * FROM ");
  const [result, setResult] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<QueryHistoryEntry[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    if (databaseName) {
      loadHistory();
    }
  }, [databaseName]);

  const loadHistory = async () => {
    if (!databaseName) return;

    setLoadingHistory(true);
    try {
      const response = await apiClient.get<QueryHistoryEntry[]>(
        `/api/v1/dbs/${databaseName}/history`
      );
      setHistory(response.data);
    } catch (err) {
      console.error("Failed to load history:", err);
    } finally {
      setLoadingHistory(false);
    }
  };

  /** 执行 SQL 查询并返回结果 */
  const executeQuery = async (): Promise<QueryResult | null> => {
    if (!databaseName || !sql.trim()) {
      setError("Please enter a SQL query");
      return null;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const input: QueryInput = { sql: sql.trim() };
      const response = await apiClient.post<QueryResult>(
        `/api/v1/dbs/${databaseName}/query`,
        input
      );
      setResult(response.data);
      await loadHistory();
      return response.data;
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || err.message || "Query execution failed";
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  };

  /** 执行查询后自动导出 */
  const handleExecuteAndExport = async (format: ExportFormat) => {
    if (!databaseName || !sql.trim()) {
      setError("Please enter a SQL query");
      return;
    }

    setExporting(true);
    try {
      const queryResult = await executeQuery();
      if (!queryResult) return;
      // 自动触发导出
      await exportData(databaseName, sql.trim(), format);
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || err.message || "Operation failed";
      setError(errorMessage);
    } finally {
      setExporting(false);
    }
  };

  /** 单独导出当前查询结果 */
  const handleExport = async (format: ExportFormat) => {
    if (!databaseName || !sql.trim()) return;

    setExporting(true);
    try {
      await exportData(databaseName, sql.trim(), format);
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || err.message || "Export failed";
      setError(errorMessage);
    } finally {
      setExporting(false);
    }
  };

  const handleHistoryClick = (historyItem: QueryHistoryEntry) => {
    setSql(historyItem.sqlText);
    setError(null);
    setResult(null);
  };

  // 一键导出下拉菜单项
  const executeExportMenuItems = [
    {
      key: "csv",
      label: "Execute & Export CSV",
      icon: <FileTextOutlined />,
    },
    {
      key: "json",
      label: "Execute & Export JSON",
      icon: <FileOutlined />,
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={`Execute Query - ${databaseName}`}
        extra={
          <Space>
            <Dropdown
              menu={{
                items: executeExportMenuItems,
                onClick: ({ key }) =>
                  handleExecuteAndExport(key as ExportFormat),
              }}
              disabled={loading}
            >
              <Button loading={loading}>
                <Space>
                  Execute
                  <DownOutlined />
                </Space>
              </Button>
            </Dropdown>
            <Button
              icon={<ReloadOutlined />}
              onClick={loadHistory}
              loading={loadingHistory}
            >
              Refresh History
            </Button>
          </Space>
        }
      >
        <Space direction="vertical" style={{ width: "100%" }} size="large">
          <div>
            <Card title="SQL Editor" size="small">
              <SqlEditor
                value={sql}
                onChange={(val) => setSql(val || "")}
                height="200px"
              />
            </Card>
          </div>

          {error && (
            <Alert
              message="Error"
              description={error}
              type="error"
              showIcon
              closable
              onClose={() => setError(null)}
            />
          )}

          {loading && (
            <div style={{ textAlign: "center", padding: "50px" }}>
              <Spin size="large" />
            </div>
          )}

          {result && (
            <Card
              title="Query Results"
              size="small"
              extra={
                <Space>
                  <Button
                    icon={<DownloadOutlined />}
                    loading={exporting}
                    onClick={() => handleExport("csv")}
                  >
                    导出 CSV
                  </Button>
                  <Button
                    icon={<DownloadOutlined />}
                    loading={exporting}
                    onClick={() => handleExport("json")}
                  >
                    导出 JSON
                  </Button>
                </Space>
              }
            >
              <ResultTable result={result} loading={loading} />
            </Card>
          )}
        </Space>
      </Card>

      <Card title="Query History" style={{ marginTop: 16 }}>
        {loadingHistory ? (
          <Spin />
        ) : (
          <List
            dataSource={history}
            renderItem={(item) => (
              <List.Item
                style={{
                  cursor: "pointer",
                  backgroundColor: item.success ? "transparent" : "#fff2f0",
                }}
                onClick={() => handleHistoryClick(item)}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Text
                        code
                        style={{
                          maxWidth: "600px",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                          display: "inline-block",
                        }}
                      >
                        {item.sqlText}
                      </Text>
                      {item.success ? (
                        <Text type="success">
                          {item.rowCount} rows in {item.executionTimeMs}ms
                        </Text>
                      ) : (
                        <Text type="danger">Failed</Text>
                      )}
                    </Space>
                  }
                  description={
                    <Text type="secondary">
                      {new Date(item.executedAt).toLocaleString()}
                    </Text>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );
};
