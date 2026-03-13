FROM python:3.10

# FFmpeg yükle
RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app

COPY . .

# Python paketlerini yükle
RUN pip install --no-cache-dir -r requirements.txt

# Botu başlat
CMD ["python", "teksaslibot.py"]
