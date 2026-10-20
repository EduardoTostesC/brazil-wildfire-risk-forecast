FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose ports for API (8000) and Streamlit (8501)
EXPOSE 8000 8501

# Default: run the API
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

