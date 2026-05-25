import { create } from "zustand";
import type { PassportData, ScanResponse, ScanStatus } from "@/lib/types";

interface ScanStore {
  status: ScanStatus;
  scanResult: ScanResponse | null;
  editedFields: Partial<PassportData>;
  uploadProgress: number;
  errorMessage: string | null;

  setStatus: (s: ScanStatus) => void;
  setScanResult: (r: ScanResponse) => void;
  setEditedField: <K extends keyof PassportData>(key: K, value: PassportData[K]) => void;
  setUploadProgress: (pct: number) => void;
  setError: (msg: string) => void;
  reset: () => void;
}

const initialState = {
  status: "idle" as ScanStatus,
  scanResult: null,
  editedFields: {},
  uploadProgress: 0,
  errorMessage: null,
};

export const useScanStore = create<ScanStore>((set) => ({
  ...initialState,

  setStatus: (status) => set({ status }),
  setScanResult: (scanResult) => set({ scanResult, status: "done", errorMessage: null }),
  setEditedField: (key, value) =>
    set((s) => ({ editedFields: { ...s.editedFields, [key]: value } })),
  setUploadProgress: (uploadProgress) => set({ uploadProgress }),
  setError: (errorMessage) => set({ errorMessage, status: "error" }),
  reset: () => set(initialState),
}));

/** Merged view: scanResult.data overridden by any manual edits */
export function useMergedData(store: ScanStore): PassportData | null {
  if (!store.scanResult?.data) return null;
  return { ...store.scanResult.data, ...store.editedFields } as PassportData;
}
