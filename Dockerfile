FROM python:3.9-slim

WORKDIR /app

# Clear proxy environment variables to prevent errors with OpenAI client
ENV HTTP_PROXY=""
ENV HTTPS_PROXY=""
ENV http_proxy=""
ENV https_proxy=""
ENV no_proxy="*"
ENV NO_PROXY="*"

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install openai==1.55.3 httpx==0.27.2 --force-reinstall --quiet

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/static /app/data /app/logs && \
    chmod 777 /app/data /app/logs

# Expose port
EXPOSE 7777
