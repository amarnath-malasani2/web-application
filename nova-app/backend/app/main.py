from fastapi import FastAPI, WebSocket
import uvicorn
import boto3
import uuid
import os

app = FastAPI()

# Initialize the AWS Transcribe client
transcribe_client = boto3.client('transcribe', region_name='us-east-1')  # Replace with your AWS region

@app.websocket("/audio")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    audio_chunks = []
    while True:
        try:
            data = await websocket.receive_bytes()
            audio_chunks.append(data)
        except Exception as e:
            print(f"Connection closed: {e}")
            break

    # Save the received audio data to a file
    audio_file_path = f"/tmp/{uuid.uuid4()}.webm"
    with open(audio_file_path, 'wb') as audio_file:
        audio_file.write(b''.join(audio_chunks))

    # Convert the audio file to a format supported by AWS Transcribe (e.g., WAV)
    wav_file_path = audio_file_path.replace('.webm', '.wav')
    os.system(f"ffmpeg -i {audio_file_path} {wav_file_path}")

    # Start the transcription job
    job_name = f"transcription_{uuid.uuid4()}"
    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': f"file://{wav_file_path}"},
        MediaFormat='wav',
        LanguageCode='en-US'  # Replace with the appropriate language code
    )

    # Wait for the transcription job to complete
    while True:
        status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break

    if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
        transcript_url = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
        transcript_response = requests.get(transcript_url)
        transcript_text = transcript_response.json()['results']['transcripts'][0]['transcript']
        await websocket.send_text(transcript_text)
    else:
        await websocket.send_text("Transcription failed")

    # Clean up temporary files
    os.remove(audio_file_path)
    os.remove(wav_file_path)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
