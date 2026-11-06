# TruthLensAI - kisi bhi server par chalane ke liye (Render, Railway, Hugging Face, VPS...)
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY frontend ./frontend
COPY models ./models

# Server jo PORT de wahi use karo, warna 7860 (Hugging Face Spaces ka default)
ENV PORT=7860
EXPOSE 7860
CMD gunicorn --chdir backend --workers 1 --threads 4 --timeout 60 --bind 0.0.0.0:$PORT app:app
