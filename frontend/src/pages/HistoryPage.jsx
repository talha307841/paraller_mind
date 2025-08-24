import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Search, Clock, User, FileText, Eye, Brain } from 'lucide-react';
import axios from 'axios';

const HistoryPage = () => {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredConversations, setFilteredConversations] = useState([]);

  useEffect(() => {
    fetchConversations();
  }, []);

  useEffect(() => {
    // Filter conversations based on search query
    if (searchQuery.trim() === '') {
      setFilteredConversations(conversations);
    } else {
      const filtered = conversations.filter(conv => 
        conv.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
        conv.status.toLowerCase().includes(searchQuery.toLowerCase())
      );
      setFilteredConversations(filtered);
    }
  }, [searchQuery, conversations]);

  const fetchConversations = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/conversations');
      setConversations(response.data.conversations);
      setFilteredConversations(response.data.conversations);
    } catch (error) {
      console.error('Error fetching conversations:', error);
    } finally {
      setLoading(false);
    }
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

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getSegmentCount = (conversation) => {
    return conversation.segments ? conversation.segments.length : 0;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-64">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">Conversation History</h1>
        <p className="text-gray-600">
          View and manage all your recorded conversations and their processing status
        </p>
      </div>

      {/* Search and Actions */}
      <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-200 mb-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div className="flex space-x-3">
            <button
              onClick={fetchConversations}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Refresh
            </button>
            <Link
              to="/"
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              Record New
            </Link>
          </div>
        </div>
      </div>

      {/* Statistics */}
      <div className="grid md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-200 text-center">
          <div className="text-3xl font-bold text-blue-600 mb-2">
            {conversations.length}
          </div>
          <div className="text-gray-600">Total Conversations</div>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-200 text-center">
          <div className="text-3xl font-bold text-green-600 mb-2">
            {conversations.filter(c => c.status === 'processed').length}
          </div>
          <div className="text-gray-600">Processed</div>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-200 text-center">
          <div className="text-3xl font-bold text-yellow-600 mb-2">
            {conversations.filter(c => c.status === 'processing').length}
          </div>
          <div className="text-gray-600">Processing</div>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-200 text-center">
          <div className="text-3xl font-bold text-red-600 mb-2">
            {conversations.filter(c => c.status === 'error').length}
          </div>
          <div className="text-gray-600">Errors</div>
        </div>
      </div>

      {/* Conversations List */}
      {filteredConversations.length === 0 ? (
        <div className="bg-white p-12 rounded-xl shadow-lg border border-gray-200 text-center">
          <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-800 mb-2">
            {searchQuery ? 'No conversations found' : 'No conversations yet'}
          </h3>
          <p className="text-gray-600 mb-6">
            {searchQuery 
              ? 'Try adjusting your search terms or clear the search to see all conversations.'
              : 'Start by recording your first conversation using the microphone.'
            }
          </p>
          {!searchQuery && (
            <Link
              to="/"
              className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Record First Conversation
            </Link>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {filteredConversations.map((conversation) => (
            <div
              key={conversation.id}
              className="conversation-card bg-white p-6 rounded-xl shadow-lg"
            >
              <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
                <div className="flex-1">
                  <div className="flex items-center space-x-4 mb-3">
                    <h3 className="text-lg font-semibold text-gray-800">
                      {conversation.filename}
                    </h3>
                    {getStatusBadge(conversation.status)}
                  </div>
                  
                  <div className="flex items-center space-x-6 text-sm text-gray-600">
                    <div className="flex items-center space-x-2">
                      <Clock className="w-4 h-4" />
                      <span>{formatDate(conversation.created_at)}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <User className="w-4 h-4" />
                      <span>{getSegmentCount(conversation)} segments</span>
                    </div>
                  </div>
                </div>
                
                <div className="flex space-x-3">
                  <Link
                    to={`/conversation/${conversation.id}`}
                    className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <Eye className="w-4 h-4 mr-2" />
                    View Details
                  </Link>
                  
                  {conversation.status === 'processed' && (
                    <Link
                      to={`/conversation/${conversation.id}`}
                      className="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                    >
                      <Brain className="w-4 h-4 mr-2" />
                      AI Insights
                    </Link>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default HistoryPage;
