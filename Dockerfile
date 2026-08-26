FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 XDG_CACHE_HOME=/tmp \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false STREAMLIT_SERVER_HEADLESS=true
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN groupadd --system finscope && useradd --system --gid finscope --home-dir /app finscope
COPY --chown=finscope:finscope . .
RUN mkdir -p /tmp/finscope-yfinance && chown -R finscope:finscope /tmp/finscope-yfinance
USER finscope
EXPOSE 8501
HEALTHCHECK CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://localhost:' + os.getenv('PORT', '8501') + '/_stcore/health')"]
CMD ["sh", "-c", "streamlit run streamlit_app.py --server.address=0.0.0.0 --server.port=${PORT:-8501}"]
