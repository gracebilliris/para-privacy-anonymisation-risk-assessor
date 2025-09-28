import { execFile } from "child_process";
import path from "path";
import fs from "fs";
import os from "os";

export type ValidatorParams = {
    dataPath: string;
    auxPath?: string;
    qi: string[];
    sensitive: string;
    k: number;
    l: number;
    lMethod: "entropy" | "distinct";
    t: number;
    numericBins: number;
    outPath?: string; // optional caller-specified out path
};

export class AnonymisationValidatorAgent {
    async runValidator(params: ValidatorParams): Promise<any> {
        const script = path.resolve(__dirname, "../../privacy_validator/anonymisation_validator_cli.py");
        const pythonPath = path.resolve(__dirname, "../../"); // Project root

        // Just generate a unique output file in /tmp by default (no folder creation)
        const outFile = params.outPath ?? path.join(os.tmpdir(), `validator_report_${Date.now()}_${Math.random().toString(36).slice(2, 8)}.json`);

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
            execFile("python3.11", [script, ...args], { env: { ...process.env, PYTHONPATH: pythonPath } }, (error, stdout, stderr) => {
                if (error) {
                    const msg = `Validator process failed: ${stderr || error.message}`;
                    return reject(new Error(msg));
                }
                fs.readFile(outFile, "utf8", (err, data) => {
                    if (err) return reject(err);
                    try {
                        const parsed = JSON.parse(data);
                        return resolve({ report: parsed, python_stdout: stdout, outFile });
                    } catch (parseErr) {
                        return reject(parseErr);
                    }
                });
            });
        });
    }
}
