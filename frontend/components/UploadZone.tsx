"use client";

import { useCallback, useRef, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, Camera, AlertCircle, Loader2 } from "lucide-react";
import { cn, formatBytes, checkImageResolution } from "@/lib/utils";
import { scanPassport } from "@/lib/api";
import { useScanStore } from "@/store/scanStore";
import { DataHandlingNotice } from "./DataHandlingNotice";

const ACCEPTED_TYPES = {
  "image/jpeg": [".jpg", ".jpeg"],
  "image/png": [".png"],
  "image/heic": [".heic"],
  "image/heif": [".heif"],
};
const MAX_SIZE = 10 * 1024 * 1024; // 10 MB

async function normalizeFile(file: File): Promise<File> {
  const isHeic =
    file.type === "image/heic" ||
    file.type === "image/heif" ||
    file.name.toLowerCase().endsWith(".heic") ||
    file.name.toLowerCase().endsWith(".heif");

  if (isHeic) {
    try {
      const heic2any = (await import("heic2any")).default;
      const blob = await heic2any({ blob: file, toType: "image/jpeg", quality: 0.92 });
      const out = Array.isArray(blob) ? blob[0] : blob;
      return new File([out], file.name.replace(/\.(heic|heif)$/i, ".jpg"), {
        type: "image/jpeg",
      });
    } catch {
      throw new Error("Failed to convert HEIC file. Please convert to JPEG manually.");
    }
  }
  return file;
}

export function UploadZone() {
  const { setStatus, setScanResult, setUploadProgress, setError, reset, status } = useScanStore();
  const [clientError, setClientError] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const cameraRef = useRef<HTMLInputElement>(null);

  const processFile = useCallback(
    async (rawFile: File) => {
      setClientError(null);
      reset();

      // Validate size
      if (rawFile.size > MAX_SIZE) {
        setClientError(`File is ${formatBytes(rawFile.size)} — maximum is 10 MB.`);
        return;
      }

      let file: File;
      try {
        file = await normalizeFile(rawFile);
      } catch (err: unknown) {
        setClientError(err instanceof Error ? err.message : "Conversion failed");
        return;
      }

      // Resolution check
      const res = await checkImageResolution(file);
      if (!res.ok) {
        setClientError(
          `Image resolution ${res.width}×${res.height}px is too low. Minimum long edge: 1400px.`
        );
        return;
      }

      // Preview
      const objectUrl = URL.createObjectURL(file);
      setPreview(objectUrl);

      // Upload
      setStatus("uploading");
      try {
        const result = await scanPassport(file, (pct) => {
          setUploadProgress(pct);
          if (pct === 100) setStatus("processing");
        });
        setScanResult(result);
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          (err instanceof Error ? err.message : "Unknown error");
        setError(msg);
      } finally {
        URL.revokeObjectURL(objectUrl);
      }
    },
    [reset, setError, setScanResult, setStatus, setUploadProgress]
  );

  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted[0]) processFile(accepted[0]);
    },
    [processFile]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxFiles: 1,
    disabled: status === "uploading" || status === "processing",
  });

  const isLoading = status === "uploading" || status === "processing";

  return (
    <div className="space-y-4">
      <DataHandlingNotice />

      <div
        {...getRootProps()}
        className={cn(
          "relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 transition-colors",
          isDragActive
            ? "border-blue-500 bg-blue-50"
            : "border-gray-300 bg-gray-50 hover:border-blue-400 hover:bg-blue-50",
          isLoading && "pointer-events-none opacity-60"
        )}
      >
        <input {...getInputProps()} />

        {isLoading ? (
          <Loader2 className="mb-3 h-10 w-10 animate-spin text-blue-500" />
        ) : (
          <Upload className="mb-3 h-10 w-10 text-gray-400" />
        )}

        <p className="text-center text-sm font-medium text-gray-700">
          {isLoading
            ? status === "uploading"
              ? "Uploading…"
              : "Processing with AI…"
            : isDragActive
            ? "Drop the passport image here"
            : "Drag & drop your passport image, or click to browse"}
        </p>
        <p className="mt-1 text-xs text-gray-500">JPEG, PNG, or HEIC — max 10 MB, min 1400px</p>
      </div>

      {/* Camera capture button */}
      <button
        type="button"
        onClick={() => cameraRef.current?.click()}
        disabled={isLoading}
        className="flex w-full items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 disabled:opacity-50"
      >
        <Camera className="h-4 w-4" />
        Take a photo
      </button>
      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) processFile(f);
          e.target.value = "";
        }}
      />

      {clientError && (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          {clientError}
        </div>
      )}

      {preview && !isLoading && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={preview}
          alt="Passport preview"
          className="mx-auto max-h-48 rounded-lg border object-contain shadow-sm"
        />
      )}
    </div>
  );
}
