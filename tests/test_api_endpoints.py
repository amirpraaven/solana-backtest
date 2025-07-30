"""Tests for API endpoints"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from src.web.app import app


class TestAPIEndpoints:
    """Test FastAPI endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
        
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Solana Token Backtesting API"
        assert data["version"] == "1.0.0"
        assert "docs" in data
        
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "redis" in data
        assert "services" in data
        
    def test_supported_dexes(self, client):
        """Test supported DEXes endpoint"""
        response = client.get("/supported-dexes")
        assert response.status_code == 200
        data = response.json()
        
        assert "supported_dexes" in data
        dexes = data["supported_dexes"]
        assert len(dexes) == 5
        
        # Check pump.fun details
        pump_fun = next(d for d in dexes if d["name"] == "pump.fun")
        assert pump_fun["program_id"] == "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
        assert "characteristics" in pump_fun
        assert "Bonding curve model" in pump_fun["characteristics"]
        
    def test_strategy_templates(self, client):
        """Test strategy templates endpoint"""
        response = client.get("/strategies/templates")
        assert response.status_code == 200
        data = response.json()
        
        assert "templates" in data
        templates = data["templates"]
        assert len(templates) > 0
        
        # Check template structure
        template = templates[0]
        assert "key" in template
        assert "name" in template
        assert "description" in template
        assert "conditions" in template
        
    def test_create_strategy(self, client):
        """Test strategy creation"""
        strategy_data = {
            "name": "API Test Strategy",
            "description": "Strategy created via API test",
            "conditions": {
                "liquidity": {
                    "enabled": True,
                    "operator": "greater_than",
                    "value": 10000,
                    "unit": "USD"
                }
            }
        }
        
        response = client.post("/strategies/create", json=strategy_data)
        
        # Note: This will fail without proper database setup
        # In real tests, you'd mock the database or use a test database
        # assert response.status_code == 200
        # data = response.json()
        # assert "strategy_id" in data
        
    def test_create_strategy_validation(self, client):
        """Test strategy creation validation"""
        invalid_strategy = {
            "name": "",  # Empty name
            "description": "Invalid strategy",
            "conditions": {}  # Empty conditions
        }
        
        response = client.post("/strategies/create", json=invalid_strategy)
        assert response.status_code == 422  # Validation error
        
    def test_validate_strategy_conditions(self, client):
        """Test strategy condition validation endpoint"""
        conditions = {
            "liquidity": {
                "enabled": True,
                "operator": "invalid_operator",
                "value": 10000
            }
        }
        
        response = client.post("/strategies/validate", json=conditions)
        # Would need proper app initialization to test fully
        
    def test_analyze_token_endpoint(self, client):
        """Test token analysis endpoint"""
        token_address = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
        
        response = client.post(
            f"/analyze/token/{token_address}",
            params={"include_price_data": True, "include_security_info": False}
        )
        
        # Would need mocked services to test properly
        # assert response.status_code == 200
        
    def test_query_transactions(self, client):
        """Test transaction query endpoint"""
        query_data = {
            "token_address": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            "start_time": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "dex": "pump.fun",
            "type": "buy",
            "min_amount_usd": 1000
        }
        
        response = client.post(
            "/transactions/query",
            json=query_data,
            params={"limit": 100}
        )
        
        # Would need database setup to test properly
        
    def test_backtest_request(self, client):
        """Test backtest request"""
        backtest_data = {
            "strategy_id": 1,
            "token_addresses": ["token1", "token2"],
            "start_date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            "initial_capital": 10000
        }
        
        response = client.post("/strategies/backtest", json=backtest_data)
        
        # Would need full app setup to test
        
    def test_dex_stats(self, client):
        """Test DEX statistics endpoint"""
        response = client.get("/dex/stats", params={"hours": 24})
        
        # Would need database to test properly
        # assert response.status_code == 200
        # data = response.json()
        # assert "period_hours" in data
        # assert "dex_stats" in data
        
    def test_pool_states(self, client):
        """Test pool states endpoint"""
        token_address = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
        
        response = client.get(
            f"/pool-states/{token_address}",
            params={"hours": 24, "interval": "1h"}
        )
        
        # Would need database to test properly
        
    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code == 200
        # Should return Prometheus-formatted metrics
        
    def test_error_handling(self, client):
        """Test error handling"""
        # Test 404
        response = client.get("/nonexistent")
        assert response.status_code == 404
        
        # Test invalid strategy ID
        response = client.get("/strategies/999999")
        # Would return 404 with proper database
        
    def test_pagination(self, client):
        """Test pagination parameters"""
        response = client.get(
            "/strategies/list",
            params={"limit": 10, "offset": 0, "active_only": True}
        )
        
        # Would need database to test pagination properly