import requests

def check_key(key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    data = {"contents": [{"parts": [{"text": "Hi"}]}]}
    res = requests.post(url, json=data)
    print(f"Key: {key[:10]}... Status: {res.status_code}")
    if res.status_code != 200:
        print(res.json())

keys = [
    "AIzaSyAluLuMcW3upXfQbDv0eN-9Dzxz45ffAo8",
    "AIzaSyD331Anzof74C4NbcRDT4UYzRRNQUF47lM",
    "AIzaSyDZTeHXVp4Rzd8tKerTMpbG_sND14xUHyY"
]

for k in keys:
    check_key(k)
