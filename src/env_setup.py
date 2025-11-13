import os
import getpass

def setup_langsmith_env():
    """Setup LangSmith and OpenAI environment variables with defaults."""
    
    env_vars = {
        "LANGSMITH_TRACING": ("true", False),  # (default_value, is_secret)
        "LANGSMITH_ENDPOINT": ("https://api.smith.langchain.com", False),
        "LANGSMITH_API_KEY": (None, True),
        "LANGSMITH_PROJECT": ("hitl_test", False),
        "GROQ_API_KEY": (None, True)
    }
    
    missing_vars = []
    
    for var_name, (default, is_secret) in env_vars.items():
        value = os.getenv(var_name)
        
        if not value:
            if default:
                print(f"{var_name} not set. Using default: {default}")
                value = default
            else:
                prompt = f"Enter your {var_name}: "
                value = getpass.getpass(prompt) if is_secret else input(prompt)
            
            missing_vars.append((var_name, value))
            os.environ[var_name] = value
    
    if missing_vars:
        with open(".env", "a") as f:
            for var_name, value in missing_vars:
                f.write(f"\n{var_name}={value}")


