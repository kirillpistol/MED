FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/med
RUN groupadd --system med && useradd --system --gid med med
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
USER med
EXPOSE 8091
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8091"]
