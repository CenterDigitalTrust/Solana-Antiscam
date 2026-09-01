import requests

SUPABASE_URL = "https://qfknvpozbzvzflhfjdte.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFma252cG96Ynp2emZsaGZqZHRlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4ODAxNzUyMywiZXhwIjoyMTAzNTkzNTIzfQ.h_aQjRRDQg87TwgEAKecgq7BfiVbQ9suLOHYPVoa16E"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# Create a test table or check if we can query
resp = requests.get(f"{SUPABASE_URL}/rest/v1/", headers=headers)
print("Connection Check:", resp.status_code)
