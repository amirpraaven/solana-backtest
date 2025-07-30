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
    },
    
    "backtest_recipe_v12": {
        "name": "Backtest Recipe v1.2",
        "description": "MC band-based strategy with 5-minute slices and ladder exits",
        "conditions": {
            "token_age": {
                "enabled": True,
                "operator": "less_than_equal",
                "value": 30,
                "unit": "days"
            },
            "custom": {
                "enabled": True,
                "type": "mc_band_big_buys",
                "slice_duration": 300,  # 5 minutes
                "mc_bands": [
                    [100000, 300, 1500],      # <= $100k: $300+ buys, $1.5k total
                    [400000, 1000, 5000],     # <= $400k: $1k+ buys, $5k total (min 5 buys)
                    [1000000, 2000, 10000],   # <= $1m: $2k-$4k buys, $10k total
                    [2000000, 4000, 20000]    # <= $2m: $4k-$12k buys, $20k total
                ]
            }
        },
        "entry": {
            "type": "fixed_sol",
            "amount": 1.0  # Buy 1 SOL worth
        },
        "exit": {
            "type": "ladder",
            "targets": [
                [2.0, 0.3],   # At 2x: sell to lock 70% profit
                [7.0, 0.5]    # At 7x: sell 50% of remainder
            ]
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