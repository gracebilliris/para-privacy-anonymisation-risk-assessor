import fs from "fs/promises"; // Async file system operations
import path from "path"; // Utilities for file and directory paths
import { spawn } from "child_process"; // To run Python scripts as subprocesses

export class AnonymisationSummariserAgent {
    private resultsFile: string; // Path to JSON file containing scan results
    private outputFile: string; // Path to write human-readable summary

    constructor(resultsFile?: string, outputFile?: string) {
        // Set default file paths if none are provided
        this.resultsFile = resultsFile || path.resolve(__dirname, "../../results/scan_results.json");
        this.outputFile = outputFile || path.resolve(__dirname, "../../results/explaination_report.txt");
    }

    /**
     * Load scan results from the JSON file.
     * Returns an empty array if the file cannot be read or parsed.
     */
    async loadScanResults() {
        try {
            const data = await fs.readFile(this.resultsFile, "utf8"); // Read file contents
            return JSON.parse(data); // Parse JSON into an object/array
        } catch (err) {
            console.error("Error loading scan results:", err);
            return []; // Return empty array on error
        }
    }

    /**
     * Categorise the dataset's risk based on flags.
     * - Low: No flags
     * - Medium: Flags exist but not critical
     * - High: Flags indicate thresholds breached
     */
    categoriseRisk(flags = []) {
        if (!flags || flags.length === 0) return "Low"; // No issues detected

        // If any flag contains critical keywords, classify as High risk
        if (flags.some((f: string) => f.includes("below threshold") || f.includes("above threshold"))) {
            return "High";
        }

        // Default to Medium if flags exist but not critical
        return "Medium";
    }

    /**
     * Generate a textual summary of scan results for human readers.
     * Includes dataset name, risk category, flagged issues, and suggested actions.
     */
    generateSummaryText(scanResults: any[]) {
        let summary = "Here are the anonymisation scan results for several datasets:\n\n";

        scanResults.forEach((entry) => {
            const dataset = path.basename(entry.file || "Unknown"); // Extract file name
            const flags = entry.report?.risk_flags || []; // Get any risk flags from validator
            const risk = this.categoriseRisk(flags); // Determine overall risk

            summary += `Dataset: ${dataset}\n`;
            summary += `  Risk Category: ${risk}\n`;

            // List flagged issues if present
            if (flags.length > 0) {
                summary += "  Issues:\n";
                flags.forEach((flag: string) => (summary += `    - ${flag}\n`));
            } else {
                summary += "  No privacy risks detected.\n";
            }

            // Suggest actions based on risk category
            if (risk === "High") {
                summary += "  Action: ALERT security/privacy team immediately.\n";
            } else if (risk === "Medium") {
                summary += "  Action: Review and consider improvements.\n";
            } else {
                summary += "  Action: Log for compliance, no immediate action needed.\n";
            }

            summary += "\n";
        });

        // Add instructions for generating a human-friendly explanation
        summary +=
            "Please summarise these findings for a non-technical audience, include the flagged datasets and the Quasi-Identifer and sensitive columns that were the cause of the risk category, and suggest practical actions to improve privacy protection for any flagged datasets.";

        return summary;
    }

    /**
     * Call the Gemma Python client with a prompt string.
     * Returns the output from the Python script as a string.
     */
    async callGemmaWithPrompt(prompt: string): Promise<string> {
        return new Promise((resolve, reject) => {
            // Path to the ADK multi-agent orchestrator Python client
            const scriptPath = path.resolve(__dirname, "../../privacy_validator/adk_multi_agent_system.py");
            // Spawn Python process with stdin input mode for summariser
            const py = spawn("python3.11", [scriptPath, "summariser", "--stdin"]);
            let output = "";
            let errorOutput = "";
            py.stdout.on("data", (data) => (output += data.toString()));
            py.stderr.on("data", (data) => (errorOutput += data.toString()));
            py.on("close", (code) => {
                if (code === 0) resolve(output.trim());
                else reject(new Error(errorOutput || `LLM agent client failed with code ${code}`));
            });
            py.stdin.write(prompt);
            py.stdin.end();
        });
    }

    /**
     * Main method to run summarisation of scan results.
     * Loads scan results, generates a prompt, calls Gemma client,
     * and writes the output to a file.
     */
    async runSummarisation() {
        const scanResults = await this.loadScanResults(); // Load previous scan results

        if (!scanResults.length) {
            console.log("No scan results available. Skipping summarisation.");
            return "No datasets were scanned, so no summary is available.";
        }

        // Always use the directory of the resultsFile for all outputs
        const resultsDir = path.dirname(this.resultsFile);

        // Only generate per-dataset explanation reports if the resultsFile is a temp array (per-dataset mode)
        if (this.resultsFile.includes("temp_array_")) {
            // This is a per-dataset explanation report
            const entry = scanResults[0];
            const dataset = path.basename(entry.file || "Unknown");
            const singlePrompt = this.generateSummaryText([entry]);
            try {
                const explanation = await this.callGemmaWithPrompt(singlePrompt);
                const baseName = dataset.replace(/\.csv$/i, "");
                const perDatasetPath = path.resolve(resultsDir, `explanation_report_${baseName}.txt`);
                await fs.writeFile(perDatasetPath, explanation, "utf8");
                console.log(`Per-dataset explanation report saved to ${perDatasetPath}`);
                return explanation;
            } catch (err) {
                console.error(`Failed to generate explanation for ${dataset}:`, err);
                return null;
            }
        } else {
            // This is a folder-level summary
            const summaryPrompt = this.generateSummaryText(scanResults); // Generate textual summary
            const readableReport = await this.callGemmaWithPrompt(summaryPrompt);
            await fs.writeFile(this.outputFile, readableReport, "utf8");
            console.log(`Explanation report saved to ${this.outputFile}`);
            return readableReport;
        }
    }
}
