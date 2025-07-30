import axios from 'axios';

// Use environment variable for production
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API functions
export const strategyAPI = {
  // Get all strategies
  getAll: () => api.get('/strategies'),
  
  // Get strategy by ID
  getById: (id) => api.get(`/strategies/${id}`),
  
  // Create new strategy
  create: (strategyData) => api.post('/strategies/create', strategyData),
  
  // Update strategy
  update: (id, strategyData) => api.put(`/strategies/${id}`, strategyData),
  
  // Delete strategy
  delete: (id) => api.delete(`/strategies/${id}`),
  
  // Get strategy templates
  getTemplates: () => api.get('/strategies/templates'),
  
  // Create from template
  createFromTemplate: (data) => api.post('/strategies/create-from-template', data),
  
  // Run backtest
  runBacktest: (data) => api.post('/strategies/backtest', data),
  
  // Get backtest result
  getBacktestResult: (id, includeTrades = true) => 
    api.get(`/strategies/backtest/${id}?include_trades=${includeTrades}`),
};

export const tokenAPI = {
  // Get new tokens
  getNewTokens: (maxAgeHours = 72, minLiquidity = 5000) => 
    api.get(`/tokens/new?max_age_hours=${maxAgeHours}&min_liquidity=${minLiquidity}`),
  
  // Analyze token
  analyzeToken: (tokenAddress) => 
    api.post(`/analyze/token/${tokenAddress}?include_price_data=true`),
};

export const systemAPI = {
  // Health check
  health: () => api.get('/health'),
  
  // Get supported DEXes
  getSupportedDexes: () => api.get('/supported-dexes'),
};

export default api;