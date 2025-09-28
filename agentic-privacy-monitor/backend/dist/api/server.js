"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const cors_1 = __importDefault(require("cors"));
const promises_1 = __importDefault(require("fs/promises"));
const datasetService_1 = require("../agents/datasetService");
const path_1 = __importDefault(require("path"));
const datasetService = new datasetService_1.DatasetService();
const app = (0, express_1.default)();
app.use(express_1.default.json());
app.use((0, cors_1.default)());
// -------------------------------
// Datasets - Detailed Info
// -------------------------------
app.get("/datasets", async (req, res) => {
    const datasets = datasetService.findDatasets();
    const details = await Promise.all(datasets.map(async (ds) => {
        let size = 0;
        let mtime = null;
        let columns = [];
        try {
            const stat = await promises_1.default.stat(ds.path);
            size = stat.size;
            mtime = stat.mtime;
            // Read first line for columns
            const file = await promises_1.default.open(ds.path, "r");
            const buffer = Buffer.alloc(4096);
            await file.read(buffer, 0, buffer.length, 0);
            const text = buffer.toString();
            columns = text
                .split("\n")[0]
                .split(",")
                .map((c) => c.trim());
            await file.close();
        }
        catch (e) {
            // Ignore errors, return minimal info
        }
        return {
            name: ds.name,
            path: ds.path,
            size,
            lastModified: mtime,
            columns,
        };
    }));
    res.json(details);
});
// In-memory jobs storage
const jobs = {};
// -------------------------------
// Health check
// -------------------------------
app.get("/health", (req, res) => res.json({ status: "ok" }));
// -------------------------------
// Privacy Monitor - Start Scan
// -------------------------------
app.post("/privacymonitor/start", async (req, res) => {
    // Use ISO string for folder name
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const resultsDir = path_1.default.resolve(__dirname, "../../results", timestamp);
    await promises_1.default.mkdir(resultsDir, { recursive: true });
    const resultsFile = path_1.default.join(resultsDir, "scan_results.json");
    const summaryFile = path_1.default.join(resultsDir, "explanation_report.txt");
    // Find all datasets
    const datasets = datasetService.findDatasets();
    if (!datasets || datasets.length === 0) {
        return res.status(404).json({ error: "No datasets found to scan." });
    }
    // Prepare dataset paths for orchestrator
    const datasetPaths = datasets.map((ds) => ds.path);
    // Call orchestrator FastAPI service via HTTP POST
    try {
        const orchestratorUrl = "http://localhost:8000/orchestrate";
        const axios = require("axios");
        const response = await axios.post(orchestratorUrl, { datasets: datasetPaths });
        const orchestratorResult = response.data;
        // Save orchestrator result to resultsFile
        await promises_1.default.writeFile(resultsFile, JSON.stringify(orchestratorResult, null, 2), "utf8");
        // Save summary to summaryFile
        const summaryText = orchestratorResult.summary && orchestratorResult.summary.summary ? orchestratorResult.summary.summary : "";
        await promises_1.default.writeFile(summaryFile, summaryText, "utf8");
        // Save job info
        jobs[timestamp] = { status: "done", resultsFile, summaryFile, timestamp: Date.now(), filename: datasetPaths.join(",") };
        res.json({
            folder: timestamp,
            status: "completed",
            results: resultsFile,
            summary: summaryFile,
            summaryText,
            scanFiles: [],
            explanationFiles: [],
        });
    }
    catch (error) {
        console.error("Orchestrator service error:", error);
        const errorMessage = error instanceof Error ? error.toString() : String(error);
        return res.status(500).json({ error: "Orchestrator service failed", details: errorMessage });
    }
});
// -------------------------------
// Privacy Monitor - Status
// -------------------------------
app.get("/privacymonitor/status/:jobId", async (req, res) => {
    const job = jobs[req.params.jobId];
    if (!job)
        return res.status(404).json({ error: "Job not found" });
    if (job.status === "done") {
        try {
            const results = JSON.parse(await promises_1.default.readFile(job.resultsFile, "utf8"));
            const summary = await promises_1.default.readFile(job.summaryFile, "utf8");
            return res.json({ status: "done", results, summary });
        }
        catch (err) {
            console.error("Error reading explanation file:", err);
            return res.status(500).json({ error: "Failed to read files" });
        }
    }
    res.json({ status: job.status });
});
// -------------------------------
// Historical scans grouped by session with explanation
// -------------------------------
app.get("/privacymonitor/historical", async (req, res) => {
    try {
        const resultsDir = path_1.default.resolve(__dirname, "../../results");
        const entries = await promises_1.default.readdir(resultsDir, { withFileTypes: true });
        const scanFolders = entries.filter((e) => e.isDirectory());
        const historicalScans = await Promise.all(scanFolders.map(async (folder) => {
            const folderPath = path_1.default.join(resultsDir, folder.name);
            const resultsFile = path_1.default.join(folderPath, "scan_results.json");
            let scanResults = [];
            try {
                const resultsRaw = await promises_1.default.readFile(resultsFile, "utf8");
                scanResults = JSON.parse(resultsRaw);
            }
            catch {
                // If scan_results.json missing, keep empty
            }
            // Only load folder-level explanation report
            const reportPath = path_1.default.join(folderPath, "explanation_report.txt");
            let folderExplanationReport = null;
            try {
                folderExplanationReport = await promises_1.default.readFile(reportPath, "utf8");
            }
            catch {
                // If report is missing, keep null
            }
            const stats = await promises_1.default.stat(folderPath);
            return {
                id: folder.name,
                folder: folder.name,
                timestamp: stats.ctimeMs,
                scanResults,
                explanationReport: folderExplanationReport,
            };
        }));
        historicalScans.sort((a, b) => b.timestamp - a.timestamp);
        res.json({ scans: historicalScans });
    }
    catch (err) {
        console.error("Error loading historical scans:", err);
        res.status(500).json({ error: "Failed to load historical scans", details: err });
    }
});
// -------------------------------
// Individual scan results
// -------------------------------
app.get("/privacymonitor/results/:jobId", async (req, res) => {
    const job = jobs[req.params.jobId];
    if (!job)
        return res.status(404).json({ error: "Job not found" });
    try {
        const results = JSON.parse(await promises_1.default.readFile(job.resultsFile, "utf8"));
        res.json({ results });
    }
    catch (err) {
        console.error("Error reading scan results:", err);
        res.status(500).json({ error: "Failed to read scan results" });
    }
});
// -------------------------------
// Individual scan summary
// -------------------------------
app.get("/privacymonitor/summary/:jobId", async (req, res) => {
    const job = jobs[req.params.jobId];
    if (!job)
        return res.status(404).json({ error: "Job not found" });
    try {
        const summary = await promises_1.default.readFile(job.summaryFile, "utf8");
        res.json({ summary });
    }
    catch (err) {
        console.error("Error reading scan summary:", err);
        res.status(500).json({ error: "Failed to read scan summary" });
    }
});
// -------------------------------
// Get list of datasets
// -------------------------------
app.get("/datasets", async (req, res) => {
    try {
        // Find all CSV datasets
        const datasets = datasetService.findDatasets();
        // Try to find the latest scan folder with scan_results.json
        const resultsDir = path_1.default.resolve(__dirname, "../../results");
        const entries = await promises_1.default.readdir(resultsDir, { withFileTypes: true });
        const scanFolders = entries.filter((e) => e.isDirectory());
        let latestFolder = null;
        let latestTime = 0;
        for (const folder of scanFolders) {
            const folderPath = path_1.default.join(resultsDir, folder.name);
            const resultsFile = path_1.default.join(folderPath, "scan_results.json");
            try {
                const stats = await promises_1.default.stat(resultsFile);
                if (stats.mtimeMs > latestTime) {
                    latestTime = stats.mtimeMs;
                    latestFolder = folderPath;
                }
            }
            catch {
                // skip if scan_results.json missing
            }
        }
        let perDatasetExplanations = {};
        if (latestFolder) {
            // Read all per-dataset explanation reports in the latest scan folder
            const files = await promises_1.default.readdir(latestFolder);
            for (const file of files) {
                const match = file.match(/^explanation_report_(.+)\.txt$/);
                if (match) {
                    const datasetKey = match[1];
                    const explanation = await promises_1.default.readFile(path_1.default.join(latestFolder, file), "utf8");
                    perDatasetExplanations[datasetKey] = explanation;
                }
            }
        }
        // Attach explanationReport to each dataset if available
        const datasetsWithExplanation = datasets.map((ds) => {
            const name = ds.name; // now always base filename
            const baseName = name ? name.replace(/\.csv$/i, "") : "Unknown";
            return {
                ...ds,
                explanationReport: perDatasetExplanations[baseName] || null,
            };
        });
        res.json({ data: { datasets: datasetsWithExplanation } });
    }
    catch (err) {
        console.error("Error fetching datasets:", err);
        res.status(500).json({ error: "Failed to fetch datasets", details: err });
    }
});
// -------------------------------
// Dataset details endpoint for Datasets UI (always latest scan, with findings)
// -------------------------------
app.get("/dataset-details", async (req, res) => {
    try {
        // Find all CSV datasets
        const datasets = datasetService.findDatasets();
        // Find latest scan folder with scan_results.json
        const resultsDir = path_1.default.resolve(__dirname, "../../results");
        const entries = await promises_1.default.readdir(resultsDir, { withFileTypes: true });
        const scanFolders = entries.filter((e) => e.isDirectory());
        let latestFolder = null;
        let latestTime = 0;
        for (const folder of scanFolders) {
            const folderPath = path_1.default.join(resultsDir, folder.name);
            const resultsFile = path_1.default.join(folderPath, "scan_results.json");
            try {
                const stats = await promises_1.default.stat(resultsFile);
                if (stats.mtimeMs > latestTime) {
                    latestTime = stats.mtimeMs;
                    latestFolder = folderPath;
                }
            }
            catch {
                // skip if scan_results.json missing
            }
        }
        const perDatasetExplanations = {};
        let scanResults = [];
        if (latestFolder) {
            // Read all per-dataset explanation reports in the latest scan folder
            const files = await promises_1.default.readdir(latestFolder);
            for (const file of files) {
                const match = file.match(/^explanation_report_(.+)\.txt$/);
                if (match) {
                    const datasetKey = match[1];
                    const explanation = await promises_1.default.readFile(path_1.default.join(latestFolder, file), "utf8");
                    perDatasetExplanations[datasetKey] = explanation;
                }
            }
            // Read scan_results.json
            try {
                scanResults = JSON.parse(await promises_1.default.readFile(path_1.default.join(latestFolder, "scan_results.json"), "utf8"));
            }
            catch { }
        }
        // Attach explanationReport and scanResult to each dataset if available
        const datasetsWithDetails = datasets.map((ds) => {
            const name = ds.name;
            const baseName = name ? name.replace(/\.csv$/i, "") : "Unknown";
            // Try to find scan result for this dataset
            const scanResult = scanResults.find((r) => {
                const rName = r.file ? r.file.split("/").pop() : null;
                return rName === name;
            });
            return {
                ...ds,
                explanationReport: perDatasetExplanations[baseName] || null,
                scanResult: scanResult || null,
            };
        });
        res.json({ data: { datasets: datasetsWithDetails } });
    }
    catch (err) {
        console.error("Error fetching dataset details:", err);
        res.status(500).json({ error: "Failed to fetch dataset details", details: err });
    }
});
// -------------------------------
// Scan endpoint using scannerAgent
// -------------------------------
app.get("/scan", async (req, res) => {
    try {
        // Always use the latest scan folder with scan_results.json
        const resultsDir = path_1.default.resolve(__dirname, "../../results");
        const entries = await promises_1.default.readdir(resultsDir, { withFileTypes: true });
        const scanFolders = entries.filter((e) => e.isDirectory());
        let latestFolder = null;
        let latestTime = 0;
        for (const folder of scanFolders) {
            const folderPath = path_1.default.join(resultsDir, folder.name);
            const resultsFile = path_1.default.join(folderPath, "scan_results.json");
            try {
                const stats = await promises_1.default.stat(resultsFile);
                if (stats.mtimeMs > latestTime) {
                    latestTime = stats.mtimeMs;
                    latestFolder = folderPath;
                }
            }
            catch {
                // skip if scan_results.json missing
            }
        }
        if (!latestFolder) {
            return res.status(404).json({ error: "No scan results found. Please run a scan first." });
        }
        // Read scan_results.json
        let scanResults = [];
        try {
            scanResults = JSON.parse(await promises_1.default.readFile(path_1.default.join(latestFolder, "scan_results.json"), "utf8"));
        }
        catch {
            return res.status(500).json({ error: "Could not read scan_results.json in latest folder." });
        }
        // Read all per-dataset explanation reports in the latest scan folder
        let perDatasetExplanations = {};
        const files = await promises_1.default.readdir(latestFolder);
        for (const file of files) {
            const match = file.match(/^explanation_report_(.+)\.txt$/);
            if (match) {
                const datasetKey = match[1];
                const explanation = await promises_1.default.readFile(path_1.default.join(latestFolder, file), "utf8");
                perDatasetExplanations[datasetKey] = explanation;
            }
        }
        // Create simplified dataset list (name + path + metadata + explanationReport)
        const datasets = scanResults.map((item) => {
            const name = item.file.split("/").pop(); // base filename only
            const baseName = name ? name.replace(/\.csv$/i, "") : "Unknown";
            return {
                name,
                path: item.file,
                ...item.metadata,
                explanationReport: perDatasetExplanations[baseName] || null,
            };
        });
        // Return summary datasets, full results, folder-level and per-dataset explanations
        let folderExplanationReport = null;
        try {
            folderExplanationReport = await promises_1.default.readFile(path_1.default.join(latestFolder, "explanation_report.txt"), "utf8");
        }
        catch { }
        res.json({
            datasets,
            fullResults: scanResults,
            resultsFolder: latestFolder,
            explanationReport: folderExplanationReport,
            perDatasetExplanations,
        });
    }
    catch (err) {
        console.error("Error scanning datasets:", err);
        res.status(500).json({ error: "Failed to scan datasets", details: err });
    }
});
// -------------------------------
// Overall risk level based on latest scan
// -------------------------------
app.get("/overview/risk", async (req, res) => {
    try {
        const resultsDir = path_1.default.resolve(__dirname, "../../results");
        // Get all scan folders
        const entries = await promises_1.default.readdir(resultsDir, { withFileTypes: true });
        const scanFolders = entries.filter((e) => e.isDirectory());
        if (scanFolders.length === 0) {
            return res.json({ riskLevel: "Unknown", message: "No scans found" });
        }
        // Find the latest scan folder that actually contains scan_results.json
        let latestValidFolder = null;
        let latestTimestamp = 0;
        for (const folder of scanFolders) {
            const folderTimestamp = parseInt(folder.name);
            if (isNaN(folderTimestamp))
                continue;
            const resultsFile = path_1.default.join(resultsDir, folder.name, "scan_results.json");
            try {
                await promises_1.default.access(resultsFile);
                if (folderTimestamp > latestTimestamp) {
                    latestTimestamp = folderTimestamp;
                    latestValidFolder = folder.name;
                }
            }
            catch {
                // skip folders without scan_results.json
            }
        }
        if (!latestValidFolder) {
            return res.json({ riskLevel: "Unknown", message: "No valid scan results found" });
        }
        const resultsFile = path_1.default.join(resultsDir, latestValidFolder, "scan_results.json");
        let scanResultsRaw = null;
        let scanResults = [];
        try {
            scanResultsRaw = JSON.parse(await promises_1.default.readFile(resultsFile, "utf8"));
        }
        catch {
            // If scan_results.json missing or malformed, continue (riskLevel will be from explanation_report.txt)
        }
        if (Array.isArray(scanResultsRaw)) {
            scanResults = scanResultsRaw;
        }
        // Always try to extract overall risk from explanation_report.txt if present
        let riskLevel = "Unknown";
        let highRiskCount = 0;
        let mediumRiskCount = 0;
        if (Array.isArray(scanResults)) {
            for (const item of scanResults) {
                const flags = item.report?.risk_flags || [];
                flags.forEach((flag) => {
                    if (flag.toLowerCase().includes("below threshold") || flag.toLowerCase().includes("above threshold")) {
                        highRiskCount++;
                    }
                    else {
                        mediumRiskCount++;
                    }
                });
            }
        }
        const folderPath = path_1.default.join(resultsDir, latestValidFolder);
        const explanationPath = path_1.default.join(folderPath, "explanation_report.txt");
        try {
            const explanation = await promises_1.default.readFile(explanationPath, "utf8");
            // Extract the overall assessment section
            const overallSection = explanation.match(/\*\*Overall Assessment:\*\*[\s\S]*?(?=\*\*|$)/i);
            let assessmentText = overallSection ? overallSection[0] : explanation;
            assessmentText = assessmentText.toLowerCase();
            if (assessmentText.includes("high level of privacy risk") ||
                assessmentText.includes("significant privacy risk") ||
                assessmentText.includes("severe")) {
                riskLevel = "High";
            }
            else if (assessmentText.includes("moderate level of privacy risk") ||
                assessmentText.includes("moderate potential for re-identification") ||
                assessmentText.includes("moderate risk") ||
                assessmentText.includes("moderate")) {
                riskLevel = "Moderate";
            }
            else if (assessmentText.includes("low level of privacy risk") ||
                assessmentText.includes("minimal risk") ||
                assessmentText.includes("low risk") ||
                assessmentText.includes("low")) {
                riskLevel = "Low";
            }
            else {
                // fallback to old logic
                if (highRiskCount > 0)
                    riskLevel = "High";
                else if (mediumRiskCount > 0)
                    riskLevel = "Medium";
                else
                    riskLevel = "Low";
            }
        }
        catch {
            // fallback to old logic
            if (highRiskCount > 0)
                riskLevel = "High";
            else if (mediumRiskCount > 0)
                riskLevel = "Medium";
            else
                riskLevel = "Low";
        }
        res.json({
            riskLevel,
            latestScan: latestValidFolder,
            highRiskCount,
            mediumRiskCount,
            totalDatasets: Array.isArray(scanResults) ? scanResults.length : 0,
        });
    }
    catch (err) {
        console.error("Error computing overall risk:", err);
        // Type-safe error message
        const errorMessage = err instanceof Error ? err.message : String(err);
        res.status(500).json({ riskLevel: "Unknown", error: errorMessage });
    }
});
// -------------------------------
// Run basic metrics tests
// -------------------------------
app.get("/test", async (req, res) => {
    try {
        const timestamp = Date.now().toString();
        const resultsDir = path_1.default.resolve(__dirname, "../../tests/results", timestamp);
        await promises_1.default.mkdir(resultsDir, { recursive: true });
        const testFile = path_1.default.resolve(__dirname, "../../tests/test_basic_metrics.py");
        const stdoutFile = path_1.default.join(resultsDir, "stdout.txt");
        const stderrFile = path_1.default.join(resultsDir, "stderr.txt");
        const summaryFile = path_1.default.join(resultsDir, "summary.json");
        const { exec } = await Promise.resolve().then(() => __importStar(require("child_process")));
        exec(`python3.11 -m pytest "${testFile}" -v --tb=short`, { cwd: path_1.default.dirname(testFile) }, async (error, stdout, stderr) => {
            await promises_1.default.writeFile(stdoutFile, stdout, "utf8");
            await promises_1.default.writeFile(stderrFile, stderr, "utf8");
            const summary = {
                status: error ? "failed" : "passed",
                timestamp: Date.now(),
            };
            await promises_1.default.writeFile(summaryFile, JSON.stringify(summary, null, 2), "utf8");
            res.json({
                resultsFolder: resultsDir,
                summary,
            });
        });
    }
    catch (err) {
        console.error("Error running tests:", err);
        res.status(500).json({ error: "Failed to run tests", details: err instanceof Error ? err.message : String(err) });
    }
});
// -------------------------------
// Recent individual dataset explanation reports
// -------------------------------
app.get("/api/recent-reports", async (req, res) => {
    try {
        const resultsDir = path_1.default.resolve(__dirname, "../../results");
        const entries = await promises_1.default.readdir(resultsDir, { withFileTypes: true });
        const scanFolders = entries.filter((e) => e.isDirectory());
        // Sort folders by timestamp descending
        scanFolders.sort((a, b) => b.name.localeCompare(a.name));
        const seenDatasets = new Set();
        const recentReports = [];
        for (const folder of scanFolders) {
            const folderPath = path_1.default.join(resultsDir, folder.name);
            const files = await promises_1.default.readdir(folderPath);
            for (const file of files) {
                const match = file.match(/^explanation_report_(.+)\.txt$/);
                if (match) {
                    const datasetKey = match[1];
                    if (!seenDatasets.has(datasetKey)) {
                        const filePath = path_1.default.join(folderPath, file);
                        const content = await promises_1.default.readFile(filePath, "utf8");
                        const stats = await promises_1.default.stat(filePath);
                        recentReports.push({
                            name: datasetKey,
                            content,
                            timestamp: stats.mtime,
                        });
                        seenDatasets.add(datasetKey);
                    }
                }
            }
        }
        // Sort by timestamp descending
        recentReports.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
        res.json(recentReports);
    }
    catch (err) {
        console.error("Error loading recent reports:", err);
        res.status(500).json({ error: "Failed to load recent reports", details: err });
    }
});
// -------------------------------
// Start server
// -------------------------------
const PORT = process.env.PORT || 8080;
app.listen(PORT, () => console.log(`Server listening on port ${PORT}`));
