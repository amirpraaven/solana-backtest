import React, { useState, useEffect } from 'react';
import {
  Box,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  TextField,
  Chip,
  CircularProgress,
  IconButton,
  Typography,
  Grid,
  Card,
  CardContent,
  Alert
} from '@mui/material';
import {
  Add as AddIcon,
  Search as SearchIcon,
  TrendingUp as TrendingIcon,
  FiberNew as NewIcon,
  Info as InfoIcon
} from '@mui/icons-material';
import { tokenAPI } from '../api';
import toast from 'react-hot-toast';

function TokenSelector({ open, onClose, onTokensSelected, selectedTokens = [] }) {
  const [tab, setTab] = useState(0);
  const [tokens, setTokens] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selected, setSelected] = useState(new Set(selectedTokens));
  
  // Filters
  const [timeFrame, setTimeFrame] = useState('24h');
  const [sortBy, setSortBy] = useState('volume');
  const [maxAge, setMaxAge] = useState(24);
  const [minLiquidity, setMinLiquidity] = useState(1000);

  useEffect(() => {
    if (open) {
      loadTokens();
    }
  }, [open, tab]);

  const loadTokens = async () => {
    setLoading(true);
    try {
      let response;
      
      switch (tab) {
        case 0: // Trending
          response = await tokenAPI.getTrending(timeFrame, sortBy, 50);
          break;
        case 1: // New Listings
          response = await tokenAPI.getNewListings(maxAge, minLiquidity, 50);
          break;
        case 2: // Search
          if (searchQuery.length > 0) {
            response = await tokenAPI.searchTokens(searchQuery, 20);
          } else {
            response = { data: { tokens: [] } };
          }
          break;
        default:
          response = { data: { tokens: [] } };
      }
      
      setTokens(response.data.tokens || []);
    } catch (error) {
      console.error('Error loading tokens:', error);
      toast.error('Failed to load tokens');
      setTokens([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      loadTokens();
    }
  };

  const toggleSelection = (token) => {
    const newSelected = new Set(selected);
    if (newSelected.has(token.address)) {
      newSelected.delete(token.address);
    } else {
      newSelected.add(token.address);
    }
    setSelected(newSelected);
  };

  const handleConfirm = () => {
    const selectedTokenData = tokens
      .filter(t => selected.has(t.address))
      .map(t => ({
        address: t.address,
        symbol: t.symbol,
        name: t.name
      }));
    
    onTokensSelected(selectedTokenData);
    onClose();
  };

  const formatNumber = (num) => {
    if (!num) return '0';
    if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
    if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
    if (num >= 1e3) return `$${(num / 1e3).toFixed(2)}K`;
    return `$${num.toFixed(2)}`;
  };

  const formatAge = (hours) => {
    if (!hours) return 'Unknown';
    if (hours < 1) return `${Math.round(hours * 60)}m`;
    if (hours < 24) return `${Math.round(hours)}h`;
    return `${Math.round(hours / 24)}d`;
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        Select Tokens for Backtest
        <Typography variant="body2" color="text.secondary">
          Selected: {selected.size} token{selected.size !== 1 ? 's' : ''}
        </Typography>
      </DialogTitle>
      
      <DialogContent>
        <Tabs value={tab} onChange={(e, v) => setTab(v)} sx={{ mb: 2 }}>
          <Tab icon={<TrendingIcon />} label="Trending" />
          <Tab icon={<NewIcon />} label="New Listings" />
          <Tab icon={<SearchIcon />} label="Search" />
        </Tabs>

        {/* Trending Tab */}
        {tab === 0 && (
          <Box>
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={6}>
                <TextField
                  select
                  fullWidth
                  size="small"
                  label="Time Frame"
                  value={timeFrame}
                  onChange={(e) => setTimeFrame(e.target.value)}
                  SelectProps={{ native: true }}
                >
                  <option value="5m">5 minutes</option>
                  <option value="15m">15 minutes</option>
                  <option value="30m">30 minutes</option>
                  <option value="1h">1 hour</option>
                  <option value="4h">4 hours</option>
                  <option value="24h">24 hours</option>
                </TextField>
              </Grid>
              <Grid item xs={6}>
                <TextField
                  select
                  fullWidth
                  size="small"
                  label="Sort By"
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  SelectProps={{ native: true }}
                >
                  <option value="volume">Volume</option>
                  <option value="price_change">Price Change</option>
                  <option value="trades">Trade Count</option>
                  <option value="liquidity">Liquidity</option>
                </TextField>
              </Grid>
            </Grid>
          </Box>
        )}

        {/* New Listings Tab */}
        {tab === 1 && (
          <Box>
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={6}>
                <TextField
                  type="number"
                  fullWidth
                  size="small"
                  label="Max Age (hours)"
                  value={maxAge}
                  onChange={(e) => setMaxAge(parseInt(e.target.value))}
                />
              </Grid>
              <Grid item xs={6}>
                <TextField
                  type="number"
                  fullWidth
                  size="small"
                  label="Min Liquidity ($)"
                  value={minLiquidity}
                  onChange={(e) => setMinLiquidity(parseInt(e.target.value))}
                />
              </Grid>
            </Grid>
          </Box>
        )}

        {/* Search Tab */}
        {tab === 2 && (
          <Box component="form" onSubmit={handleSearch} sx={{ mb: 2 }}>
            <TextField
              fullWidth
              size="small"
              label="Search by symbol or address"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              InputProps={{
                endAdornment: (
                  <IconButton type="submit" size="small">
                    <SearchIcon />
                  </IconButton>
                )
              }}
            />
          </Box>
        )}

        {/* Apply Filters Button */}
        {tab !== 2 && (
          <Box sx={{ mb: 2 }}>
            <Button
              variant="outlined"
              size="small"
              onClick={loadTokens}
              disabled={loading}
            >
              Apply Filters
            </Button>
          </Box>
        )}

        {/* Token List */}
        {loading ? (
          <Box display="flex" justifyContent="center" p={4}>
            <CircularProgress />
          </Box>
        ) : tokens.length === 0 ? (
          <Alert severity="info">
            {tab === 2 && !searchQuery ? 
              "Enter a token symbol or address to search" : 
              "No tokens found"
            }
          </Alert>
        ) : (
          <List sx={{ maxHeight: 400, overflow: 'auto' }}>
            {tokens.map((token) => (
              <ListItem
                key={token.address}
                button
                onClick={() => toggleSelection(token)}
                selected={selected.has(token.address)}
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
                  secondary={
                    <Box>
                      <Typography variant="caption" component="div">
                        {token.address}
                      </Typography>
                      <Box display="flex" gap={1} mt={0.5}>
                        {token.price !== undefined && (
                          <Chip size="small" label={`$${token.price.toFixed(6)}`} />
                        )}
                        {token.liquidity !== undefined && (
                          <Chip size="small" label={`Liq: ${formatNumber(token.liquidity)}`} />
                        )}
                        {token.volume_24h !== undefined && (
                          <Chip size="small" label={`Vol: ${formatNumber(token.volume_24h)}`} />
                        )}
                        {token.age_hours !== undefined && (
                          <Chip size="small" label={`Age: ${formatAge(token.age_hours)}`} />
                        )}
                        {token.price_change_24h !== undefined && (
                          <Chip 
                            size="small" 
                            label={`${token.price_change_24h > 0 ? '+' : ''}${token.price_change_24h.toFixed(2)}%`}
                            color={token.price_change_24h > 0 ? 'success' : 'error'}
                          />
                        )}
                      </Box>
                    </Box>
                  }
                />
                <ListItemSecondaryAction>
                  <Chip
                    label={selected.has(token.address) ? "Selected" : "Select"}
                    color={selected.has(token.address) ? "primary" : "default"}
                    onClick={() => toggleSelection(token)}
                  />
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        )}
      </DialogContent>
      
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button 
          onClick={handleConfirm} 
          variant="contained" 
          disabled={selected.size === 0}
        >
          Add {selected.size} Token{selected.size !== 1 ? 's' : ''}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default TokenSelector;