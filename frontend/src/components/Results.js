import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tab,
  Tabs
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  TrendingUp as ProfitIcon,
  TrendingDown as LossIcon
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

function Results({ results }) {
  const [selectedResult, setSelectedResult] = useState(0);
  const [tabValue, setTabValue] = useState(0);

  if (results.length === 0) {
    return (
      <Box>
        <Typography variant="h5" gutterBottom>Backtest Results</Typography>
        <Card>
          <CardContent>
            <Typography color="text.secondary" align="center">
              No backtest results yet. Run a backtest to see results here.
            </Typography>
          </CardContent>
        </Card>
      </Box>
    );
  }

  const currentResult = results[selectedResult];
  const metrics = currentResult.metrics || {};
  const trades = currentResult.trades || [];

  // Prepare equity curve data
  const equityData = trades.reduce((acc, trade, index) => {
    const prevEquity = index > 0 ? acc[index - 1].equity : metrics.initial_capital || 10000;
    const equity = prevEquity + (trade.pnl || 0);
    acc.push({
      tradeNumber: index + 1,
      equity: equity,
      pnl: trade.pnl || 0,
      timestamp: new Date(trade.exit_time).toLocaleDateString()
    });
    return acc;
  }, []);

  // Prepare PnL distribution data
  const pnlDistribution = trades.reduce((acc, trade) => {
    const pnl = trade.pnl || 0;
    const bucket = pnl >= 0 ? 'Wins' : 'Losses';
    acc[bucket] = (acc[bucket] || 0) + 1;
    return acc;
  }, {});

  const pnlDistributionData = Object.entries(pnlDistribution).map(([key, value]) => ({
    name: key,
    value: value,
    fill: key === 'Wins' ? '#4caf50' : '#f44336'
  }));

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(value);
  };

  const formatPercent = (value) => {
    return `${(value * 100).toFixed(2)}%`;
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Backtest Results</Typography>

      {/* Result Selector */}
      {results.length > 1 && (
        <Box mb={2}>
          <Tabs value={selectedResult} onChange={(e, v) => setSelectedResult(v)}>
            {results.map((result, index) => (
              <Tab 
                key={index} 
                label={`${result.strategy_name} - ${new Date(result.created_at).toLocaleDateString()}`}
              />
            ))}
          </Tabs>
        </Box>
      )}

      {/* Summary Metrics */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Total Return
              </Typography>
              <Typography variant="h5" color={metrics.total_return >= 0 ? 'success.main' : 'error.main'}>
                {formatCurrency(metrics.total_return)}
              </Typography>
              <Typography variant="body2">
                {formatPercent(metrics.total_return_pct)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Win Rate
              </Typography>
              <Typography variant="h5">
                {formatPercent(metrics.win_rate)}
              </Typography>
              <Typography variant="body2">
                {metrics.winning_trades} / {metrics.total_trades} trades
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Sharpe Ratio
              </Typography>
              <Typography variant="h5">
                {metrics.sharpe_ratio?.toFixed(2) || 'N/A'}
              </Typography>
              <Typography variant="body2">
                Risk-adjusted return
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Max Drawdown
              </Typography>
              <Typography variant="h5" color="error.main">
                {formatPercent(metrics.max_drawdown)}
              </Typography>
              <Typography variant="body2">
                Peak to trough
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts */}
      <Box sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
          <Tab label="Equity Curve" />
          <Tab label="Win/Loss Distribution" />
          <Tab label="Trade Details" />
        </Tabs>

        {/* Equity Curve */}
        {tabValue === 0 && (
          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>Portfolio Equity</Typography>
              <ResponsiveContainer width="100%" height={400}>
                <AreaChart data={equityData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" />
                  <YAxis />
                  <Tooltip formatter={(value) => formatCurrency(value)} />
                  <Area 
                    type="monotone" 
                    dataKey="equity" 
                    stroke="#1976d2" 
                    fill="#1976d2" 
                    fillOpacity={0.3}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {/* Win/Loss Distribution */}
        {tabValue === 1 && (
          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>Win/Loss Distribution</Typography>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={pnlDistributionData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {/* Trade Details */}
        {tabValue === 2 && (
          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>Trade Details</Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Token</TableCell>
                      <TableCell>Entry Time</TableCell>
                      <TableCell>Exit Time</TableCell>
                      <TableCell align="right">Entry Price</TableCell>
                      <TableCell align="right">Exit Price</TableCell>
                      <TableCell align="right">Size</TableCell>
                      <TableCell align="right">PnL</TableCell>
                      <TableCell align="right">Return</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {trades.slice(0, 50).map((trade, index) => (
                      <TableRow key={index}>
                        <TableCell>
                          <Typography variant="body2" style={{ fontFamily: 'monospace' }}>
                            {trade.token_address.slice(0, 8)}...
                          </Typography>
                        </TableCell>
                        <TableCell>
                          {new Date(trade.entry_time).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          {new Date(trade.exit_time).toLocaleString()}
                        </TableCell>
                        <TableCell align="right">
                          ${trade.entry_price.toFixed(6)}
                        </TableCell>
                        <TableCell align="right">
                          ${trade.exit_price.toFixed(6)}
                        </TableCell>
                        <TableCell align="right">
                          {formatCurrency(trade.position_size)}
                        </TableCell>
                        <TableCell align="right">
                          <Chip
                            label={formatCurrency(trade.pnl)}
                            color={trade.pnl >= 0 ? 'success' : 'error'}
                            size="small"
                            icon={trade.pnl >= 0 ? <ProfitIcon /> : <LossIcon />}
                          />
                        </TableCell>
                        <TableCell align="right">
                          <Typography 
                            variant="body2" 
                            color={trade.return_pct >= 0 ? 'success.main' : 'error.main'}
                          >
                            {formatPercent(trade.return_pct)}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
              {trades.length > 50 && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                  Showing first 50 trades of {trades.length} total
                </Typography>
              )}
            </CardContent>
          </Card>
        )}
      </Box>

      {/* Additional Metrics */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography>Detailed Metrics</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" gutterBottom>Performance Metrics</Typography>
              <Table size="small">
                <TableBody>
                  <TableRow>
                    <TableCell>Average Win</TableCell>
                    <TableCell align="right">{formatCurrency(metrics.avg_win)}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Average Loss</TableCell>
                    <TableCell align="right">{formatCurrency(metrics.avg_loss)}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Profit Factor</TableCell>
                    <TableCell align="right">{metrics.profit_factor?.toFixed(2) || 'N/A'}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Expectancy</TableCell>
                    <TableCell align="right">{formatCurrency(metrics.expectancy)}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" gutterBottom>Risk Metrics</Typography>
              <Table size="small">
                <TableBody>
                  <TableRow>
                    <TableCell>Max Consecutive Wins</TableCell>
                    <TableCell align="right">{metrics.max_consecutive_wins}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Max Consecutive Losses</TableCell>
                    <TableCell align="right">{metrics.max_consecutive_losses}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Recovery Factor</TableCell>
                    <TableCell align="right">{metrics.recovery_factor?.toFixed(2) || 'N/A'}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Total Fees Paid</TableCell>
                    <TableCell align="right">{formatCurrency(metrics.total_fees)}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>
    </Box>
  );
}

export default Results;