FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY exporter.py .
COPY pair.py .
COPY node_check.py .

ENV ZWAVE_WS_URL=ws://zwave-js-ui:3001
ENV METRICS_PORT=9100

EXPOSE 9100

CMD ["python", "exporter.py"]
