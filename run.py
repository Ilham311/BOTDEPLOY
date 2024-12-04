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

# Fungsi untuk deploy skrip dari URL atau file
@app.on_message(filters.command("deploy") | filters.document)
async def deploy(client: Client, message: Message):
    if message.document and message.document.file_name.endswith(".py"):
        # Jika file dikirim, gunakan file yang diunggah
        await message.reply("Menerima file skrip. Sedang mendownload...")
        file_path = await message.download()
    elif len(message.command) > 1:
        # Jika URL dikirim, unduh skrip dari URL
        url = message.command[1]
        await message.reply(f"Men-download skrip dari {url}...")
        try:
            response = requests.get(url)
            response.raise_for_status()  # Jika terjadi error saat mengunduh
            with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as temp_file:
                temp_file.write(response.content)
                file_path = temp_file.name
        except requests.exceptions.RequestException as e:
            await message.reply(f"Gagal mendownload skrip: {e}")
            return
    else:
        await message.reply("Silakan berikan URL atau file skrip untuk dideploy!")
        return

    try:
        # Jalankan skrip dalam subprocess dan simpan log di file terpisah
        log_file_path = file_path + ".log"
        with open(log_file_path, "w") as log_file:
            process = subprocess.Popen(
                ['python', file_path],
                stdout=log_file,
                stderr=log_file,
                env=os.environ
            )

        # Tambahkan ke registry
        process_registry[process.pid] = {
            "process": process,
            "file": file_path,
            "log": log_file_path,
            "status": "✅ Berjalan"
        }
        await message.reply(f"Skrip berhasil dijalankan dengan PID {process.pid}.")
    except Exception as e:
        await message.reply(f"Terjadi kesalahan saat menjalankan skrip: {e}")

# Fungsi untuk cek status semua proses
@app.on_message(filters.command("status"))
async def status(client: Client, message: Message):
    if not process_registry:
        await message.reply("Tidak ada skrip yang sedang berjalan.")
        return

    status_message = "Status Skrip yang Berjalan:\n"
    for pid, info in process_registry.items():
        if info["process"].poll() is not None:  # Proses telah berhenti
            info["status"] = "❌ Gagal"
        status_message += f"- PID {pid}: {info['status']} (File: {os.path.basename(info['file'])})\n"
    await message.reply(status_message)

# Fungsi untuk mengambil log proses tertentu
@app.on_message(filters.command("log"))
async def log(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("Gunakan: /log <PID>")
        return

    try:
        pid = int(message.command[1])
        if pid not in process_registry:
            await message.reply("PID tidak ditemukan.")
            return

        log_file_path = process_registry[pid]["log"]
        if os.path.exists(log_file_path):
            await message.reply_document(log_file_path)
        else:
            await message.reply("Log file tidak ditemukan.")
    except ValueError:
        await message.reply("PID harus berupa angka.")

# Fungsi untuk menghentikan proses tertentu
@app.on_message(filters.command("stop"))
async def stop(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("Gunakan: /stop <PID>")
        return

    try:
        pid = int(message.command[1])
        if pid not in process_registry:
            await message.reply("PID tidak ditemukan.")
            return

        process_info = process_registry[pid]
        if process_info["process"].poll() is None:  # Proses masih berjalan
            process_info["process"].terminate()
            process_info["process"].wait()
            os.remove(process_info["file"])  # Hapus file sementara
            os.remove(process_info["log"])  # Hapus file log
            del process_registry[pid]
            await message.reply(f"Proses dengan PID {pid} berhasil dihentikan.")
        else:
            await message.reply("Proses telah berhenti.")
    except ValueError:
        await message.reply("PID harus berupa angka.")

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
