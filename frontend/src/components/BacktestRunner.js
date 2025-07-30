import React, { useState } from 'react';
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
  IconButton
} from '@mui/material';
import {
  PlayArrow as RunIcon,
  Add as AddIcon,
  Delete as DeleteIcon
} from '@mui/icons-material';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import toast from 'react-hot-toast';
import { strategyAPI } from '../api';

function BacktestRunner({ strategies, onBacktestComplete }) {
  const [loading, setLoading] = useState(false);
  const [backtestConfig, setBacktestConfig] = useState({
    strategy_id: '',
    token_addresses: [],
    start_date: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000), // 7 days ago
    end_date: new Date(),
    initial_capital: 10000,
    position_size: 0.1, // 10% of capital
    max_positions: 5,
    slippage: 0.02,
    fees: 0.0025,
    exit_strategy: {
      hold_duration: 300, // 5 minutes
      stop_loss: 0.1, // 10%
      take_profit: 0.5 // 50%
    }
  });
  const [currentToken, setCurrentToken] = useState('');

  const popularTokens = [
    { address: 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', symbol: 'USDC' },
    { address: 'So11111111111111111111111111111111111111112', symbol: 'WSOL' },
    { address: 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263', symbol: 'BONK' }
  ];

  const handleRunBacktest = async () => {
    if (!backtestConfig.strategy_id) {
      toast.error('Please select a strategy');
      return;
    }

    if (backtestConfig.token_addresses.length === 0) {
      toast.error('Please add at least one token address');
      return;
    }

    setLoading(true);
    
    try {
      const response = await strategyAPI.runBacktest({
        ...backtestConfig,
        start_date: backtestConfig.start_date.toISOString(),
        end_date: backtestConfig.end_date.toISOString()
      });

      toast.success('Backtest completed successfully!');
      
      // Poll for results
      const checkResult = async () => {
        try {
          const result = await strategyAPI.getBacktestResult(response.data.backtest_id);
          if (result.data.status === 'completed') {
            onBacktestComplete(result.data);
          } else if (result.data.status === 'failed') {
            toast.error('Backtest failed');
            setLoading(false);
          } else {
            // Keep polling
            setTimeout(checkResult, 2000);
          }
        } catch (error) {
          console.error('Error checking result:', error);
          setLoading(false);
        }
      };

      setTimeout(checkResult, 2000);
    } catch (error) {
      toast.error('Failed to start backtest');
      setLoading(false);
    }
  };

  const addToken = () => {
    if (!currentToken) return;
    
    if (backtestConfig.token_addresses.includes(currentToken)) {
      toast.error('Token already added');
      return;
    }

    setBacktestConfig({
      ...backtestConfig,
      token_addresses: [...backtestConfig.token_addresses, currentToken]
    });
    setCurrentToken('');
  };

  const removeToken = (token) => {
    setBacktestConfig({
      ...backtestConfig,
      token_addresses: backtestConfig.token_addresses.filter(t => t !== token)
    });
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Run Backtest</Typography>
      
      <Grid container spacing={3}>
        {/* Strategy Selection */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>1. Select Strategy</Typography>
              
              <FormControl fullWidth>
                <InputLabel>Strategy</InputLabel>
                <Select
                  value={backtestConfig.strategy_id}
                  onChange={(e) => setBacktestConfig({ ...backtestConfig, strategy_id: e.target.value })}
                  label="Strategy"
                >
                  {strategies.map((strategy) => (
                    <MenuItem key={strategy.id} value={strategy.id}>
                      {strategy.name} - {strategy.description}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </CardContent>
          </Card>
        </Grid>

        {/* Token Selection */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>2. Select Tokens</Typography>
              
              <Box mb={2}>
                <Typography variant="body2" gutterBottom>Popular Tokens:</Typography>
                <Box display="flex" gap={1}>
                  {popularTokens.map((token) => (
                    <Chip
                      key={token.address}
                      label={token.symbol}
                      onClick={() => setCurrentToken(token.address)}
                      variant="outlined"
                      size="small"
                    />
                  ))}
                </Box>
              </Box>

              <Box display="flex" gap={2} mb={2}>
                <TextField
                  fullWidth
                  label="Token Address"
                  value={currentToken}
                  onChange={(e) => setCurrentToken(e.target.value)}
                  placeholder="Enter Solana token address"
                />
                <Button
                  variant="contained"
                  onClick={addToken}
                  startIcon={<AddIcon />}
                >
                  Add
                </Button>
              </Box>

              {backtestConfig.token_addresses.length > 0 && (
                <List dense>
                  {backtestConfig.token_addresses.map((token) => (
                    <ListItem
                      key={token}
                      secondaryAction={
                        <IconButton edge="end" onClick={() => removeToken(token)}>
                          <DeleteIcon />
                        </IconButton>
                      }
                    >
                      <ListItemText 
                        primary={token}
                        primaryTypographyProps={{ 
                          style: { 
                            fontFamily: 'monospace',
                            fontSize: '0.875rem'
                          } 
                        }}
                      />
                    </ListItem>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Time Period */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>3. Select Time Period</Typography>
              
              <LocalizationProvider dateAdapter={AdapterDateFns}>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <DateTimePicker
                      label="Start Date"
                      value={backtestConfig.start_date}
                      onChange={(newValue) => 
                        setBacktestConfig({ ...backtestConfig, start_date: newValue })
                      }
                      slotProps={{ textField: { fullWidth: true } }}
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <DateTimePicker
                      label="End Date"
                      value={backtestConfig.end_date}
                      onChange={(newValue) => 
                        setBacktestConfig({ ...backtestConfig, end_date: newValue })
                      }
                      slotProps={{ textField: { fullWidth: true } }}
                    />
                  </Grid>
                </Grid>
              </LocalizationProvider>
            </CardContent>
          </Card>
        </Grid>

        {/* Parameters */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>4. Backtest Parameters</Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Initial Capital (USD)"
                    type="number"
                    value={backtestConfig.initial_capital}
                    onChange={(e) => 
                      setBacktestConfig({ ...backtestConfig, initial_capital: Number(e.target.value) })
                    }
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Position Size (%)"
                    type="number"
                    value={backtestConfig.position_size * 100}
                    onChange={(e) => 
                      setBacktestConfig({ ...backtestConfig, position_size: Number(e.target.value) / 100 })
                    }
                    InputProps={{
                      endAdornment: '%'
                    }}
                  />
                </Grid>
                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    label="Stop Loss (%)"
                    type="number"
                    value={backtestConfig.exit_strategy.stop_loss * 100}
                    onChange={(e) => 
                      setBacktestConfig({ 
                        ...backtestConfig, 
                        exit_strategy: {
                          ...backtestConfig.exit_strategy,
                          stop_loss: Number(e.target.value) / 100
                        }
                      })
                    }
                    InputProps={{
                      endAdornment: '%'
                    }}
                  />
                </Grid>
                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    label="Take Profit (%)"
                    type="number"
                    value={backtestConfig.exit_strategy.take_profit * 100}
                    onChange={(e) => 
                      setBacktestConfig({ 
                        ...backtestConfig, 
                        exit_strategy: {
                          ...backtestConfig.exit_strategy,
                          take_profit: Number(e.target.value) / 100
                        }
                      })
                    }
                    InputProps={{
                      endAdornment: '%'
                    }}
                  />
                </Grid>
                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    label="Hold Duration (seconds)"
                    type="number"
                    value={backtestConfig.exit_strategy.hold_duration}
                    onChange={(e) => 
                      setBacktestConfig({ 
                        ...backtestConfig, 
                        exit_strategy: {
                          ...backtestConfig.exit_strategy,
                          hold_duration: Number(e.target.value)
                        }
                      })
                    }
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Run Button */}
        <Grid item xs={12}>
          <Box display="flex" justifyContent="center">
            <Button
              variant="contained"
              size="large"
              onClick={handleRunBacktest}
              disabled={loading}
              startIcon={loading ? <CircularProgress size={20} /> : <RunIcon />}
            >
              {loading ? 'Running Backtest...' : 'Run Backtest'}
            </Button>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
}

export default BacktestRunner;