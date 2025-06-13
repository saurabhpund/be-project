import sys
import json
import torch
import numpy as np
from pyannote.audio import Pipeline
import logging
import os
import soundfile as sf
import librosa

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_audio(audio_path):
    """Validate audio file format and properties"""
    try:
        # Check file exists
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return False
            
        # Get file stats
        file_stats = os.stat(audio_path)
        logger.info(f"Audio file stats: size={file_stats.st_size}, modified={file_stats.st_mtime}")
        
        # Check if file is empty
        if file_stats.st_size == 0:
            logger.error("Audio file is empty")
            return False
            
        # Load audio file to check format
        try:
            # Try loading with soundfile first
            audio_data, sample_rate = sf.read(audio_path)
            logger.info(f"Audio loaded with soundfile: shape={audio_data.shape}, sample_rate={sample_rate}")
        except Exception as e:
            logger.warning(f"Failed to load with soundfile: {str(e)}")
            try:
                # Try loading with librosa as fallback
                audio_data, sample_rate = librosa.load(audio_path, sr=None)
                logger.info(f"Audio loaded with librosa: shape={audio_data.shape}, sample_rate={sample_rate}")
            except Exception as e:
                logger.error(f"Failed to load audio with both soundfile and librosa: {str(e)}")
                return False
                
        # Check audio properties
        if len(audio_data.shape) > 1:
            logger.info(f"Audio is {audio_data.shape[1]}-channel")
            # Convert to mono if needed
            if audio_data.shape[1] > 1:
                audio_data = np.mean(audio_data, axis=1)
                logger.info("Converted to mono")
                
        # Check audio levels
        rms = np.sqrt(np.mean(np.square(audio_data)))
        logger.info(f"Audio RMS level: {rms}")
        if rms < 0.01:
            logger.warning("Audio level is very low, might be too quiet")
            
        # Check for silence
        is_silent = np.all(np.abs(audio_data) < 0.01)
        if is_silent:
            logger.warning("Audio appears to be silent")
            
        return True
        
    except Exception as e:
        logger.error(f"Error validating audio: {str(e)}", exc_info=True)
        return False

def diarize_audio(audio_path):
    try:
        logger.info(f"Starting diarization for: {audio_path}")
        
        # Validate audio file
        if not validate_audio(audio_path):
            logger.error("Audio validation failed")
            return []
            
        # Load the pipeline
        logger.info("Loading diarization pipeline...")
        hf_token = os.getenv("HUGGINGFACE_TOKEN")
        if not hf_token:
            logger.error("HUGGINGFACE_TOKEN environment variable not set")
            return []
            
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token
        )
        
        # Move pipeline to GPU if available
        if torch.cuda.is_available():
            logger.info("Using GPU for diarization")
            pipeline = pipeline.to(torch.device("cuda"))
        else:
            logger.info("Using CPU for diarization")
            
        # Process the audio
        logger.info("Processing audio file...")
        diarization = pipeline(audio_path)
        
        # Convert to list of segments
        logger.info("Converting diarization to segments...")
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segment = {
                "start": turn.start,
                "end": turn.end,
                "speaker": speaker
            }
            segments.append(segment)
            logger.info(f"Detected segment: {segment}")
            
        logger.info(f"Total segments detected: {len(segments)}")
        
        if not segments:
            logger.warning("No voice segments detected in the audio")
            
        return segments
        
    except Exception as e:
        logger.error(f"Error during diarization: {str(e)}", exc_info=True)
        return []

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Please provide an audio file path"}))
        sys.exit(1)
        
    audio_path = sys.argv[1]
    segments = diarize_audio(audio_path)
    print(json.dumps(segments)) 