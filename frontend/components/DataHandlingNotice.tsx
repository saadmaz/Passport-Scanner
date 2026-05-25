"use client";

import { ShieldCheck } from "lucide-react";

export function DataHandlingNotice() {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-800">
      <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-blue-600" />
      <div>
        <p className="font-semibold">Data handling notice</p>
        <p className="mt-1 text-blue-700">
          Your passport image is processed in-memory only and is never stored on disk or logged.
          It is sent to Claude Vision for OCR and immediately discarded. No biometric data is
          retained after your session ends.
        </p>
      </div>
    </div>
  );
}
