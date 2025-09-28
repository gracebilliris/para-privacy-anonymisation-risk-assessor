"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.DatasetService = void 0;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
class DatasetService {
    constructor(baseDir) {
        // Default to project root if not provided
        this.baseDir = baseDir || path_1.default.resolve(__dirname, "../../../");
    }
    /**
     * Recursively find all CSV datasets under the base directory.
     */
    findDatasets() {
        const datasets = [];
        const walk = (dir) => {
            const entries = fs_1.default.readdirSync(dir);
            for (const entry of entries) {
                const entryPath = path_1.default.join(dir, entry);
                const stat = fs_1.default.statSync(entryPath);
                if (stat.isDirectory()) {
                    walk(entryPath); // recurse into subdirectory
                }
                else if (entry.toLowerCase().endsWith(".csv")) {
                    datasets.push({
                        name: path_1.default.basename(entryPath), // base filename only
                        path: entryPath, // absolute path
                    });
                }
            }
        };
        walk(this.baseDir);
        return datasets;
    }
}
exports.DatasetService = DatasetService;
