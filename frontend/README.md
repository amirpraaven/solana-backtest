# Solana Backtest Frontend

A React-based UI for the Solana Token Backtesting System.

## Features

- **Strategy Management**: Create, edit, and manage trading strategies with flexible conditions
- **Backtest Runner**: Configure and run backtests with custom parameters
- **Results Visualization**: View detailed backtest results with charts and metrics
- **Real-time Updates**: Live status updates during backtest execution

## Local Development

1. Install dependencies:
```bash
npm install
```

2. Create `.env` file:
```bash
cp .env.example .env
# Edit .env and set REACT_APP_API_URL to your backend URL
```

3. Start development server:
```bash
npm start
```

The app will open at http://localhost:3000

## Production Build

```bash
npm run build
```

This creates an optimized production build in the `build/` directory.

## Deployment to Railway

### Option 1: Deploy with Backend (Recommended)

Add the frontend build to your main repository and serve it from FastAPI:

1. Build the frontend:
```bash
cd frontend
npm install
npm run build
```

2. Update your backend to serve the frontend (already configured in the main app)

### Option 2: Separate Frontend Deployment

1. Create a new Railway service for the frontend
2. Set the build command: `cd frontend && npm install && npm run build`
3. Set the start command: `npx serve -s frontend/build`
4. Add environment variable: `REACT_APP_API_URL=https://your-backend.railway.app`

## Environment Variables

- `REACT_APP_API_URL`: Backend API URL (defaults to http://localhost:8000 for development)

## UI Components

### Strategy Manager
- Create strategies with configurable conditions
- Use pre-built templates
- View and manage existing strategies

### Backtest Runner
- Select strategies and tokens
- Configure time periods and parameters
- Set risk management rules

### Results Viewer
- Equity curve visualization
- Win/loss distribution
- Detailed trade analysis
- Performance metrics

## Tech Stack

- React 18
- Material-UI 5
- Recharts for data visualization
- Axios for API calls
- React Hot Toast for notifications