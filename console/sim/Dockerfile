FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY sim ./sim
COPY tests ./tests
EXPOSE 8090
CMD ["uvicorn", "sim.app:app", "--host", "0.0.0.0", "--port", "8090"]
