import os
import numpy as np
import librosa
from .diarization_core.voice_detector import VoiceDetector
from .diarization_core.feature_extractor import FeatureExtractor
from .diarization_core.speaker_diarization import SpeakerDiarization
import logging

logger = logging.getLogger(__name__)

class ExamAudioDiarizer:
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self.voice_detector = VoiceDetector(sample_rate=sample_rate)
        self.feature_extractor = FeatureExtractor(sample_rate=sample_rate)
        self.speaker_diarizer = SpeakerDiarization(num_speakers=2)  # Assuming 2 speakers (student and proctor)
        logger.info(f"Initialized ExamAudioDiarizer with sample_rate={sample_rate}")
        
    def process_exam_audio(self, audio_file_path):
        """
        Process exam audio file to detect and separate speakers
        
        Args:
            audio_file_path: Path to the exam audio file
            
        Returns:
            dict: Dictionary containing diarization results with speaker segments
        """
        try:
            logger.info(f"Starting to process audio file: {audio_file_path}")
            
            # Load audio file with original sample rate
            logger.info("Loading audio file with librosa")
            audio_data, sr = librosa.load(audio_file_path, sr=None)  # Load with original sample rate
            logger.info(f"Loaded audio: duration={len(audio_data)/sr:.2f}s, sample_rate={sr}Hz")
            
            # Preprocess audio
            logger.info("Preprocessing audio")
            # Normalize audio
            audio_data = librosa.util.normalize(audio_data)
            # Apply pre-emphasis filter
            audio_data = librosa.effects.preemphasis(audio_data)
            # Resample to target rate
            if sr != self.sample_rate:
                logger.info(f"Resampling from {sr}Hz to {self.sample_rate}Hz")
                audio_data = librosa.resample(audio_data, orig_sr=sr, target_sr=self.sample_rate)
            
            # Detect voice segments
            logger.info("Starting voice detection")
            voice_segments = self.voice_detector.detect_voice_segments(audio_data)
            logger.info(f"Detected {len(voice_segments)} voice segments")
            
            if not voice_segments:
                logger.warning("No voice segments detected in the audio")
                return {
                    "success": False,
                    "error": "No voice segments detected in the audio"
                }
            
            # Extract features from segments
            logger.info("Starting feature extraction")
            features_list = self.feature_extractor.extract_features_from_segments(
                audio_data, voice_segments, self.sample_rate
            )
            logger.info(f"Extracted features from {len(features_list)} segments")
            
            if not features_list:
                logger.warning("No features could be extracted from the voice segments")
                return {
                    "success": False,
                    "error": "No features could be extracted from the voice segments"
                }
            
            # Perform speaker diarization
            logger.info("Starting speaker diarization")
            diarized_segments = self.speaker_diarizer.diarize(features_list)
            logger.info(f"Diarized {len(diarized_segments)} segments")
            
            if not diarized_segments:
                logger.warning("No segments were diarized")
                return {
                    "success": False,
                    "error": "No segments were diarized"
                }
            
            # Merge consecutive segments from same speaker
            logger.info("Merging consecutive segments")
            merged_segments = self.speaker_diarizer.merge_consecutive_segments(diarized_segments)
            logger.info(f"Merged into {len(merged_segments)} segments")
            
            # Format results for visualization
            results = {
                "success": True,
                "segments": [
                    {
                        "speaker": f"Speaker {segment['speaker']}",
                        "start": segment['start_time'],
                        "end": segment['end_time'],
                        "duration": segment['end_time'] - segment['start_time']
                    }
                    for segment in merged_segments
                ],
                "total_duration": sum(segment['end_time'] - segment['start_time'] 
                                    for segment in merged_segments)
            }
            
            logger.info(f"Successfully processed audio. Found {len(results['segments'])} segments")
            return results
            
        except Exception as e:
            logger.error(f"Error in exam audio diarization: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            } 