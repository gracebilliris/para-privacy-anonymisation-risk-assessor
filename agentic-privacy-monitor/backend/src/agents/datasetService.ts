import fs from "fs";
import path from "path";

export class DatasetService {
    private baseDir: string;

    constructor(baseDir?: string) {
        // Default to project root if not provided
        this.baseDir = baseDir || path.resolve(__dirname, "../../../");
    }

    /**
     * Recursively find all CSV datasets under the base directory.
     */
    public findDatasets(): { name: string; path: string }[] {
        const datasets: { name: string; path: string }[] = [];

        const walk = (dir: string) => {
            const entries = fs.readdirSync(dir);
            for (const entry of entries) {
                const entryPath = path.join(dir, entry);
                const stat = fs.statSync(entryPath);

                if (stat.isDirectory()) {
                    walk(entryPath); // recurse into subdirectory
                } else if (entry.toLowerCase().endsWith(".csv")) {
                    datasets.push({
                        name: path.basename(entryPath), // base filename only
                        path: entryPath, // absolute path
                    });
                }
            }
        };

        walk(this.baseDir);
        return datasets;
    }
}
