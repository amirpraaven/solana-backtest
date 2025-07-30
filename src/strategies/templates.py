"""Pre-built strategy templates for common trading patterns"""

STRATEGY_TEMPLATES = {
    "early_momentum": {
        "name": "Early Token Momentum",
        "description": "Detect momentum in new tokens (< 3 days)",
        "conditions": {
            "token_age": {
                "enabled": True,
                "operator": "less_than",
                "value": 3,
                "unit": "days"
            },
            "liquidity": {
                "enabled": True,
                "operator": "greater_than",
                "value": 10000,
                "unit": "USD"
            },
            "volume_window": {
                "enabled": True,
                "window_seconds": 30,
                "operator": "greater_than_equal",
                "value": 5000,
                "unit": "USD"
            },
            "market_cap": {
                "enabled": True,
                "operator": "less_than",
                "value": 300000,
                "unit": "USD"
            },
            "large_buys": {
                "enabled": True,
                "min_count": 5,
                "min_amount": 1000,
                "window_seconds": 30
            }
        }
    },
    
    "micro_cap_surge": {
        "name": "Micro Cap Surge",
        "description": "Detect surges in very small cap tokens",
        "conditions": {
            "market_cap": {
                "enabled": True,
                "operator": "less_than",
                "value": 100000,
                "unit": "USD"
            },
            "liquidity": {
                "enabled": True,
                "operator": "greater_than",
                "value": 5000,
                "unit": "USD"
            },
            "volume_window": {
                "enabled": True,
                "window_seconds": 10,
                "operator": "greater_than",
                "value": 2000,
                "unit": "USD"
            },
            "large_buys": {
                "enabled": True,
                "min_count": 3,
                "min_amount": 500,
                "window_seconds": 10
            }
        }
    },
    
    "fresh_launch": {
        "name": "Fresh Launch Detection",
        "description": "Catch tokens in first hour of trading",
        "conditions": {
            "token_age": {
                "enabled": True,
                "operator": "less_than",
                "value": 1,
                "unit": "hours"
            },
            "liquidity": {
                "enabled": True,
                "operator": "greater_than",
                "value": 5000,
                "unit": "USD"
            },
            "volume_window": {
                "enabled": True,
                "window_seconds": 30,
                "operator": "greater_than",
                "value": 1000,
                "unit": "USD"
            },
            "large_buys": {
                "enabled": True,
                "min_count": 3,
                "min_amount": 500,
                "window_seconds": 30
            }
        }
    },
    
    "high_volume_breakout": {
        "name": "High Volume Breakout",
        "description": "Detect sudden volume increases",
        "conditions": {
            "volume_window": {
                "enabled": True,
                "window_seconds": 60,
                "operator": "greater_than",
                "value": 10000,
                "unit": "USD"
            },
            "buy_pressure": {
                "enabled": True,
                "operator": "greater_than",
                "value": 2.0
            },
            "unique_wallets": {
                "enabled": True,
                "operator": "greater_than_equal",
                "value": 10
            },
            "liquidity": {
                "enabled": True,
                "operator": "greater_than",
                "value": 20000,
                "unit": "USD"
            }
        }
    },
    
    "pump_fun_graduate": {
        "name": "pump.fun Graduation",
        "description": "Tokens approaching Raydium graduation",
        "conditions": {
            "market_cap": {
                "enabled": True,
                "operator": "greater_than",
                "value": 50000,
                "unit": "USD"
            },
            "market_cap": {
                "enabled": True,
                "operator": "less_than",
                "value": 70000,
                "unit": "USD"
            },
            "volume_window": {
                "enabled": True,
                "window_seconds": 300,
                "operator": "greater_than",
                "value": 5000,
                "unit": "USD"
            },
            "buy_pressure": {
                "enabled": True,
                "operator": "greater_than",
                "value": 1.5
            }
        }
    },
    
    "whale_accumulation": {
        "name": "Whale Accumulation",
        "description": "Large buyers accumulating positions",
        "conditions": {
            "large_buys": {
                "enabled": True,
                "min_count": 3,
                "min_amount": 5000,
                "window_seconds": 300
            },
            "buy_pressure": {
                "enabled": True,
                "operator": "greater_than",
                "value": 3.0
            },
            "liquidity": {
                "enabled": True,
                "operator": "greater_than",
                "value": 50000,
                "unit": "USD"
            }
        }
    }
}

def get_template(template_name: str) -> dict:
    """Get a strategy template by name"""
    return STRATEGY_TEMPLATES.get(template_name, {}).copy()

def list_templates() -> list:
    """List all available templates"""
    return [
        {
            "key": key,
            "name": template["name"],
            "description": template["description"]
        }
        for key, template in STRATEGY_TEMPLATES.items()
    ]