FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Disables huggingface_hub's tqdm-based progress bars for the
# FastEmbed model download. This isn't cosmetic: it avoids a real
# thread-safety race in tqdm's parallel-download progress callbacks
# (tqdm.contrib.concurrent.thread_map) that surfaces as
# "AttributeError: 'tqdm' object has no attribute '_lock'" under
# containers with constrained/uneven network+CPU. See the matching
# comment in app/rag/embedder.py for the full explanation — this ENV
# is a defense-in-depth belt (guaranteed set before any Python code
# runs); the code-level fix is the actual root-cause fix.
ENV HF_HUB_DISABLE_PROGRESS_BARS=1

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data ./data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]