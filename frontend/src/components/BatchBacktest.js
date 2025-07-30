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
  Slider,
  Alert,
  CircularProgress,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction
} from '@mui/material';
import {
  PlayArrow as RunIcon,
  NewReleases as NewTokenIcon,
  Assessment as ResultsIcon,
  TrendingUp as ProfitIcon,
  TrendingDown as LossIcon
} from '@mui/icons-material';
import toast from 'react-hot-toast';
import { batchAPI } from '../api';

function BatchBacktest({ strategies }) {
  const [loading, setLoading] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [results, setResults] = useState(null);
  const [resultsDialogOpen, setResultsDialogOpen] = useState(false);
  
  const [config, setConfig] = useState({
    strategy_id: '',
    hours_back: 24,
    min_liquidity: 10000,
    max_tokens: 20,
    backtest_days: 7,
    initial_capital: 10000,
    position_size: 0.1
  });

  // Poll job status
  useEffect(() => {
    if (!jobId) return;

    const pollInterval = setInterval(async () => {
      try {
        const response = await batchAPI.getStatus(jobId);
        setJobStatus(response.data);

        if (response.data.status === 'completed') {
          clearInterval(pollInterval);
          toast.success('Batch backtest completed!');
          fetchResults();
        } else if (response.data.status === 'failed') {
          clearInterval(pollInterval);
          toast.error('Batch backtest failed');
        }
      } catch (error) {
        console.error('Error polling job:', error);
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [jobId]);

  const fetchResults = async () => {
    try {
      const response = await batchAPI.getResults(jobId);
      setResults(response.data);
    } catch (error) {
      toast.error('Failed to fetch results');
    }
  };

  const handleRunBatch = async () => {
    if (!config.strategy_id) {
      toast.error('Please select a strategy');
      return;
    }

    setLoading(true);
    setJobStatus(null);
    setResults(null);

    try {
      const response = await batchAPI.runNewTokenBacktest({
        strategy_id: parseInt(config.strategy_id),
        hours_back: config.hours_back,
        min_liquidity: config.min_liquidity,
        max_tokens: config.max_tokens,
        backtest_days: config.backtest_days,
        initial_capital: config.initial_capital,
        position_size: config.position_size
      });

      setJobId(response.data.job_id);
      toast.success(`Started batch backtest for tokens from last ${config.hours_back} hours`);
    } catch (error) {
      console.error('Error starting batch:', error);
      toast.error(error.response?.data?.detail || 'Failed to start batch backtest');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(value);
  };

  const formatPercent = (value) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Batch Backtest - All New Tokens
      </Typography>
      
      <Grid container spacing={3}>
        {/* Configuration */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <NewTokenIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Token Discovery Settings
              </Typography>

              <FormControl fullWidth margin="normal">
                <InputLabel>Strategy</InputLabel>
                <Select
                  value={config.strategy_id}
                  onChange={(e) => setConfig({ ...config, strategy_id: e.target.value })}
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

              <Box mt={2}>
                <Typography gutterBottom>
                  Find tokens created in last {config.hours_back} hours
                </Typography>
                <Slider
                  value={config.hours_back}
                  onChange={(e, v) => setConfig({ ...config, hours_back: v })}
                  min={1}
                  max={168}
                  marks={[
                    { value: 1, label: '1h' },
                    { value: 24, label: '24h' },
                    { value: 168, label: '7d' }
                  ]}
                  valueLabelDisplay="auto"
                />
              </Box>

              <TextField
                fullWidth
                margin="normal"
                label="Minimum Liquidity ($)"
                type="number"
                value={config.min_liquidity}
                onChange={(e) => setConfig({ ...config, min_liquidity: parseFloat(e.target.value) })}
                helperText="Only test tokens with at least this much liquidity"
              />

              <TextField
                fullWidth
                margin="normal"
                label="Maximum Tokens to Test"
                type="number"
                value={config.max_tokens}
                onChange={(e) => setConfig({ ...config, max_tokens: parseInt(e.target.value) })}
                InputProps={{ inputProps: { min: 1, max: 100 } }}
                helperText="Limit to avoid long processing times"
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Backtest Settings */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Backtest Parameters</Typography>

              <TextField
                fullWidth
                margin="normal"
                label="Backtest Days"
                type="number"
                value={config.backtest_days}
                onChange={(e) => setConfig({ ...config, backtest_days: parseInt(e.target.value) })}
                helperText="How many days of history to test"
              />

              <TextField
                fullWidth
                margin="normal"
                label="Initial Capital ($)"
                type="number"
                value={config.initial_capital}
                onChange={(e) => setConfig({ ...config, initial_capital: parseFloat(e.target.value) })}
              />

              <TextField
                fullWidth
                margin="normal"
                label="Position Size (%)"
                type="number"
                value={config.position_size * 100}
                onChange={(e) => setConfig({ ...config, position_size: parseFloat(e.target.value) / 100 })}
                InputProps={{ endAdornment: '%' }}
                helperText="Percentage of capital per trade"
              />

              <Alert severity="info" sx={{ mt: 2 }}>
                This will test your strategy on ALL tokens created in the selected timeframe,
                showing you which ones would have been profitable.
              </Alert>
            </CardContent>
          </Card>
        </Grid>

        {/* Progress */}
        {jobStatus && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Progress</Typography>
                <Box display="flex" alignItems="center" gap={2}>
                  <LinearProgress 
                    variant="determinate" 
                    value={jobStatus.progress || 0} 
                    sx={{ flexGrow: 1, height: 10, borderRadius: 5 }}
                  />
                  <Typography variant="body2">{jobStatus.progress || 0}%</Typography>
                </Box>
                {jobStatus.current_task && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    {jobStatus.current_task}
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Results Summary */}
        {results && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="h6">
                    <ResultsIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                    Results Summary
                  </Typography>
                  <Button
                    variant="outlined"
                    onClick={() => setResultsDialogOpen(true)}
                  >
                    View Detailed Results
                  </Button>
                </Box>

                <Grid container spacing={2}>
                  <Grid item xs={6} md={3}>
                    <Typography variant="subtitle2" color="text.secondary">
                      Tokens Tested
                    </Typography>
                    <Typography variant="h4">
                      {results.summary.total_tokens}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="subtitle2" color="text.secondary">
                      Profitable Tokens
                    </Typography>
                    <Typography variant="h4" color="success.main">
                      {results.summary.profitable_tokens}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="subtitle2" color="text.secondary">
                      Total P&L
                    </Typography>
                    <Typography variant="h4" color={results.summary.total_pnl >= 0 ? 'success.main' : 'error.main'}>
                      {formatCurrency(results.summary.total_pnl)}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="subtitle2" color="text.secondary">
                      Success Rate
                    </Typography>
                    <Typography variant="h4">
                      {results.summary.success_rate?.toFixed(1) || 0}%
                    </Typography>
                  </Grid>
                </Grid>

                {results.summary.best_token && (
                  <Box mt={3}>
                    <Chip
                      icon={<ProfitIcon />}
                      label={`Best: ${results.summary.best_token.symbol} ${formatCurrency(results.summary.best_token.pnl)}`}
                      color="success"
                      sx={{ mr: 2 }}
                    />
                    {results.summary.worst_token && results.summary.worst_token.pnl < 0 && (
                      <Chip
                        icon={<LossIcon />}
                        label={`Worst: ${results.summary.worst_token.symbol} ${formatCurrency(results.summary.worst_token.pnl)}`}
                        color="error"
                      />
                    )}
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Run Button */}
        <Grid item xs={12}>
          <Box display="flex" justifyContent="center">
            <Button
              variant="contained"
              size="large"
              startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <RunIcon />}
              onClick={handleRunBatch}
              disabled={loading || !config.strategy_id}
            >
              {loading ? 'Starting Batch Test...' : 'Test All New Tokens'}
            </Button>
          </Box>
        </Grid>
      </Grid>

      {/* Detailed Results Dialog */}
      <Dialog 
        open={resultsDialogOpen} 
        onClose={() => setResultsDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>Detailed Token Results</DialogTitle>
        <DialogContent>
          {results && results.tokens && (
            <TableContainer component={Paper}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Token</TableCell>
                    <TableCell>Age</TableCell>
                    <TableCell align="right">Liquidity</TableCell>
                    <TableCell align="right">Signals</TableCell>
                    <TableCell align="right">Trades</TableCell>
                    <TableCell align="right">P&L</TableCell>
                    <TableCell align="right">Return %</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {results.tokens.map((item, index) => (
                    <TableRow key={index}>
                      <TableCell>
                        <Box>
                          <Typography variant="body2">{item.token.symbol}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {item.token.address.slice(0, 8)}...
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>{item.token.age_hours?.toFixed(1)}h</TableCell>
                      <TableCell align="right">
                        {formatCurrency(item.token.liquidity)}
                      </TableCell>
                      <TableCell align="right">
                        {item.backtest.signals_found || 0}
                      </TableCell>
                      <TableCell align="right">
                        {item.backtest.trade_count || 0}
                      </TableCell>
                      <TableCell 
                        align="right"
                        sx={{ 
                          color: item.backtest.total_pnl >= 0 ? 'success.main' : 'error.main',
                          fontWeight: 'bold'
                        }}
                      >
                        {formatCurrency(item.backtest.total_pnl || 0)}
                      </TableCell>
                      <TableCell 
                        align="right"
                        sx={{ 
                          color: item.backtest.total_return_pct >= 0 ? 'success.main' : 'error.main'
                        }}
                      >
                        {formatPercent(item.backtest.total_return_pct || 0)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResultsDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default BatchBacktest;