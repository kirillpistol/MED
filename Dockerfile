FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/med
RUN groupadd --system med && useradd --system --gid med med
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py research.py clinical_trials.py history.py collector.py analytics.py reports.py quality.py themes.py ./
COPY config/collection.json ./config/collection.json
RUN mkdir -p /var/lib/med && chown med:med /var/lib/med
USER med
EXPOSE 8091
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8091"]
