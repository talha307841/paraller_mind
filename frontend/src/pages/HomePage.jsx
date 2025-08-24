import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { History, Brain, Search, Upload } from 'lucide-react';
import AudioRecorder from '../components/AudioRecorder';

const HomePage = () => {
  const [recentUpload, setRecentUpload] = useState(null);

  const handleUploadComplete = (uploadData) => {
    setRecentUpload(uploadData);
  };

  return (
    <div className="max-w-6xl mx-auto">
      {/* Hero Section */}
      <div className="text-center mb-12">
        <h1 className="text-5xl font-bold text-gray-800 mb-4">
          Welcome to <span className="text-blue-600">Parallel Mind</span>
        </h1>
        <p className="text-xl text-gray-600 max-w-3xl mx-auto">
          Advanced AI-powered conversation analysis that records, transcribes, and understands your conversations 
          with intelligent speaker diarization and semantic search capabilities.
        </p>
      </div>

      {/* Feature Grid */}
      <div className="grid md:grid-cols-3 gap-8 mb-12">
        <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-200 text-center">
          <div className="bg-blue-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
            <Upload className="w-8 h-8 text-blue-600" />
          </div>
          <h3 className="text-xl font-semibold text-gray-800 mb-2">Smart Recording</h3>
          <p className="text-gray-600">
            Record conversations with high-quality audio capture and automatic processing
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-200 text-center">
          <div className="bg-green-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
            <Brain className="w-8 h-8 text-green-600" />
          </div>
          <h3 className="text-xl font-semibold text-gray-800 mb-2">AI Analysis</h3>
          <p className="text-gray-600">
            Advanced transcription, speaker identification, and intelligent conversation insights
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-200 text-center">
          <div className="bg-purple-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
            <Search className="w-8 h-8 text-purple-600" />
          </div>
          <h3 className="text-xl font-semibold text-gray-800 mb-2">Semantic Search</h3>
          <p className="text-gray-600">
            Find specific topics and conversations using AI-powered semantic search
          </p>
        </div>
      </div>

      {/* Main Recording Section */}
      <div className="mb-12">
        <AudioRecorder onUploadComplete={handleUploadComplete} />
      </div>

      {/* Recent Upload Status */}
      {recentUpload && (
        <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-200 mb-8">
          <div className="text-center">
            <h3 className="text-xl font-semibold text-gray-800 mb-2">
              🎉 Upload Successful!
            </h3>
            <p className="text-gray-600 mb-4">
              Your conversation is now being processed. This may take a few minutes.
            </p>
            <div className="bg-blue-50 p-4 rounded-lg">
              <p className="text-blue-800">
                <strong>Conversation ID:</strong> {recentUpload.conversation_id}
              </p>
              <p className="text-blue-800">
                <strong>Status:</strong> {recentUpload.status}
              </p>
            </div>
            <div className="mt-4 space-x-4">
              <Link
                to={`/conversation/${recentUpload.conversation_id}`}
                className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Search className="w-4 h-4 mr-2" />
                View Progress
              </Link>
              <Link
                to="/history"
                className="inline-flex items-center px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
              >
                <History className="w-4 h-4 mr-2" />
                View All Conversations
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid md:grid-cols-2 gap-6">
        <Link
          to="/history"
          className="bg-white p-6 rounded-xl shadow-lg border border-gray-200 hover:border-blue-300 transition-all hover:shadow-xl"
        >
          <div className="flex items-center space-x-4">
            <div className="bg-blue-100 p-3 rounded-lg">
              <History className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-800">Conversation History</h3>
              <p className="text-gray-600">View and manage all your recorded conversations</p>
            </div>
          </div>
        </Link>

        <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-200">
          <div className="flex items-center space-x-4">
            <div className="bg-green-100 p-3 rounded-lg">
              <Brain className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-800">AI Insights</h3>
              <p className="text-gray-600">Get summaries and suggested replies for your conversations</p>
            </div>
          </div>
        </div>
      </div>

      {/* How It Works */}
      <div className="mt-16 bg-gray-50 p-8 rounded-xl">
        <h2 className="text-3xl font-bold text-gray-800 text-center mb-8">
          How It Works
        </h2>
        <div className="grid md:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="bg-blue-600 text-white w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">
              1
            </div>
            <h3 className="font-semibold text-gray-800 mb-2">Record</h3>
            <p className="text-gray-600 text-sm">
              Record your conversation using the microphone
            </p>
          </div>
          <div className="text-center">
            <div className="bg-blue-600 text-white w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">
              2
            </div>
            <h3 className="font-semibold text-gray-800 mb-2">Process</h3>
            <p className="text-gray-600 text-sm">
              AI processes audio for transcription and speaker identification
            </p>
          </div>
          <div className="text-center">
            <div className="bg-blue-600 text-white w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">
              3
            </div>
            <h3 className="font-semibold text-gray-800 mb-2">Analyze</h3>
            <p className="text-gray-600 text-sm">
              Generate embeddings and enable semantic search
            </p>
          </div>
          <div className="text-center">
            <div className="bg-blue-600 text-white w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">
              4
            </div>
            <h3 className="font-semibold text-gray-800 mb-2">Insights</h3>
            <p className="text-gray-600 text-sm">
              Get summaries and AI-powered conversation insights
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
