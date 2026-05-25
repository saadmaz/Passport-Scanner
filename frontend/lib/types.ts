export type Confidence = "high" | "medium" | "low";
export type ExtractionMethod = "tesseract_mrz" | "none";
export type MrzFormat = "TD1" | "TD2" | "TD3";
export type Sex = "M" | "F" | "X";

export interface CheckDigitResult {
  passport_number: boolean;
  date_of_birth: boolean;
  date_of_expiry: boolean;
  composite: boolean;
}

export interface PassportData {
  document_type: string | null;
  issuing_country: string | null;
  surname: string | null;
  given_names: string | null;
  passport_number: string | null;
  nationality: string | null;
  date_of_birth: string | null;
  sex: Sex | null;
  date_of_expiry: string | null;
  personal_number: string | null;
  mrz_line_1: string | null;
  mrz_line_2: string | null;
  mrz_format: MrzFormat | null;
}

export interface ScanResponse {
  success: boolean;
  extraction_method: ExtractionMethod;
  confidence: Confidence;
  check_digits_valid: CheckDigitResult;
  warnings: string[];
  processing_time_ms: number;
  data: PassportData | null;
}

export type ScanStatus = "idle" | "uploading" | "processing" | "done" | "error";

export interface ApiError {
  detail: string;
}
