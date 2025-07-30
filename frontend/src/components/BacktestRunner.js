import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Grid,
  Typography,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  Chip,
  List,
  ListItem,
  ListItemText,
  IconButton,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Paper
} from '@mui/material';
import {
  PlayArrow as RunIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Info as InfoIcon
} from '@mui/icons-material';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import toast from 'react-hot-toast';
import { strategyAPI } from '../api';
import TokenSelector from './TokenSelector';

function BacktestRunner({ strategies, onBacktestComplete }) {
  const [loading, setLoading] = useState(false);
  const [tokenSelectorOpen, setTokenSelectorOpen] = useState(false);
  const [runningJobs, setRunningJobs] = useState([]);
  const [jobDialogOpen, setJobDialogOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);
  const [backtestConfig, setBacktestConfig] = useState({
    strategy_id: '',
    start_date: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000), // 7 days ago
    end_date: new Date(),
    initial_capital: 10000,
    position_size: 0.1, // 10% of capital
    max_positions: 5,
    stop_loss: 0.1, // 10%
    take_profit: 0.5, // 50%
    time_limit_hours: 24
  });
  const [selectedTokens, setSelectedTokens] = useState([]);

  // Poll for running jobs
  useEffect(() => {
    const pollJobs = async () => {
      try {
        const response = await strategyAPI.listJobs('running', 10);
        setRunningJobs(response.data.jobs || []);
      } catch (error) {
        console.error('Error fetching jobs:', error);
      }
    };

    pollJobs();
    const interval = setInterval(pollJobs, 5000); // Poll every 5 seconds

    return () => clearInterval(interval);
  }, []);

  const handleRunBacktest = async () => {
    if (!backtestConfig.strategy_id) {
      toast.error('Please select a strategy');
      return;
    }

    if (selectedTokens.length === 0) {
      toast.error('Please add at least one token');
      return;
    }

    setLoading(true);
    
    try {
      const response = await strategyAPI.runBacktest({
        ...backtestConfig,
        token_addresses: selectedTokens.map(t => t.address),
        start_date: backtestConfig.start_date.toISOString(),
        end_date: backtestConfig.end_date.toISOString()
      });

      const jobId = response.data.job_id;
      toast.success(`Backtest job started! Job ID: ${jobId.slice(0, 8)}...`);
      
      // Start monitoring the job
      monitorJob(jobId);
      setLoading(false);
    } catch (error) {
      console.error('Error running backtest:', error);
      toast.error(error.response?.data?.detail || 'Failed to start backtest');
      setLoading(false);
    }
  };

  const monitorJob = async (jobId) => {
    const checkJob = async () => {
      try {
        const response = await strategyAPI.getJobStatus(jobId);
        const job = response.data;
        
        if (job.status === 'completed') {
          toast.success('Backtest completed!');
          if (job.result && job.result.backtest_id) {
            // Fetch full backtest results
            const result = await strategyAPI.getBacktestResult(job.result.backtest_id);
            onBacktestComplete(result.data);
          }
        } else if (job.status === 'failed') {
          toast.error(`Backtest failed: ${job.error || 'Unknown error'}`);
        } else {
          // Keep polling
          setTimeout(checkJob, 2000);
        }
      } catch (error) {
        console.error('Error checking job:', error);
        toast.error('Failed to check job status');
      }
    };
    
    setTimeout(checkJob, 2000);
  };

  const handleTokensSelected = (tokens) => {
    setSelectedTokens(tokens);
  };

  const removeToken = (address) => {
    setSelectedTokens(selectedTokens.filter(t => t.address !== address));
  };

  const viewJobDetails = async (jobId) => {
    try {
      const response = await strategyAPI.getJobStatus(jobId);
      setSelectedJob(response.data);
      setJobDialogOpen(true);
    } catch (error) {
      toast.error('Failed to fetch job details');
    }
  };

  const cancelJob = async (jobId) => {
    try {
      await strategyAPI.cancelJob(jobId);
      toast.success('Job cancelled');
    } catch (error) {
      toast.error('Failed to cancel job');
    }
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Run Backtest</Typography>

      {/* Running Jobs Alert */}
      {runningJobs.length > 0 && (
        <Alert severity="info" sx={{ mb: 2 }}>
          <Typography variant="subtitle2">
            {runningJobs.length} backtest{runningJobs.length > 1 ? 's' : ''} running
          </Typography>
          <Box mt={1}>
            {runningJobs.map(job => (
              <Box key={job.id} display="flex" alignItems="center" gap={1} mb={1}>
                <LinearProgress 
                  variant="determinate" 
                  value={job.progress || 0} 
                  sx={{ flexGrow: 1, height: 8, borderRadius: 4 }}
                />
                <Typography variant="caption">{job.progress || 0}%</Typography>
                <IconButton size="small" onClick={() => viewJobDetails(job.id)}>
                  <InfoIcon fontSize="small" />
                </IconButton>
              </Box>
            ))}
          </Box>
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Configuration */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Configuration</Typography>
              
              <FormControl fullWidth margin="normal">
                <InputLabel>Strategy</InputLabel>
                <Select
                  value={backtestConfig.strategy_id}
                  onChange={(e) => setBacktestConfig({ ...backtestConfig, strategy_id: e.target.value })}
                  label="Strategy"
                >
                  <MenuItem value="">
                    <em>Select a strategy</em>
                  </MenuItem>
                  {strategies.map(strategy => (
                    <MenuItem key={strategy.id} value={strategy.id}>
                      {strategy.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <LocalizationProvider dateAdapter={AdapterDateFns}>
                <DateTimePicker
                  label="Start Date"
                  value={backtestConfig.start_date}
                  onChange={(newValue) => setBacktestConfig({ ...backtestConfig, start_date: newValue })}
                  renderInput={(params) => <TextField {...params} fullWidth margin="normal" />}
                />
                
                <DateTimePicker
                  label="End Date"
                  value={backtestConfig.end_date}
                  onChange={(newValue) => setBacktestConfig({ ...backtestConfig, end_date: newValue })}
                  renderInput={(params) => <TextField {...params} fullWidth margin="normal" />}
                />
              </LocalizationProvider>

              <TextField
                fullWidth
                margin="normal"
                label="Initial Capital ($)"
                type="number"
                value={backtestConfig.initial_capital}
                onChange={(e) => setBacktestConfig({ ...backtestConfig, initial_capital: parseFloat(e.target.value) })}
              />

              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    margin="normal"
                    label="Position Size (%)"
                    type="number"
                    value={backtestConfig.position_size * 100}
                    onChange={(e) => setBacktestConfig({ ...backtestConfig, position_size: parseFloat(e.target.value) / 100 })}
                    InputProps={{ endAdornment: '%' }}
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    margin="normal"
                    label="Max Positions"
                    type="number"
                    value={backtestConfig.max_positions}
                    onChange={(e) => setBacktestConfig({ ...backtestConfig, max_positions: parseInt(e.target.value) })}
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Risk Management */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Risk Management</Typography>
              
              <TextField
                fullWidth
                margin="normal"
                label="Stop Loss (%)"
                type="number"
                value={backtestConfig.stop_loss * 100}
                onChange={(e) => setBacktestConfig({ ...backtestConfig, stop_loss: parseFloat(e.target.value) / 100 })}
                InputProps={{ endAdornment: '%' }}
                helperText="Maximum loss per trade"
              />

              <TextField
                fullWidth
                margin="normal"
                label="Take Profit (%)"
                type="number"
                value={backtestConfig.take_profit * 100}
                onChange={(e) => setBacktestConfig({ ...backtestConfig, take_profit: parseFloat(e.target.value) / 100 })}
                InputProps={{ endAdornment: '%' }}
                helperText="Target profit per trade"
              />

              <TextField
                fullWidth
                margin="normal"
                label="Time Limit (hours)"
                type="number"
                value={backtestConfig.time_limit_hours}
                onChange={(e) => setBacktestConfig({ ...backtestConfig, time_limit_hours: parseInt(e.target.value) })}
                helperText="Maximum holding period"
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Token Selection */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">Selected Tokens ({selectedTokens.length})</Typography>
                <Button
                  variant="outlined"
                  startIcon={<AddIcon />}
                  onClick={() => setTokenSelectorOpen(true)}
                >
                  Add Tokens
                </Button>
              </Box>

              {selectedTokens.length === 0 ? (
                <Alert severity="info">
                  No tokens selected. Click "Add Tokens" to browse trending tokens or search for specific ones.
                </Alert>
              ) : (
                <List>
                  {selectedTokens.map((token) => (
                    <ListItem
                      key={token.address}
                      secondaryAction={
                        <IconButton edge="end" onClick={() => removeToken(token.address)}>
                          <DeleteIcon />
                        </IconButton>
                      }
                    >
                      <ListItemText
                        primary={
                          <Box display="flex" alignItems="center" gap={1}>
                            <Typography variant="subtitle1">{token.symbol}</Typography>
                            <Typography variant="body2" color="text.secondary">
                              {token.name}
                            </Typography>
                          </Box>
                        }
                        secondary={token.address}
                      />
                    </ListItem>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Run Button */}
        <Grid item xs={12}>
          <Box display="flex" justifyContent="center">
            <Button
              variant="contained"
              size="large"
              startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <RunIcon />}
              onClick={handleRunBacktest}
              disabled={loading || !backtestConfig.strategy_id || selectedTokens.length === 0}
            >
              {loading ? 'Starting Backtest...' : 'Run Backtest'}
            </Button>
          </Box>
        </Grid>
      </Grid>

      {/* Token Selector Dialog */}
      <TokenSelector
        open={tokenSelectorOpen}
        onClose={() => setTokenSelectorOpen(false)}
        onTokensSelected={handleTokensSelected}
        selectedTokens={selectedTokens.map(t => t.address)}
      />

      {/* Job Details Dialog */}
      <Dialog open={jobDialogOpen} onClose={() => setJobDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          Job Details
          {selectedJob && selectedJob.status === 'running' && (
            <IconButton
              onClick={() => cancelJob(selectedJob.id)}
              sx={{ position: 'absolute', right: 8, top: 8 }}
            >
              <DeleteIcon />
            </IconButton>
          )}
        </DialogTitle>
        <DialogContent>
          {selectedJob && (
            <Box>
              <Typography variant="body2" gutterBottom>
                <strong>Job ID:</strong> {selectedJob.id}
              </Typography>
              <Typography variant="body2" gutterBottom>
                <strong>Status:</strong> <Chip size="small" label={selectedJob.status} />
              </Typography>
              <Typography variant="body2" gutterBottom>
                <strong>Progress:</strong> {selectedJob.progress}%
              </Typography>
              <LinearProgress 
                variant="determinate" 
                value={selectedJob.progress} 
                sx={{ mb: 2 }}
              />
              
              {selectedJob.logs && selectedJob.logs.length > 0 && (
                <Paper variant="outlined" sx={{ p: 1, maxHeight: 200, overflow: 'auto' }}>
                  {selectedJob.logs.map((log, index) => (
                    <Typography key={index} variant="caption" component="div">
                      [{new Date(log.timestamp).toLocaleTimeString()}] {log.message}
                    </Typography>
                  ))}
                </Paper>
              )}
              
              {selectedJob.error && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {selectedJob.error}
                </Alert>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setJobDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default BacktestRunner;