import requests
import json

queries = [
    "Tell me a story about a dragon",
    "Which products are associated with the highest number of billing documents?",
    "Trace the full flow of billing document 91150187",
    "Identify sales orders that have broken or incomplete flows"
]

results = {}

for q in queries:
    req = {"message": q, "history": []}
    response_text = ""
    try:
        with requests.post("http://localhost:8000/query/chat", json=req, stream=True) as r:
            for line in r.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith("data: "):
                        data = json.loads(line_str[6:])
                        if "chunk" in data:
                            response_text += data["chunk"]
                        elif "sql" in data:
                            response_text += f"\n[SQL EXECUTED: {data['sql']}]\n"
        results[q] = response_text
    except Exception as e:
        results[q] = f"Error: {e}"

with open("test_results.json", "w") as f:
    json.dump(results, f, indent=4)
