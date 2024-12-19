# Gunakan image dasar Python
FROM python:3.9-slim

# Instal aria2
RUN apt-get update && apt-get install -y aria2

# Set lingkungan kerja di dalam kontainer
WORKDIR /app

# Salin requirements.txt ke lingkungan kerja
COPY requirements.txt .

# Instal dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Salin semua file ke lingkungan kerja
COPY . .

# Tentukan command yang akan dijalankan saat kontainer dimulai
CMD ["python", "run.py"]
