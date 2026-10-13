const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    cache: "no-store",
    headers: { "Content-Type": "application/json", "X-User-Role": "billing_staff", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${init?.method || "GET"} ${path} failed: ${res.status} ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export function getClaims(filters: { status?: string; risk_level?: string; payer_code?: string } = {}) {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.risk_level) params.set("risk_level", filters.risk_level);
  if (filters.payer_code) params.set("payer_code", filters.payer_code);
  const qs = params.toString();
  return request<import("./types").ClaimListItem[]>(`/claims${qs ? `?${qs}` : ""}`);
}

export function getClaimDetail(id: string) {
  return request<import("./types").ClaimDetail>(`/claims/${id}`);
}

export function scoreClaim(id: string) {
  return request(`/claims/${id}/score`, { method: "POST" });
}

export function submitClaim(id: string) {
  return request(`/claims/${id}/submit`, { method: "POST" });
}

export function getDashboardSummary() {
  return request<import("./types").DashboardSummary>("/dashboard/summary");
}

export function getAppeals() {
  return request<import("./types").AppealListItem[]>("/appeals");
}

export function generateAppeal(claimId: string) {
  return request<import("./types").AppealLetter>(`/appeals/${claimId}/generate`, { method: "POST" });
}

export function getAppealsForClaim(claimId: string) {
  return request<import("./types").AppealLetter[]>(`/appeals/${claimId}`);
}

export function updateAppealStatus(letterId: string, status: string) {
  return request(`/appeals/letter/${letterId}/status?status=${status}`, { method: "PATCH" });
}

export function getPolicies(payerCode?: string) {
  const qs = payerCode ? `?payer_code=${payerCode}` : "";
  return request<import("./types").PolicyDoc[]>(`/policies${qs}`);
}

export function searchPolicies(q: string, payerCode: string) {
  return request<import("./types").PolicySearchResult[]>(`/policies/search?q=${encodeURIComponent(q)}&payer_code=${payerCode}`);
}

export function askQuestion(question: string) {
  return request<{ answer: string; context_used: Record<string, unknown> }>("/chat/ask", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}
