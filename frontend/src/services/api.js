async function request(path, options = {}) {
  const response = await fetch(path, options);
  const contentType = response.headers.get("content-type") || "";
  let body = null;
  if (contentType.includes("application/json")) {
    try {
      body = await response.json();
    } catch {
      body = null;
    }
  } else if (!response.ok) {
    try {
      body = { detail: await response.text() };
    } catch {
      body = null;
    }
  }
  if (!response.ok) {
    const detail = body?.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : detail
          ? JSON.stringify(detail)
          : `Request failed (${response.status})`,
    );
  }
  return body;
}

export const api = {
  health: () => request("/api/health"),
  reports: () => request("/api/reports"),
  report: (id) => request(`/api/reports/${encodeURIComponent(id)}`),
  deleteReport: (id) =>
    request(`/api/reports/${encodeURIComponent(id)}`, { method: "DELETE" }),
  sample: (docType) =>
    request(`/api/sample?doc_type=${encodeURIComponent(docType)}`),
  analyzeText: (payload) =>
    request("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  analyzeFile: (file, language, persist, sourceLanguage = "auto") => {
    const form = new FormData();
    form.append("file", file);
    form.append("language", language);
    form.append("source_language", sourceLanguage);
    form.append("persist", String(persist));
    return request("/api/analyze/file", { method: "POST", body: form });
  },
  translateReport: (report, language) =>
    request("/api/translate/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        report: report?.canonical_report || report,
        language,
      }),
    }),
  translationStatus: () => request("/api/translation/status"),
  ask: (report, question, language) =>
    request("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        language,
        clauses: report.clauses || [],
      }),
    }),
  calculateBond: (payload) =>
    request("/api/calc/bond", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  metrics: () => request("/api/metrics"),
};
