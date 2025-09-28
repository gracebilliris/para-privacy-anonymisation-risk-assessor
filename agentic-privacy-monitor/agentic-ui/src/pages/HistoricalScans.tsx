import React, { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { historicalScansAPI } from "../api/client";
import "../App.css";

export const HistoricalScans: React.FC = () => {
    const [historicalScans, setHistoricalScans] = useState<any[]>([]);
    const [selectedFolder, setSelectedFolder] = useState<any | null>(null);
    const [selectedScan, setSelectedScan] = useState<any | null>(null);
    const [selectedTimestamp, setSelectedTimestamp] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchHistoricalScans = async () => {
        setLoading(true);
        try {
            const res = await historicalScansAPI();
            setHistoricalScans(res.data.scans ?? res.data ?? []);
        } catch (err) {
            setError("Error fetching historical scans");
            console.error("Error fetching historical scans:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchHistoricalScans();
    }, []);

    return (
        <div className="bg-white shadow-lg rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Historical Scans</h2>
            <div
                className="historical-scans-container"
                style={{ display: "flex", gap: "2rem" }}
            >
                {/* Left column: scan folders/timestamps */}
                <div
                    className="historical-scans-list"
                    style={{ minWidth: 180 }}
                >
                    <h3 className="font-semibold mb-2">Scan Timestamps</h3>
                    {loading && <p className="placeholder">Loading...</p>}
                    {error && <p className="text-red-500">{error}</p>}
                    {!loading && !error && historicalScans.length > 0 ? (
                        <ul>
                            {historicalScans.map((folder: any) => {
                                let dateString = "Unknown";
                                if (folder.timestamp) {
                                    // Support both ms timestamps, ISO strings, and custom dash-separated timestamps
                                    let dateObj: Date | null = null;
                                    if (typeof folder.timestamp === "number") {
                                        dateObj = new Date(folder.timestamp);
                                    } else if (typeof folder.timestamp === "string") {
                                        let ts = folder.timestamp;
                                        // Try to convert dash-separated time to ISO (e.g., 2025-09-19T23-22-57-634058Z)
                                        const dashIsoMatch = ts.match(/^(\d{4}-\d{2}-\d{2})T(\d{2})-(\d{2})-(\d{2})(?:-(\d+))?Z?$/);
                                        if (dashIsoMatch) {
                                            // Remove microseconds if present
                                            const [_, date, h, m, s] = dashIsoMatch;
                                            ts = `${date}T${h}:${m}:${s}Z`;
                                        }
                                        const parsed = Date.parse(ts);
                                        if (!isNaN(parsed)) {
                                            dateObj = new Date(parsed);
                                        } else if (!isNaN(Number(folder.timestamp))) {
                                            dateObj = new Date(Number(folder.timestamp));
                                        }
                                    }
                                    if (dateObj && !isNaN(dateObj.getTime())) {
                                        dateString = dateObj.toLocaleString(undefined, {
                                            year: "numeric",
                                            month: "short",
                                            day: "2-digit",
                                            hour: "2-digit",
                                            minute: "2-digit",
                                            second: "2-digit",
                                            hour12: false,
                                        });
                                    } else {
                                        dateString = String(folder.timestamp);
                                    }
                                }
                                return (
                                    <li
                                        key={folder.id}
                                        className={`scan-item ${selectedTimestamp === folder.id ? "active" : ""}`}
                                        onClick={() => {
                                            setSelectedTimestamp(folder.id);
                                            setSelectedFolder(folder);
                                            setSelectedScan(null);
                                        }}
                                        style={{ cursor: "pointer" }}
                                    >
                                        <span style={{ textDecoration: "underline" }}>{dateString}</span>
                                    </li>
                                );
                            })}
                        </ul>
                    ) : (
                        !loading && !error && <p className="placeholder">No historical scans available.</p>
                    )}
                </div>

                {/* Right column: scan details and explanation */}
                <div
                    className="historical-scans-report"
                    style={{ flex: 1 }}
                >
                    {selectedScan ? (
                        <div>
                            <div
                                className="report-content"
                                style={{ overflowY: "auto" }}
                            >
                                <ReactMarkdown>{selectedScan.explanationReport || "No explanation report available."}</ReactMarkdown>
                            </div>
                        </div>
                    ) : selectedFolder ? (
                        <div>
                            <div
                                className="report-content"
                                style={{ overflowY: "auto" }}
                            >
                                <ReactMarkdown>{selectedFolder.explanationReport || "No explanation report available."}</ReactMarkdown>
                            </div>
                        </div>
                    ) : (
                        <p className="placeholder">Select a scan folder and scan to view details.</p>
                    )}
                </div>
            </div>
        </div>
    );
};
