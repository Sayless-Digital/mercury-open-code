"""
Mercury Whisper Service
Minimal FastAPI server for Whisper audio transcription
"""

import os
import json
import asyncio
import tempfile
import threading
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Mercury Whisper Service", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Whisper model configuration
WHISPER_MODELS = [
    {"id": "tiny", "name": "Tiny (~39 MB)", "size": "~39 MB", "description": "Fastest, least accurate"},
    {"id": "base", "name": "Base (~74 MB)", "size": "~74 MB", "description": "Good balance"},
    {"id": "small", "name": "Small (~244 MB)", "size": "~244 MB", "description": "Better accuracy"},
    {"id": "medium", "name": "Medium (~769 MB)", "size": "~769 MB", "description": "Good accuracy"},
    {"id": "large-v2", "name": "Large v2 (~1550 MB)", "size": "~1550 MB", "description": "Best accuracy"},
    {"id": "large-v3", "name": "Large v3 (~1550 MB)", "size": "~1550 MB", "description": "Latest, best accuracy"},
]

whisper_model_cache = {}
whisper_model_lock = threading.Lock()


# Pydantic models
class WhisperModelInfo(BaseModel):
    id: str
    name: str
    size: str
    description: str
    downloaded: bool = False


class WhisperModelsResponse(BaseModel):
    models: List[WhisperModelInfo]
    current_model: Optional[str] = None
    success: bool = True


class WhisperDownloadRequest(BaseModel):
    model_id: str


class WhisperTranscribeResponse(BaseModel):
    text: str
    language: Optional[str] = None
    success: bool = True


# Helper functions
def format_sse_payload(data: Dict[str, Any]) -> str:
    """Format data as Server-Sent Event payload"""
    return f"data: {json.dumps(data)}\n\n"


def check_whisper_model_downloaded(model_id: str) -> bool:
    """Check if a Whisper model is already downloaded."""
    try:
        model_path = os.path.join(os.path.expanduser("~"), ".cache", "whisper", f"{model_id}.pt")
        return os.path.exists(model_path)
    except Exception:
        return False


def get_whisper_model(model_id: str):
    """Get or load a Whisper model."""
    with whisper_model_lock:
        if model_id in whisper_model_cache:
            return whisper_model_cache[model_id]
        
        try:
            import whisper
            print(f"[Whisper] Loading model: {model_id}")
            model = whisper.load_model(model_id)
            whisper_model_cache[model_id] = model
            print(f"[Whisper] Model {model_id} loaded successfully")
            return model
        except Exception as e:
            print(f"[Whisper] Error loading model {model_id}: {e}")
            raise Exception(f"Failed to load Whisper model: {str(e)}")


# API Endpoints
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "whisper"}


