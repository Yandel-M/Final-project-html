# Use the official Python image as a base for stability and size optimization
FROM python:3.11-slim

# Set environment variables for non-buffered output and Flask config
ENV PYTHONUNBUFFERED 1
ENV FLASK_APP app.py
ENV FLASK_RUN_HOST 0.0.0.0
ENV FLASK_DEBUG 0

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files into the working directory
COPY . /app

# Expose the default port for Flask
EXPOSE 5000

# Fix: Define the command to run the application using the Python interpreter,
# explicitly running 'flask' as a module to ensure it's found.
CMD ["python", "-m", "flask", "run"]