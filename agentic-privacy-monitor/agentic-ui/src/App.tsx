import React from "react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import { Overview } from "./pages/Overview";
import { Datasets } from "./pages/Datasets";
import { HistoricalScans } from "./pages/HistoricalScans";
import { PrivacyMonitor } from "./pages/PrivacyMonitor";
import About from "./pages/About";
import RecentReports from "./pages/RecentReports";
import "./App.css";

function App() {
    return (
        <Router>
            <header className="menu-bar bg-gray-800 text-white px-6 py-3 flex justify-between items-center">
                <h1 className="font-bold text-xl">Agentic Privacy Monitor</h1>
                <nav className="flex gap-4">
                    <Link
                        to="/overview"
                        className="hover:underline"
                    >
                        Overview
                    </Link>
                    <Link
                        to="/datasets"
                        className="hover:underline"
                    >
                        Datasets
                    </Link>
                    <Link
                        to="/historical"
                        className="hover:underline"
                    >
                        Historical Privacy Monitor
                    </Link>
                    <Link
                        to="/privacy-monitor"
                        className="hover:underline"
                    >
                        Privacy Monitor
                    </Link>
                    <Link
                        to="/recent-reports"
                        className="hover:underline"
                    >
                        Recent Reports
                    </Link>
                    <Link
                        to="/about"
                        className="hover:underline"
                    >
                        About
                    </Link>
                </nav>
            </header>

            <main className="container mx-auto mt-6 px-4">
                <Routes>
                    <Route
                        path="/"
                        element={<Overview />}
                    />
                    <Route
                        path="/overview"
                        element={<Overview />}
                    />
                    <Route
                        path="/datasets"
                        element={<Datasets />}
                    />
                    <Route
                        path="/historical"
                        element={<HistoricalScans />}
                    />
                    <Route
                        path="/privacy-monitor"
                        element={<PrivacyMonitor />}
                    />
                    <Route
                        path="/about"
                        element={<About />}
                    />
                    <Route
                        path="/recent-reports"
                        element={<RecentReports />}
                    />
                </Routes>
            </main>
        </Router>
    );
}

export default App;
