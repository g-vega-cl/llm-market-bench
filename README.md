# llm-market-bench

This repository contains tools for AI-driven market analysis and benchmarking.

## Engine

The `apps/engine` directory contains the core processing logic, including newsletter ingestion and database snapshotting.

### Local Execution

To run the ingestion and upload to Supabase locally:

1.  **Navigate to the engine directory**:
    ```bash
    cd apps/engine
    ```

2.  **Activate the virtual environment**:
    ```bash
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the ingest command**:
    ```bash
    python3 main.py ingest
    ```

### Testing

To run the automated test suite for the engine:

1.  **Activate the virtual environment** (if not already done):
    ```bash
    source venv/bin/activate
    ```

2.  **Run tests**:
    ```bash
    python3 -m pytest
    ```

> [!NOTE]
> The test suite currently covers core configuration and ingestion utilities. Database interaction tests have been omitted to avoid third-party dependency warnings with the supabase official testing library and prioritize a secure, minimal dependency footprint for automated verification.

### Environment Configuration

Ensure you have a `.env` file in `apps/engine/` with the following variables:

- `SUPABASE_PROJECT_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `GMAIL_CREDENTIALS_JSON`
- `GMAIL_TOKEN_JSON`

## Automation

The project uses GitHub Actions for daily automated ingestion. See [.github/workflows/ingest.yml](.github/workflows/ingest.yml) for details.