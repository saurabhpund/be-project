import React, { useState, useEffect } from 'react';
import { FaPlay, FaPause, FaFileAlt, FaMicrophone } from 'react-icons/fa';

const ExamMonitoring = ({ examId, username }) => {
  const [monitoringData, setMonitoringData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedAudio, setSelectedAudio] = useState(null);
  const [diarizationResults, setDiarizationResults] = useState(null);
  const [isDiarizing, setIsDiarizing] = useState(false);
  const BASE_URL = process.env.REACT_APP_BASE_URL;

  useEffect(() => {
    fetchMonitoringData();
  }, [examId, username]);

  const fetchMonitoringData = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `${BASE_URL}/exam/monitoring-data?examId=${examId}&username=${username}`
      );
      const data = await response.json();
      
      if (data.success) {
        setMonitoringData(data);
      } else {
        setError(data.message);
      }
    } catch (err) {
      setError('Failed to fetch monitoring data');
    } finally {
      setLoading(false);
    }
  };

  const handleRunDiarization = async (audioPath) => {
    try {
      setIsDiarizing(true);
      setSelectedAudio(audioPath);
      
      const response = await fetch(`${BASE_URL}/run-diarization`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          examId,
          username,
          audioPath,
        }),
      });
      
      const data = await response.json();
      if (data.success) {
        setDiarizationResults(data.segments);
      } else {
        setError(data.message);
      }
    } catch (err) {
      setError('Failed to run diarization');
    } finally {
      setIsDiarizing(false);
    }
  };

  if (loading) {
    return <div className="p-4">Loading monitoring data...</div>;
  }

  if (error) {
    return <div className="p-4 text-red-600">{error}</div>;
  }

  return (
    <div className="space-y-6">
      {/* Keylogs Section */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center">
          <FaFileAlt className="mr-2" />
          Keylogs
        </h3>
        {monitoringData?.keylogs?.length > 0 ? (
          <div className="space-y-4">
            {monitoringData.keylogs.map((keylog, index) => (
              <div key={index} className="border rounded p-3">
                <div className="text-sm text-gray-500 mb-2">
                  {new Date(keylog.timestamp).toLocaleString()}
                </div>
                <pre className="bg-gray-50 p-2 rounded text-sm overflow-x-auto">
                  {keylog.content}
                </pre>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No keylogs available</p>
        )}
      </div>

      {/* Audio Recordings Section */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center">
          <FaMicrophone className="mr-2" />
          Audio Recordings
        </h3>
        {monitoringData?.audio_recordings?.length > 0 ? (
          <div className="space-y-4">
            {monitoringData.audio_recordings.map((recording, index) => (
              <div key={index} className="border rounded p-3">
                <div className="flex justify-between items-center mb-2">
                  <div className="text-sm text-gray-500">
                    {new Date(recording.timestamp).toLocaleString()}
                  </div>
                  <button
                    onClick={() => handleRunDiarization(recording.s3_path)}
                    disabled={isDiarizing}
                    className={`px-3 py-1 rounded text-sm ${
                      isDiarizing && selectedAudio === recording.s3_path
                        ? 'bg-gray-300'
                        : 'bg-blue-500 text-white hover:bg-blue-600'
                    }`}
                  >
                    {isDiarizing && selectedAudio === recording.s3_path
                      ? 'Processing...'
                      : 'Run Diarization'}
                  </button>
                </div>
                <audio controls className="w-full">
                  <source src={recording.url} type="audio/webm" />
                  Your browser does not support the audio element.
                </audio>
                
                {/* Diarization Results */}
                {diarizationResults && selectedAudio === recording.s3_path && (
                  <div className="mt-3">
                    <h4 className="font-medium mb-2">Diarization Results:</h4>
                    <div className="space-y-2">
                      {diarizationResults.map((segment, idx) => (
                        <div key={idx} className="text-sm">
                          <span className="font-medium">Speaker {segment.speaker}:</span>{' '}
                          {segment.start.toFixed(2)}s - {segment.end.toFixed(2)}s
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No audio recordings available</p>
        )}
      </div>
    </div>
  );
};

export default ExamMonitoring; 