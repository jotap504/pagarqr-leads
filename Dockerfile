# -------------------------------------------------
#  Imagen base
# -------------------------------------------------
FROM python:3.12-slim

# Crear directorio de trabajo
WORKDIR /app

# Copiar requerimientos e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY scraper_web.py .
COPY db_handler.py .
COPY email_sender.py .
COPY .env .

# Exponer puerto Streamlit
EXPOSE 8501

# Entrypoint - ejecuta Streamlit en modo headless y con basePath /search
CMD ["streamlit", "run", "scraper_web.py", "--server.port", "8501", "--server.baseUrlPath", "/search", "--server.headless", "true"]
