import axios from "axios";
// Two Axios clients for different backend ports
const api8080 = axios.create({
    baseURL: "http://localhost:8080",
    headers: { "Content-Type": "application/json" },
});
const api8000 = axios.create({
    baseURL: "http://localhost:8000",
    headers: { "Content-Type": "application/json" },
});

// Dataset details endpoint for Datasets UI
export const datasetDetailsAPI = () => api8080.get("/datasets");

// --- A2A Protocol Endpoints ---
export const getAgentCardAPI = () => api8080.get("/.well-known/agent.json");
export const sendA2AMessageAPI = (message: any) => api8080.post("/a2a/message", { message });

// --- MCP Tool Endpoints (example) ---
export const mcpValidatePrivacyAPI = (datasetPath: string, model = "gemini-pro") => api8080.post("/mcp/validate_privacy", { datasetPath, model });
export const mcpScanPrivacyAPI = (datasetPath: string, model = "gemini-pro") => api8080.post("/mcp/scan_privacy", { datasetPath, model });
export const mcpSummarisePrivacyAPI = (validationResult: any, scanResult: any, model = "gemini-pro") =>
    api8080.post("/mcp/summarise_privacy", { validationResult, scanResult, model });
export const mcpFullReportAPI = (datasetPath: string, qiCols: string[], sensitiveCol: string, params: any = {}) =>
    api8080.post("/mcp/full_report", { datasetPath, qiCols, sensitiveCol, ...params });

// Scan endpoints
export const scanAPI = (folder: string) => api8080.get(`/scan?folder=${encodeURIComponent(folder)}`);
export const scanDatasetsAPI = (folder: string) => api8080.get(`/scan?folder=${encodeURIComponent(folder)}`);
export const summaryAPI = () => api8080.get("/summary");
export const validateAPI = () => api8080.get("/validate");
export const datasetsAPI = () => api8080.get("/datasets");
export const healthCheckAPI = () => api8080.get("/health");
export const getOverviewRiskAPI = () => api8080.get("/overview/risk");

// Privacy Monitor endpoints
export const startOrchestratorAPI = (datasets: string[]) => api8000.post("/orchestrate", { datasets });

export const getExplanationReportAPI = (timestamp: string) => api8000.get(`/results/${encodeURIComponent(timestamp)}/explanation_report.txt`);
export const privacyMonitorStatusAPI = (jobId: string) => api8000.get(`/privacymonitor/status/${jobId}`);
export const historicalScansAPI = () => api8000.get("/privacymonitor/historical");
export const getScanResultsAPI = (jobId: string) => api8000.get(`/privacymonitor/results/${jobId}`);
export const getScanSummaryAPI = (jobId: string) => api8000.get(`/privacymonitor/summary/${jobId}`);
