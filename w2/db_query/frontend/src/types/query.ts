/** Query execution types. */

export interface QueryColumn {
  name: string;
  dataType: string;
}

export interface QueryResult {
  columns: QueryColumn[];
  rows: Record<string, any>[];
  rowCount: number;
  executionTimeMs: number;
  sql: string;
}

export interface QueryInput {
  sql: string;
}

export interface QueryHistoryEntry {
  id: number;
  databaseName: string;
  sqlText: string;
  executedAt: string;
  executionTimeMs?: number | null;
  rowCount?: number | null;
  success: boolean;
  errorMessage?: string | null;
  querySource: "manual" | "natural_language";
}

/** 导出格式类型 */
export type ExportFormat = "csv" | "json";

/** 导出请求参数 */
export interface ExportRequest {
  sql: string;
  format: ExportFormat;
}
