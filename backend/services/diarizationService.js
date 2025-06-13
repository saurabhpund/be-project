const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const diarizeAudio = async (audioPath) => {
    console.log('Starting diarization for:', audioPath);
    
    // Check if file exists
    if (!fs.existsSync(audioPath)) {
        console.error('Audio file not found:', audioPath);
        throw new Error('Audio file not found');
    }

    // Get file stats
    const stats = fs.statSync(audioPath);
    console.log('Audio file stats:', {
        size: stats.size,
        created: stats.birthtime,
        modified: stats.mtime
    });

    return new Promise((resolve, reject) => {
        const pythonProcess = spawn('python', [
            path.join(__dirname, '../diarization.py'),
            audioPath
        ]);

        let outputData = '';
        let errorData = '';

        pythonProcess.stdout.on('data', (data) => {
            const output = data.toString();
            console.log('Python stdout:', output);
            outputData += output;
        });

        pythonProcess.stderr.on('data', (data) => {
            const error = data.toString();
            console.error('Python stderr:', error);
            errorData += error;
        });

        pythonProcess.on('close', (code) => {
            console.log('Python process exited with code:', code);
            
            if (code !== 0) {
                console.error('Diarization failed with error:', errorData);
                reject(new Error(`Diarization failed: ${errorData}`));
                return;
            }

            try {
                const segments = JSON.parse(outputData);
                console.log('Parsed segments:', segments);
                
                if (!segments || segments.length === 0) {
                    console.warn('No segments detected in audio');
                    resolve([]);
                    return;
                }

                // Log segment details
                segments.forEach((segment, index) => {
                    console.log(`Segment ${index + 1}:`, {
                        start: segment.start,
                        end: segment.end,
                        speaker: segment.speaker,
                        duration: segment.end - segment.start
                    });
                });

                resolve(segments);
            } catch (error) {
                console.error('Error parsing diarization output:', error);
                console.error('Raw output:', outputData);
                reject(new Error('Failed to parse diarization output'));
            }
        });
    });
};

module.exports = {
    diarizeAudio
}; 