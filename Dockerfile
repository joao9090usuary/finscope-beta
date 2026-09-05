FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 XDG_CACHE_HOME=/tmp \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false STREAMLIT_SERVER_HEADLESS=true
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN groupadd --system revo && useradd --system --gid revo --home-dir /app revo
COPY --chown=revo:revo . .
RUN mkdir -p /tmp/revo-yfinance && chown -R revo:revo /tmp/revo-yfinance
USER revo
EXPOSE 8501
HEALTHCHECK CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://localhost:' + os.getenv('PORT', '8501') + '/_stcore/health')"]
CMD ["sh", "-c", "streamlit run streamlit_app.py --server.address=0.0.0.0 --server.port=${PORT:-8501}"]
