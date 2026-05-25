import axios from "axios";
import axiosRetry from "axios-retry";
import type { ScanResponse } from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 60_000,
});

axiosRetry(apiClient, {
  retries: 2,
  retryDelay: axiosRetry.exponentialDelay,
  retryCondition: (error) =>
    error.response?.status !== undefined && error.response.status >= 500,
});

export async function scanPassport(
  file: File,
  onUploadProgress?: (pct: number) => void
): Promise<ScanResponse> {
  const form = new FormData();
  form.append("passport_image", file);

  const { data } = await apiClient.post<ScanResponse>("/api/v1/scan", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (evt) => {
      if (onUploadProgress && evt.total) {
        onUploadProgress(Math.round((evt.loaded / evt.total) * 100));
      }
    },
  });
  return data;
}

export async function validateMRZ(line1: string, line2: string) {
  const { data } = await apiClient.post("/api/v1/validate", {
    mrz_line_1: line1,
    mrz_line_2: line2,
  });
  return data;
}

export async function checkHealth() {
  const { data } = await apiClient.get("/api/v1/health");
  return data;
}
