import os
import requests
import tempfile
import subprocess
from threading import Thread
from pyrogram import Client, filters, idle
from pyrogram.types import Message
import logging
import sys
from datetime import datetime

# Konfigurasi logging
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

# Variabel Lingkungan
API_ID = os.getenv("API_ID", "961780")
API_HASH = os.getenv("API_HASH", "bbbfa43f067e1e8e2fb41f334d32a6a7")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7342220709:AAH0eJDE-B-GeDxJ5wbGwJxCJp_1rGimkjI") 
# Inisialisasi bot Telegram
app = Client("deploy_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Menyimpan informasi tentang subprocess yang berjalan
process_registry = {}

# Penanganan `ModuleNotFoundError` otomatis
def handle_module_not_found_error(script_path):
    try:
        result = subprocess.run(
            ['python3', script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ
        )

        if "ModuleNotFoundError" in result.stderr:
            missing_module = result.stderr.split("No module named ")[-1].strip().replace("'", "")
            logging.info(f"Modul yang hilang: {missing_module}. Menginstal otomatis...")
            install_result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', missing_module],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=os.environ
            )
            if install_result.returncode == 0:
                logging.info(f"Modul {missing_module} berhasil diinstal.")
                return True
            else:
                logging.error(f"Gagal menginstal modul {missing_module}: {install_result.stderr}")
                return False
        return True
    except Exception as e:
        logging.error(f"Terjadi kesalahan saat memeriksa modul yang hilang: {e}")
        return False

# Menjalankan skrip Python secara aman
def run_script_safe(script_path, chat_id, client):
    try:
        if not handle_module_not_found_error(script_path):
            client.send_message(chat_id, "Gagal menginstal modul yang hilang. Periksa log untuk detailnya.")
            return

        log_file_path = script_path + ".log"
        with open(log_file_path, "w") as log_file:
            process = subprocess.Popen(
                ['python3', script_path],
                stdout=log_file,
                stderr=log_file,
                env=os.environ
            )
        process_registry[process.pid] = {
            "process": process,
            "file": script_path,
            "log": log_file_path,
            "status": "✅ Berjalan"
        }
        client.send_message(chat_id, f"Skrip berhasil dijalankan dengan PID {process.pid}.")
        monitor_process(client, process.pid, chat_id)

    except Exception as e:
        client.send_message(chat_id, f"Terjadi kesalahan saat menjalankan skrip: {e}")

# Fungsi memantau proses untuk restart otomatis
def monitor_process(client: Client, pid: int, chat_id: int):
    def check():
        process_info = process_registry[pid]
        process = process_info["process"]
        return_code = process.poll()
        if return_code is not None:
            process_info["status"] = f"❌ Gagal (Kode: {return_code})"
            log_path = process_info["log"]
            error_message = f"Proses dengan PID {pid} telah berhenti. "
            if os.path.exists(log_path):
                with open(log_path, "r") as log_file:
                    error_logs = log_file.read()
                error_message += f"\n\nLog terakhir:\n```\n{error_logs[-4000:]}\n```"
            else:
                error_message += "\nLog file tidak ditemukan."
            client.send_message(chat_id, error_message, parse_mode="markdown")

            # Restart jika diperlukan
            client.send_message(chat_id, "Mencoba me-restart proses...")
            run_script_safe(process_info["file"], chat_id, client)

    thread = Thread(target=check)
    thread.start()

# Deploy skrip dengan URL atau file
@app.on_message(filters.command("deploy") | filters.document)
async def deploy(client: Client, message: Message):
    try:
        if message.document and message.document.file_name.endswith(".py"):
            await message.reply("Menerima file skrip. Sedang mendownload...")
            file_path = await message.download()
        elif len(message.command) > 1:
            url = message.command[1]
            await message.reply(f"Men-download skrip dari {url}...")
            try:
                response = requests.get(url)
                response.raise_for_status()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as temp_file:
                    temp_file.write(response.content)
                    file_path = temp_file.name
            except requests.exceptions.RequestException as e:
                await message.reply(f"Gagal mendownload skrip: {e}")
                return
        else:
            await message.reply("Silakan berikan URL atau file skrip untuk dideploy!")
            return

        run_script_safe(file_path, message.chat.id, client)

    except Exception as e:
        await message.reply(f"Terjadi kesalahan: {e}")

# Menampilkan status proses yang sedang berjalan
@app.on_message(filters.command("status"))
async def status(client: Client, message: Message):
    if not process_registry:
        await message.reply("Tidak ada skrip yang sedang berjalan.")
        return
    status_message = "Status Proses yang Berjalan:\n"
    for pid, info in process_registry.items():
        if info["process"].poll() is not None:
            info["status"] = "❌ Gagal"
        status_message += f"- PID {pid}: {info['status']} (File: {os.path.basename(info['file'])})\n"
    await message.reply(status_message)

# Membaca log proses tertentu
@app.on_message(filters.command("log"))
async def log(client: Client, message: Message):
    try:
        pid = int(message.command[1])
        if pid not in process_registry:
            await message.reply("PID tidak ditemukan.")
            return
        log_file_path = process_registry[pid]["log"]
        if os.path.exists(log_file_path):
            with open(log_file_path, "r") as log_file:
                log_content = log_file.read()
            await message.reply_document(log_file_path, caption=f"Log PID {pid}.")
        else:
            await message.reply("Log file tidak ditemukan.")
    except Exception:
        await message.reply("Gunakan format: `/log <PID>`.")

# Menghentikan proses tertentu
@app.on_message(filters.command("stop"))
async def stop(client: Client, message: Message):
    try:
        pid = int(message.command[1])
        if pid not in process_registry:
            await message.reply("PID tidak ditemukan.")
            return
        process_info = process_registry.pop(pid, None)
        process_info["process"].terminate()
        os.remove(process_info["file"])
        os.remove(process_info["log"])
        await message.reply(f"Proses PID {pid} telah dihentikan dan file terkait dihapus.")
    except Exception:
        await message.reply("Gunakan format: `/stop <PID>`.")

# Jalankan bot
if __name__ == "__main__":
    print("Bot sedang berjalan...")
    try:
        app.start()
        idle()
    except KeyboardInterrupt:
        print("Menutup bot...")
    finally:
        app.stop()
