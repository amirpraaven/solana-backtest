"""Strategy management and CRUD operations"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncpg
import json
import logging

from .templates import STRATEGY_TEMPLATES, get_template

logger = logging.getLogger(__name__)


class StrategyManager:
    """Manage strategy configurations in database"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        
    async def create_strategy(
        self,
        name: str,
        description: str,
        conditions: Dict[str, Any],
        is_active: bool = True
    ) -> int:
        """Create a new strategy"""
        
        # Validate conditions
        self._validate_conditions(conditions)
        
        async with self.db.acquire() as conn:
            try:
                strategy_id = await conn.fetchval("""
                    INSERT INTO strategy_configs (name, description, conditions, is_active)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                """, name, description, json.dumps(conditions), is_active)
                
                logger.info(f"Created strategy '{name}' with ID {strategy_id}")
                return strategy_id
                
            except asyncpg.UniqueViolationError:
                raise ValueError(f"Strategy with name '{name}' already exists")
                
    async def create_from_template(
        self,
        template_name: str,
        custom_name: Optional[str] = None,
        modifications: Optional[Dict] = None
    ) -> int:
        """Create strategy from template with optional modifications"""
        
        template = get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
            
        # Apply custom name if provided
        if custom_name:
            template['name'] = custom_name
            
        # Apply modifications to conditions
        if modifications:
            for condition, changes in modifications.items():
                if condition in template['conditions']:
                    template['conditions'][condition].update(changes)
                    
        return await self.create_strategy(
            template['name'],
            template['description'],
            template['conditions']
        )
        
    async def get_strategy(self, strategy_id: int) -> Optional[Dict]:
        """Get strategy by ID"""
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM strategy_configs
                WHERE id = $1
            """, strategy_id)
            
        if row:
            return {
                'id': row['id'],
                'name': row['name'],
                'description': row['description'],
                'conditions': json.loads(row['conditions']) if isinstance(row['conditions'], str) else row['conditions'],
                'is_active': row['is_active'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            }
            
        return None
        
    async def get_strategy_by_name(self, name: str) -> Optional[Dict]:
        """Get strategy by name"""
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM strategy_configs
                WHERE name = $1
            """, name)
            
        if row:
            return {
                'id': row['id'],
                'name': row['name'],
                'description': row['description'],
                'conditions': json.loads(row['conditions']) if isinstance(row['conditions'], str) else row['conditions'],
                'is_active': row['is_active'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            }
            
        return None
        
    async def list_strategies(
        self,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """List all strategies"""
        
        query = """
            SELECT * FROM strategy_configs
            WHERE ($1 = false OR is_active = true)
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, active_only, limit, offset)
            
        return [
            {
                'id': row['id'],
                'name': row['name'],
                'description': row['description'],
                'conditions': json.loads(row['conditions']) if isinstance(row['conditions'], str) else row['conditions'],
                'is_active': row['is_active'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            }
            for row in rows
        ]
        
    async def update_strategy(
        self,
        strategy_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        conditions: Optional[Dict] = None,
        is_active: Optional[bool] = None
    ) -> bool:
        """Update strategy configuration"""
        
        updates = []
        values = [strategy_id]
        param_count = 1
        
        if name is not None:
            param_count += 1
            updates.append(f"name = ${param_count}")
            values.append(name)
            
        if description is not None:
            param_count += 1
            updates.append(f"description = ${param_count}")
            values.append(description)
            
        if conditions is not None:
            self._validate_conditions(conditions)
            param_count += 1
            updates.append(f"conditions = ${param_count}")
            values.append(json.dumps(conditions))
            
        if is_active is not None:
            param_count += 1
            updates.append(f"is_active = ${param_count}")
            values.append(is_active)
            
        if not updates:
            return False
            
        updates.append("updated_at = NOW()")
        
        query = f"""
            UPDATE strategy_configs
            SET {', '.join(updates)}
            WHERE id = $1
        """
        
        async with self.db.acquire() as conn:
            result = await conn.execute(query, *values)
            
        return result.split()[-1] != '0'
        
    async def delete_strategy(self, strategy_id: int) -> bool:
        """Delete strategy (soft delete by setting inactive)"""
        
        return await self.update_strategy(strategy_id, is_active=False)
        
    async def duplicate_strategy(
        self,
        strategy_id: int,
        new_name: str
    ) -> int:
        """Duplicate an existing strategy with a new name"""
        
        original = await self.get_strategy(strategy_id)
        if not original:
            raise ValueError(f"Strategy {strategy_id} not found")
            
        return await self.create_strategy(
            new_name,
            f"Copy of {original['description']}",
            original['conditions']
        )
        
    async def validate_strategy(
        self,
        conditions: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Validate strategy conditions and return any errors"""
        
        # Simplified validation - be more lenient to allow flexibility
        errors = {}
        
        # Just ensure we have at least one enabled condition
        enabled_count = 0
        for condition_name, config in conditions.items():
            if isinstance(config, dict) and config.get('enabled', False):
                enabled_count += 1
                
        if enabled_count == 0:
            errors['general'] = ["At least one condition must be enabled"]
            
        return errors
        
    def _validate_conditions(self, conditions: Dict[str, Any]):
        """Basic validation of conditions structure"""
        
        if not isinstance(conditions, dict):
            raise ValueError("Conditions must be a dictionary")
            
        # Filter enabled conditions
        enabled_conditions = {
            k: v for k, v in conditions.items()
            if isinstance(v, dict) and v.get('enabled', False)
        }
        
        if not enabled_conditions:
            raise ValueError("At least one condition must be enabled")
            
    async def get_strategy_performance(
        self,
        strategy_id: int,
        limit: int = 10
    ) -> Dict:
        """Get performance metrics for a strategy"""
        
        async with self.db.acquire() as conn:
            # Get strategy info
            strategy = await self.get_strategy(strategy_id)
            if not strategy:
                return None
                
            # Get backtest results
            results = await conn.fetch("""
                SELECT 
                    br.*,
                    COUNT(bt.id) as trade_count,
                    AVG(bt.pnl_percent) as avg_trade_pnl
                FROM backtest_results br
                LEFT JOIN backtest_trades bt ON br.id = bt.backtest_id
                WHERE br.strategy_id = $1 AND br.status = 'completed'
                GROUP BY br.id
                ORDER BY br.created_at DESC
                LIMIT $2
            """, strategy_id, limit)
            
        return {
            'strategy': strategy,
            'backtests': [dict(row) for row in results],
            'summary': {
                'total_backtests': len(results),
                'avg_win_rate': sum(r['win_rate'] for r in results) / len(results) if results else 0,
                'avg_sharpe_ratio': sum(r['sharpe_ratio'] for r in results) / len(results) if results else 0
            }
        }