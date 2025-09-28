import React, { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

interface ReportEntry {
    name: string;
    content: string;
    timestamp: string;
}

const fetchRecentReports = async (): Promise<ReportEntry[]> => {
    const res = await fetch("http://localhost:8080/api/recent-reports");
    if (!res.ok) return [];
    return res.json();
};

export default function RecentReports() {
    const [reports, setReports] = useState<ReportEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedReport, setSelectedReport] = useState<ReportEntry | null>(null);
    const [search, setSearch] = useState("");

    useEffect(() => {
        fetchRecentReports().then((data) => {
            setReports(data);
            setLoading(false);
            if (data.length > 0) setSelectedReport(data[0]);
        });
    }, []);

    return (
        <div className="bg-white shadow-lg rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Recent Dataset Explanation Reports</h2>
            <div className="flex historical-scans-container">
                {/* Left column: report list */}
                <div
                    className="historical-scans-list"
                    style={{ minWidth: 260, maxWidth: 340, marginRight: 32 }}
                >
                    <h3 className="font-semibold mb-2">Report List</h3>
                    <input
                        type="text"
                        className="border p-2 rounded mb-4 w-full"
                        placeholder="Search reports..."
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
                            <span className="ml-2">Loading reports...</span>
                        </div>
                    ) : reports.length === 0 ? (
                        <div className="text-gray-500 py-8">No recent reports found.</div>
                    ) : (
                        <ul>
                            {reports
                                .filter((r) => r.name.toLowerCase().includes(search.toLowerCase()))
                                .map((report, idx) => (
                                    <li
                                        key={report.name + report.timestamp}
                                        className={`scan-item ${selectedReport && selectedReport.name === report.name ? "active" : ""}`}
                                        style={{
                                            cursor: "pointer",
                                            marginBottom: 8,
                                            padding: 8,
                                            borderRadius: 4,
                                            background: selectedReport && selectedReport.name === report.name ? "#f0f4ff" : "transparent",
                                        }}
                                        onClick={() => setSelectedReport(report)}
                                    >
                                        <span style={{ textDecoration: "underline" }}>{report.name}</span>
                                    </li>
                                ))}
                        </ul>
                    )}
                </div>
                {/* Right column: report details */}
                <div
                    className="historical-scans-report"
                    style={{ flex: 1, minWidth: 0 }}
                >
                    {selectedReport ? (
                        <div>
                            <h3 className="font-semibold mb-2">{selectedReport.name}</h3>
                            <div className="text-xs text-gray-400 mb-4 break-all">{new Date(selectedReport.timestamp).toLocaleString()}</div>
                            <div
                                className="markdown-body"
                                style={{ background: "#f6f6f6", padding: 16, borderRadius: 6, overflowX: "auto" }}
                            >
                                <ReactMarkdown>{selectedReport.content}</ReactMarkdown>
                            </div>
                        </div>
                    ) : (
                        <p className="placeholder">Select a report to view details.</p>
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
}
