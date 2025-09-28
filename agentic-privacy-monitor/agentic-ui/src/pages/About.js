import React from "react";

function About() {
    return (
        <div>
            <h2>About This Prototype</h2>
            <p>
                This web application is a prototype developed as part of Grace Billiris' PhD research project. Its purpose is to explore interactive,
                user-friendly approaches to privacy assessment.
            </p>
            <h3>About the MCP Tools</h3>
            <ul>
                <li>
                    <strong>Privacy Validation</strong>
                    <br />
                    Analyses your dataset to identify quasi-identifiers (columns that could indirectly identify individuals) and sensitive columns (fields
                    containing private or confidential information).
                    <br />
                    Uses advanced AI models to classify columns and then calculates privacy metrics such as k-anonymity, l-diversity, and t-closeness.
                    <br />
                    Thresholds for these metrics are determined based on the number of quasi-identifiers and sensitive columns in your data, ensuring that
                    privacy requirements are tailored to your datasets structure.
                </li>
                <li>
                    <strong>Privacy Scanning</strong>
                    <br />
                    The scanner reviews your dataset for privacy risks and highlights any sensitive information or potential vulnerabilities.
                    <br />
                    It provides a quick overview of which columns may require special handling and flags any detected privacy issues.
                    <br />
                    The scan results help inform the selection of appropriate thresholds for privacy validation.
                </li>
                <li>
                    <strong>Privacy Summarisation</strong>
                    <br />
                    Generates a clear, human-readable summary of the privacy validation and scan results.
                    <br />
                    Explains the key findings, including the calculated privacy metrics and any recommendations for improving data privacy.
                    <br />
                    The summary is designed to be accessible to non-technical users, making privacy risks and protections easy to understand.
                </li>
                <li>
                    <strong>Full Privacy Report</strong>
                    <br />
                    Combines the results of validation and scanning, providing a comprehensive assessment of your dataset’s privacy status.
                    <br />
                    Details the identified quasi-identifiers, sensitive columns, calculated privacy metrics, and the thresholds used.
                    <br />
                    This report supports compliance, risk management, and ongoing privacy monitoring.
                </li>
            </ul>
            <h4>How thresholds are calculated</h4>
            <p>
                Thresholds for privacy metrics (like k-anonymity, l-diversity, t-closeness) are automatically set based on the number of quasi-identifiers and
                sensitive columns detected in your dataset. This ensures that privacy protections are appropriate for the specific structure and risk profile of
                your data.
            </p>
            <h4>How quasi-identifiers and sensitive columns are identified</h4>
            <p>
                The system uses AI models to analyse column names and sample data, classifying each column as a quasi-identifier, sensitive, or neither.
                Quasi-identifiers are fields that, when combined, could be used to re-identify individuals. Sensitive columns contain information that should be
                protected from disclosure.
            </p>
            <h4>How privacy metrics are reported</h4>
            <p>
                Not all privacy metrics (k-anonymity, l-diversity, t-closeness, etc.) are always shown in every summary. You may see metrics marked as{" "}
                <strong>"Not met"</strong> (the metric was evaluated but not satisfied), <strong>"Not applicable"</strong> (the metric does not apply to this
                dataset), or omitted entirely (the metric was not calculated or not relevant for this data). This ensures the summary only reflects what was
                actually computed and relevant for your dataset. For more details, see the privacy assessment summary notes.
            </p>
            <p>For more information, please contact Grace Billiris (grace.v.billiris@student.uts.edu.au) or refer to the research documentation.</p>
        </div>
    );
}

export default About;
