FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask requests \
    opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc \
    opentelemetry-instrumentation-flask opentelemetry-instrumentation-requests
COPY app.py loadgen.py ./
ENV PYTHONUNBUFFERED=1
CMD ["sh", "-c", "if [ \"$SERVICE\" = loadgen ]; then python loadgen.py; else python app.py; fi"]
