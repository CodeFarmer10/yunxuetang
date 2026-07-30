/** Axios API client instance. */

import axios from "axios";
import { ExportFormat } from "../types/query";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Handle common errors
    if (error.response) {
      const message =
        error.response.data?.detail || error.response.data?.error || "An error occurred";
      console.error("API Error:", message);
    }
    return Promise.reject(error);
  }
);

/**
 * 导出查询结果为文件并触发浏览器下载.
 *
 * @param databaseName - 数据库连接名称
 * @param sql - SQL 查询语句
 * @param format - 导出格式 ("csv" | "json")
 */
export async function exportData(
  databaseName: string,
  sql: string,
  format: ExportFormat
): Promise<void> {
  const response = await apiClient.post(
    `/api/v1/dbs/${databaseName}/export`,
    { sql, format },
    { responseType: "blob" }
  );

  // 从 Content-Disposition 头提取文件名，或使用默认命名
  const disposition = response.headers["content-disposition"] || "";
  const filenameMatch = disposition.match(/filename="?(.+?)"?$/);
  const filename = filenameMatch ? filenameMatch[1] : `export.${format}`;

  // 创建下载链接并触发浏览器下载
  const contentType = response.headers["content-type"] || "application/octet-stream";
  const blob =
    response.data instanceof Blob
      ? response.data
      : new Blob([response.data], { type: contentType });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

export async function naturalQueryAndExport(
  databaseName: string,
  prompt: string
): Promise<void> {
  const response = await apiClient.post(
    `/api/v1/dbs/${databaseName}/query/natural-and-export`,
    { prompt },
    { responseType: "blob" }
  );

  const disposition = response.headers["content-disposition"] || "";
  const filenameMatch = disposition.match(/filename="?(.+?)"?$/);
  const filename = filenameMatch ? filenameMatch[1] : "export.csv";

  const contentType = response.headers["content-type"] || "application/octet-stream";
  const blob =
    response.data instanceof Blob
      ? response.data
      : new Blob([response.data], { type: contentType });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}
