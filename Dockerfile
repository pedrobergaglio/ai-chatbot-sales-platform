FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose the port the app runs on
EXPOSE 7777

# Command to run the application
CMD ["gunicorn", "--bind", "0.0.0.0:7777", "app:app"]
