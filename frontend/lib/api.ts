import axios from "axios";
import axiosRetry from "axios-retry";
import type { ScanResponse } from "./types";

// Empty string = relative URL → requests go through the Next.js proxy route
// (frontend/app/api/v1/[...path]/route.ts), never directly to the backend.
// The proxy reads BACKEND_URL server-side, so CORS is never an issue.
const BASE_URL = "";

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 60_000,
});

axiosRetry(apiClient, {
  retries: 2,
  retryDelay: axiosRetry.exponentialDelay,
  retryCondition: (error) => {
    const status = error.response?.status;
    // Don't retry 502/503/504 — gateway is down, retrying immediately won't help
    if (status === 502 || status === 503 || status === 504) return false;
    return status !== undefined && status >= 500;
  },
});

export async function scanPassport(
  file: File,
  onUploadProgress?: (pct: number) => void
): Promise<ScanResponse> {
  const form = new FormData();
  form.append("passport_image", file);

  const { data } = await apiClient.post<ScanResponse>("/api/v1/scan", form, {
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
