# ── Stage 1: builder ─────────────────────────────────────
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libjpeg-dev \
    libpng-dev \
    libboost-python-dev \
    libboost-thread-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /install
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --prefix=/install/deps --no-cache-dir -r requirements.txt

# ── Stage 2: runtime ─────────────────────────────────────
FROM python:3.11-slim

# Only runtime libs (MINIMAL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenblas0 \
    libgomp1 \
    libglib2.0-0 \
    libgl1 \
    libjpeg62-turbo \
    libpng16-16 \
    libx11-6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages
COPY --from=builder /install/deps /usr/local

WORKDIR /app
COPY . .

# 🔥 Important: ensure bcrypt works properly
RUN python -c "import bcrypt; print('bcrypt OK')"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]