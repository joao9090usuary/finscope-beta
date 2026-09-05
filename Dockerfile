FROM caddy:2.11.4-alpine AS caddy_runtime

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 XDG_CACHE_HOME=/tmp \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false STREAMLIT_SERVER_HEADLESS=true
WORKDIR /app
COPY --from=caddy_runtime /usr/bin/caddy /tmp/caddy
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN groupadd --system revo && useradd --system --gid revo --home-dir /app revo
RUN install -m 0755 /tmp/caddy /usr/local/bin/caddy && rm /tmp/caddy
COPY --chown=revo:revo . .
COPY --chown=revo:revo Caddyfile /etc/caddy/Caddyfile
RUN mkdir -p /tmp/revo-yfinance && chown -R revo:revo /tmp/revo-yfinance
USER revo
EXPOSE 8501
HEALTHCHECK CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://localhost:' + os.getenv('PORT', '8501') + '/_stcore/health')"]
CMD ["python", "-m", "jobs.start_web"]