@app.get("/api/whisper/models", response_model=WhisperModelsResponse)
async def get_whisper_models():
    """Get list of available Whisper models and their download status."""
    try:
        models = []
        current_model = os.getenv('WHISPER_MODEL', 'base')
        
        for model in WHISPER_MODELS:
            downloaded = check_whisper_model_downloaded(model['id'])
            models.append(WhisperModelInfo(
                id=model['id'],
                name=model['name'],
                size=model['size'],
                description=model['description'],
                downloaded=downloaded
            ))
        
        return WhisperModelsResponse(
            models=models,
            current_model=current_model,
            success=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Whisper models: {str(e)}")


@app.post("/api/whisper/download")
async def download_whisper_model_stream(request: WhisperDownloadRequest):
    """Download a Whisper model with progress streaming."""
    try:
        # Validate model ID
        model_ids = [m['id'] for m in WHISPER_MODELS]
        if request.model_id not in model_ids:
            raise HTTPException(status_code=400, detail=f"Invalid model ID. Must be one of: {', '.join(model_ids)}")
        
        # Check if already downloaded
        if check_whisper_model_downloaded(request.model_id):
            async def already_downloaded():
                yield format_sse_payload({"type": "complete", "message": f"Model {request.model_id} is already downloaded", "progress": 100})
            return StreamingResponse(already_downloaded(), media_type="text/event-stream")
        
        async def progress_generator():
            loop = asyncio.get_running_loop()
            progress_queue = asyncio.Queue()
            
            def download_with_progress():
                try:
                    import whisper
                    import sys
                    
                    # Send initial status
                    loop.call_soon_threadsafe(
                        progress_queue.put_nowait,
                        {"type": "status", "message": f"Starting download of {request.model_id}...", "progress": 0}
                    )
                    
                    # Capture stdout to monitor tqdm progress
                    class ProgressCapture:
                        def __init__(self, queue, loop):
                            self.queue = queue
                            self.loop = loop
                            self.last_percent = 0
                            self.buffer = ""
                            
                        def write(self, text):
                            self.buffer += text
                            # Look for percentage indicators from tqdm
                            if '%' in text:
                                try:
                                    # Extract percentage from tqdm output
                                    parts = text.split('%')
                                    if len(parts) > 0:
                                        percent_part = parts[0].strip().split()[-1]
                                        percent = float(percent_part)
                                        if abs(percent - self.last_percent) >= 1:  # Update every 1%
                                            self.last_percent = percent
                                            self.loop.call_soon_threadsafe(
                                                self.queue.put_nowait,
                                                {"type": "progress", "progress": int(percent), "message": f"Downloading... {int(percent)}%"}
                                            )
                                except (ValueError, IndexError):
                                    pass
                            # Still write to actual stdout
                            sys.__stdout__.write(text)
                            
                        def flush(self):
                            sys.__stdout__.flush()
                    
                    # Redirect stdout
                    old_stdout = sys.stdout
                    sys.stdout = ProgressCapture(progress_queue, loop)
                    
                    try:
                        whisper.load_model(request.model_id)
                        
                        loop.call_soon_threadsafe(
                            progress_queue.put_nowait,
                            {"type": "complete", "progress": 100, "message": f"Model {request.model_id} downloaded successfully!"}
                        )
                    finally:
                        sys.stdout = old_stdout
                        loop.call_soon_threadsafe(progress_queue.put_nowait, {"type": "done"})
                        
                except Exception as e:
                    loop.call_soon_threadsafe(
                        progress_queue.put_nowait,
                        {"type": "error", "message": str(e)}
                    )
            
            # Start download in background thread
            threading.Thread(target=download_with_progress, daemon=True).start()
            
            # Stream progress updates
            while True:
                try:
                    update = await asyncio.wait_for(progress_queue.get(), timeout=60)
                    
                    if update.get("type") == "done":
                        # Update environment variable
                        os.environ['WHISPER_MODEL'] = request.model_id
                        break
                    elif update.get("type") == "error":
                        yield format_sse_payload({"type": "error", "message": update.get("message", "Unknown error")})
                        break
                    else:
                        yield format_sse_payload(update)
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield format_sse_payload({"type": "status", "message": "Download in progress..."})
        
        return StreamingResponse(
            progress_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download model: {str(e)}")


@app.delete("/api/whisper/models/{model_id}")
async def delete_whisper_model(model_id: str):
    """Delete a Whisper model from disk."""
    try:
        # Validate model ID
        model_ids = [m['id'] for m in WHISPER_MODELS]
        if model_id not in model_ids:
            raise HTTPException(status_code=400, detail=f"Invalid model ID. Must be one of: {', '.join(model_ids)}")
        
        # Check if model is downloaded
        if not check_whisper_model_downloaded(model_id):
            raise HTTPException(status_code=404, detail=f"Model {model_id} is not downloaded")
        
        # Get model path
        model_path = os.path.join(os.path.expanduser("~"), ".cache", "whisper", f"{model_id}.pt")
        
        # Remove from cache if loaded
        with whisper_model_lock:
            if model_id in whisper_model_cache:
                del whisper_model_cache[model_id]
        
        # Delete the file
        try:
            os.remove(model_path)
            print(f"[Whisper] Deleted model: {model_id} from {model_path}")
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete model file: {str(e)}")
        
        return {"success": True, "message": f"Model {model_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete model: {str(e)}")


@app.post("/api/whisper/transcribe", response_model=WhisperTranscribeResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    model_id: Optional[str] = Form(None)
):
    """Transcribe audio file using Whisper."""
    try:
        # Use default model if not specified
        if not model_id:
            model_id = os.getenv('WHISPER_MODEL', 'base')
        
        print(f"[Transcribe] Received audio file: {file.filename}, content_type: {file.content_type}")
        print(f"[Transcribe] Using model: {model_id}")
        
        # Validate model ID
        model_ids = [m['id'] for m in WHISPER_MODELS]
        if model_id not in model_ids:
            raise HTTPException(status_code=400, detail=f"Invalid model ID. Must be one of: {', '.join(model_ids)}")
        
        # Get file extension from filename
        file_ext = os.path.splitext(file.filename or 'audio.wav')[1] or '.wav'
        print(f"[Transcribe] File extension: {file_ext}")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content_bytes = await file.read()
            tmp_file.write(content_bytes)
            tmp_path = tmp_file.name
            file_size = len(content_bytes)
        
        print(f"[Transcribe] Saved to: {tmp_path}, size: {file_size} bytes")
        
        # Minimum size check: require at least 5KB for transcription
        if file_size < 5000:  # Less than 5KB
            raise HTTPException(
                status_code=400, 
                detail=f"Audio file too small ({file_size} bytes). Minimum size: 5KB. Please record longer audio."
            )
        
        try:
            def transcribe():
                model = get_whisper_model(model_id)
                print(f"[Transcribe] Starting transcription...")
                result = model.transcribe(tmp_path, fp16=False)  # Disable fp16 for compatibility
                print(f"[Transcribe] Transcription result: {result}")
                return result
            
            # Run transcription in thread pool
            result = await asyncio.to_thread(transcribe)
            
            transcribed_text = result.get('text', '').strip()
            detected_language = result.get('language')
            
            print(f"[Transcribe] Text: '{transcribed_text}', Language: {detected_language}")
            
            if not transcribed_text:
                print("[Transcribe] WARNING: Empty transcription result")
                raise Exception("No speech detected in audio. Please try speaking louder or closer to the microphone.")
            
            return WhisperTranscribeResponse(
                text=transcribed_text,
                language=detected_language,
                success=True
            )
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
                print(f"[Transcribe] Cleaned up temp file")
            except Exception as e:
                print(f"[Transcribe] Failed to clean up temp file: {e}")
                
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Transcribe] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    host = os.getenv("HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=port)
