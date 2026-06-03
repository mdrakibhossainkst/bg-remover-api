from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
from itertools import cycle
from typing import Dict
import time

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# আপনার ১৬টি API Key
API_KEYS = [
    "DNvyvXobzpgTrHQ5vKcvD57k",
    "RbU1muit9JpTggHnbLYt31pM",
    "nTLhzX1gxPqqvSGufxpuFrnA",
    "ubXXXtzHc6HskjVCs4iSmu7s",
    "hAcWrKkV4Bfs5ptcoEFiWzxZ",
    "qh4W8Rsb8MjVbguYYHZnVCdA",
    "UA88URCSw9stnDfNfN48BREt",
    "pFJiQZWKyt57qrej1qiT2GKF",
    "KtBA1CamxG2DPR9VWf5kJtgW",
    "opPy2JKhPhWXcVsiywsALhPQ",
    "2znY4rfF4o3vZnRzvFYCynsD",
    "K3uHCsbeQoE5j1Dt9WbaAtSS",
    "6VLTpWF5a1sCotGmng2D89cf",
    "PY4y7oAmovMgH6po3YvfJjuJ",
    "6Co67UYntMT7gpFovnTLWVKB",
    "LAGMziK35mibykVYXSWh55Hk"
]

# API কীগুলোর স্ট্যাটাস ট্র্যাক করা
key_status: Dict[str, Dict] = {}
for key in API_KEYS:
    key_status[key] = {
        "requests_today": 0,
        "last_used": 0,
        "errors": 0,
        "active": True
    }

# রাউন্ড-রবিন রোটেশনের জন্য
key_cycle = cycle(API_KEYS)
current_key = next(key_cycle)

def get_next_key():
    """পরবর্তী API কী রিটার্ন করে"""
    global current_key
    # সবচেয়ে কম ব্যবহৃত কী বের করা
    min_used_key = min(API_KEYS, key=lambda k: key_status[k]["requests_today"])
    current_key = min_used_key
    return current_key

@app.get("/")
def root():
    return {
        "service": "BG Remover Load Balancer",
        "total_keys": len(API_KEYS),
        "status": "active",
        "endpoints": {
            "remove_bg": "/remove-bg",
            "health": "/health",
            "stats": "/stats"
        }
    }

@app.get("/health")
def health():
    active_keys = sum(1 for k in key_status.values() if k["active"])
    return {
        "status": "healthy",
        "active_keys": active_keys,
        "total_keys": len(API_KEYS),
        "total_requests": sum(k["requests_today"] for k in key_status.values())
    }

@app.get("/stats")
def stats():
    return {
        "key_usage": {k[:8] + "...": v["requests_today"] for k, v in key_status.items()},
        "total_requests": sum(k["requests_today"] for k in key_status.values()),
        "active_keys": sum(1 for k in key_status.values() if k["active"])
    }

@app.post("/remove-bg")
async def remove_background(file: UploadFile = File(...)):
    # চেক ফাইল সাইজ (10MB)
    file_content = await file.read()
    if len(file_content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    
    # চেক ফাইল টাইপ
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files allowed")
    
    selected_key = get_next_key()
    
    # প্রতি রিকোয়েস্টে ভিন্ন কী ব্যবহারের জন্য ফাইল রিওয়াইন্ড করতে হবে
    files = {'image_file': (file.filename, file_content, file.content_type)}
    headers = {'X-API-Key': selected_key}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                'https://api.remove.bg/v1.0/removebg',
                headers=headers,
                files=files
            )
            
            # স্ট্যাটাস আপডেট
            key_status[selected_key]["requests_today"] += 1
            key_status[selected_key]["last_used"] = int(time.time())
            
            if response.status_code == 200:
                return Response(content=response.content, media_type="image/png")
            elif response.status_code == 402:
                key_status[selected_key]["active"] = False
                raise HTTPException(status_code=402, detail="API key quota exceeded")
            else:
                key_status[selected_key]["errors"] += 1
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Request timeout")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
