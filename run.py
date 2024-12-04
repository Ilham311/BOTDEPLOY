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

@web_app.route('/')
def home():
    return "Fake Website - Server is Running!"

# Menjalankan server Flask
def run_flask():
    port = int(os.getenv("PORT", 5000))  # Default ke 5000 jika tidak ada PORT di environment
    web_app.run(host="0.0.0.0", port=port, threaded=True)

# Dictionary untuk melacak proses yang sedang berjalan
running_processes = {}

# Fungsi untuk perintah /deploy
@app.on_message(filters.command("deploy"))
async def deploy(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("Silakan berikan URL skrip untuk dideploy!")
        return

    url = message.command[1]
    await message.reply(f"Men-download skrip dari {url}...")
    
    try:
        # Unduh skrip
        response = requests.get(url)
        response.raise_for_status()  # Jika gagal, lempar error
        script_content = response.text

        # Simpan skrip ke file sementara
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as temp_file:
            temp_file.write(script_content.encode())
            temp_file_path = temp_file.name

        await message.reply("Skrip berhasil didownload! Menjalankan skrip di profil baru...")

        # Jalankan skrip di subprocess
        process = subprocess.Popen(['python', temp_file_path], env=os.environ)
        pid = process.pid
        running_processes[pid] = temp_file_path

        await message.reply(f"Skrip berhasil dijalankan dengan PID {pid}.")

    except requests.exceptions.RequestException as e:
        await message.reply(f"Gagal mendownload skrip: {e}")
    except Exception as e:
        await message.reply(f"Terjadi kesalahan: {e}")

# Fungsi untuk perintah /status
@app.on_message(filters.command("status"))
async def status(client: Client, message: Message):
    if not running_processes:
        await message.reply("Tidak ada skrip yang sedang berjalan.")
        return

    status_message = "Skrip yang sedang berjalan:\n\n"
    for pid, path in running_processes.items():
        status_message += f"PID: {pid}, Path: {path}\n"

    await message.reply(status_message)

# Fungsi untuk perintah /stop
@app.on_message(filters.command("stop"))
async def stop(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("Silakan berikan PID proses yang ingin dihentikan!")
        return

    try:
        pid = int(message.command[1])
        if pid in running_processes:
            os.kill(pid, 9)  # Hentikan proses dengan PID
            del running_processes[pid]
            await message.reply(f"Proses dengan PID {pid} berhasil dihentikan.")
        else:
            await message.reply(f"Tidak ada proses dengan PID {pid}.")
    except ValueError:
        await message.reply("PID harus berupa angka.")
    except Exception as e:
        await message.reply(f"Terjadi kesalahan saat menghentikan proses: {e}")

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
