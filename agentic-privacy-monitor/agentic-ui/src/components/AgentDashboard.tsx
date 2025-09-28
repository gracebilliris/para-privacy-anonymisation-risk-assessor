import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { startOrchestratorAPI, getExplanationReportAPI, healthCheckAPI, historicalScansAPI, datasetsAPI } from "../api/client";

export const AgentDashboard: React.FC = () => {
    const [activeTab, setActiveTab] = useState("overview");
    const [datasets, setDatasets] = useState<any[]>([]);
    const [fullResults, setFullResults] = useState<any[]>([]);
    const [selectedDataset, setSelectedDataset] = useState<any | null>(null);
    const [health, setHealth] = useState<string | { status: string }>("Unknown");
    const [search, setSearch] = useState("");
    const [loading, setLoading] = useState<{ [key: string]: boolean }>({});

    // Historical scans
    const [historicalScans, setHistoricalScans] = useState<any[]>([]);
    const [selectedScan, setSelectedScan] = useState<any | null>(null);

    // Generic API caller
    const callAPI = async (key: string, apiFn: () => Promise<any>, setter: (data: any) => void, errorMsg: string) => {
        setLoading((prev) => ({ ...prev, [key]: true }));
        try {
            const res = await apiFn();
            await new Promise((r) => setTimeout(r, 500));
            setter(res.data?.results ?? res.data?.datasets ?? res.data ?? res);
        } catch (err) {
            console.error(err);
            setter(key === "privacyMonitor" || key === "datasets" ? [] : `Error: ${err}`);
            alert(errorMsg);
        } finally {
            setLoading((prev) => ({ ...prev, [key]: false }));
        }
    };

    const getStatusColor = (status: string) => {
        if (status.toLowerCase() === "ok") return "bg-green-100 text-green-800";
        if (status.toLowerCase() === "warning") return "bg-yellow-100 text-yellow-800";
        return "bg-red-100 text-red-800";
    };

    // Fetch scanned datasets
    const fetchScannedDatasets = async () => {
        setLoading((prev) => ({ ...prev, datasets: true }));
        try {
            const res = await fetch("http://localhost:8080/scan");
            const data = await res.json();

            setDatasets(data.datasets || []);
            setFullResults(data.fullResults || []);
        } catch (err) {
            console.error("Error fetching datasets:", err);
        } finally {
            setLoading((prev) => ({ ...prev, datasets: false }));
        }
    };

    const matchingResult = selectedDataset ? fullResults.find((r) => r.file === selectedDataset.path) : null;

    // Fetch health and historical scans on mount
    useEffect(() => {
        callAPI("health", healthCheckAPI, setHealth, "Error checking health");

        // Historical scans
        callAPI("historicalScans", historicalScansAPI, (data) => setHistoricalScans(data.scans ?? data ?? []), "Error fetching historical scans");
    }, []);

    // Start Privacy Monitor Scan (updated for orchestrator)
    const startScan = async () => {
        setLoading((prev) => ({ ...prev, privacyMonitor: true }));
        try {
            // Fetch dataset paths
            const res = await datasetsAPI();
            const datasets = Array.isArray(res.data) ? res.data.map((d: any) => d.path || d) : [];
            if (datasets.length === 0) {
                alert("No datasets found.");
                setLoading((prev) => ({ ...prev, privacyMonitor: false }));
                return;
            }
            // Start orchestrator scan
            const orchestrateRes = await startOrchestratorAPI(datasets);
            const timestamp = orchestrateRes.data.timestamp;
            // Fetch explanation report from backend results
            const reportRes = await getExplanationReportAPI(timestamp);
            alert(reportRes.data); // You can display this in the UI as needed
        } catch (err) {
            console.error("Error starting scan:", err);
            alert("Scan failed: " + ((err as Error)?.message || String(err)));
        } finally {
            setLoading((prev) => ({ ...prev, privacyMonitor: false }));
        }
    };

    // Removed unused cleanup effect

    return (
        <div className="min-h-screen bg-gray-100 p-6">
            <header className="mb-6 flex flex-col md:flex-row md:items-center md:justify-between">
                <h1 className="text-3xl font-bold text-gray-800">Agentic Privacy Monitor</h1>
            </header>

            {/* Tabs */}
            <div className="border-b mb-6 flex gap-4">
                {["overview", "datasets", "historicalScans", "privacyMonitor"].map((tab) => (
                    <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`pb-2 text-sm font-medium capitalize ${
                            activeTab === tab ? "border-b-2 border-blue-600 text-blue-600" : "text-gray-600 hover:text-gray-800"
                        }`}
                    >
                        {tab === "overview" && "Overview"}
                        {tab === "datasets" && "Datasets"}
                        {tab === "historicalScans" && "Historical Privacy Monitor"}
                        {tab === "privacyMonitor" && "Privacy Monitor"}
                    </button>
                ))}
            </div>

            {/* Overview Tab */}
            {activeTab === "overview" && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-white shadow-lg rounded-lg p-6">
                        <h2 className="text-xl font-semibold mb-4">Overall Risk Level</h2>
                        <div className="w-32 h-32 mx-auto rounded-full bg-red-200 flex items-center justify-center">
                            <span className="text-lg font-bold text-red-800">High</span>
                        </div>
                    </div>
                    <div className="bg-white shadow-lg rounded-lg p-6 flex flex-col justify-between">
                        <div className="flex justify-between items-center mb-4">
                            <h2 className="text-xl font-semibold text-gray-700">Health Check</h2>
                            <button
                                onClick={() => callAPI("health", healthCheckAPI, setHealth, "Error checking health")}
                                className="px-2 py-1 text-sm border rounded hover:bg-gray-100"
                            >
                                Refresh
                            </button>
                        </div>
                        <div className={`p-4 rounded ${getStatusColor(typeof health === "string" ? health : health.status ?? "Unknown")}`}>
                            <span className="font-bold text-lg">{typeof health === "string" ? health : health.status ?? "Unknown"}</span>
                        </div>
                        {loading.health && <p className="text-gray-500 mt-2">⏳ Loading...</p>}
                    </div>
                </div>
            )}

            {/* Datasets Tab */}
            {activeTab === "datasets" && (
                <div className="bg-white shadow-lg rounded-lg p-6">
                    <h2 className="text-xl font-semibold mb-4">Datasets</h2>
                    <div className="historical-scans-container">
                        {/* LEFT column: datasets */}
                        <div className="historical-scans-list">
                            <div className="flex justify-between items-center mb-2 px-2">
                                <button
                                    onClick={fetchScannedDatasets}
                                    className="px-2 py-1 text-sm border rounded hover:bg-gray-100"
                                >
                                    Refresh
                                </button>
                            </div>
                            <input
                                type="text"
                                placeholder="Search datasets..."
                                className="border p-2 rounded w-full mb-2"
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                            />
                            {datasets.length ? (
                                <ul>
                                    {datasets
                                        .filter((ds: any) => ds.name.toLowerCase().includes(search.toLowerCase()))
                                        .map((ds: any, idx: number) => (
                                            <li
                                                key={idx}
                                                className={`scan-item ${selectedDataset?.name === ds.name ? "active" : ""}`}
                                                onClick={() => setSelectedDataset(ds)}
                                            >
                                                <p className="font-medium truncate">{ds.name}</p>
                                                <p className="text-xs text-gray-500 truncate">{ds.path}</p>
                                            </li>
                                        ))}
                                </ul>
                            ) : (
                                <p className="placeholder">No datasets loaded.</p>
                            )}
                            {loading.datasets && <p className="placeholder">⏳ Loading...</p>}
                        </div>

                        {/* RIGHT column: dataset details */}
                        <div className="historical-scans-report">
                            {selectedDataset ? (
                                matchingResult ? (
                                    <div className="report-content">
                                        <h3 className="mb-2">Dataset Details</h3>
                                        <p>
                                            <strong>Name:</strong> {selectedDataset.name}
                                        </p>
                                        <p>
                                            <strong>Path:</strong> {selectedDataset.path}
                                        </p>

                                        <h4 className="mt-3 mb-1">Privacy Risk Analysis</h4>
                                        <p>
                                            <strong>Sensitive Column:</strong> {matchingResult.sensitive}
                                        </p>
                                        <p>
                                            <strong>Quasi-Identifiers:</strong> {matchingResult.qi.join(", ")}
                                        </p>

                                        <h4 className="mt-3 mb-1">Thresholds</h4>
                                        <ul>
                                            <li>k = {matchingResult.thresholds.k}</li>
                                            <li>l = {matchingResult.thresholds.l}</li>
                                            <li>t = {matchingResult.thresholds.t}</li>
                                            <li>Re-ID Probability = {matchingResult.thresholds.reid_probability}</li>
                                        </ul>

                                        <h4 className="mt-3 mb-1">Report</h4>
                                        <ul>
                                            <li>
                                                k-anonymity: min {matchingResult.report.k_anonymity.k_min}, avg {matchingResult.report.k_anonymity.k_avg}
                                            </li>
                                            <li>
                                                l-diversity: min {matchingResult.report.l_diversity.l_min}, avg {matchingResult.report.l_diversity.l_avg}
                                            </li>
                                            <li>
                                                t-closeness: max {matchingResult.report.t_closeness.t_max}, avg {matchingResult.report.t_closeness.t_avg}
                                            </li>
                                        </ul>

                                        <h4 className="mt-3 mb-1">Risk Flags</h4>
                                        <ul className="text-red-600">
                                            {matchingResult.report.risk_flags.map((flag: string, i: number) => (
                                                <li key={i}>{flag}</li>
                                            ))}
                                        </ul>
                                    </div>
                                ) : (
                                    <p className="placeholder">No detailed scan results available for this dataset.</p>
                                )
                            ) : (
                                <p className="placeholder">Click a dataset to view details.</p>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Historical Privacy Monitoring Scans Tab */}
            {activeTab === "historicalScans" && (
                <div className="bg-white shadow-lg rounded-lg p-6">
                    <h2 className="text-xl font-semibold mb-4">Historical Scans</h2>
                    <div className="historical-scans-container">
                        {/* Left column: timestamps */}
                        <div className="historical-scans-list">
                            {historicalScans.length ? (
                                <ul>
                                    {historicalScans.map((scan: any) => (
                                        <li
                                            key={scan.id}
                                            className={`scan-item ${selectedScan?.id === scan.id ? "active" : ""}`}
                                            onClick={() => setSelectedScan(scan)}
                                        >
                                            {new Date(scan.timestamp).toLocaleString()}
                                        </li>
                                    ))}
                                </ul>
                            ) : (
                                <p className="placeholder">No historical scans available.</p>
                            )}
                        </div>

                        {/* Right column: explanation report */}
                        <div className="historical-scans-report">
                            {selectedScan ? (
                                selectedScan.explanationReport ? (
                                    <div className="report-content">
                                        <ReactMarkdown>{selectedScan.explanationReport}</ReactMarkdown>
                                    </div>
                                ) : (
                                    <p className="placeholder">No report available for this scan.</p>
                                )
                            ) : (
                                <p className="placeholder">Click a scan timestamp to view the explanation report.</p>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Privacy Monitoring Scan Tab */}
            {activeTab === "privacyMonitor" && (
                <div className="bg-white shadow-lg rounded-lg p-6">
                    {/* Header */}
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-xl font-semibold text-gray-700">Privacy Monitor</h2>
                        <button
                            onClick={startScan}
                            className="px-2 py-1 text-sm border rounded hover:bg-gray-100"
                        >
                            Start Scan
                        </button>
                    </div>

                    {loading.privacyMonitor && <p className="text-blue-600 font-medium mt-4">⏳ Scanning in progress...</p>}
                </div>
            )}
        </div>
    );
};
