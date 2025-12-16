# UAdminAI

A modular, agent-driven system powering student study-plan evaluation,
human-in-the-loop workflows, and advisor dashboards.


## Running the Project

> **Run all commands from the project root folder:**
>
>     uadminai/

### 1. Run the Agent in CLI

Execute the full evaluation pipeline directly from the terminal:

```bash
python -m src.main
```

### 2. Launch Student UI

Streamlit app for students to submit study plans:

```bash
streamlit run apps/ui/app_student.py
```

### 3. Launch Admin UI

Advisor/admin interface with HITL workflow controls:

```bash
streamlit run apps/ui/app_advisor.py
```

### 4. Run Backend FastAPI Server

Starts the backend consumed by both UIs and external clients:

```bash
uvicorn apps.api.main:app --reload
```

### 5. FastAPI Documentation & Testing

Swagger UI for exploring and testing APIs:

```bash
http://127.0.0.1:8000/docs
```

### Folder Structure

| Path                       | Description                                                    |
| -------------------------- | -------------------------------------------------------------- |
| **configs/**               | YAML configs for base and environment-specific settings.       |
| **docs/diagrams/**         | System and process flow diagrams.                              |
| **src/agents/**            | Individual AI agents (e.g., `main_agent`, `study_eval_agent`). |
| **src/workflows/**         | Multi-step logic for tasks like planning or updating.          |
| **src/langchain/**         | LangChain integration and human-in-the-loop helpers.           |
| **src/prompts/templates/** | Prompt templates (Jinja or plain text).                        |
| **src/object_models.py**   | Shared data models for agents and workflows.                   |
| **src/tools.py**           | Helper utilities or external integrations.                     |
| **src/logging/**           | Logging setup for debugging and tracking.                      |
| **apps/api/**              | FastAPI backend for agent access via HTTP endpoints.           |
| **src/tests/**             | Unit and integration tests.                                    |
| **README.md**              | This file.                                                     |

## Python Version

Project built and tested with: Python 3.11.6

Please ensure your environment uses: Python 3.10+
