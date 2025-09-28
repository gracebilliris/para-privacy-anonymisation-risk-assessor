import React, { useState, useEffect } from "react";
import { startOrchestratorAPI, datasetDetailsAPI, getScanResultsAPI } from "../api/client";
import ReactMarkdown from "react-markdown";

export const PrivacyMonitor: React.FC = () => {
    // Estimate scan time: assume 1 dataset takes 8 seconds (example)
    const avgScanTimePerDataset = 12; // seconds
    const [datasetCount, setDatasetCount] = useState(0);
    const predictedScanTime = datasetCount * avgScanTimePerDataset;
    const [scanInProgress, setScanInProgress] = useState(false);
    const [explanationReport, setExplanationReport] = useState<string>("");
    const [scanResults, setScanResults] = useState<any[]>([]);
    // Removed unused scanTimestamp and pollingRef

    // Fetch dataset count on mount
    useEffect(() => {
        const fetchCount = async () => {
            try {
                const res = await datasetDetailsAPI();
                setDatasetCount(Array.isArray(res.data) ? res.data.length : 0);
            } catch {
                setDatasetCount(0);
            }
        };
        fetchCount();
    }, []);

    // Start scan for all datasets (no path needed)
    const startScan = async () => {
        setScanInProgress(true);
        setExplanationReport("");
        setScanResults([]);
        try {
            // Fetch dataset paths
            const res = await datasetDetailsAPI();
            const datasets = Array.isArray(res.data) ? res.data.map((d: any) => d.path || d) : [];
            if (datasets.length === 0) {
                setExplanationReport("No datasets found.");
                setScanInProgress(false);
                return;
            }
            // Start orchestrator scan and get explanation report directly
            const orchestrateRes = await startOrchestratorAPI(datasets);
            setExplanationReport(orchestrateRes.data.explanation_report || "No explanation report available.");
            // Try to get scan results if timestamp or jobId is returned
            const jobId = orchestrateRes.data.timestamp || orchestrateRes.data.job_id || orchestrateRes.data.jobId;
            if (jobId) {
                try {
                    const resultsRes = await getScanResultsAPI(jobId);
                    if (resultsRes.data && Array.isArray(resultsRes.data.results)) {
                        setScanResults(resultsRes.data.results);
                    } else if (resultsRes.data && resultsRes.data.results) {
                        setScanResults(resultsRes.data.results);
                    }
                } catch (e) {
                    // fallback: no scan results found
                }
            }
        } catch (err) {
            console.error("Error starting scan:", err);
            const errorMsg = (err as Error)?.message || String(err) || "Scan failed";
            setExplanationReport("Error: " + errorMsg);
        } finally {
            setScanInProgress(false);
        }
    };

    return (
        <div className="bg-white shadow-lg rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Privacy Monitor</h2>
            <div className="flex items-center gap-4 mb-4">
                <button
                    onClick={startScan}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                    disabled={scanInProgress}
                >
                    {scanInProgress ? "Scanning..." : "Start Scan"}
                </button>
                <br />
                <span className="text-xs text-gray-500">
                    Avg scan time: {avgScanTimePerDataset}s per dataset. Predicted: {predictedScanTime}s for {datasetCount} dataset
                    {datasetCount !== 1 ? "s" : ""}.
                </span>
            </div>
            <div className="mt-4">
                {scanInProgress && <p className="placeholder">Scan in progress...</p>}
                {!scanInProgress && (
                    <div>
                        {explanationReport ? (
                            <div className="bg-gray-50 p-3 rounded text-sm mb-6">
                                <ReactMarkdown>{explanationReport}</ReactMarkdown>
                            </div>
                        ) : (
                            <p className="text-gray-500">No explanation report available. Run a scan to generate one.</p>
                        )}
                        {scanResults.length > 0 && (
                            <div className="mt-6">
                                <h3 className="text-lg font-semibold mb-2">Raw Privacy Metrics</h3>
                                {scanResults.map((item, idx) => {
                                    let validation = null;
                                    try {
                                        validation = item.result?.validation?.validation_result ? JSON.parse(item.result.validation.validation_result) : null;
                                    } catch (e) {}
                                    return (
                                        <div
                                            key={item.dataset || idx}
                                            className="mb-4 border-b pb-4"
                                        >
                                            <div className="font-medium text-blue-700 mb-1">Dataset: {item.dataset?.split("/").slice(-1)[0] || "Unknown"}</div>
                                            {validation ? (
                                                <table className="table-auto text-xs border mb-2">
                                                    <thead>
                                                        <tr className="bg-gray-100">
                                                            <th className="px-2 py-1 border">Metric</th>
                                                            <th className="px-2 py-1 border">Value</th>
                                                            <th className="px-2 py-1 border">Threshold</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        <tr>
                                                            <td className="border px-2 py-1">k-anonymity (min)</td>
                                                            <td className="border px-2 py-1">{validation.k_anonymity?.k_min ?? "N/A"}</td>
                                                            <td className="border px-2 py-1">{validation.params?.k_required ?? "N/A"}</td>
                                                        </tr>
                                                        <tr>
                                                            <td className="border px-2 py-1">l-diversity (min)</td>
                                                            <td className="border px-2 py-1">{validation.l_diversity?.l_min ?? "N/A"}</td>
                                                            <td className="border px-2 py-1">{validation.params?.l_required ?? "N/A"}</td>
                                                        </tr>
                                                        <tr>
                                                            <td className="border px-2 py-1">t-closeness (max)</td>
                                                            <td className="border px-2 py-1">
                                                                {validation.t_closeness?.t_max ? validation.t_closeness.t_max.toFixed(4) : "N/A"}
                                                            </td>
                                                            <td className="border px-2 py-1">{validation.params?.t_required ?? "N/A"}</td>
                                                        </tr>
                                                    </tbody>
                                                </table>
                                            ) : (
                                                <div className="text-gray-500">No metrics available for this dataset.</div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};
