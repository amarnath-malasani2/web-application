from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import boto3
import asyncio
import uuid
import os
import requests
from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION

app = FastAPI()

# Initialize AWS Transcribe and S3 clients
transcribe_client = boto3.client(
    "transcribe",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

BUCKET_NAME = "your-bucket-name"  # Replace with your S3 bucket name

@app.websocket("/audio")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected")

    audio_chunks = []
    try:
        while True:
            data = await websocket.receive_bytes()
            audio_chunks.append(data)
    except WebSocketDisconnect:
        print("Client disconnected")

    # Save the received audio data to a file
    audio_file_path = f"/tmp/{uuid.uuid4()}.webm"
    with open(audio_file_path, 'wb') as audio_file:
        audio_file.write(b''.join(audio_chunks))

    # Convert the audio file to a format supported by AWS Transcribe (e.g., WAV)
    wav_file_path = audio_file_path.replace('.webm', '.wav')
    os.system(f"ffmpeg -i {audio_file_path} {wav_file_path}")

    # Upload the audio file to S3
    s3_client.upload_file(wav_file_path, BUCKET_NAME, os.path.basename(wav_file_path))
    s3_uri = f"s3://{BUCKET_NAME}/{os.path.basename(wav_file_path)}"

    # Start the transcription job
    transcript = await process_audio(s3_uri)
    await websocket.send_text(transcript)

    # Clean up temporary files
    os.remove(audio_file_path)
    os.remove(wav_file_path)

async def process_audio(s3_uri):
    job_name = f"transcription-job-{uuid.uuid4()}"
    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": s3_uri},
        MediaFormat="wav",
        LanguageCode="en-US",
    )

    while True:
        status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        if status["TranscriptionJob"]["TranscriptionJobStatus"] in ["COMPLETED", "FAILED"]:
            break
        await asyncio.sleep(2)

    if status["TranscriptionJob"]["TranscriptionJobStatus"] == "COMPLETED":
        transcript_url = status["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
        transcript_data = requests.get(transcript_url).json()
        return transcript_data["results"]["transcripts"][0]["transcript"]

    return "Error in transcription"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
