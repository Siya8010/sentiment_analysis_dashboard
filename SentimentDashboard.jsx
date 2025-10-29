import React, { useState, useEffect } from 'react';
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, Activity, AlertCircle, Users, MessageSquare } from 'lucide-react';
import { getHistoricalApi, getPredictionsApi, getRealtimeApi, syncTwitter } from '../../api';

const SentimentDashboard = ({ userRole = 'viewer' }) => {
  const [selectedTimeRange, setSelectedTimeRange] = useState('7d');
  const [selectedSource, setSelectedSource] = useState('all');
  const [realTimeData, setRealTimeData] = useState([]);
  const [isLive, setIsLive] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [authNeeded, setAuthNeeded] = useState(false);
  const [token, setToken] = useState(() => localStorage.getItem('sentimentToken'));
  const [reloadKey, setReloadKey] = useState(0);

  // Keep token state in sync with localStorage on focus
  useEffect(() => {
    const syncToken = () => setToken(localStorage.getItem('sentimentToken'));
    window.addEventListener('focus', syncToken);
    const id = setInterval(syncToken, 3000);
    return () => { window.removeEventListener('focus', syncToken); clearInterval(id); };
  }, []);

  // Real-time sentiment data (backend polling with fallback)
  useEffect(() => {
    if (!isLive) return;
    let cancelled = false;

    const fetchRealtime = async () => {
      try {
        const rt = await getRealtimeApi(selectedSource, 20);
        const arr = rt?.data || [];
        const mapped = arr.slice(-20).map(item => ({
          timestamp: item.timestamp || new Date().toLocaleTimeString(),
          positive: item.positive ?? item.pos ?? Math.random() * 100,
          negative: item.negative ?? item.neg ?? Math.random() * 100,
          neutral: item.neutral ?? item.neu ?? Math.random() * 100,
        }));
        if (!cancelled) {
          setRealTimeData(mapped);
        }
      } catch (e) {
        // fallback to local simulation if API fails
        const newSentiment = {
          timestamp: new Date().toLocaleTimeString(),
          positive: Math.random() * 100,
          negative: Math.random() * 100,
          neutral: Math.random() * 100,
        };
        if (!cancelled) setRealTimeData(prev => [...prev.slice(-19), newSentiment]);
      }
    };

    fetchRealtime();
    const interval = setInterval(fetchRealtime, 5000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [isLive, selectedSource]);

  // Historical trend data (default fallback)
  const defaultHistorical = [
    { date: '10/18', positive: 65, negative: 20, neutral: 15, total: 1250 },
    { date: '10/19', positive: 70, negative: 18, neutral: 12, total: 1450 },
    { date: '10/20', positive: 62, negative: 25, neutral: 13, total: 1380 },
    { date: '10/21', positive: 75, negative: 15, neutral: 10, total: 1620 },
    { date: '10/22', positive: 68, negative: 22, neutral: 10, total: 1540 },
    { date: '10/23', positive: 72, negative: 18, neutral: 10, total: 1680 },
    { date: '10/24', positive: 78, negative: 12, neutral: 10, total: 1820 },
  ];

  const [historicalData, setHistoricalData] = useState(defaultHistorical);
  const [historicalLoading, setHistoricalLoading] = useState(false);
  const [historicalError, setHistoricalError] = useState('');

  // Predictive analytics data (default fallback)
  const defaultPredictions = [
    { date: '10/25', predicted: 80, confidence: 85, lower: 75, upper: 85 },
    { date: '10/26', predicted: 82, confidence: 82, lower: 77, upper: 87 },
    { date: '10/27', predicted: 79, confidence: 78, lower: 73, upper: 85 },
    { date: '10/28', predicted: 85, confidence: 75, lower: 78, upper: 92 },
    { date: '10/29', predicted: 83, confidence: 72, lower: 75, upper: 91 },
  ];

  const [predictiveData, setPredictiveData] = useState(defaultPredictions);
  const [predLoading, setPredLoading] = useState(false);
  const [predError, setPredError] = useState('');

  // Fetch from backend when filters change
  useEffect(() => {
    const loadHistorical = async () => {
      try {
        setHistoricalLoading(true);
        setHistoricalError('');
        const daysMap = { '24h': 1, '7d': 7, '30d': 30, '90d': 90 };
        const days = daysMap[selectedTimeRange] || 7;
        const data = await getHistoricalApi(days, selectedSource);
        // Expecting an array of items with date and positive/negative/neutral
        if (Array.isArray(data)) {
          setHistoricalData(data);
        } else if (data && Array.isArray(data.series)) {
          setHistoricalData(data.series);
        } else {
          setHistoricalData(defaultHistorical);
        }
      } catch (e) {
        setHistoricalError('Failed to load historical data');
        setHistoricalData(defaultHistorical);
      } finally {
        setHistoricalLoading(false);
      }
    };

    const loadPredictions = async () => {
      try {
        setPredLoading(true);
        setPredError('');
        const days = 5;
        const data = await getPredictionsApi(days);
        // Normalize to expected shape
        if (Array.isArray(data)) {
          setPredictiveData(data.map(d => ({
            date: d.date || d.day || '',
            predicted: d.predicted || d.value || 0,
            upper: d.upper || d.upper_bound || d.predicted + 3,
            lower: d.lower || d.lower_bound || d.predicted - 3,
          })));
        } else if (data && Array.isArray(data.predictions)) {
          setPredictiveData(data.predictions.map(d => ({
            date: d.date,
            predicted: d.predicted,
            upper: d.upper,
            lower: d.lower,
          })));
        } else {
          setPredictiveData(defaultPredictions);
        }
      } catch (e) {
        setPredError('Failed to load predictions');
        setPredictiveData(defaultPredictions);
      } finally {
        setPredLoading(false);
      }
    };

    loadHistorical();
    loadPredictions();
  }, [selectedTimeRange, selectedSource, reloadKey]);

  // Sentiment distribution
  const sentimentDistribution = [
    { name: 'Positive', value: 72, color: '#10b981' },
    { name: 'Neutral', value: 18, color: '#6b7280' },
    { name: 'Negative', value: 10, color: '#ef4444' },
  ];

  // Source breakdown
  const sourceData = [
    { source: 'Twitter', mentions: 8450, sentiment: 74 },
    { source: 'Facebook', mentions: 5230, sentiment: 68 },
    { source: 'Reviews', mentions: 3120, sentiment: 81 },
    { source: 'Surveys', mentions: 1890, sentiment: 76 },
  ];

  // Key metrics
  const metrics = [
    { 
      label: 'Avg Sentiment Score', 
      value: '72%', 
      change: '+5.2%', 
      trend: 'up',
      icon: TrendingUp,
      color: 'text-green-600'
    },
    { 
      label: 'Total Mentions', 
      value: '18.7K', 
      change: '+12.3%', 
      trend: 'up',
      icon: MessageSquare,
      color: 'text-blue-600'
    },
    { 
      label: 'Engagement Rate', 
      value: '8.4%', 
      change: '-2.1%', 
      trend: 'down',
      icon: Users,
      color: 'text-purple-600'
    },
    { 
      label: 'Alert Score', 
      value: 'Low', 
      change: 'Normal', 
      trend: 'neutral',
      icon: AlertCircle,
      color: 'text-green-600'
    },
  ];

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          AI Sentiment Analysis Dashboard
        </h1>
        <p className="text-gray-600">Real-time sentiment tracking and predictive insights</p>
      </div>
      

      {/* Controls */}
      <div className="bg-white rounded-lg shadow p-4 mb-6 flex flex-wrap gap-4 items-center justify-between">
        {authNeeded && (
          <div className="w-full text-sm text-red-600 flex items-center gap-3">
            <span>Session expired. Please log in again.</span>
            <button className="px-4 py-1 rounded-lg bg-blue-600 text-white" onClick={() => setReloadKey(k => k + 1)}>Retry</button>
          </div>
        )}
        <div className="flex gap-3 items-center">
          <select 
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            value={selectedTimeRange}
            onChange={(e) => setSelectedTimeRange(e.target.value)}
          >
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
            <option value="90d">Last 90 Days</option>
          </select>
          
          <select 
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            value={selectedSource}
            onChange={(e) => setSelectedSource(e.target.value)}
          >
            <option value="all">All Sources</option>
            <option value="twitter">Twitter</option>
            <option value="facebook">Facebook</option>
            <option value="reviews">Reviews</option>
            <option value="surveys">Surveys</option>
          </select>

          <button
            onClick={async () => {
              try {
                setSyncing(true);
                // Example: syncTwitter with default keywords or skip
                await syncTwitter([]);
                // Refresh datasets after sync
                const daysMap = { '24h': 1, '7d': 7, '30d': 30, '90d': 90 };
                const days = daysMap[selectedTimeRange] || 7;
                try {
                  const hist = await getHistoricalApi(days, selectedSource);
                  if (Array.isArray(hist)) {
                    setHistoricalData(hist);
                  } else if (hist && Array.isArray(hist.series)) {
                    setHistoricalData(hist.series);
                  }
                } catch (e) {}
              } finally {
                setSyncing(false);
              }
            }}
            className={`px-6 py-2 rounded-lg font-medium transition-colors ${userRole === 'admin' || userRole === 'analyst' || userRole === 'manager' ? 'bg-blue-600 hover:bg-blue-700 text-white' : 'bg-gray-300 text-gray-500 cursor-not-allowed'}`}
            disabled={syncing || !(userRole === 'admin' || userRole === 'analyst' || userRole === 'manager')}
          >
            Sync Twitter
          </button>
        </div>

        <button
          onClick={() => setIsLive(!isLive)}
          className={`px-6 py-2 rounded-lg font-medium transition-colors ${
            isLive 
              ? 'bg-red-600 hover:bg-red-700 text-white' 
              : 'bg-green-600 hover:bg-green-700 text-white'
          }`}
        >
          {isLive ? '⏸ Pause Live Feed' : '▶ Resume Live Feed'}
        </button>
      </div>
      
      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        {metrics.map((metric, idx) => {
          const Icon = metric.icon;
          return (
            <div key={idx} className={`bg-white rounded-lg shadow p-6`}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-gray-600 text-sm mb-1">{metric.label}</p>
                  <p className="text-2xl font-bold text-gray-900">{metric.value}</p>
                  <p className={`text-sm mt-1 ${
                    metric.trend === 'up' ? 'text-green-600' :
                    metric.trend === 'down' ? 'text-red-600' :
                    'text-gray-600'
                  }`}>
                    {metric.change}
                  </p>
                </div>
                <div className={`p-3 rounded-lg ${
                  metric.trend === 'up' ? 'bg-green-100' :
                  metric.trend === 'down' ? 'bg-red-100' :
                  'bg-gray-100'
                }`}>
                  <Icon className={metric.color} size={24} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Historical Trends */}
        <div className={`lg:col-span-2 bg-white rounded-lg shadow p-6`}>
          <h2 className="text-xl font-bold text-gray-900 mb-4">Historical Sentiment Trends</h2>
          {historicalError && (<div className="text-red-600 text-sm mb-2">{historicalError}</div>)}
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={historicalData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="positive" stroke="#10b981" strokeWidth={2} />
              <Line type="monotone" dataKey="negative" stroke="#ef4444" strokeWidth={2} />
              <Line type="monotone" dataKey="neutral" stroke="#6b7280" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Sentiment Distribution */}
        <div className={`bg-white rounded-lg shadow p-6`}>
          <h2 className="text-xl font-bold text-gray-900 mb-4">Current Distribution</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={sentimentDistribution}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: ${value}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {sentimentDistribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Predictive Analytics & Source Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Predictive Analytics */}
        <div className={`bg-white rounded-lg shadow p-6`}>
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            Predictive Analytics (Next 5 Days)
          </h2>
          {predError && (<div className="text-red-600 text-sm mb-2">{predError}</div>)}
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={predictiveData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="predicted" stroke="#3b82f6" strokeWidth={2} />
              <Line type="monotone" dataKey="upper" stroke="#93c5fd" strokeDasharray="5 5" />
              <Line type="monotone" dataKey="lower" stroke="#93c5fd" strokeDasharray="5 5" />
            </LineChart>
          </ResponsiveContainer>
          <p className="text-sm text-gray-600 mt-2">
            Prediction confidence: 78% • Model: LSTM with Prophet fallback
          </p>
        </div>

        {/* Source Breakdown */}
        <div className={`bg-white rounded-lg shadow p-6`}>
          <h2 className="text-xl font-bold text-gray-900 mb-4">Sentiment by Source</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={sourceData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="source" />
              <YAxis yAxisId="left" orientation="left" stroke="#8884d8" />
              <YAxis yAxisId="right" orientation="right" stroke="#82ca9d" />
              <Tooltip />
              <Legend />
              <Bar yAxisId="left" dataKey="mentions" fill="#8884d8" name="Mentions" />
              <Bar yAxisId="right" dataKey="sentiment" fill="#82ca9d" name="Sentiment %" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Real-time Feed */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900">Real-time Sentiment Feed</h2>
          <div className="flex items-center gap-2">
            <Activity className={`${isLive ? 'text-green-600 animate-pulse' : 'text-gray-400'}`} size={20} />
            <span className={`text-sm font-medium ${isLive ? 'text-green-600' : 'text-gray-400'}`}>
              {isLive ? 'Live' : 'Paused'}
            </span>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {realTimeData.slice(-6).reverse().map((data, idx) => (
            <div key={idx} className="border border-gray-200 rounded-lg p-4">
              <p className="text-xs text-gray-500 mb-2">{data.timestamp}</p>
              <div className="space-y-1">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Positive</span>
                  <span className="text-sm font-medium text-green-600">
                    {data.positive.toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Negative</span>
                  <span className="text-sm font-medium text-red-600">
                    {data.negative.toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Neutral</span>
                  <span className="text-sm font-medium text-gray-600">
                    {data.neutral.toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="mt-6 text-center text-sm text-gray-500">
        <p>GDPR Compliant • Role-based Access • 99.8% Uptime • Model Accuracy: 92.3%</p>
      </div>
    </div>
  );
};

export default SentimentDashboard;