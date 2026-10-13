export type RiskLevel = "low" | "medium" | "high";
export type ClaimStatus = "draft" | "ready" | "submitted" | "paid" | "denied" | "appealed" | "recovered";

export interface ClaimListItem {
  id: string;
  claim_number: string;
  status: ClaimStatus;
  total_billed: string;
  icd10_codes: string[];
  cpt_codes: string[];
  denial_reason: string | null;
  submitted_at: string | null;
  decided_at: string | null;
  created_at: string;
  first_name: string;
  last_name: string;
  mrn: string;
  payer_name: string;
  payer_code: string;
  encounter_type: string;
  department: string | null;
  attending_physician: string | null;
  risk_score: string | null;
  risk_level: RiskLevel | null;
  scored_at: string | null;
}

export interface PolicyCitation {
  policy_number: string;
  title: string;
  relevance_score?: number;
}

export interface RiskReason {
  severity: "high" | "medium" | "low" | "info";
  message: string;
  suggested_action: string | null;
  suggested_code?: string | null;
  policy_citation: PolicyCitation | null;
}

export interface PositiveFinding {
  message: string;
  policy_citation: PolicyCitation | null;
}

export interface DenialScoreReasons {
  raw_reasons: RiskReason[];
  positive_findings: PositiveFinding[];
  bullets: string[];
  executive_summary: string | null;
}

export interface LatestScore {
  risk_score: string;
  risk_level: RiskLevel;
  reasons: DenialScoreReasons;
  policy_citations: PolicyCitation[];
  model_version: string;
  scored_at: string;
}

export interface ClinicalNote {
  id: string;
  note_type: string;
  author: string | null;
  content: string;
  created_at: string;
}

export interface CodeSuggestion {
  code_system: "ICD10" | "CPT";
  code: string;
  description: string;
  rationale: string;
}

export interface LatestExtraction {
  icd10_codes: CodeSuggestion[];
  cpt_codes: CodeSuggestion[];
  missing_charges: CodeSuggestion[];
  model_used: string;
  created_at: string;
}

export interface FraudFlag {
  flag_type: string;
  severity: "low" | "medium" | "high";
  description: string;
  detected_at: string;
}

export interface AppealLetter {
  id: string;
  denial_reason: string | null;
  letter_content: string;
  evidence_used: PolicyCitation[];
  status: "draft" | "reviewed" | "sent";
  generated_at: string;
}

export interface ClaimDetail {
  claim: ClaimListItem & { encounter_id: string; payer_id: string; date_of_birth: string };
  notes: ClinicalNote[];
  latest_score: LatestScore | null;
  latest_extraction: LatestExtraction | null;
  fraud_flags: FraudFlag[];
  appeal: AppealLetter | null;
}

export interface DashboardSummary {
  kpis: {
    total_billed: string;
    total_denied_amount: string;
    denied_count: number;
    decided_count: number;
    ready_count: number;
    recovered_count: number;
    denial_rate: number;
    revenue_at_risk: string;
  };
  risk_distribution: { risk_level: RiskLevel; claim_count: number }[];
  denials_by_payer: { payer_name: string; denial_count: number; denied_amount: string }[];
  recent_denials: { claim_number: string; payer_name: string; denial_reason: string; total_billed: string; decided_at: string }[];
}

export interface AppealListItem {
  claim_id: string;
  claim_number: string;
  denial_reason: string;
  total_billed: string;
  decided_at: string;
  payer_name: string;
  first_name: string;
  last_name: string;
  appeal_id: string | null;
  appeal_status: "draft" | "reviewed" | "sent" | null;
  generated_at: string | null;
}

export interface PolicySearchResult {
  id: string;
  text: string;
  score: number;
  metadata: { policy_number: string; title: string; category?: string; payer_code?: string };
}

export interface PolicyDoc {
  id: string;
  payer_code: string;
  payer_name: string;
  policy_number: string;
  title: string;
  category: string | null;
  content: string;
  effective_date: string | null;
}
