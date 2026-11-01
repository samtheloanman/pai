FROM node:24-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npx vite build --outDir /out --emptyOutDir

FROM python:3.12-slim
WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/main.py ./
COPY litellm.local.yaml ./
COPY app/pai/ ./pai/
COPY app/static/manifest.json ./static/manifest.json
COPY --from=web /out ./static
ENV DATA_DIR=/data
EXPOSE 8088
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8088"]
