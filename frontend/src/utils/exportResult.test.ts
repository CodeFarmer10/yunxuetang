import { describe, expect, it } from "vitest";
import {
  buildExportFile,
  type QueryResultForExport,
} from "./exportResult";

const result: QueryResultForExport = {
  columns: [
    { name: "id", dataType: "integer" },
    { name: "name", dataType: "text" },
    { name: "note", dataType: "text" },
  ],
  rows: [
    { id: 1, name: "Ada", note: "hello, world" },
    { id: 2, name: "Grace", note: 'said "hi"' },
    { id: 3, name: null, note: "multi\nline" },
  ],
  rowCount: 3,
  executionTimeMs: 12,
  sql: "SELECT * FROM users",
};

describe("buildExportFile", () => {
  it("builds an escaped CSV file from query results", () => {
    const file = buildExportFile({
      databaseName: "analytics",
      format: "csv",
      result,
      now: new Date("2026-08-19T09:10:11.000Z"),
    });

    expect(file.fileName).toBe("analytics_2026-08-19T09-10-11.csv");
    expect(file.mimeType).toBe("text/csv;charset=utf-8;");
    expect(file.content).toBe(
      [
        "id,name,note",
        "1,Ada,\"hello, world\"",
        "2,Grace,\"said \"\"hi\"\"\"",
        "3,,\"multi\nline\"",
      ].join("\n")
    );
  });

  it("builds a JSON file with rows and query metadata", () => {
    const file = buildExportFile({
      databaseName: "analytics",
      format: "json",
      result,
      now: new Date("2026-08-19T09:10:11.000Z"),
    });

    expect(file.fileName).toBe("analytics_2026-08-19T09-10-11.json");
    expect(file.mimeType).toBe("application/json;charset=utf-8;");
    expect(JSON.parse(file.content)).toEqual({
      sql: "SELECT * FROM users",
      rowCount: 3,
      executionTimeMs: 12,
      columns: result.columns,
      rows: result.rows,
      exportedAt: "2026-08-19T09:10:11.000Z",
    });
  });
});
