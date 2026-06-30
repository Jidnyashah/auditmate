import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import config
import google.genai as genai

print("Loaded API key:", repr(config.GOOGLE_API_KEY))
try:
    client = genai.Client(api_key=config.GOOGLE_API_KEY)
    print("Client initialized successfully.")
    
    print("Generating content...")
    response = client.models.generate_content(
        model=config.MODEL_NAME,
        contents="Hello, tell me 'success'!",
    )
    print("API Response:", response.text)
        
except Exception as e:
    print("Error:", e)
