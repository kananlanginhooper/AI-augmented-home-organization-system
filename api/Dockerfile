FROM node:22-slim AS ui
WORKDIR /ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY ui/ ./
RUN npx ng build

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UI_DIR=/app/ui PHOTO_DIR=/data/photos FORWARDED_ALLOW_IPS=127.0.0.1 API_PORT=8109
WORKDIR /app
COPY api/requirements.txt api/requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS test
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY api/app ./app
COPY api/tests ./tests
CMD ["python", "-m", "pytest", "-q"]

FROM base
COPY api/app ./app
COPY --from=ui /ui/dist/ui/browser ./ui
# readable by the app user whatever the modes were in the clone it was built from
RUN chmod -R a+rX /app && useradd --system --uid 10001 app && mkdir -p /data/photos && chown -R app /data
USER app
EXPOSE 8109
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"$API_PORT\" --proxy-headers --forwarded-allow-ips \"$FORWARDED_ALLOW_IPS\""]
