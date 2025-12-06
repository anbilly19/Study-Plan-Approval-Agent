import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.append(os.getcwd())

from src.main import init_eval_agents, evaluate_study_plan, GPT_4O

def verify_openai_migration():
    print("Verifying OpenAI Migration...")
    
    # Check API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in environment.")
        return False
    print(f"OPENAI_API_KEY found: {api_key[:5]}...")

    # Initialize Agents
    try:
        print("Initializing agents with GPT-4o...")
        init_eval_agents(model_name=GPT_4O)
        print("Agents initialized successfully.")
    except Exception as e:
        print(f"ERROR: Failed to initialize agents: {e}")
        return False

    # Test Evaluation
    try:
        print("Testing evaluation with a dummy study plan...")
        dummy_plan = "I want to take Introduction to Computer Science and Linear Algebra."
        result = evaluate_study_plan(study_plan=dummy_plan, hitl=False, model_name=GPT_4O)
        print("Evaluation successful!")
        print("Result keys:", result.keys() if isinstance(result, dict) else result)
        print("Result:", result)
    except Exception as e:
        print(f"ERROR: Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    if verify_openai_migration():
        print("✅ MIGRATION VERIFIED SUCCESSFULLY")
    else:
        print("❌ MIGRATION VERIFICATION FAILED")
