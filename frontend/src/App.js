import React, { useState } from 'react';
import { 
  Container, 
  AppBar, 
  Toolbar, 
  Typography, 
  Box, 
  Tab, 
  Tabs,
  Paper
} from '@mui/material';
import { Toaster } from 'react-hot-toast';
import StrategyManager from './components/StrategyManager';
import BacktestRunner from './components/BacktestRunner';
import Results from './components/Results';
import './App.css';

function TabPanel({ children, value, index }) {
  return (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

function App() {
  const [tabValue, setTabValue] = useState(0);
  const [strategies, setStrategies] = useState([]);
  const [backtestResults, setBacktestResults] = useState([]);

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  return (
    <div className="App">
      <Toaster position="top-right" />
      
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Solana Token Backtesting System
          </Typography>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Paper elevation={3}>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={tabValue} onChange={handleTabChange}>
              <Tab label="Strategies" />
              <Tab label="Run Backtest" />
              <Tab label="Results" />
            </Tabs>
          </Box>

          <TabPanel value={tabValue} index={0}>
            <StrategyManager 
              strategies={strategies} 
              setStrategies={setStrategies} 
            />
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <BacktestRunner 
              strategies={strategies}
              onBacktestComplete={(result) => {
                setBacktestResults([result, ...backtestResults]);
                setTabValue(2); // Switch to results tab
              }}
            />
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            <Results results={backtestResults} />
          </TabPanel>
        </Paper>
      </Container>
    </div>
  );
}

export default App;