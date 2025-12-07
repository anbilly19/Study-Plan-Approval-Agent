import getpass
import os

ENABLE_LANGSMITH = False  # change to True when you want to use LangSmith


def setup_langsmith_env():
    """Set up environment variables for LangSmith.

    Provides easy on/off control for LangSmith tracing in development and production.
    """
    # If LangSmith is disabled, set tracing variables to false.
    if not ENABLE_LANGSMITH:
        os.environ["LANGSMITH_TRACING"] = "false"
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        print("LangSmith disabled.")
    else:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        print("LangSmith enabled.")

    # Environment variables your app needs
    env_vars = {
        # LangSmith (only matters if enabled)
        "LANGSMITH_ENDPOINT": ("https://api.smith.langchain.com" if ENABLE_LANGSMITH else None, False),
        "LANGSMITH_API_KEY": (None, True),
        # Optional project name
        "LANGSMITH_PROJECT": ("hitl_test", False),
        # Other required API keys
        "OPENAI_API_KEY": (None, True),
        "GROQ_API_KEY": (None, True)
    }

    missing_vars = []

    for var_name, (default, is_secret) in env_vars.items():
        # Skip LangSmith keys when disabled
        if not ENABLE_LANGSMITH and var_name.startswith("LANGSMITH"):
            continue

        value = os.getenv(var_name)
        # If env var not set
        if not value:
            if default:
                print(f"{var_name} not set. Using default: {default}")
                value = default
            else:
                prompt = f"Enter your {var_name}: "
                value = getpass.getpass(prompt) if is_secret else input(prompt)

            missing_vars.append((var_name, value))
            os.environ[var_name] = value

    # Save missing values to .env
    if missing_vars:
        with open(".env", "a") as f:
            for var_name, value in missing_vars:
                f.write(f"\n{var_name}={value}")

    print("Environment configuration complete.")