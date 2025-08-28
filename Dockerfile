# Use official Python slim image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose the port (optional, Cloud Run يستخدم متغير PORT)
EXPOSE 8080

# Run the app
CMD ["python", "main.py"]
