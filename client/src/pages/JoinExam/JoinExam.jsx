import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const JoinExam = () => {
  const [examId, setExamId] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      // Get the token from localStorage
      const token = localStorage.getItem('token');
      if (!token) {
        setError('Please login first');
        return;
      }

      // Make the request to connect to the exam
      const response = await axios.post(
        'http://192.168.1.33:5000/exam/connect',
        {
          token,
          examId
        },
        {
          withCredentials: true,
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (response.data.success) {
        // Store the exam token
        localStorage.setItem('examToken', response.data.examToken);
        // Navigate to the exam page
        navigate(`/exam/${examId}`);
      } else {
        setError(response.data.message || 'Failed to join exam');
      }
    } catch (err) {
      console.error('Error joining exam:', err);
      setError(err.response?.data?.message || 'Failed to join exam. Please try again.');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Join Exam
          </h2>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="exam-id" className="sr-only">
                Exam ID
              </label>
              <input
                id="exam-id"
                name="examId"
                type="text"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md rounded-b-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                placeholder="Enter Exam ID"
                value={examId}
                onChange={(e) => setExamId(e.target.value)}
              />
            </div>
          </div>

          {error && (
            <div className="text-red-500 text-sm text-center">{error}</div>
          )}

          <div>
            <button
              type="submit"
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Join Exam
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default JoinExam; 