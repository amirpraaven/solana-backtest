"""Async job management for backtests"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional, Any, List
from enum import Enum
import aioredis

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobManager:
    """Manages backtest jobs with Redis for state storage"""
    
    def __init__(self, redis_client: aioredis.Redis, db_pool=None):
        self.redis = redis_client
        self.db_pool = db_pool
        self.running_jobs: Dict[str, asyncio.Task] = {}
        
    async def create_job(
        self,
        job_type: str,
        params: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> str:
        """Create a new job and return job ID"""
        
        job_id = str(uuid.uuid4())
        
        job_data = {
            'id': job_id,
            'type': job_type,
            'params': params,
            'status': JobStatus.PENDING,
            'progress': 0,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'result': None,
            'error': None,
            'logs': []
        }
        
        # Store in Redis with 24h expiry
        await self.redis.setex(
            f"job:{job_id}",
            86400,  # 24 hours
            json.dumps(job_data)
        )
        
        # Add to pending queue
        await self.redis.lpush("job_queue:pending", job_id)
        
        logger.info(f"Created job {job_id} of type {job_type}")
        return job_id
        
    async def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job details"""
        
        data = await self.redis.get(f"job:{job_id}")
        if data:
            return json.loads(data)
        return None
        
    async def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
        log_message: Optional[str] = None
    ):
        """Update job status and progress"""
        
        job = await self.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return
            
        if status:
            job['status'] = status
        if progress is not None:
            job['progress'] = max(0, min(100, progress))
        if result:
            job['result'] = result
        if error:
            job['error'] = error
        if log_message:
            job['logs'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'message': log_message
            })
            
        job['updated_at'] = datetime.utcnow().isoformat()
        
        # Store updated job
        await self.redis.setex(
            f"job:{job_id}",
            86400,
            json.dumps(job)
        )
        
        # Publish update for real-time monitoring
        await self.redis.publish(
            f"job_updates:{job_id}",
            json.dumps({
                'job_id': job_id,
                'status': job['status'],
                'progress': job['progress']
            })
        )
        
    async def start_job(self, job_id: str, executor_func):
        """Start executing a job"""
        
        await self.update_job(job_id, status=JobStatus.RUNNING, progress=0)
        
        try:
            # Create task for job execution
            task = asyncio.create_task(self._execute_job(job_id, executor_func))
            self.running_jobs[job_id] = task
            
        except Exception as e:
            logger.error(f"Failed to start job {job_id}: {e}")
            await self.update_job(
                job_id,
                status=JobStatus.FAILED,
                error=str(e)
            )
            
    async def _execute_job(self, job_id: str, executor_func):
        """Execute job with error handling"""
        
        try:
            job = await self.get_job(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")
                
            # Execute the job
            result = await executor_func(
                job_id=job_id,
                params=job['params'],
                progress_callback=lambda p, msg=None: asyncio.create_task(
                    self.update_job(job_id, progress=p, log_message=msg)
                )
            )
            
            # Update job as completed
            await self.update_job(
                job_id,
                status=JobStatus.COMPLETED,
                progress=100,
                result=result
            )
            
        except asyncio.CancelledError:
            await self.update_job(
                job_id,
                status=JobStatus.CANCELLED,
                error="Job was cancelled"
            )
            raise
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            await self.update_job(
                job_id,
                status=JobStatus.FAILED,
                error=str(e)
            )
            
        finally:
            # Remove from running jobs
            self.running_jobs.pop(job_id, None)
            
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job"""
        
        if job_id in self.running_jobs:
            task = self.running_jobs[job_id]
            task.cancel()
            return True
            
        return False
        
    async def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 100
    ) -> List[Dict]:
        """List jobs with optional status filter"""
        
        # Get all job keys
        keys = await self.redis.keys("job:*")
        
        jobs = []
        for key in keys[:limit]:
            data = await self.redis.get(key)
            if data:
                job = json.loads(data)
                if status is None or job['status'] == status:
                    jobs.append(job)
                    
        # Sort by created_at descending
        jobs.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jobs
        
    async def cleanup_old_jobs(self, days: int = 7):
        """Clean up jobs older than specified days"""
        
        cutoff = datetime.utcnow().timestamp() - (days * 86400)
        
        keys = await self.redis.keys("job:*")
        
        for key in keys:
            data = await self.redis.get(key)
            if data:
                job = json.loads(data)
                created_at = datetime.fromisoformat(job['created_at']).timestamp()
                
                if created_at < cutoff:
                    await self.redis.delete(key)
                    logger.info(f"Deleted old job {job['id']}")


class BacktestJobExecutor:
    """Executes backtest jobs"""
    
    def __init__(
        self,
        backtest_engine,
        strategy_manager,
        db_pool
    ):
        self.engine = backtest_engine
        self.strategy_manager = strategy_manager
        self.db = db_pool
        
    async def execute_backtest_job(
        self,
        job_id: str,
        params: Dict[str, Any],
        progress_callback
    ) -> Dict:
        """Execute a backtest job with progress updates"""
        
        try:
            # Extract parameters
            strategy_id = params['strategy_id']
            token_addresses = params['token_addresses']
            start_date = datetime.fromisoformat(params['start_date'])
            end_date = datetime.fromisoformat(params['end_date'])
            initial_capital = params.get('initial_capital', 10000)
            
            await progress_callback(10, "Loading strategy configuration")
            
            # Get strategy
            strategy = await self.strategy_manager.get_strategy(strategy_id)
            if not strategy:
                raise ValueError(f"Strategy {strategy_id} not found")
                
            await progress_callback(20, f"Analyzing {len(token_addresses)} tokens")
            
            # Calculate progress increments
            progress_per_token = 60 / len(token_addresses)  # 60% for token processing
            current_progress = 20
            
            # Create backtest record
            async with self.db.acquire() as conn:
                backtest_id = await conn.fetchval("""
                    INSERT INTO backtest_results (strategy_id, date_range, status)
                    VALUES ($1, $2, 'running')
                    RETURNING id
                """, strategy_id, (start_date, end_date))
                
            # Process each token with progress updates
            all_signals = []
            all_trades = []
            
            for i, token_address in enumerate(token_addresses):
                await progress_callback(
                    int(current_progress),
                    f"Processing token {i+1}/{len(token_addresses)}: {token_address[:8]}..."
                )
                
                # Run backtest for this token
                # (Simplified - in real implementation would use the engine)
                token_result = await self._process_token(
                    token_address,
                    strategy,
                    start_date,
                    end_date
                )
                
                all_signals.extend(token_result.get('signals', []))
                all_trades.extend(token_result.get('trades', []))
                
                current_progress += progress_per_token
                
            await progress_callback(80, "Calculating portfolio metrics")
            
            # Calculate metrics
            metrics = self._calculate_metrics(all_trades, initial_capital)
            
            await progress_callback(90, "Storing results")
            
            # Store results
            await self._store_results(
                backtest_id,
                all_signals,
                all_trades,
                metrics
            )
            
            await progress_callback(100, "Backtest completed successfully")
            
            return {
                'backtest_id': backtest_id,
                'summary': {
                    'total_signals': len(all_signals),
                    'total_trades': len(all_trades),
                    'metrics': metrics
                }
            }
            
        except Exception as e:
            logger.error(f"Backtest job {job_id} failed: {e}")
            raise
            
    async def _process_token(
        self,
        token_address: str,
        strategy: Dict,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """Process a single token (simplified)"""
        
        # In real implementation, would use the backtest engine
        return {
            'signals': [],
            'trades': []
        }
        
    def _calculate_metrics(
        self,
        trades: List[Dict],
        initial_capital: float
    ) -> Dict:
        """Calculate portfolio metrics"""
        
        if not trades:
            return {
                'total_return': 0,
                'win_rate': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0
            }
            
        # Simplified metric calculation
        winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        
        return {
            'total_return': total_pnl,
            'total_return_pct': (total_pnl / initial_capital) * 100,
            'win_rate': winning_trades / len(trades) if trades else 0,
            'total_trades': len(trades),
            'winning_trades': winning_trades,
            'losing_trades': len(trades) - winning_trades
        }
        
    async def _store_results(
        self,
        backtest_id: int,
        signals: List[Dict],
        trades: List[Dict],
        metrics: Dict
    ):
        """Store backtest results"""
        
        async with self.db.acquire() as conn:
            # Update backtest summary
            await conn.execute("""
                UPDATE backtest_results
                SET 
                    total_signals = $2,
                    trades_executed = $3,
                    win_rate = $4,
                    total_pnl = $5,
                    status = 'completed',
                    completed_at = NOW()
                WHERE id = $1
            """, backtest_id, len(signals), len(trades),
                metrics.get('win_rate', 0), metrics.get('total_return', 0))
                
            # Store individual trades
            for trade in trades:
                await conn.execute("""
                    INSERT INTO backtest_trades (
                        backtest_id, token_address, signal_time,
                        entry_time, entry_price, exit_time, exit_price,
                        pnl_percent, pnl_usd, exit_reason
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """, backtest_id, trade['token_address'], trade['signal_time'],
                    trade['entry_time'], trade['entry_price'], trade['exit_time'],
                    trade['exit_price'], trade['pnl_percent'], trade['pnl_usd'],
                    trade['exit_reason'])
# Backward compatibility alias
BacktestJobManager = JobManager
