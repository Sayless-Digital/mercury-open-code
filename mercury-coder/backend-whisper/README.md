# Mercury Whisper Service

Minimal FastAPI service for Whisper audio transcription.

## Features

- 🎙️ Audio transcription using OpenAI Whisper
- 📦 6 model sizes (tiny to large-v3)
- ⬇️ Model download with progress streaming
- 🗑️ Model management (list, download, delete)

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
# Development
uvicorn main:app --reload --port 8001

# Production
python main.py
```

## Environment Variables

Create a `.env` file:

```bash
PORT=8001
HOST=127.0.0.1
WHISPER_MODEL=base
```

## API Endpoints

### GET /health
Health check

### GET /api/whisper/models
List available Whisper models and their download status

### POST /api/whisper/download
Download a Whisper model (SSE stream with progress)

Body: `{"model_id": "base"}`

### DELETE /api/whisper/models/{model_id}
Delete a downloaded model

### POST /api/whisper/transcribe
Transcribe audio file

Form data:
- `file`: Audio file (webm, wav, mp3, etc.)
- `model_id`: (Optional) Model to use, defaults to env WHISPER_MODEL

## Models

| Model | Size | Description |
|-------|------|-------------|
| tiny | ~39 MB | Fastest, least accurate |
| base | ~74 MB | Good balance (default) |
| small | ~244 MB | Better accuracy |
| medium | ~769 MB | Good accuracy |
| large-v2 | ~1550 MB | Best accuracy |
| large-v3 | ~1550 MB | Latest, best accuracy |

Models are cached in `~/.cache/whisper/`

## Usage Example

```python
import requests

# List models
response = requests.get('http://localhost:8001/api/whisper/models')
print(response.json())

# Transcribe audio
with open('audio.webm', 'rb') as f:
    files = {'file': f}
    response = requests.post(
        'http://localhost:8001/api/whisper/transcribe',
        files=files
    )
    print(response.json()['text'])
```
