FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e ".[test]"
EXPOSE 8000
CMD ["uvicorn", "src.interfaces.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
