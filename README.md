# Privacy Anonymisation Risk Assessor (PARA)

## Overview

PARA is an agentic prototype for automated anonymisation risk assessment in tabular data. It helps software developers and governance stakeholders evaluate privacy risks using interpretable metrics (k-anonymity, l-diversity, t-closeness, re-identification risk) and generates both machine-readable and human-readable reports.

Includes dashboard (UI), workflow orchestrator, scanner agent, validator agent, summariser agent, and reporting. Read-only scanning; in‑environment computation.

NOTE: it is a prototype.

For full details, see the [PARA project page](https://gracebilliris.github.io/para-privacy-anonymisation-risk-assessor/) or watch the [demonstration video](https://youtu.be/qGkDELNTh8M).

## Features

-   Automatic scanning and discovery of tabular datasets
-   Privacy risk assessment using k-anonymity, l-diversity, t-closeness, and re-identification risk
-   LLM-powered column classification and summary generation
-   Machine-readable JSON reports and narrative summaries
-   Audit trail and historical report access

---

## Usage

1. **Clone the repository:**

    ```bash
    git clone https://github.com/gracebilliris/para-privacy-anonymisation-risk-assessor.git
    cd agentic-privacy-monitor
    ```

2. **Install dependencies:**

    ```bash
    cd backend && npm install
    cd ../agentic-ui && npm install
    ```

3. **Start the backend (Python microservices):**

    In a new terminal:

    ```bash
    cd agentic-privacy-monitor/backend

    # Start orchestrator and agents
    npm run dev
    ```

4. **Start the frontend (React dashboard):**

    In a new terminal:

    ```bash
    cd agentic-privacy-monitor/agentic-ui
    npm start
    ```

5. **Access the dashboard:**
   Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Project Structure

-   `agentic-privacy-monitor/backend/` — Orchestrator, agents (Python), and API
-   `agentic-privacy-monitor/agentic-ui/` — React dashboard frontend
-   [PARA Project paper](https://gracebilliris.github.io/para-privacy-anonymisation-risk-assessor/) — Full PARA project paper, figures, architecture, and academic reference

---

## Adding New Datasets

-   Place new CSV files into any folder in the repository. Subfolders are supported.
-   Ensure columns are descriptive; the LLM will classify them as quasi-identifiers or sensitive attributes.
-   Optionally, provide auxiliary datasets for simulated re-identification attacks.

---

## Customisation

-   Adjust adaptive thresholds in `privacy_validator/anonymisation_validator.py`
-   Update LLM prompts in `privacy_validator/gemma_client.py` for improved column classification and summary generation
-   Extend `AnonymisationValidator` for additional privacy metrics or attack types

---

## Requirements

-   Python 3.8+
-   Node.js 18+
-   LLM API key (for Gemma or similar) in your environment

---

## License

MIT

---

## Contact

For questions or contributions, please contact @gracebilliris
