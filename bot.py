import os
import asyncio
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiohttp import web

# --- CẤU HÌNH ---
API_TOKEN = "8862266782:AAH3EoSeCJFgRFM1nUrXush7tMtR5w1WPNA"
BOT_USERNAME = "@ATMPAY68bot"
ADMIN_IDS = [2106916939, 228160692]
RATE_FILE_USDT = "rate_usdt.txt"
RATE_FILE_RMB = "rate_rmb.txt"
FEE_FILE = "fee.txt"
COUNTER_FILE = "counter.txt"
DATE_FILE = "last_date.txt"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- HÀM HỖ TRỢ ---
def format_vn(value):
    return f"{value:,.0f}".replace(",", ".")

def get_value(file_path, default):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try: return float(f.read().strip())
            except: return default
    return default

def save_value(file_path, value):
    with open(file_path, "w") as f:
        f.write(str(value))

# --- HÀM RESET ORDER THEO NGÀY ---
def get_next_order_id():
    tz_vietnam = timezone(timedelta(hours=7))
    today = datetime.now(tz_vietnam).strftime("%Y-%m-%d")
    
    # Đọc ngày lưu lần cuối
    if os.path.exists(DATE_FILE):
        with open(DATE_FILE, "r") as f:
            last_date = f.read().strip()
    else:
        last_date = ""

    # Nếu sang ngày mới, reset counter về 1
    if last_date != today:
        current_counter = 1
        save_value(DATE_FILE, today)
    else:
        # Nếu cùng ngày, đọc file counter
        current_counter = int(get_value(COUNTER_FILE, 1))
    
    # Lưu counter tiếp theo vào file
    save_value(COUNTER_FILE, current_counter + 1)
    return current_counter

# --- CÁC LỆNH ADMIN ---
@dp.message(Command("setrate_usdt"))
async def set_rate_usdt(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        new_rate = float(message.text.split()[1])
        save_value(RATE_FILE_USDT, new_rate)
        await message.answer(f"✅ Đã set tỷ giá VND/USDT: {format_vn(new_rate)}")
    except: await message.answer("⚠️ Lỗi định dạng.")

@dp.message(Command("setrate_rmb"))
async def set_rate_rmb(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        new_rate = float(message.text.split()[1])
        save_value(RATE_FILE_RMB, new_rate)
        await message.answer(f"✅ Đã set tỷ giá RMB/VND: {format_vn(new_rate)}")
    except: await message.answer("⚠️ Lỗi định dạng.")

@dp.message(Command("setfee"))
async def set_fee(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        # Lấy giá trị sau lệnh /setfee
        args = message.text.split()
        if len(args) < 2:
            await message.answer("⚠️ Thiếu giá trị. Ví dụ: /setfee 6")
            return
        
        # Bỏ dấu % nếu có
        val = float(args[1].replace('%', ''))
        save_value(FEE_FILE, val)
        await message.answer(f"✅ Đã cập nhật phí: {val}%")
    except Exception as e:
        await message.answer("⚠️ Lỗi định dạng số phí.")

# --- LOGIC ĐỐI SOÁT ---
@dp.message()
async def process_message(message: Message):
    if not message.text or "@ATMPAY68bot" not in message.text: return
    
    raw_text = message.text.replace("@ATMPAY68bot", "").strip()
    clean_text = raw_text.replace(',', '').replace('.', '')
    
    if clean_text.isdigit():
        try:
            import_rmb = float(clean_text)
            # Lấy tỷ giá
            rate_rmb_vnd = get_value(RATE_FILE_RMB, 3500)
            rate_vnd_usdt = get_value(RATE_FILE_USDT, 25000)
            fee_percent = get_value(FEE_FILE, 6.0)
            
            # Tính toán
            total_vnd = import_rmb * rate_rmb_vnd
            fee_amount = total_vnd * (fee_percent / 100)
            remaining_vnd = total_vnd - fee_amount
            usdt_amount = remaining_vnd / rate_vnd_usdt
            
            # Lấy ID order reset theo ngày
            order_id = get_next_order_id()
            
            tz_vietnam = timezone(timedelta(hours=7))
            current_time = datetime.now(tz_vietnam).strftime("%H:%M:%S - %d/%m/%Y")
            
            response = (
                f"📊 **对账结果 (RMB)**\n\n"
                f"- Order: #{order_id}\n"
                f"- 时间: `{current_time}`\n\n"
                f"- 汇率 RMB/VND: {format_vn(rate_rmb_vnd)}\n"
                f"- 汇率VND/USDT: {format_vn(rate_vnd_usdt)}\n"
                f"- RMB: {format_vn(import_rmb)}\n"
                f"- 兑换 VND: {format_vn(total_vnd)}\n"
                f"- 手续费 ({fee_percent}%): {format_vn(fee_amount)}\n"
                f"- 实际到账金额 (VND): {format_vn(remaining_vnd)}\n"
                f"- 兑换成 USDT: **{usdt_amount:.2f} USDT**"
            )
            await message.answer(response, parse_mode="Markdown")
        except Exception as e:
            print(f"Lỗi: {e}")

# --- WEB SERVER ---
async def start_web_server():
    app = web.Application()
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
