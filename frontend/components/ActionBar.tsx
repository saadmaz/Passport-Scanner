"use client";

import { useState } from "react";
import { Copy, Download, RotateCcw, CheckCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { useScanStore, useMergedData } from "@/store/scanStore";

export function ActionBar() {
  const store = useScanStore();
  const merged = useMergedData(store);
  const { reset, scanResult } = store;
  const [copied, setCopied] = useState(false);

  if (!scanResult) return null;

  const jsonString = JSON.stringify(merged, null, 2);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([jsonString], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "passport-data.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border bg-white p-3 shadow-sm">
      <span className="text-sm font-medium text-gray-600 mr-auto">
        Processed in {scanResult.processing_time_ms.toFixed(0)} ms
      </span>

      <button
        onClick={handleCopy}
        className={cn(
          "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
          copied
            ? "bg-green-100 text-green-700"
            : "border border-gray-200 bg-white text-gray-700 hover:bg-gray-50"
        )}
      >
        {copied ? <CheckCheck className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
        {copied ? "Copied!" : "Copy JSON"}
      </button>

      <button
        onClick={handleDownload}
        className="flex items-center gap-2 rounded-md border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
      >
        <Download className="h-4 w-4" />
        Download JSON
      </button>

      <button
        onClick={reset}
        className="flex items-center gap-2 rounded-md border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-red-50 hover:border-red-200 hover:text-red-700 transition-colors"
      >
        <RotateCcw className="h-4 w-4" />
        Clear
      </button>
    </div>
  );
}
