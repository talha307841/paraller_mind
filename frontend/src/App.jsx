import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import HistoryPage from './pages/HistoryPage';
import ConversationDetailPage from './pages/ConversationDetailPage';
import './index.css';

function App() {
  return (
    <Router>
      <div className="App">
        <header className="bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg">
          <div className="container mx-auto px-6 py-4">
            <h1 className="text-3xl font-bold">🧠 Parallel Mind</h1>
            <p className="text-blue-100 mt-1">Advanced Conversational AI with Audio Intelligence</p>
          </div>
        </header>
        
        <main className="container mx-auto px-6 py-8">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/conversation/:id" element={<ConversationDetailPage />} />
          </Routes>
        </main>
        
        <footer className="bg-gray-800 text-white py-6 mt-16">
          <div className="container mx-auto px-6 text-center">
            <p>&copy; 2024 Parallel Mind. Advanced AI-powered conversation analysis.</p>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
