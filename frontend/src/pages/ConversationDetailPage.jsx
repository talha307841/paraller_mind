import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Clock, User, Brain, MessageSquare, FileText, Search, Loader2 } from 'lucide-react';
import axios from 'axios';

const ConversationDetailPage = () => {
  const { id } = useParams();
  const [conversation, setConversation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [suggestedReplies, setSuggestedReplies] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [generatingSummary, setGeneratingSummary] = useState(false);
  const [generatingReplies, setGeneratingReplies] = useState(false);

  useEffect(() => {
    fetchConversation();
  }, [id]);

  const fetchConversation = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/conversations/${id}`);
      setConversation(response.data);
    } catch (error) {
      console.error('Error fetching conversation:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateSummary = async () => {
    try {
      setGeneratingSummary(true);
      const response = await axios.post(`/api/conversations/${id}/summarize`);
      setSummary(response.data);
    } catch (error) {
      console.error('Error generating summary:', error);
      alert('Failed to generate summary. Please try again.');
    } finally {
      setGeneratingSummary(false);
    }
  };

  const generateSuggestedReplies = async () => {
    try {
      setGeneratingReplies(true);
      const response = await axios.post(`/api/conversations/${id}/suggest-reply`, {
        query: searchQuery || "What should I say next?"
      });
      setSuggestedReplies(response.data);
    } catch (error) {
      console.error('Error generating suggested replies:', error);
      alert('Failed to generate suggested replies. Please try again.');
    } finally {
      setGeneratingReplies(false);
    }
  };

  const searchConversation = async () => {
    if (!searchQuery.trim()) return;
    
    try {
      setSearching(true);
      const response = await axios.get(`/api/search?query=${encodeURIComponent(searchQuery)}&conversation_id=${id}`);
      setSearchResults(response.data.results);
    } catch (error) {
      console.error('Error searching conversation:', error);
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getStatusBadge = (status) => {
    const statusClasses = {
      'uploaded': 'status-uploaded',
      'processing': 'status-processing',
      'processed': 'status-processed',
      'error': 'status-error'
    };

    return (
      <span className={`status-badge ${statusClasses[status] || 'status-uploaded'}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-64">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  if (!conversation) {
    return (
      <div className="max-w-4xl mx-auto text-center">
        <h1 className="text-2xl font-bold text-gray-800 mb-4">Conversation Not Found</h1>
        <p className="text-gray-600 mb-6">The conversation you're looking for doesn't exist.</p>
        <Link to="/history" className="text-blue-600 hover:text-blue-800">
          ← Back to History
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center space-x-4 mb-4">
          <Link
            to="/history"
            className="text-blue-600 hover:text-blue-800 flex items-center space-x-2"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>Back to History</span>
          </Link>
        </div>
        
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-800 mb-2">
              Conversation: {conversation.filename}
            </h1>
            <div className="flex items-center space-x-4 text-gray-600">
              <div className="flex items-center space-x-2">
                <Clock className="w-4 h-4" />
                <span>{new Date(conversation.created_at).toLocaleString()}</span>
              </div>
              <div className="flex items-center space-x-2">
                <User className="w-4 h-4" />
                <span>{conversation.segments?.length || 0} segments</span>
              </div>
              {getStatusBadge(conversation.status)}
            </div>
          </div>
        </div>
      </div>

      {/* Search Section */}
      <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-200 mb-8">
        <h2 className="text-xl font-semibold text-gray-800 mb-4">Search Conversation</h2>
        <div className="flex space-x-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Search for specific topics or phrases..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <button
            onClick={searchConversation}
            disabled={!searchQuery.trim() || searching}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {searching ? <Loader2 className="w-5 h-5 animate-spin" /> : <Search className="w-5 h-5" />}
          </button>
        </div>
        
        {/* Search Results */}
        {searchResults.length > 0 && (
          <div className="mt-4">
            <h3 className="font-semibold text-gray-800 mb-2">Search Results:</h3>
            <div className="space-y-2">
              {searchResults.map((result, index) => (
                <div key={index} className="bg-gray-50 p-3 rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-gray-800">{result.speaker_label}</span>
                    <span className="text-sm text-gray-600">{formatTime(result.start_time)}</span>
                  </div>
                  <p className="text-gray-700 mt-1">{result.text}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* AI Insights Section */}
      <div className="grid md:grid-cols-2 gap-8 mb-8">
        {/* Summary */}
        <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-800 flex items-center space-x-2">
              <Brain className="w-5 h-5 text-green-600" />
              <span>AI Summary</span>
            </h2>
            <button
              onClick={generateSummary}
              disabled={conversation.status !== 'processed' || generatingSummary}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
            >
              {generatingSummary ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Generate'}
            </button>
          </div>
          
          {summary ? (
            <div>
              <p className="text-gray-700 mb-4">{summary.summary}</p>
              {summary.key_points && summary.key_points.length > 0 && (
                <div>
                  <h4 className="font-semibold text-gray-800 mb-2">Key Points:</h4>
                  <ul className="list-disc list-inside space-y-1 text-gray-700">
                    {summary.key_points.map((point, index) => (
                      <li key={index}>{point}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-500 italic">
              {conversation.status === 'processed' 
                ? 'Click "Generate" to create an AI summary of this conversation.'
                : 'Summary will be available once processing is complete.'
              }
            </p>
          )}
        </div>

        {/* Suggested Replies */}
        <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-800 flex items-center space-x-2">
              <MessageSquare className="w-5 h-5 text-blue-600" />
              <span>Suggested Replies</span>
            </h2>
            <button
              onClick={generateSuggestedReplies}
              disabled={conversation.status !== 'processed' || generatingReplies}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {generatingReplies ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Generate'}
            </button>
          </div>
          
          {suggestedReplies ? (
            <div>
              <div className="space-y-3">
                {suggestedReplies.replies.map((reply, index) => (
                  <div key={index} className="bg-blue-50 p-3 rounded-lg">
                    <p className="text-gray-800">{reply}</p>
                  </div>
                ))}
              </div>
              {suggestedReplies.context_segments && suggestedReplies.context_segments.length > 0 && (
                <div className="mt-4">
                  <h4 className="font-semibold text-gray-800 mb-2">Based on context:</h4>
                  <div className="space-y-2">
                    {suggestedReplies.context_segments.slice(0, 3).map((segment, index) => (
                      <div key={index} className="bg-gray-50 p-2 rounded text-sm">
                        <span className="font-medium">{segment.speaker_label}:</span> {segment.text}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-500 italic">
              {conversation.status === 'processed' 
                ? 'Click "Generate" to get AI-suggested replies based on conversation context.'
                : 'Suggested replies will be available once processing is complete.'
              }
            </p>
          )}
        </div>
      </div>

      {/* Transcript Section */}
      <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-200">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-800 flex items-center space-x-2">
            <FileText className="w-5 h-5 text-purple-600" />
            <span>Conversation Transcript</span>
          </h2>
          <div className="text-sm text-gray-600">
            {conversation.segments?.length || 0} segments
          </div>
        </div>
        
        {conversation.segments && conversation.segments.length > 0 ? (
          <div className="space-y-4">
            {conversation.segments.map((segment, index) => (
              <div key={segment.id} className="border-l-4 border-blue-200 pl-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-3">
                    <span className="font-semibold text-blue-600 bg-blue-100 px-3 py-1 rounded-full text-sm">
                      {segment.speaker_label}
                    </span>
                    <span className="text-sm text-gray-500">
                      {formatTime(segment.start_time)} - {formatTime(segment.end_time)}
                    </span>
                  </div>
                  {segment.confidence && (
                    <span className="text-xs text-gray-500">
                      Confidence: {(segment.confidence * 100).toFixed(1)}%
                    </span>
                  )}
                </div>
                <p className="text-gray-800 leading-relaxed">{segment.text}</p>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            {conversation.status === 'processing' ? (
              <div className="flex flex-col items-center space-y-4">
                <div className="loading-spinner"></div>
                <p className="text-gray-600">Processing conversation...</p>
                <p className="text-sm text-gray-500">This may take a few minutes for longer recordings.</p>
              </div>
            ) : (
              <p className="text-gray-500 italic">No transcript available yet.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ConversationDetailPage;
