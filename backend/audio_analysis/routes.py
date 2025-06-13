from flask import Blueprint, request, jsonify
from .diarization import ExamAudioDiarizer
import os
import logging
from pydub import AudioSegment

logger = logging.getLogger(__name__)

audio_analysis = Blueprint('audio_analysis', __name__)
diarizer = ExamAudioDiarizer()

@audio_analysis.route('/analyze-exam-audio', methods=['POST'])
def analyze_exam_audio():
    """
    Analyze exam audio file for speaker diarization
    """
    try:
        logger.info("Received request for audio analysis")
        
        if 'audio_file' not in request.files:
            logger.error("No audio file in request")
            return jsonify({
                'success': False,
                'error': 'No audio file provided'
            }), 400
            
        audio_file = request.files['audio_file']
        if not audio_file.filename:
            logger.error("Empty filename in request")
            return jsonify({
                'success': False,
                'error': 'No selected file'
            }), 400
            
        logger.info(f"Processing audio file: {audio_file.filename}")
            
        # Save the uploaded file temporarily
        temp_dir = 'temp'
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, audio_file.filename)
        audio_file.save(temp_path)
        logger.info(f"Saved temporary file at: {temp_path}")
        
        # If the file is .webm, convert to .wav for processing
        if temp_path.endswith('.webm'):
            logger.info("Converting WebM to WAV format")
            wav_path = temp_path.rsplit('.', 1)[0] + '.wav'
            try:
                audio = AudioSegment.from_file(temp_path, format='webm')
                audio.export(wav_path, format='wav')
                logger.info(f"Successfully converted to WAV: {wav_path}")
                os.remove(temp_path)  # Remove the .webm temp file
                temp_path = wav_path
            except Exception as e:
                logger.error(f"Error converting WebM to WAV: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': f'Error converting audio format: {str(e)}'
                }), 500
        
        # Process the audio file
        logger.info("Starting audio diarization process")
        results = diarizer.process_exam_audio(temp_path)
        logger.info(f"Diarization results: {results}")
        
        # Clean up temporary file
        try:
            os.remove(temp_path)
            logger.info("Cleaned up temporary file")
        except Exception as e:
            logger.warning(f"Error cleaning up temporary file: {str(e)}")
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Error processing exam audio: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 