import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Grid,
  Typography,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Switch,
  Chip,
  Alert
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  ContentCopy as CopyIcon
} from '@mui/icons-material';
import toast from 'react-hot-toast';
import { strategyAPI } from '../api';

function StrategyManager({ strategies, setStrategies }) {
  const [open, setOpen] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    conditions: {
      token_age: {
        enabled: false,
        operator: 'less_than',
        value: 3,
        unit: 'days'
      },
      liquidity: {
        enabled: false,
        operator: 'greater_than',
        value: 10000
      },
      volume_24h: {
        enabled: false,
        operator: 'greater_than',
        value: 50000
      },
      price_change_5m: {
        enabled: false,
        operator: 'greater_than',
        value: 5
      },
      large_buys: {
        enabled: false,
        min_count: 5,
        min_amount: 1000,
        window_seconds: 30
      }
    }
  });

  useEffect(() => {
    loadStrategies();
    loadTemplates();
  }, []);

  const loadStrategies = async () => {
    try {
      const response = await strategyAPI.getAll();
      setStrategies(response.data);
    } catch (error) {
      toast.error('Failed to load strategies');
    }
  };

  const loadTemplates = async () => {
    try {
      const response = await strategyAPI.getTemplates();
      setTemplates(response.data);
    } catch (error) {
      console.error('Failed to load templates');
    }
  };

  const handleCreateStrategy = async () => {
    try {
      const response = await strategyAPI.create(formData);
      toast.success('Strategy created successfully');
      setStrategies([...strategies, response.data]);
      setOpen(false);
      resetForm();
    } catch (error) {
      toast.error('Failed to create strategy');
    }
  };

  const handleDeleteStrategy = async (id) => {
    if (!window.confirm('Are you sure you want to delete this strategy?')) return;
    
    try {
      await strategyAPI.delete(id);
      toast.success('Strategy deleted');
      setStrategies(strategies.filter(s => s.id !== id));
    } catch (error) {
      toast.error('Failed to delete strategy');
    }
  };

  const handleCreateFromTemplate = async (templateName) => {
    try {
      const response = await strategyAPI.createFromTemplate({
        template_name: templateName,
        custom_name: `${templateName}_${Date.now()}`
      });
      toast.success('Strategy created from template');
      setStrategies([...strategies, response.data]);
    } catch (error) {
      toast.error('Failed to create from template');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      conditions: {
        token_age: {
          enabled: false,
          operator: 'less_than',
          value: 3,
          unit: 'days'
        },
        liquidity: {
          enabled: false,
          operator: 'greater_than',
          value: 10000
        },
        volume_24h: {
          enabled: false,
          operator: 'greater_than',
          value: 50000
        },
        price_change_5m: {
          enabled: false,
          operator: 'greater_than',
          value: 5
        },
        large_buys: {
          enabled: false,
          min_count: 5,
          min_amount: 1000,
          window_seconds: 30
        }
      }
    });
  };

  const updateCondition = (conditionKey, field, value) => {
    setFormData({
      ...formData,
      conditions: {
        ...formData.conditions,
        [conditionKey]: {
          ...formData.conditions[conditionKey],
          [field]: value
        }
      }
    });
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5">Strategy Management</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setOpen(true)}
        >
          Create Strategy
        </Button>
      </Box>

      {/* Templates */}
      {templates.length > 0 && (
        <Box mb={3}>
          <Typography variant="h6" gutterBottom>Quick Start Templates</Typography>
          <Grid container spacing={2}>
            {Object.entries(templates).map(([key, template]) => (
              <Grid item xs={12} sm={6} md={4} key={key}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="subtitle1" fontWeight="bold">
                      {template.name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      {template.description}
                    </Typography>
                    <Button
                      size="small"
                      startIcon={<CopyIcon />}
                      onClick={() => handleCreateFromTemplate(key)}
                    >
                      Use Template
                    </Button>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}

      {/* Strategies List */}
      <Grid container spacing={2}>
        {strategies.map((strategy) => (
          <Grid item xs={12} md={6} key={strategy.id}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="start">
                  <Box>
                    <Typography variant="h6">{strategy.name}</Typography>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      {strategy.description}
                    </Typography>
                    <Box mt={1}>
                      {strategy.is_active ? (
                        <Chip label="Active" color="success" size="small" />
                      ) : (
                        <Chip label="Inactive" color="default" size="small" />
                      )}
                    </Box>
                  </Box>
                  <Box>
                    <IconButton size="small" onClick={() => handleDeleteStrategy(strategy.id)}>
                      <DeleteIcon />
                    </IconButton>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Create Strategy Dialog */}
      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Create New Strategy</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <TextField
              fullWidth
              label="Strategy Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              margin="normal"
            />
            
            <TextField
              fullWidth
              label="Description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              margin="normal"
              multiline
              rows={2}
            />

            <Typography variant="h6" sx={{ mt: 3, mb: 2 }}>Conditions</Typography>

            {/* Token Age Condition */}
            <Card variant="outlined" sx={{ mb: 2, p: 2 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.conditions.token_age.enabled}
                    onChange={(e) => updateCondition('token_age', 'enabled', e.target.checked)}
                  />
                }
                label="Token Age"
              />
              {formData.conditions.token_age.enabled && (
                <Box sx={{ mt: 2 }}>
                  <Grid container spacing={2}>
                    <Grid item xs={4}>
                      <FormControl fullWidth size="small">
                        <InputLabel>Operator</InputLabel>
                        <Select
                          value={formData.conditions.token_age.operator}
                          onChange={(e) => updateCondition('token_age', 'operator', e.target.value)}
                          label="Operator"
                        >
                          <MenuItem value="less_than">Less than</MenuItem>
                          <MenuItem value="greater_than">Greater than</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={4}>
                      <TextField
                        fullWidth
                        size="small"
                        type="number"
                        label="Value"
                        value={formData.conditions.token_age.value}
                        onChange={(e) => updateCondition('token_age', 'value', Number(e.target.value))}
                      />
                    </Grid>
                    <Grid item xs={4}>
                      <FormControl fullWidth size="small">
                        <InputLabel>Unit</InputLabel>
                        <Select
                          value={formData.conditions.token_age.unit}
                          onChange={(e) => updateCondition('token_age', 'unit', e.target.value)}
                          label="Unit"
                        >
                          <MenuItem value="hours">Hours</MenuItem>
                          <MenuItem value="days">Days</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                  </Grid>
                </Box>
              )}
            </Card>

            {/* Liquidity Condition */}
            <Card variant="outlined" sx={{ mb: 2, p: 2 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.conditions.liquidity.enabled}
                    onChange={(e) => updateCondition('liquidity', 'enabled', e.target.checked)}
                  />
                }
                label="Liquidity (USD)"
              />
              {formData.conditions.liquidity.enabled && (
                <Box sx={{ mt: 2 }}>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <FormControl fullWidth size="small">
                        <InputLabel>Operator</InputLabel>
                        <Select
                          value={formData.conditions.liquidity.operator}
                          onChange={(e) => updateCondition('liquidity', 'operator', e.target.value)}
                          label="Operator"
                        >
                          <MenuItem value="greater_than">Greater than</MenuItem>
                          <MenuItem value="less_than">Less than</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={6}>
                      <TextField
                        fullWidth
                        size="small"
                        type="number"
                        label="Value (USD)"
                        value={formData.conditions.liquidity.value}
                        onChange={(e) => updateCondition('liquidity', 'value', Number(e.target.value))}
                      />
                    </Grid>
                  </Grid>
                </Box>
              )}
            </Card>

            <Box sx={{ mt: 3, display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
              <Button onClick={() => setOpen(false)}>Cancel</Button>
              <Button variant="contained" onClick={handleCreateStrategy}>
                Create Strategy
              </Button>
            </Box>
          </Box>
        </DialogContent>
      </Dialog>
    </Box>
  );
}

export default StrategyManager;