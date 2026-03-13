FROM python:3.10

RUN apt update && apt install -y ffmpeg

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "teksaslibot.py"]