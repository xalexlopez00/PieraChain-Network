FROM python:3.11-slim
WORKDIR /app
# Instala dependencias del sistema para criptografía
RUN apt-get update && apt-get install -y gcc libffi-dev g++ && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Render usa el puerto 10000 por defecto
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]