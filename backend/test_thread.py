import requests

base_url = 'http://127.0.0.1:8000/apps'

# 1. Login as guest
print("Logging in...")
resp = requests.post(f"{base_url}/auth/guest-login", json={"device_id": "test_device_123"})
if not resp.ok:
    print("Login failed:", resp.text)
    exit(1)

token = resp.json().get('access_token')
print("Token:", token)

# 2. Create thread
print("Creating thread...")
headers = {'Authorization': f'Bearer {token}'}
resp = requests.post(f"{base_url}/threads", json={"task": "hello world"}, headers=headers)
print("Response:", resp.status_code, resp.text)
