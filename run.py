import os
import requests
import tempfile
import subprocess
from threading import Thread
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from flask import Flask

# Inisialisasi bot Telegram
app = Client("deploy_bot", api_id="961780", api_hash="bbbfa43f067e1e8e2fb41f334d32a6a7", bot_token="7342220709:AAEyZVJPKuy6w_N9rwrVW3GghYyxx3jixww")

# Inisialisasi Flask untuk fake website
web_app = Flask(__name__)

# Menyimpan informasi tentang subprocess yang berjalan
process_registry = {}

@web_app.route('/')
def home():
    return "Fake Website - Server is Running!"

# Menjalankan server Flask
def run_flask():
    port = int(os.getenv("PORT", 5000))  # Default ke 5000 jika tidak ada PORT di environment
    web_app.run(host="0.0.0.0", port=port, threaded=True)

# Fungsi untuk deploy skrip dari URL
@app.on_message(filters.command("deploy"))
async def deploy(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("Silakan berikan URL skrip untuk dideploy!")
        return
    
    url = message.command[1]
    
    # Unduh skrip dari URL
    await message.reply(f"Men-download skrip dari {url}...")
    try:
        response = requests.get(url)
        response.raise_for_status()  # Jika terjadi error saat mengunduh
        script_content = response.text
        
        # Membuat file sementara untuk skrip
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as temp_file:
            temp_file.write(script_content.encode())
            temp_file_path = temp_file.name
        
        await message.reply(f"Skrip berhasil didownload! Menjalankan skrip di profil baru...")
        
        # Menjalankan skrip dalam subprocess
        with open(f"{temp_file_path}.log", "w") as log_file:
            process = subprocess.Popen(['python', temp_file_path], stdout=log_file, stderr=log_file, env=os.environ)
            process_registry[message.chat.id] = {"process": process, "file": temp_file_path, "log": f"{temp_file_path}.log"}
        
        await message.reply(f"Skrip berhasil dijalankan dengan PID {process.pid}. ✅")
        
    except requests.exceptions.RequestException as e:
        await message.reply(f"Gagal mendownload skrip: {e} ❌")
    except Exception as e:
        await message.reply(f"Terjadi kesalahan: {e} ❌")

# Fungsi untuk cek status proses
@app.on_message(filters.command("status"))
async def status(client: Client, message: Message):
    process_info = process_registry.get(message.chat.id)
    if process_info:
        if process_info["process"].poll() is None:
            await message.reply(f"Skrip berjalan dengan PID {process_info['process'].pid}. ✅")
        else:
            await message.reply(f"Skrip telah berhenti. ❌")
    else:
        await message.reply("Tidak ada skrip yang sedang berjalan. ❌")

# Fungsi untuk menghentikan proses
@app.on_message(filters.command("stop"))
async def stop(client: Client, message: Message):
    process_info = process_registry.get(message.chat.id)
    if process_info and process_info["process"].poll() is None:
        process_info["process"].terminate()
        process_info["process"].wait()
        os.remove(process_info["file"])  # Hapus file sementara
        del process_registry[message.chat.id]
        await message.reply("Proses skrip berhasil dihentikan. ✅")
    else:
        await message.reply("Tidak ada proses yang dapat dihentikan. ❌")

# Fungsi untuk mendapatkan log proses
@app.on_message(filters.command("log"))
async def log(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("Silakan masukkan nama file atau PID untuk mendapatkan log!")
        return

    identifier = message.command[1]
    for chat_id, info in process_registry.items():
        if str(info["process"].pid) == identifier or info["file"].endswith(identifier):
            if os.path.exists(info["log"]):
                await message.reply_document(info["log"], caption=f"Log untuk proses PID {info['process'].pid}")
            else:
                await message.reply("Log tidak ditemukan. ❌")
            return
    await message.reply("Proses tidak ditemukan. ❌")

# Fungsi untuk deploy dari file
@app.on_message(filters.document & filters.private)
async def deploy_from_file(client: Client, message: Message):
    file_name = message.document.file_name
    if not file_name.endswith(".py"):
        await message.reply("Hanya file dengan ekstensi `.py` yang didukung. ❌")
        return
    
    await message.reply("Men-download file...")
    file_path = await message.download()
    
    try:
        await message.reply("Menjalankan skrip...")
        with open(f"{file_path}.log", "w") as log_file:
            process = subprocess.Popen(['python', file_path], stdout=log_file, stderr=log_file, env=os.environ)
            process_registry[message.chat.id] = {"process": process, "file": file_path, "log": f"{file_path}.log"}
        
        await message.reply(f"Skrip berhasil dijalankan dengan PID {process.pid}. ✅")
    except Exception as e:
        await message.reply(f"Terjadi kesalahan: {e} ❌")

# Fungsi utama untuk menjalankan bot dan web server
if __name__ == "__main__":
    print("Bot dan Web Server sedang berjalan...")
    try:
        # Jalankan server Flask di thread terpisah
        thread = Thread(target=run_flask)
        thread.start()
        
        # Mulai bot Pyrogram
        app.start()

        # Pastikan bot tetap berjalan
        idle()  # Menjaga bot tetap berjalan

    except KeyboardInterrupt:
        print("Menutup aplikasi...")
    finally:
        app.stop()
        # Jika ingin menghentikan Flask juga saat bot berhenti, Anda bisa menambah ini:
        # web_app.shutdown()
