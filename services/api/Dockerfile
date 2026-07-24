FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update \
    && apt-get install --no-install-recommends --yes ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY darkttk ./darkttk
RUN groupadd --gid 10001 darkttk \
    && useradd --uid 10001 --gid darkttk --no-create-home --shell /usr/sbin/nologin darkttk \
    && mkdir -p /app/work/media \
    && chown -R darkttk:darkttk /app
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "darkttk.main:app", "--host", "0.0.0.0", "--port", "8000"]
