"use client";

import { ScanLine, AlertCircle, RefreshCw } from "lucide-react";
import { UploadZone } from "@/components/UploadZone";
import { PassportForm } from "@/components/PassportForm";
import { ActionBar } from "@/components/ActionBar";
import { useScanStore } from "@/store/scanStore";

export default function Home() {
  const { status, errorMessage, reset } = useScanStore();
  const isDone = status === "done";
  const isError = status === "error";

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="border-b bg-white shadow-sm">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600">
            <ScanLine className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900">Passport Scanner</h1>
            <p className="text-xs text-gray-500">AI-powered MRZ extraction</p>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-4 py-8 space-y-6">
        {/* Upload section — always visible unless result is shown */}
        {!isDone && (
          <section className="rounded-xl border bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-base font-semibold text-gray-800">Upload Passport Image</h2>
            <UploadZone />
          </section>
        )}

        {/* Error state */}
        {isError && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-6">
            <div className="flex items-start gap-3">
              <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-500" />
              <div className="flex-1">
                <p className="font-semibold text-red-800">Extraction failed</p>
                <p className="mt-1 text-sm text-red-700">{errorMessage}</p>
              </div>
              <button
                onClick={reset}
                className="flex items-center gap-2 rounded-md border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Try again
              </button>
            </div>
          </div>
        )}

        {/* Results */}
        {isDone && (
          <>
            <ActionBar />

            <section className="rounded-xl border bg-white p-6 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-base font-semibold text-gray-800">Extracted Fields</h2>
                <button
                  onClick={reset}
                  className="text-sm text-blue-600 hover:underline"
                >
                  Scan another
                </button>
              </div>
              <PassportForm />
            </section>
          </>
        )}
      </div>
    </main>
  );
}
