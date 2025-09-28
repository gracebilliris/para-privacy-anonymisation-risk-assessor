import fs from "fs/promises"; // File system module for async file operations
import { DatasetService } from "./datasetService"; // Service to manage datasets
import { AnonymisationValidatorAgent, ValidatorParams } from "./anonymisationValidatorAgent"; // Validator agent and its parameters
import { spawn } from "child_process"; // To run Python scripts as subprocesses
import path from "path"; // Utilities for working with file and directory paths

// Type representing the result of scanning a dataset
export type ScanResult = {
    file: string; // Path to the dataset file
    qi: string[]; // List of quasi-identifiers
    sensitive: string; // Sensitive column
    thresholds: {
        // Thresholds used for anonymisation checks
        k: number; // k-anonymity threshold
        l: number; // l-diversity threshold
        t: number; // t-closeness threshold
        reid_probability: number; // Probability of re-identification
        reason: string; // Explanation for chosen thresholds
    };
    report: any; // Detailed validator report
};

export class AnonymisationScannerAgent {
    private datasetService: DatasetService; // Service for dataset discovery
    private validatorAgent: AnonymisationValidatorAgent; // Agent to validate anonymisation

    constructor(baseDir?: string) {
        // Initialise dataset service with optional base directory
        this.datasetService = new DatasetService(baseDir);
        // Initialise the validator agent
        this.validatorAgent = new AnonymisationValidatorAgent();
    }

    /**
     * Ask an LLM (via a Python script) to determine which columns
     * are quasi-identifiers and which are sensitive.
     */
    private async askLLMForColumnRoles(headers: string[]): Promise<{ qi: string[]; sensitive: string | null }> {
        return new Promise((resolve, reject) => {
            if (!headers.length) return resolve({ qi: [], sensitive: null });
            // Path to the ADK multi-agent orchestrator Python client
            const pythonScript = path.resolve(__dirname, "../../privacy_validator/adk_multi_agent_system.py");
            const args = ["scanner", JSON.stringify(headers)];
            const py = spawn("python3.11", [pythonScript, ...args]);
            let output = "";
            let error = "";
            py.stdout.on("data", (data) => (output += data.toString()));
            py.stderr.on("data", (data) => (error += data.toString()));
            py.on("close", (code) => {
                if (code !== 0) {
                    console.error("Python stderr:", error);
                    return reject(new Error(error || `Python exited with code ${code}`));
                }
                try {
                    const parsed = JSON.parse(output);
                    const qi = Array.isArray(parsed.quasi_identifiers) ? parsed.quasi_identifiers : [];
                    const sensitive = Array.isArray(parsed.sensitive) ? parsed.sensitive[0] : parsed.sensitive || null;
                    resolve({ qi, sensitive });
                } catch (err) {
                    reject(err);
                }
            });
        });
    }

    /**
     * Determine anonymisation thresholds based on dataset size and
     * whether auxiliary data exists.
     */
    private adaptiveThresholds(dfLength: number, auxExists: boolean) {
        if (auxExists) {
            // Stricter thresholds if auxiliary data is present
            return {
                k: Math.max(10, Math.floor(dfLength / 100)),
                l: 2,
                t: 0.1,
                reid_probability: 0.01,
                reason: "Auxiliary data detected, stricter thresholds applied.",
            };
        } else {
            // Standard thresholds otherwise
            return {
                k: Math.max(5, Math.floor(dfLength / 200)),
                l: 2,
                t: 0.2,
                reid_probability: 0.05,
                reason: "Standard thresholds applied.",
            };
        }
    }

    /**
     * Main method to scan all datasets.
     * Returns a list of ScanResult objects.
     */
    public async runScan(resultsDir?: string): Promise<ScanResult[]> {
        // Discover datasets
        const datasets = this.datasetService.findDatasets();
        const results: ScanResult[] = [];

        // Use provided resultsDir or create a new one
        let folder: string;
        if (resultsDir && typeof resultsDir === "string") {
            folder = resultsDir;
        } else {
            const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
            folder = path.resolve(__dirname, `../../results/${timestamp}`);
        }
        await fs.mkdir(folder, { recursive: true });

        // Use streaming CSV parser for large files
        const csvParser = require("csv-parser");
        const fsStream = require("fs");

        for (const dataset of datasets) {
            try {
                // Stream CSV to get headers and row count
                const headersPromise = new Promise<string[]>((resolve, reject) => {
                    let headers: string[] = [];
                    let resolved = false;
                    fsStream
                        .createReadStream(dataset.path)
                        .pipe(csvParser())
                        .on("headers", (h: string[]) => {
                            headers = h;
                            if (!resolved) {
                                resolved = true;
                                resolve(headers);
                            }
                        })
                        .on("error", (err: any) => reject(err));
                });

                const rowCountPromise = new Promise<number>((resolve, reject) => {
                    let count = 0;
                    fsStream
                        .createReadStream(dataset.path)
                        .pipe(csvParser())
                        .on("data", () => {
                            count++;
                        })
                        .on("end", () => resolve(count))
                        .on("error", (err: any) => reject(err));
                });

                const headers = await headersPromise;
                const rowCount = await rowCountPromise;
                if (!rowCount) continue;

                // Ask LLM which columns are QI and sensitive
                const { qi, sensitive } = await this.askLLMForColumnRoles(headers);
                if (!qi.length || !sensitive) {
                    console.warn(`Skipping ${dataset.path}: no QI/sensitive identified`);
                    continue;
                }

                // Check if an auxiliary dataset exists
                const auxPath = dataset.path.replace(/\.csv$/i, "_aux.csv");
                let auxExists = false;
                try {
                    await fs.access(auxPath);
                    auxExists = true;
                } catch {}

                // Determine thresholds based on dataset properties
                const thresholds = this.adaptiveThresholds(rowCount, auxExists);

                // Build an output path INSIDE the timestamp folder
                const baseName = path.basename(dataset.path).replace(/\.csv$/i, "");
                const outPath = path.join(folder, `validator_report_${baseName}.json`);

                // Prepare parameters for the validator agent
                const validatorParams: ValidatorParams = {
                    dataPath: dataset.path,
                    auxPath: auxExists ? auxPath : undefined,
                    qi,
                    sensitive,
                    k: thresholds.k,
                    l: thresholds.l,
                    lMethod: "entropy",
                    t: thresholds.t,
                    numericBins: 15,
                    outPath, // 👈 ensure results grouped per scan
                };

                // Run anonymisation validation
                const report = await this.validatorAgent.runValidator(validatorParams);

                // Save scan result
                results.push({ file: dataset.path, qi, sensitive, thresholds, report });
            } catch (err) {
                console.error(`Error scanning ${dataset.path}:`, err);
            }
        }

        // 2. Save scan summary in the same folder
        const resultsFile = path.join(folder, "scan_results.json");
        await fs.writeFile(resultsFile, JSON.stringify(results, null, 2), "utf8");

        return results;
    }
}
