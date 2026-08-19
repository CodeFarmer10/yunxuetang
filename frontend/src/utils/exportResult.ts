export type ExportFormat = "csv" | "json";

export interface QueryResultForExport {
  columns: Array<{ name: string; dataType: string }>;
  rows: Array<Record<string, unknown>>;
  rowCount: number;
  executionTimeMs: number;
  sql: string;
}

interface BuildExportFileInput {
  databaseName: string;
  format: ExportFormat;
  result: QueryResultForExport;
  now?: Date;
}

interface ExportFile {
  content: string;
  fileName: string;
  mimeType: string;
}

const formatTimestamp = (now: Date) =>
  now.toISOString().replace(/[:.]/g, "-").slice(0, -5);

const escapeCsvValue = (value: unknown) => {
  if (value === null || value === undefined) return "";

  const stringValue = String(value);
  if (
    stringValue.includes(",") ||
    stringValue.includes('"') ||
    stringValue.includes("\n")
  ) {
    return `"${stringValue.replace(/"/g, '""')}"`;
  }

  return stringValue;
};

const buildCsvContent = (result: QueryResultForExport) => {
  const headers = result.columns.map((column) => column.name);
  const rows = result.rows.map((row) =>
    headers.map((header) => escapeCsvValue(row[header])).join(",")
  );

  return [headers.join(","), ...rows].join("\n");
};

const buildJsonContent = (result: QueryResultForExport, now: Date) =>
  JSON.stringify(
    {
      sql: result.sql,
      rowCount: result.rowCount,
      executionTimeMs: result.executionTimeMs,
      columns: result.columns,
      rows: result.rows,
      exportedAt: now.toISOString(),
    },
    null,
    2
  );

export const buildExportFile = ({
  databaseName,
  format,
  result,
  now = new Date(),
}: BuildExportFileInput): ExportFile => {
  const timestamp = formatTimestamp(now);

  if (format === "csv") {
    return {
      content: buildCsvContent(result),
      fileName: `${databaseName}_${timestamp}.csv`,
      mimeType: "text/csv;charset=utf-8;",
    };
  }

  return {
    content: buildJsonContent(result, now),
    fileName: `${databaseName}_${timestamp}.json`,
    mimeType: "application/json;charset=utf-8;",
  };
};

export const downloadExportFile = (file: ExportFile) => {
  const blob = new Blob([file.content], { type: file.mimeType });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = file.fileName;
  link.click();
  URL.revokeObjectURL(link.href);
};
