"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.AnonymisationValidatorAgent = void 0;
const child_process_1 = require("child_process");
const path_1 = __importDefault(require("path"));
const fs_1 = __importDefault(require("fs"));
const os_1 = __importDefault(require("os"));
class AnonymisationValidatorAgent {
    async runValidator(params) {
        const script = path_1.default.resolve(__dirname, "../../privacy_validator/anonymisation_validator_cli.py");
        const pythonPath = path_1.default.resolve(__dirname, "../../"); // Project root
        // Just generate a unique output file in /tmp by default (no folder creation)
        const outFile = params.outPath ?? path_1.default.join(os_1.default.tmpdir(), `validator_report_${Date.now()}_${Math.random().toString(36).slice(2, 8)}.json`);
        const args = [
            "--data",
            params.dataPath,
            ...(params.auxPath ? ["--external", params.auxPath] : []),
            "--qi",
            ...params.qi,
            "--sensitive",
            params.sensitive,
            "--k",
            params.k.toString(),
            "--l",
            params.l.toString(),
            "--l-method",
            params.lMethod,
            "--t",
            params.t.toString(),
            "--numeric-bins",
            params.numericBins.toString(),
            "--out",
            outFile,
        ];
        return new Promise((resolve, reject) => {
            (0, child_process_1.execFile)("python3.11", [script, ...args], { env: { ...process.env, PYTHONPATH: pythonPath } }, (error, stdout, stderr) => {
                if (error) {
                    const msg = `Validator process failed: ${stderr || error.message}`;
                    return reject(new Error(msg));
                }
                fs_1.default.readFile(outFile, "utf8", (err, data) => {
                    if (err)
                        return reject(err);
                    try {
                        const parsed = JSON.parse(data);
                        return resolve({ report: parsed, python_stdout: stdout, outFile });
                    }
                    catch (parseErr) {
                        return reject(parseErr);
                    }
                });
            });
        });
    }
}
exports.AnonymisationValidatorAgent = AnonymisationValidatorAgent;
