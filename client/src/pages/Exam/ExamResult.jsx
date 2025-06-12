import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ExamMonitoring from '../../Components/ExamMonitoring';

const ExamResult = () => {
  const { examId, username } = useParams();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const BASE_URL = process.env.REACT_APP_BASE_URL;
  const navigate = useNavigate();

  useEffect(() => {
    fetchExamResult();
  }, [examId, username]);

  const fetchExamResult = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `${BASE_URL}/exam/result?examId=${examId}&username=${username}`
      );
      const data = await response.json();
      
      if (data.success) {
        setResult(data.result);
      } else {
        setError(data.message);
      }
    } catch (err) {
      setError('Failed to fetch exam result');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-4">Loading exam result...</div>;
  }

  if (error) {
    return <div className="p-4 text-red-600">{error}</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Exam Result Header */}
        <div className="bg-white rounded-lg shadow p-6">
          <h1 className="text-2xl font-bold mb-4">Exam Result</h1>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-gray-600">Exam Name</p>
              <p className="font-medium">{result.examName}</p>
            </div>
            <div>
              <p className="text-gray-600">Score</p>
              <p className="font-medium">{result.score} / {result.maxScore}</p>
            </div>
            <div>
              <p className="text-gray-600">Duration</p>
              <p className="font-medium">{result.examDuration} minutes</p>
            </div>
            <div>
              <p className="text-gray-600">Submitted At</p>
              <p className="font-medium">
                {new Date(result.submittedAt).toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        {/* Monitoring Data */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4">Exam Monitoring Data</h2>
          <ExamMonitoring examId={examId} username={username} />
        </div>

        {/* Back Button */}
        <div className="flex justify-end">
          <button
            onClick={() => navigate(-1)}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          >
            Back
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExamResult; 