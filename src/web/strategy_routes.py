"""Strategy management API routes"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import uuid
import logging

from src.strategies import StrategyManager, STRATEGY_TEMPLATES, get_template
from src.engine import BacktestEngine
from src.engine.job_manager import BacktestJobManager, BacktestJobExecutor, JobStatus
from .dependencies import get_strategy_manager, get_backtest_engine, get_db, get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class StrategyCondition(BaseModel):
    enabled: bool = True
    operator: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    window_seconds: Optional[int] = None
    min_count: Optional[int] = None
    min_amount: Optional[float] = None


class StrategyConfig(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    conditions: Dict[str, Any] = Field(..., example={
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
        }
    })
    
    @validator('conditions')
    def validate_conditions(cls, v):
        """Validate condition structure"""
        if not v:
            raise ValueError("At least one condition must be specified")
            
        # Filter out disabled conditions
        enabled_conditions = {}
        for key, condition in v.items():
            if isinstance(condition, dict) and condition.get('enabled', True):
                enabled_conditions[key] = condition
                
        if not enabled_conditions:
            raise ValueError("At least one condition must be enabled")
            
        # Allow any condition name for flexibility
        # The strategy manager will validate the actual condition logic
        return enabled_conditions


class BacktestRequest(BaseModel):
    strategy_id: int
    token_addresses: List[str] = Field(..., min_items=1, max_items=100)
    start_date: datetime
    end_date: datetime
    initial_capital: float = Field(default=10000, gt=0)
    position_size: float = Field(default=0.1, gt=0, le=1)  # Percentage of capital
    max_positions: int = Field(default=5, ge=1, le=20)
    stop_loss: float = Field(default=0.1, ge=0, le=1)  # 10% default
    take_profit: float = Field(default=0.5, ge=0, le=10)  # 50% default
    time_limit_hours: int = Field(default=24, ge=1, le=168)  # Max hold time
    config_overrides: Optional[Dict[str, Any]] = None
    
    @validator('end_date')
    def validate_dates(cls, v, values):
        """Validate date range"""
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError("End date must be after start date")
        if v > datetime.utcnow():
            raise ValueError("End date cannot be in the future")
        return v


class StrategyCompareRequest(BaseModel):
    strategy_ids: List[int] = Field(..., min_items=2, max_items=10)
    token_addresses: List[str] = Field(..., min_items=1, max_items=50)
    start_date: datetime
    end_date: datetime
    initial_capital: float = Field(default=10000, gt=0)


# Routes
@router.post("/create")
async def create_strategy(
    strategy: StrategyConfig,
    manager: StrategyManager = Depends(get_strategy_manager)
):
    """Create a new strategy configuration"""
    
    try:
        # Create strategy without additional validation
        # The StrategyConfig model already validates the structure
        strategy_id = await manager.create_strategy(
            strategy.name,
            strategy.description,
            strategy.conditions
        )
        
        # Return the created strategy for frontend
        created_strategy = await manager.get_strategy(strategy_id)
        return created_strategy
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(422, detail={"message": str(e), "type": "validation_error"})
    except Exception as e:
        logger.error(f"Error creating strategy: {e}")
        raise HTTPException(500, detail={"message": "Failed to create strategy", "error": str(e)})


@router.post("/create-from-template", response_model=Dict)
async def create_from_template(
    template_name: str,
    custom_name: Optional[str] = None,
    modifications: Optional[Dict] = None,
    manager: StrategyManager = Depends(get_strategy_manager)
):
    """Create strategy from template"""
    
    try:
        strategy_id = await manager.create_from_template(
            template_name,
            custom_name,
            modifications
        )
        
        return {
            "strategy_id": strategy_id,
            "message": f"Strategy created from template '{template_name}'"
        }
        
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


@router.get("")
async def get_strategies(
    active_only: bool = Query(True, description="Only show active strategies"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    manager: StrategyManager = Depends(get_strategy_manager)
):
    """Get all strategies - main endpoint for frontend"""
    
    try:
        strategies = await manager.list_strategies(active_only, limit, offset)
        # Return array directly for frontend compatibility
        return strategies if strategies else []
    except Exception as e:
        logger.error(f"Error fetching strategies: {e}")
        # Return empty array on error to keep frontend working
        return []


@router.get("/list", response_model=Dict)
async def list_strategies(
    active_only: bool = Query(True, description="Only show active strategies"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    manager: StrategyManager = Depends(get_strategy_manager)
):
    """List all strategies - alternative endpoint with metadata"""
    
    strategies = await manager.list_strategies(active_only, limit, offset)
    
    return {
        "strategies": strategies,
        "total": len(strategies),
        "limit": limit,
        "offset": offset
    }


@router.get("/templates")
async def get_strategy_templates():
    """Get pre-built strategy templates"""
    
    try:
        # Return templates as a dictionary for frontend compatibility
        templates_dict = {}
        for key, template in STRATEGY_TEMPLATES.items():
            templates_dict[key] = {
                "name": template["name"],
                "description": template["description"],
                "conditions": template["conditions"]
            }
        
        return templates_dict
    except Exception as e:
        logger.error(f"Error fetching templates: {e}")
        return {}


@router.get("/{strategy_id}", response_model=Dict)
async def get_strategy(
    strategy_id: int,
    manager: StrategyManager = Depends(get_strategy_manager)
):
    """Get strategy details"""
    
    strategy = await manager.get_strategy(strategy_id)
    if not strategy:
        raise HTTPException(404, detail="Strategy not found")
        
    return {"strategy": strategy}


@router.put("/{strategy_id}", response_model=Dict)
async def update_strategy(
    strategy_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    conditions: Optional[Dict] = None,
    is_active: Optional[bool] = None,
    manager: StrategyManager = Depends(get_strategy_manager)
):
    """Update strategy configuration"""
    
    try:
        # Validate conditions if provided
        if conditions:
            errors = await manager.validate_strategy(conditions)
            if errors:
                raise HTTPException(400, detail={"validation_errors": errors})
                
        updated = await manager.update_strategy(
            strategy_id,
            name,
            description,
            conditions,
            is_active
        )
        
        if not updated:
            raise HTTPException(404, detail="Strategy not found")
            
        return {"message": "Strategy updated successfully"}
        
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


@router.delete("/{strategy_id}", response_model=Dict)
async def delete_strategy(
    strategy_id: int,
    manager: StrategyManager = Depends(get_strategy_manager)
):
    """Delete strategy (soft delete)"""
    
    deleted = await manager.delete_strategy(strategy_id)
    if not deleted:
        raise HTTPException(404, detail="Strategy not found")
        
    return {"message": "Strategy deleted successfully"}


@router.post("/duplicate/{strategy_id}", response_model=Dict)
async def duplicate_strategy(
    strategy_id: int,
    new_name: str,
    manager: StrategyManager = Depends(get_strategy_manager)
):
    """Duplicate an existing strategy"""
    
    try:
        new_id = await manager.duplicate_strategy(strategy_id, new_name)
        return {
            "strategy_id": new_id,
            "message": "Strategy duplicated successfully"
        }
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


@router.post("/validate", response_model=Dict)
async def validate_strategy(
    conditions: Dict[str, Any],
    manager: StrategyManager = Depends(get_strategy_manager)
):
    """Validate strategy conditions"""
    
    errors = await manager.validate_strategy(conditions)
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


@router.post("/backtest")
async def run_strategy_backtest(
    request: BacktestRequest,
    manager: StrategyManager = Depends(get_strategy_manager),
    redis_client = Depends(get_redis_client)
):
    """Run backtest with specific strategy using job queue"""
    
    # Validate strategy exists
    strategy = await manager.get_strategy(request.strategy_id)
    if not strategy:
        raise HTTPException(404, detail="Strategy not found")
    
    # Validate token addresses
    if not request.token_addresses:
        raise HTTPException(400, detail="At least one token address is required")
        
    # Create job manager
    job_manager = BacktestJobManager(redis_client)
    
    # Create job with parameters
    job_params = {
        'strategy_id': request.strategy_id,
        'strategy_name': strategy['name'],
        'token_addresses': request.token_addresses,
        'start_date': request.start_date.isoformat(),
        'end_date': request.end_date.isoformat(),
        'initial_capital': request.initial_capital,
        'position_size': request.position_size,
        'max_positions': request.max_positions,
        'stop_loss': request.stop_loss,
        'take_profit': request.take_profit,
        'time_limit_hours': request.time_limit_hours,
        'config_overrides': request.config_overrides
    }
    
    # Create job
    job_id = await job_manager.create_job(
        job_type='backtest',
        params=job_params
    )
    
    # Start job execution asynchronously
    from .dependencies import get_job_executor
    executor = await get_job_executor()
    await job_manager.start_job(job_id, executor.execute_backtest_job)
    
    return {
        "job_id": job_id,
        "status": "started",
        "message": "Backtest job created successfully",
        "monitor_url": f"/strategies/jobs/{job_id}"
    }


@router.get("/backtest/{backtest_id}", response_model=Dict)
async def get_backtest_results(
    backtest_id: int,
    include_trades: bool = Query(False, description="Include individual trades"),
    db_conn = Depends(get_db)
):
    """Get backtest results"""
    
    # Get backtest record
    result = await db_conn.fetchrow("""
        SELECT br.*, sc.name as strategy_name, sc.conditions
        FROM backtest_results br
        JOIN strategy_configs sc ON br.strategy_id = sc.id
        WHERE br.id = $1
    """, backtest_id)
    
    if not result:
        raise HTTPException(404, detail="Backtest not found")
        
    response = {
        "backtest": dict(result),
        "trades": []
    }
    
    # Get trades if requested
    if include_trades and result['status'] == 'completed':
        trades = await db_conn.fetch("""
            SELECT * FROM backtest_trades
            WHERE backtest_id = $1
            ORDER BY signal_time
            LIMIT 1000
        """, backtest_id)
        
        response["trades"] = [dict(t) for t in trades]
        
    return response


@router.post("/compare", response_model=Dict)
async def compare_strategies(
    request: StrategyCompareRequest,
    background_tasks: BackgroundTasks,
    engine: BacktestEngine = Depends(get_backtest_engine),
    manager: StrategyManager = Depends(get_strategy_manager)
):
    """Compare multiple strategies on same data"""
    
    comparison_id = str(uuid.uuid4())
    
    # Validate all strategies exist
    for strategy_id in request.strategy_ids:
        strategy = await manager.get_strategy(strategy_id)
        if not strategy:
            raise HTTPException(404, detail=f"Strategy {strategy_id} not found")
            
    # Create tasks for each strategy
    for strategy_id in request.strategy_ids:
        background_tasks.add_task(
            execute_backtest_task,
            engine,
            None,  # Will create backtest_id in task
            strategy_id,
            request.token_addresses,
            request.start_date,
            request.end_date,
            request.initial_capital,
            {"comparison_id": comparison_id}
        )
        
    return {
        "comparison_id": comparison_id,
        "strategies": request.strategy_ids,
        "status": "running",
        "message": f"Started comparison of {len(request.strategy_ids)} strategies"
    }


@router.get("/performance/{strategy_id}", response_model=Dict)
async def get_strategy_performance(
    strategy_id: int,
    limit: int = Query(10, ge=1, le=100),
    manager: StrategyManager = Depends(get_strategy_manager)
):
    """Get performance metrics for a strategy"""
    
    performance = await manager.get_strategy_performance(strategy_id, limit)
    if not performance:
        raise HTTPException(404, detail="Strategy not found")
        
    return performance


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    redis_client = Depends(get_redis_client)
):
    """Get job status and progress"""
    
    job_manager = BacktestJobManager(redis_client)
    job = await job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(404, detail="Job not found")
        
    return {
        "job_id": job_id,
        "status": job['status'],
        "progress": job['progress'],
        "created_at": job['created_at'],
        "updated_at": job['updated_at'],
        "logs": job.get('logs', []),
        "error": job.get('error'),
        "result": job.get('result') if job['status'] == JobStatus.COMPLETED else None
    }


@router.get("/jobs")
async def list_jobs(
    status: Optional[JobStatus] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    redis_client = Depends(get_redis_client)
):
    """List all jobs with optional status filter"""
    
    job_manager = BacktestJobManager(redis_client)
    jobs = await job_manager.list_jobs(status=status, limit=limit)
    
    return {
        "jobs": jobs,
        "count": len(jobs),
        "filter": {"status": status} if status else None
    }


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    redis_client = Depends(get_redis_client)
):
    """Cancel a running job"""
    
    job_manager = BacktestJobManager(redis_client)
    job = await job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(404, detail="Job not found")
        
    if job['status'] != JobStatus.RUNNING:
        raise HTTPException(400, detail=f"Cannot cancel job in {job['status']} status")
        
    cancelled = await job_manager.cancel_job(job_id)
    
    return {
        "job_id": job_id,
        "cancelled": cancelled,
        "message": "Job cancellation requested" if cancelled else "Job not found in running jobs"
    }


# Background task function
async def execute_backtest_task(
    engine: BacktestEngine,
    backtest_id: Optional[int],
    strategy_id: int,
    token_addresses: List[str],
    start_date: datetime,
    end_date: datetime,
    initial_capital: float,
    config_overrides: Optional[Dict] = None
):
    """Execute backtest in background"""
    
    try:
        logger.info(f"Starting backtest task for strategy {strategy_id}")
        
        # Apply config overrides if provided
        if config_overrides:
            engine.config.update(config_overrides)
            
        # Run backtest
        result = await engine.run_backtest(
            strategy_id,
            token_addresses,
            start_date,
            end_date,
            initial_capital
        )
        
        logger.info(f"Backtest completed: {result['backtest_id']}")
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        # Update status to failed if we have backtest_id
        if backtest_id:
            # This would need database access to update status
            pass