FROM python:3.9

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app

COPY ./app/ /app

# Install Python dependencies
RUN pip install --no-cache-dir fastapi uvicorn boto3 websockets

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
