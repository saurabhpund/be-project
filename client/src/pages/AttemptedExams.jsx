// ExamDashboard.jsx
import React, { useEffect, useState } from "react";

const ExamDashboard = () => {
  const [examResult, setExamResult] = useState(null);
  const [frames, setFrames] = useState([]);
  const username = localStorage.getItem("username"); // Ensure this is set at login

  // Fetch exam result
  useEffect(() => {
    async function fetchExamResult() {
      try {
        const res = await fetch(
          `http://localhost:5000/exam/result?examId=${examId}&username=${username}`
        );
        const data = await res.json();
        if (data.success) {
          setExamResult(data.result);
        } else {
          console.error("Error fetching exam result:", data.message);
        }
      } catch (err) {
        console.error("Error fetching exam result:", err);
      }
    }

    if (examId && username) {
      fetchExamResult();
    }
  }, [examId, username]);

  // Fetch captured image frames
  useEffect(() => {
    async function fetchFrames() {
      try {
        const res = await fetch(`http://localhost:5000/frames/${examId}`);
        const data = await res.json();
        if (data.success) {
          setFrames(data.frames);
        } else {
          console.error("Error fetching frames:", data.message);
        }
      } catch (err) {
        console.error("Error fetching frames:", err);
      }
    }

    if (examId) {
      fetchFrames();
    }
  }, [examId]);

  // if (!examResult) {
  //   return <div>Loading exam result...</div>;
  // }

  return (
    <div className="dashboard p-4">
      <h1 className="text-2xl font-bold mb-4">Exam Dashboard</h1>

      {/* Exam Result */}
      <div className="exam-result mb-6 border p-4 rounded shadow">
        <h2 className="text-xl font-semibold mb-2">Exam Result</h2>
        <p><strong>Exam ID:</strong> {examResult.examId}</p>
        <p><strong>Exam Name:</strong> {examResult.examName}</p>
        <p><strong>Duration:</strong> {examResult.examDuration} minutes</p>
        <p>
          <strong>Date:</strong>{" "}
          {examResult.examDate ? new Date(examResult.examDate).toLocaleDateString() : "N/A"}
        </p>
        <p>
          <strong>Exam Start Time:</strong>{" "}
          {examResult.examStartTime ? new Date(examResult.examStartTime).toLocaleString() : "N/A"}
        </p>
        <p>
          <strong>Submitted At:</strong>{" "}
          {examResult.submittedAt ? new Date(examResult.submittedAt).toLocaleString() : "N/A"}
        </p>
        <p><strong>Score:</strong> {examResult.score}</p>
        <p><strong>Max Score:</strong> {examResult.maxScore}</p>
        <div className="answers mt-4">
          <h3 className="text-lg font-semibold">Answers:</h3>
          {examResult.answers ? (
            <ul className="list-disc ml-6">
              {Object.entries(examResult.answers).map(([questionIdx, answer]) => (
                <li key={questionIdx}>
                  <strong>Question {questionIdx}:</strong> {answer}
                </li>
              ))}
            </ul>
          ) : (
            <p>No answers submitted.</p>
          )}
        </div>
      </div>

      {/* Audio Recordings */}
      <div className="audio-recordings border p-4 rounded shadow">
        <h2 className="text-xl font-semibold mb-2">Audio Recordings</h2>
        {examResult.recordings && examResult.recordings.length > 0 ? (
          <ul>
            {examResult.recordings.map((recording, index) => (
              <li key={index} className="mb-4 p-2 border rounded">
                <p>
                  <strong>Timestamp:</strong>{" "}
                  {new Date(recording.timestamp).toLocaleString()}
                </p>
                <audio controls>
                  <source
                    src={`http://localhost:5000/audio/${recording.file}`}
                    type="audio/webm"
                  />
                  Your browser does not support the audio element.
                </audio>
              </li>
            ))}
          </ul>
        ) : (
          <p>No audio recordings available.</p>
        )}
      </div>

      {/* Captured Image Frames */}
      <div className="captured-frames mt-6 border p-4 rounded shadow">
        <h2 className="text-xl font-semibold mb-2">Captured Frames</h2>
        {frames.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {frames.map((frame, index) => (
              <div key={index} className="frame border p-2 rounded shadow-sm">
                <p className="text-sm mb-1">
                  <strong>Timestamp:</strong>{" "}
                  {new Date(frame.timestamp).toLocaleString()}
                </p>
                <img
                  src={
                    frame.image.startsWith("data:")
                      ? frame.image
                      : `data:image/jpeg;base64,${frame.image}`
                  }
                  alt={`Frame ${index}`}
                  className="w-full h-auto rounded"
                />
              </div>
            ))}
          </div>
        ) : (
          <p>No captured frames available.</p>
        )}
      </div>
    </div>
  );
};

export default ExamDashboard;
