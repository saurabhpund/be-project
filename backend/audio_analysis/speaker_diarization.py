from flask import request, jsonify
from werkzeug.utils import secure_filename
import datetime
import os
import jwt
from pydub import AudioSegment
from pyannote.audio import Pipeline
from dotenv import load_dotenv
from database import init_db
import logging
import torch
import numpy as np
import soundfile as sf

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

db_data = init_db()
db_collection = db_data['db_collection']

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
                # Try loading with pydub as fallback
                audio = AudioSegment.from_file(audio_path)
                logger.info(f"Audio loaded with pydub: duration={len(audio)/1000}s, channels={audio.channels}")
            except Exception as e:
                logger.error(f"Failed to load audio with both soundfile and pydub: {str(e)}")
                return False
                
        return True
        
    except Exception as e:
        logger.error(f"Error validating audio: {str(e)}", exc_info=True)
        return False

def analyze_speakers_in_5min_windows(audio_path):
    try:
        logger.info(f"Starting speaker analysis for: {audio_path}")
        
        # Validate audio file
        if not validate_audio(audio_path):
            logger.error("Audio validation failed")
            return []
            
        # Load the pipeline
        logger.info("Loading diarization pipeline...")
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=os.getenv("HUGGINGFACE_TOKEN")
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
        
        # Get audio duration
        audio = AudioSegment.from_file(audio_path)
        total_duration_sec = len(audio) / 1000
        window_size = 5 * 60  # 5 minutes in seconds
        
        # Process in 5-minute windows
        windows = []
        for start_time in range(0, int(total_duration_sec), window_size):
            end_time = min(start_time + window_size, total_duration_sec)
            speakers_in_window = set()
            
            # Get segments in this window
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segment, _, speaker = turn
                seg_start = segment.start
                seg_end = segment.end
                
                # Check if segment overlaps with window
                if seg_end < start_time or seg_start > end_time:
                    continue
                    
                speakers_in_window.add(speaker)
                logger.info(f"Found speaker {speaker} in window {start_time}-{end_time}")
            
            window_data = {
                "start": str(datetime.timedelta(seconds=start_time)),
                "end": str(datetime.timedelta(seconds=end_time)),
                "speaker_count": len(speakers_in_window),
                "speakers": list(speakers_in_window)
            }
            windows.append(window_data)
            logger.info(f"Window {start_time}-{end_time}: {window_data}")
            
        logger.info(f"Analysis complete. Found {len(windows)} windows with speakers")
        return windows
        
    except Exception as e:
        logger.error(f"Error during speaker analysis: {str(e)}", exc_info=True)
        return []

def run_speaker_analysis_and_store(audio_path, exam_id, username, filename):
    logger.info(f"Starting speaker analysis for {username}, examId {exam_id}, file: {filename}")
    
    try:
        # Run the analysis
        analysis_result = analyze_speakers_in_5min_windows(audio_path)
        
        if not analysis_result:
            logger.warning(f"No speaker analysis results for {filename}")
            return
            
        # Store the results
        result = db_collection.update_one(
            {"examId": exam_id, "username": username, "recordings.file": filename},
            {"$set": {"recordings.$.analysis": analysis_result}}
        )
        
        if result.matched_count == 0:
            logger.error(f"No matching recording found for examId={exam_id}, username={username}, file={filename}")
        else:
            logger.info(f"Successfully stored speaker analysis for {filename}")
            
    except Exception as e:
        logger.error(f"Failed to analyze audio {filename}: {str(e)}", exc_info=True)
