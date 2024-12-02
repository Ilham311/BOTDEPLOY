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

# Fungsi untuk deploy skrip
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
        
        # Menjalankan skrip dalam proses baru (subprocess)
        subprocess.Popen(['python', temp_file_path], env=os.environ)  # Anda bisa menambahkan env terpisah jika diperlukan

        await message.reply("Skrip berhasil dijalankan di profil terpisah.")
        
    except requests.exceptions.RequestException as e:
        await message.reply(f"Gagal mendownload skrip: {e}")
    except Exception as e:
        await message.reply(f"Terjadi kesalahan: {e}")

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
