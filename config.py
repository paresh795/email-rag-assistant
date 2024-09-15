import os
from dotenv import load_dotenv

# Get the absolute path to the directory containing this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Construct the path to the .env file
dotenv_path = os.path.join(BASE_DIR, '.env')

# Load the .env file
load_dotenv(dotenv_path)

# Read the API key directly from the .env file
with open(dotenv_path, 'r') as f:
    for line in f:
        if line.startswith('OPENAI_API_KEY='):
            OPENAI_API_KEY = line.split('=', 1)[1].strip()
            break
    else:
        OPENAI_API_KEY = None

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
DOCUMENTS_DIR = os.path.join(BASE_DIR, "data", "documents")

# Add these new lines
LOCAL_LLM_BASE_URL = "http://localhost:1234/v1"
USE_LOCAL_LLM = os.getenv('USE_LOCAL_LLM', 'false').lower()
LOCAL_LLM_MAX_TOKENS = int(os.getenv('LOCAL_LLM_MAX_TOKENS', '500'))

print(f"OPENAI_API_KEY: {OPENAI_API_KEY}")  # This will print the actual key, be careful!
print(f"DOCUMENTS_DIR: {DOCUMENTS_DIR}")
print(f"USE_LOCAL_LLM: {USE_LOCAL_LLM}")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in the .env file")

if not DOCUMENTS_DIR:
    raise ValueError("DOCUMENTS_DIR is not set in the .env file")

# Add this line for Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

EMAIL_HISTORY_DAYS = 365  # or any other number of days you prefer
