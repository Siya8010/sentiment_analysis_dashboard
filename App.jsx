import React from 'react';
import SentimentDashboard from './components/Dashboard/SentimentDashboard.jsx';
import './App.css';

function App() {
  // Always show dashboard, no login
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation Header */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-900">
                AI Sentiment Analysis Dashboard
              </h1>
              <span className="ml-4 px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full flex items-center">
                <span className="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse"></span>
                Live
              </span>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Dashboard Content */}
      <main>
        <SentimentDashboard userRole={'viewer'} />
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-8">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="text-sm text-gray-600 mb-4 md:mb-0">
              <p>&copy; 2024 AI Sentiment Analysis Dashboard</p>
              <p className="text-xs mt-1">
                GDPR Compliant • Model Accuracy: 92.3% • Real-time Processing
              </p>
            </div>
            <div className="flex space-x-6 text-sm">
              <span className="text-green-600 font-medium flex items-center">
                <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                System Online
              </span>
              <span className="text-gray-500">v1.0.0</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;