import requests
import json
import sys

queries = [
    "Tell me a story about a dragon",
    "Which products are associated with the highest number of billing documents?",
    "Trace the full flow of billing document 91150187",
    "Identify sales orders that have broken or incomplete flows"
]

for q in queries:
    print(f"\n==========================================")
    print(f"Query: {q}")
    print(f"==========================================\n")
    req = {"message": q, "history": []}
    try:
        with requests.post("http://localhost:8000/query/chat", json=req, stream=True) as r:
            for line in r.iter_lines():
                if line:
                    print(line.decode('utf-8'))
    except Exception as e:
        print(f"Request failed: {e}")
