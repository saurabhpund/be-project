// AudioRec.js (updated)
import React, { useImperativeHandle, useRef, useEffect, forwardRef } from "react";

const AudioRecorder = forwardRef(({ examId, token }, ref) => {
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const [recording, setRecording] = React.useState(false);
  const [error, setError] = React.useState(null);
  const BASE_URL = process.env.REACT_APP_BASE_URL;

  useEffect(() => {
    async function setupRecorder() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
          audio: {
            channelCount: 1,
            sampleRate: 16000,
            sampleSize: 16
          } 
        });
        
        const recorder = new MediaRecorder(stream, {
          mimeType: 'audio/webm;codecs=opus',
          audioBitsPerSecond: 128000
        });
        
        recorder.ondataavailable = (event) => {
          if (event.data && event.data.size > 0) {
            audioChunksRef.current.push(event.data);
          }
        };
        
        mediaRecorderRef.current = recorder;
        startRecording();
      } catch (err) {
        console.error("Error setting up audio recorder:", err);
        setError("Failed to access microphone. Please check permissions.");
      }
    }
    
    setupRecorder();

    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  const startRecording = () => {
    if (mediaRecorderRef.current) {
      audioChunksRef.current = [];
      mediaRecorderRef.current.start(1000); // Collect data every second
      setRecording(true);
      setError(null);
    }
  };

  const stopRecording = () => {
    return new Promise((resolve) => {
      if (mediaRecorderRef.current && recording) {
        mediaRecorderRef.current.onstop = async () => {
          try {
            // Create a Blob from all collected audio chunks
            const webmBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
            
            // Convert WebM to WAV using AudioContext
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const arrayBuffer = await webmBlob.arrayBuffer();
            const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
            
            // Create WAV file
            const wavBlob = await audioBufferToWav(audioBuffer);
            resolve(wavBlob);
          } catch (err) {
            console.error("Error converting audio:", err);
            setError("Failed to process audio recording");
            resolve(null);
          }
        };
        mediaRecorderRef.current.stop();
        setRecording(false);
      } else {
        resolve(null);
      }
    });
  };

  // Convert AudioBuffer to WAV format
  const audioBufferToWav = async (buffer) => {
    const numChannels = buffer.numberOfChannels;
    const sampleRate = buffer.sampleRate;
    const format = 1; // PCM
    const bitDepth = 16;
    
    const bytesPerSample = bitDepth / 8;
    const blockAlign = numChannels * bytesPerSample;
    
    const dataLength = buffer.length * numChannels * bytesPerSample;
    const bufferLength = 44 + dataLength;
    
    const arrayBuffer = new ArrayBuffer(bufferLength);
    const view = new DataView(arrayBuffer);
    
    // Write WAV header
    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + dataLength, true);
    writeString(view, 8, 'WAVE');
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, format, true);
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * blockAlign, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bitDepth, true);
    writeString(view, 36, 'data');
    view.setUint32(40, dataLength, true);
    
    // Write audio data
    const offset = 44;
    const channelData = [];
    for (let i = 0; i < numChannels; i++) {
      channelData.push(buffer.getChannelData(i));
    }
    
    let pos = 0;
    while (pos < buffer.length) {
      for (let i = 0; i < numChannels; i++) {
        const sample = Math.max(-1, Math.min(1, channelData[i][pos]));
        const value = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
        view.setInt16(offset + (pos * blockAlign) + (i * bytesPerSample), value, true);
      }
      pos++;
    }
    
    return new Blob([arrayBuffer], { type: 'audio/wav' });
  };

  const writeString = (view, offset, string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };

  const uploadRecording = async () => {
    try {
      const wavBlob = await stopRecording();
      if (!wavBlob) {
        throw new Error("No audio data available");
      }

      const formData = new FormData();
      formData.append("audio", wavBlob, "recording.wav");
      formData.append("examId", examId);
      formData.append("token", token);

      const response = await fetch(`${BASE_URL}/upload/audio`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log("Audio recording uploaded:", result);
      return result;
    } catch (err) {
      console.error("Error uploading recording:", err);
      setError("Failed to upload audio recording");
      throw err;
    }
  };

  useImperativeHandle(ref, () => ({
    uploadRecording,
  }));

  return (
    <div>
      <p className="text-gray-500 font-semibold">
        {recording ? "Recording Active" : "Recording Stopped"}
      </p>
      {error && <p className="text-red-500 text-sm">{error}</p>}
    </div>
  );
});

export default AudioRecorder;
