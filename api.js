import axios from 'axios';

// Use environment variable or fallback to localhost:5001 for development
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';

const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.response.use(
  (r) => r,
  (error) => {
    // No auth error handling needed
    return Promise.reject(error);
  }
);

export const getHistoricalApi = async (days = 7, source = 'all') => {
  const { data } = await api.get('/api/analytics/historical', { params: { days, source } });
  return data;
};

export const getPredictionsApi = async (days = 5) => {
  const { data } = await api.get('/api/predictions/sentiment', { params: { days } });
  return data;
};

export const getRealtimeApi = async (source = 'all', limit = 50) => {
  const params = { source, limit };
  const { data } = await api.get('/api/sentiment/realtime', { params });
  return data; // { data: [...] }
};

export const syncTwitter = async (keywords = []) => {
  const { data } = await api.post('/api/integrations/twitter/sync', { keywords });
  return data; // { synced, timestamp }
};

export default api;
