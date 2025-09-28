import React, { useState } from "react";
import { datasetDetailsAPI } from "../api/client";
import "../App.css";

export const Datasets: React.FC = () => {
    const [datasets, setDatasets] = useState<any[]>([]);
    const [selectedDataset, setSelectedDataset] = useState<any | null>(null);
    const [loading, setLoading] = useState(false);
    const [search, setSearch] = useState("");
    const [scanStartTime, setScanStartTime] = useState<number | null>(null);
    // const [explanationReport, setExplanationReport] = useState<string>("");

    // Fetch datasets and findings from /datasets (new endpoint)
    // Fetch datasets from /datasets endpoint
    const fetchDatasets = async () => {
        setLoading(true);
        setScanStartTime(Date.now());
        try {
            const res = await datasetDetailsAPI();
            const datasetsData = Array.isArray(res.data) ? res.data : [];
            setDatasets(datasetsData);
            if (selectedDataset && !datasetsData.find((d: any) => d.path === selectedDataset.path)) {
                setSelectedDataset(null);
            }
        } catch (err) {
            console.error("Error fetching datasets:", err);
            setDatasets([]);
            setSelectedDataset(null);
        } finally {
            setLoading(false);
            setScanStartTime(null);
        }
    };

    React.useEffect(() => {
        fetchDatasets();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Remove broken/duplicate fetchScannedDatasets function

    // Two-column pane layout

    return (
        <div className="bg-white shadow-lg rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Datasets</h2>
            <div className="flex items-center gap-4 mb-4">
                <button
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                    onClick={fetchDatasets}
                    disabled={loading}
                >
                    {loading ? (
                        <span className="flex items-center gap-2">
                            <span
                                className="loader"
                                style={{
                                    width: 18,
                                    height: 18,
                                    border: "2px solid #fff",
                                    borderTop: "2px solid #3498db",
                                    borderRadius: "50%",
                                    display: "inline-block",
                                    animation: "spin 1s linear infinite",
                                }}
                            ></span>
                            Refreshing...
                        </span>
                    ) : (
                        <span>Refresh / Scan</span>
                    )}
                </button>
            </div>
            <div className="historical-scans-container">
                {/* Left column: dataset list */}
                <div className="historical-scans-list">
                    <h3 className="font-semibold mb-2">Dataset List</h3>
                    <input
                        type="text"
                        className="border p-2 rounded mb-4 w-full"
                        placeholder="Search datasets..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                    {loading ? (
                        <div className="text-center text-gray-500 py-8">
                            <span
                                className="loader"
                                style={{
                                    width: 32,
                                    height: 32,
                                    border: "4px solid #eee",
                                    borderTop: "4px solid #3498db",
                                    borderRadius: "50%",
                                    display: "inline-block",
                                    animation: "spin 1s linear infinite",
                                }}
                            ></span>
                            <span className="ml-2">Loading datasets...</span>
                        </div>
                    ) : datasets.length === 0 ? (
                        <div className="text-gray-500 py-8">No datasets found.</div>
                    ) : (
                        <ul>
                            {datasets
                                .filter(
                                    (d) =>
                                        d.name.toLowerCase().includes(search.toLowerCase()) || (d.path && d.path.toLowerCase().includes(search.toLowerCase()))
                                )
                                .map((d, idx) => (
                                    <li
                                        key={d.path || d.name || idx}
                                        className={`scan-item ${selectedDataset && selectedDataset.path === d.path ? "active" : ""}`}
                                        onClick={(e) => {
                                            e.preventDefault();
                                            setSelectedDataset(d);
                                        }}
                                    >
                                        <span style={{ textDecoration: "underline" }}>{d.name}</span>
                                    </li>
                                ))}
                        </ul>
                    )}
                </div>
                {/* Right column: dataset details */}
                <div className="historical-scans-report">
                    {selectedDataset ? (
                        <div>
                            <h3 className="font-semibold mb-2">{selectedDataset.name}</h3>
                            <div className="text-xs text-gray-400 mb-4 break-all">{selectedDataset.path}</div>
                            <div className="mb-2">
                                <b>Size:</b> {selectedDataset.size ? `${(selectedDataset.size / 1024).toFixed(1)} KB` : "-"}
                            </div>
                            <div className="mb-2">
                                <b>Last Modified:</b> {selectedDataset.lastModified ? new Date(selectedDataset.lastModified).toLocaleString() : "-"}
                            </div>
                            <div className="mb-2">
                                <b>Columns:</b> {Array.isArray(selectedDataset.columns) ? selectedDataset.columns.join(", ") : "-"}
                            </div>
                        </div>
                    ) : (
                        <p className="placeholder">Select a dataset to view details.</p>
                    )}
                </div>
            </div>
            {/* Loader animation keyframes */}
            <style>{`
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
};
