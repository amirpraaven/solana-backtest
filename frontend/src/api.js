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
  
  // Job management
  getJobStatus: (jobId) => api.get(`/strategies/jobs/${jobId}`),
  listJobs: (status = null, limit = 50) => 
    api.get(`/strategies/jobs${status ? `?status=${status}` : ''}${limit ? `&limit=${limit}` : ''}`),
  cancelJob: (jobId) => api.post(`/strategies/jobs/${jobId}/cancel`),
};

export const tokenAPI = {
  // Get trending tokens
  getTrending: (timeFrame = '24h', sortBy = 'volume', limit = 20) => 
    api.get(`/tokens/trending?time_frame=${timeFrame}&sort_by=${sortBy}&limit=${limit}`),
  
  // Get new token listings
  getNewListings: (maxAgeHours = 24, minLiquidity = 1000, limit = 50) => 
    api.get(`/tokens/new-listings?max_age_hours=${maxAgeHours}&min_liquidity=${minLiquidity}&limit=${limit}`),
  
  // Search tokens
  searchTokens: (query, limit = 10) => 
    api.get(`/tokens/search?query=${query}&limit=${limit}`),
  
  // Get token info
  getTokenInfo: (tokenAddress) => 
    api.get(`/tokens/${tokenAddress}/info`),
  
  // Populate token data (for testing)
  populateTokenData: (tokenAddress, daysBack = 7) => 
    api.post(`/tokens/${tokenAddress}/populate?days_back=${daysBack}`),
  
  // Legacy endpoints
  getNewTokens: (maxAgeHours = 72, minLiquidity = 5000) => 
    api.get(`/tokens/new?max_age_hours=${maxAgeHours}&min_liquidity=${minLiquidity}`),
  
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