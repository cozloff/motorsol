import os
import requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("OPEN_ROUTER_KEY")

url = "https://openrouter.ai/api/v1/datasets/benchmarks/artificial-analysis"

headers = {"Authorization": "Bearer {key}"}

response = requests.get(url, headers=headers)

print(response.json())