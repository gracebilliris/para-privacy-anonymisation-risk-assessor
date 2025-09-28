import React, { useEffect, useState } from "react";
import { healthCheckAPI, getOverviewRiskAPI } from "../api/client";

interface RiskOverview {
    riskLevel: string;
    latestScan: string;
    highRiskCount: number;
    mediumRiskCount: number;
    totalDatasets: number;
}

export const Overview: React.FC = () => {
    const [health, setHealth] = useState<string | { status: string }>("Unknown");
    const [riskOverview, setRiskOverview] = useState<RiskOverview | null>(null);
    const [loadingHealth, setLoadingHealth] = useState(false);
    const [loadingRisk, setLoadingRisk] = useState(false);

    const getStatusColor = (status: string) => {
        if (status.toLowerCase() === "ok") return "bg-green-100 text-green-800";
        if (status.toLowerCase() === "warning") return "bg-yellow-100 text-yellow-800";
        return "bg-red-100 text-red-800";
    };

    const fetchHealth = async () => {
        setLoadingHealth(true);
        try {
            const res = await healthCheckAPI();
            setHealth(res.data?.status ?? res.data ?? "Unknown");
        } catch (err) {
            console.error("Error fetching health:", err);
            setHealth("Error");
        } finally {
            setLoadingHealth(false);
        }
    };

    const fetchRiskOverview = async () => {
        setLoadingRisk(true);
        try {
            const res = await getOverviewRiskAPI(); // call /overview/risk
            setRiskOverview(res.data);
        } catch (err) {
            console.error("Error fetching risk overview:", err);
            setRiskOverview(null);
        } finally {
            setLoadingRisk(false);
        }
    };

    useEffect(() => {
        fetchHealth();
        fetchRiskOverview();
    }, []);

    // Helper to display a valid date or fallback
    const getLatestScanDate = (latestScan: string) => {
        if (!latestScan) return "N/A";
        const timestamp = Number(latestScan);
        if (!isNaN(timestamp) && timestamp > 0) {
            const date = new Date(timestamp);
            if (!isNaN(date.getTime())) {
                return date.toLocaleString();
            }
        }
        return latestScan;
    };

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Overall Risk Level */}
            <div className="bg-white shadow-lg rounded-lg p-6">
                <h2 className="text-xl font-semibold mb-4">Overall Risk Level</h2>
                <div className="w-32 h-32 mx-auto rounded-full bg-red-200 flex items-center justify-center">
                    <span className="text-lg font-bold text-red-800">{loadingRisk ? "⏳" : riskOverview?.riskLevel ?? "Unknown"}</span>
                </div>
                {riskOverview && (
                    <div className="mt-4 text-sm">
                        <p>
                            <strong>Total Datasets:</strong> {riskOverview.totalDatasets}
                        </p>
                        <p>
                            <strong>High Risk Count:</strong> {riskOverview.highRiskCount}
                        </p>
                        <p>
                            <strong>Medium Risk Count:</strong> {riskOverview.mediumRiskCount}
                        </p>
                        <p>
                            <strong>Latest Scan:</strong> {getLatestScanDate(riskOverview.latestScan)}
                        </p>
                    </div>
                )}
            </div>

            {/* Health Check */}
            <div className="bg-white shadow-lg rounded-lg p-6 flex flex-col justify-between">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-semibold text-gray-700">Health Check</h2>
                    <button
                        onClick={fetchHealth}
                        className="px-2 py-1 text-sm border rounded hover:bg-gray-100"
                    >
                        Refresh
                    </button>
                </div>
                <div className={`p-4 rounded ${getStatusColor(typeof health === "string" ? health : health.status ?? "Unknown")}`}>
                    <span className="font-bold text-lg">{typeof health === "string" ? health : health.status ?? "Unknown"}</span>
                </div>
                {loadingHealth && <p className="text-gray-500 mt-2">⏳ Loading...</p>}
            </div>
        </div>
    );
};
