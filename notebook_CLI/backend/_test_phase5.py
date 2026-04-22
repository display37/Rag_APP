"""
Phase 5 — Data Flow End-to-End Test
Tests:
  1. Qdrant: collection exists
  2. Upload: POST /upload/{chat_id} with the sample PDF
  3. Query:  POST /chat with a question (streams response)
  4. History: GET /chat/history/{chat_id} confirms messages saved in Mongo
"""

import sys
import json
import time
import urllib.request
import urllib.error

BASE = "http://localhost:8000"
SAMPLE_PDF = "../data/dopamine-detox.pdf"

def request(method, path, data=None, content_type="application/json"):
    url = BASE + path
    if data and content_type == "application/json":
        data = json.dumps(data).encode()
    req = urllib.request.Request(url, data=data, method=method)
    if content_type == "application/json" and data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

def section(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print('='*55)

# ─────────────────────────────────────────
# STEP 0: Check backend is up
# ─────────────────────────────────────────
section("STEP 0 — Backend health check")
status, body = request("GET", "/")
assert status == 200, f"Backend not up! Status {status}"
print("✅ Backend is running:", body)

# ─────────────────────────────────────────
# STEP 1: Qdrant collection check
# ─────────────────────────────────────────
section("STEP 1 — Qdrant collection")
with urllib.request.urlopen("http://localhost:6333/collections") as r:
    data = json.loads(r.read())
collections = [c["name"] for c in data["result"]["collections"]]
print("Collections:", collections)
if "rag_collection" not in collections:
    print("⚠️  rag_collection missing — it will be auto-created on first upload")
else:
    print("✅ rag_collection exists")

# ─────────────────────────────────────────
# STEP 2: Create a chat
# ─────────────────────────────────────────
section("STEP 2 — Create chat")
status, body = request("POST", "/chat/create", {})
assert status == 200, f"Create chat failed: {status} {body}"
chat_id = json.loads(body)["chat_id"]
print(f"✅ Chat created. chat_id = {chat_id}")

# ─────────────────────────────────────────
# STEP 3: Upload PDF
# ─────────────────────────────────────────
section("STEP 3 — Upload PDF")
import os, mimetypes
if not os.path.exists(SAMPLE_PDF):
    print(f"❌ Sample PDF not found at {SAMPLE_PDF}")
    sys.exit(1)

boundary = "----TestBoundary1234"
filename = os.path.basename(SAMPLE_PDF)
with open(SAMPLE_PDF, "rb") as f:
    pdf_bytes = f.read()

body_parts = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
    f"Content-Type: application/pdf\r\n\r\n"
).encode() + pdf_bytes + f"\r\n--{boundary}--\r\n".encode()

req = urllib.request.Request(
    f"{BASE}/upload/{chat_id}",
    data=body_parts,
    method="POST"
)
req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

print(f"Uploading {filename} ({len(pdf_bytes)//1024} KB) to chat {chat_id}...")
t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        upload_status = resp.status
        upload_body = resp.read().decode()
except urllib.error.HTTPError as e:
    upload_status = e.code
    upload_body = e.read().decode()

elapsed = time.time() - t0
print(f"Status: {upload_status}  ({elapsed:.1f}s)")
print("Response:", upload_body)
assert upload_status == 200, f"Upload failed: {upload_status}"
result = json.loads(upload_body)
print(f"✅ Upload OK — {result.get('chunks_indexed', '?')} chunks indexed")

# Confirm collection now exists
with urllib.request.urlopen("http://localhost:6333/collections") as r:
    data = json.loads(r.read())
collections = [c["name"] for c in data["result"]["collections"]]
assert "rag_collection" in collections, "rag_collection still missing after upload!"
print("✅ Qdrant rag_collection confirmed")

# ─────────────────────────────────────────
# STEP 4: Ask a question (streaming)
# ─────────────────────────────────────────
section("STEP 4 — Chat / streaming")
question = "What is dopamine detox and why do people do it?"
payload = json.dumps({
    "question": question,
    "history": [],
    "chat_id": chat_id
}).encode()

req = urllib.request.Request(f"{BASE}/chat", data=payload, method="POST")
req.add_header("Content-Type", "application/json")

print(f"Question: {question}\n")
t0 = time.time()
full_response = ""
sources_raw = ""
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = resp.read().decode()
        if "###SOURCES###" in raw:
            parts = raw.split("###SOURCES###")
            full_response = parts[0].strip()
            sources_raw = parts[1]
        else:
            full_response = raw.strip()
except urllib.error.HTTPError as e:
    print(f"❌ Chat failed: {e.code} {e.read().decode()}")
    sys.exit(1)

elapsed = time.time() - t0
print(f"Answer ({elapsed:.1f}s):\n{full_response[:500]}")
if sources_raw:
    sources = json.loads(sources_raw)
    print(f"\n✅ Retrieved {len(sources)} source chunks")
assert len(full_response) > 20, "Response too short — something went wrong"
print("✅ Streaming response OK")

# ─────────────────────────────────────────
# STEP 5: Reload history from Mongo
# ─────────────────────────────────────────
section("STEP 5 — History reload from MongoDB")
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check_history():
    mongo = AsyncIOMotorClient(
        "mongodb+srv://someshg897_db_user:xsH8Jg94y0L9tNd0@aiagent.albdljr.mongodb.net/rag_app?retryWrites=true&w=majority"
    )
    col = mongo["rag_app"]["messages"]
    cursor = col.find({"chat_id": chat_id}).sort("_id", 1)
    messages = await cursor.to_list(length=100)
    mongo.close()
    return messages

messages = asyncio.run(check_history())
print(f"Messages in Mongo for chat_id={chat_id}: {len(messages)}")
for m in messages:
    role = m.get("role", "?")
    text = m.get("text", "")[:80]
    print(f"  [{role}] {text}")

assert len(messages) >= 2, f"Expected ≥2 messages, got {len(messages)}"
roles = [m["role"] for m in messages]
assert "user" in roles and "bot" in roles, f"Missing user/bot messages: {roles}"
print("✅ History persisted correctly in MongoDB")

# ─────────────────────────────────────────
# STEP 6: Verify /chat/history endpoint
# ─────────────────────────────────────────
section("STEP 6 — GET /chat/history/{chat_id} endpoint")
status, body = request("GET", f"/chat/history/{chat_id}")
assert status == 200, f"history endpoint failed: {status}"
hist = json.loads(body)
print(f"Returned {len(hist)} messages via API")
for m in hist:
    print(f"  [{m['role']}] {m['text'][:60]}")
assert len(hist) >= 2, "History endpoint returned too few messages"
print("✅ History endpoint works")

# ─────────────────────────────────────────
# DONE
# ─────────────────────────────────────────
section("PHASE 5 COMPLETE ✅")
print(f"""
  chat_id        : {chat_id}
  chunks indexed : {result.get('chunks_indexed', '?')}
  response len   : {len(full_response)} chars
  mongo messages : {len(messages)}
  history via API: {len(hist)} messages
""")
