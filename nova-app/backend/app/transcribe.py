import boto3

def transcribe_audio(audio_data):
    client = boto3.client('transcribe', region_name='us-east-1')
    
    response = client.start_transcription_job(
        TranscriptionJobName="LiveTranscription",
        LanguageCode="en-US",
        MediaFormat="webm",
        Media={"MediaFileUri": "s3://amarnath-malasani-nova-audio-bucket/audio.webm"}
    )
    
    return response
