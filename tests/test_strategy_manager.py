"""Tests for strategy management"""

import pytest
from src.strategies import StrategyManager, STRATEGY_TEMPLATES


class TestStrategyManager:
    """Test strategy CRUD operations"""
    
    @pytest.mark.asyncio
    async def test_create_strategy(self, strategy_manager):
        """Test creating a new strategy"""
        
        strategy_id = await strategy_manager.create_strategy(
            name="Test Strategy",
            description="A test strategy",
            conditions={
                "liquidity": {
                    "enabled": True,
                    "operator": "greater_than",
                    "value": 10000
                }
            }
        )
        
        assert isinstance(strategy_id, int)
        assert strategy_id > 0
        
        # Verify strategy was created
        strategy = await strategy_manager.get_strategy(strategy_id)
        assert strategy is not None
        assert strategy['name'] == "Test Strategy"
        assert strategy['description'] == "A test strategy"
        assert 'liquidity' in strategy['conditions']
        
    @pytest.mark.asyncio
    async def test_create_duplicate_strategy(self, strategy_manager):
        """Test creating duplicate strategy name"""
        
        # Create first strategy
        await strategy_manager.create_strategy(
            name="Unique Strategy",
            description="First",
            conditions={"liquidity": {"enabled": True, "value": 1000}}
        )
        
        # Try to create duplicate
        with pytest.raises(ValueError, match="already exists"):
            await strategy_manager.create_strategy(
                name="Unique Strategy",
                description="Second",
                conditions={"liquidity": {"enabled": True, "value": 2000}}
            )
            
    @pytest.mark.asyncio
    async def test_create_from_template(self, strategy_manager):
        """Test creating strategy from template"""
        
        strategy_id = await strategy_manager.create_from_template(
            "early_momentum",
            custom_name="My Early Momentum"
        )
        
        strategy = await strategy_manager.get_strategy(strategy_id)
        assert strategy['name'] == "My Early Momentum"
        assert 'token_age' in strategy['conditions']
        assert strategy['conditions']['token_age']['value'] == 3
        
    @pytest.mark.asyncio
    async def test_create_from_template_with_modifications(self, strategy_manager):
        """Test creating strategy from template with modifications"""
        
        modifications = {
            "liquidity": {"value": 20000},
            "token_age": {"value": 5}
        }
        
        strategy_id = await strategy_manager.create_from_template(
            "early_momentum",
            modifications=modifications
        )
        
        strategy = await strategy_manager.get_strategy(strategy_id)
        assert strategy['conditions']['liquidity']['value'] == 20000
        assert strategy['conditions']['token_age']['value'] == 5
        
    @pytest.mark.asyncio
    async def test_update_strategy(self, strategy_manager, sample_strategy):
        """Test updating strategy"""
        
        # Update name and conditions
        updated = await strategy_manager.update_strategy(
            sample_strategy['id'],
            name="Updated Strategy",
            conditions={
                "market_cap": {
                    "enabled": True,
                    "operator": "less_than",
                    "value": 500000
                }
            }
        )
        
        assert updated is True
        
        # Verify updates
        strategy = await strategy_manager.get_strategy(sample_strategy['id'])
        assert strategy['name'] == "Updated Strategy"
        assert 'market_cap' in strategy['conditions']
        
    @pytest.mark.asyncio
    async def test_delete_strategy(self, strategy_manager, sample_strategy):
        """Test soft deleting strategy"""
        
        deleted = await strategy_manager.delete_strategy(sample_strategy['id'])
        assert deleted is True
        
        # Verify strategy is inactive
        strategies = await strategy_manager.list_strategies(active_only=True)
        assert not any(s['id'] == sample_strategy['id'] for s in strategies)
        
        # Should still exist but inactive
        all_strategies = await strategy_manager.list_strategies(active_only=False)
        deleted_strategy = next(
            (s for s in all_strategies if s['id'] == sample_strategy['id']),
            None
        )
        assert deleted_strategy is not None
        assert deleted_strategy['is_active'] is False
        
    @pytest.mark.asyncio
    async def test_duplicate_strategy(self, strategy_manager, sample_strategy):
        """Test duplicating a strategy"""
        
        new_id = await strategy_manager.duplicate_strategy(
            sample_strategy['id'],
            "Duplicated Strategy"
        )
        
        new_strategy = await strategy_manager.get_strategy(new_id)
        assert new_strategy['name'] == "Duplicated Strategy"
        assert new_strategy['conditions'] == sample_strategy['conditions']
        assert new_strategy['id'] != sample_strategy['id']
        
    @pytest.mark.asyncio
    async def test_validate_strategy(self, strategy_manager):
        """Test strategy validation"""
        
        # Valid conditions
        valid_conditions = {
            "liquidity": {
                "enabled": True,
                "operator": "greater_than",
                "value": 10000
            }
        }
        
        errors = await strategy_manager.validate_strategy(valid_conditions)
        assert len(errors) == 0
        
        # Invalid operator
        invalid_conditions = {
            "liquidity": {
                "enabled": True,
                "operator": "invalid_op",
                "value": 10000
            }
        }
        
        errors = await strategy_manager.validate_strategy(invalid_conditions)
        assert 'liquidity' in errors
        assert any("Invalid operator" in e for e in errors['liquidity'])
        
        # Missing required field
        missing_field = {
            "large_buys": {
                "enabled": True,
                "min_count": 5
                # Missing min_amount
            }
        }
        
        errors = await strategy_manager.validate_strategy(missing_field)
        assert 'large_buys' in errors
        assert any("min_amount" in e for e in errors['large_buys'])
        
    @pytest.mark.asyncio
    async def test_list_strategies(self, strategy_manager):
        """Test listing strategies"""
        
        # Create multiple strategies
        for i in range(3):
            await strategy_manager.create_strategy(
                name=f"List Test {i}",
                description=f"Strategy {i}",
                conditions={"liquidity": {"enabled": True, "value": 1000}}
            )
            
        # List all active
        strategies = await strategy_manager.list_strategies(limit=10)
        assert len(strategies) >= 3
        
        # Test pagination
        page1 = await strategy_manager.list_strategies(limit=2, offset=0)
        page2 = await strategy_manager.list_strategies(limit=2, offset=2)
        
        assert len(page1) <= 2
        assert all(s1['id'] != s2['id'] for s1 in page1 for s2 in page2)
        
    def test_validate_conditions_structure(self, strategy_manager):
        """Test condition structure validation"""
        
        # Empty conditions
        with pytest.raises(ValueError, match="At least one condition"):
            strategy_manager._validate_conditions({})
            
        # Non-dict condition
        with pytest.raises(ValueError, match="must be a dictionary"):
            strategy_manager._validate_conditions({"liquidity": "invalid"})
            
        # No enabled conditions
        with pytest.raises(ValueError, match="At least one condition must be enabled"):
            strategy_manager._validate_conditions({
                "liquidity": {"enabled": False, "value": 1000}
            })