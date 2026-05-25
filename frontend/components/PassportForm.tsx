"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { useScanStore, useMergedData } from "@/store/scanStore";
import type { PassportData, CheckDigitResult, Confidence } from "@/lib/types";

type FormValues = Partial<PassportData>;

const FIELDS: Array<{
  key: keyof PassportData;
  label: string;
  checkDigitKey?: keyof CheckDigitResult;
}> = [
  { key: "surname", label: "Surname" },
  { key: "given_names", label: "Given Names" },
  { key: "document_type", label: "Document Type" },
  { key: "issuing_country", label: "Issuing Country" },
  { key: "nationality", label: "Nationality" },
  { key: "passport_number", label: "Passport Number", checkDigitKey: "passport_number" },
  { key: "date_of_birth", label: "Date of Birth", checkDigitKey: "date_of_birth" },
  { key: "sex", label: "Sex" },
  { key: "date_of_expiry", label: "Date of Expiry", checkDigitKey: "date_of_expiry" },
  { key: "personal_number", label: "Personal Number" },
  { key: "mrz_line_1", label: "MRZ Line 1" },
  { key: "mrz_line_2", label: "MRZ Line 2" },
  { key: "mrz_format", label: "MRZ Format" },
];

export function PassportForm() {
  const store = useScanStore();
  const merged = useMergedData(store);
  const { scanResult, setEditedField } = store;

  const { register, reset, watch } = useForm<FormValues>({ defaultValues: merged ?? {} });

  useEffect(() => {
    if (merged) reset(merged);
  }, [scanResult, reset, merged]);

  // Persist edits back to store
  useEffect(() => {
    const sub = watch((values) => {
      Object.entries(values).forEach(([k, v]) => {
        setEditedField(k as keyof PassportData, v as PassportData[keyof PassportData]);
      });
    });
    return () => sub.unsubscribe();
  }, [watch, setEditedField]);

  if (!scanResult) return null;

  const { confidence, check_digits_valid, extraction_method, warnings } = scanResult;

  const fieldConfidence = (key: keyof CheckDigitResult | undefined): Confidence => {
    if (!key) return confidence;
    return check_digits_valid[key] ? confidence : "low";
  };

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="flex flex-wrap items-center gap-3 rounded-lg border bg-white p-4 shadow-sm">
        <span className="text-sm font-medium text-gray-700">Extraction:</span>
        <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">
          {extraction_method}
        </span>
        <ConfidenceBadge confidence={confidence} label={`${confidence} confidence`} />
      </div>

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="space-y-2">
          {warnings.map((w, i) => (
            <div
              key={i}
              className="flex items-start gap-2 rounded-lg border border-orange-200 bg-orange-50 p-3 text-sm text-orange-800"
            >
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-orange-500" />
              {w}
            </div>
          ))}
        </div>
      )}

      {/* Fields grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {FIELDS.map(({ key, label, checkDigitKey }) => {
          const fc = fieldConfidence(checkDigitKey);
          const checkFailed = checkDigitKey && !check_digits_valid[checkDigitKey];

          return (
            <div key={key} className="space-y-1">
              <div className="flex items-center gap-2">
                <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  {label}
                </label>
                <ConfidenceBadge confidence={fc} />
                {extraction_method === "tesseract_mrz" && (
                  <span className="rounded-full bg-purple-100 px-2 py-0.5 text-xs text-purple-700">
                    OCR fallback
                  </span>
                )}
                {checkFailed && (
                  <span className="rounded-full bg-orange-100 px-2 py-0.5 text-xs text-orange-700">
                    check digit
                  </span>
                )}
              </div>
              <input
                {...register(key)}
                className={cn(
                  "w-full rounded-md border px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500",
                  checkFailed ? "border-orange-300 bg-orange-50" : "border-gray-200 bg-white"
                )}
                placeholder="—"
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
