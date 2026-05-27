FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Set USE_GPU=1 at build time to install CUDA PyTorch (requires NVIDIA Container Toolkit at run time).
ARG USE_GPU=0

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        libgl1 \
        libglib2.0-0 \
        libreoffice-impress \
        libreoffice-writer \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && if [ "$USE_GPU" = "1" ]; then \
        pip install --no-cache-dir --force-reinstall torch torchvision \
            --index-url https://download.pytorch.org/whl/cu124; \
    fi

# Pre-download EasyOCR English models during image build (CPU is fine for caching weights).
RUN python -c "import easyocr; easyocr.Reader(['en'], gpu=False, verbose=False)"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
