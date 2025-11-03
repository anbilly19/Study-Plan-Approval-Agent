# UAdminAI


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


Built with Python 3.11.6

Please ensure that you have a Python version that is 3.10+
