from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, String, DateTime, Numeric, Integer, Boolean, 
    ForeignKey, JSON, BigInteger, Interval, Text, 
    CheckConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import TSTZRANGE
from sqlalchemy.orm import relationship

Base = declarative_base()


class Transaction(Base):
    __tablename__ = 'transactions'
    
    signature = Column(String, primary_key=True)
    time = Column(DateTime(timezone=True), nullable=False, index=True)
    token_address = Column(String, nullable=False, index=True)
    dex = Column(String, nullable=False)
    type = Column(String)  # buy or sell
    amount_token = Column(Numeric)
    amount_usd = Column(Numeric)
    wallet_address = Column(String, index=True)
    block_slot = Column(BigInteger)
    success = Column(Boolean, default=True)
    
    __table_args__ = (
        CheckConstraint(
            "dex IN ('pump.fun', 'raydium_clmm', 'raydium_cpmm', 'meteora_dlmm', 'meteora_dyn')",
            name='check_dex_type'
        ),
        CheckConstraint(
            "type IN ('buy', 'sell')",
            name='check_transaction_type'
        ),
        Index('idx_token_time', 'token_address', 'time'),
        Index('idx_wallet_time', 'wallet_address', 'time'),
        Index('idx_dex_time', 'dex', 'time'),
    )


class PoolState(Base):
    __tablename__ = 'pool_states'
    
    time = Column(DateTime(timezone=True), primary_key=True)
    token_address = Column(String, primary_key=True)
    dex = Column(String, primary_key=True)
    liquidity_usd = Column(Numeric)
    market_cap = Column(Numeric)
    price = Column(Numeric)
    holders = Column(Integer)
    active_bin_id = Column(Integer)  # Meteora DLMM
    current_tick = Column(Integer)   # Raydium CLMM
    fee_rate = Column(Numeric)       # Dynamic fees
    
    __table_args__ = (
        CheckConstraint(
            "dex IN ('pump.fun', 'raydium_clmm', 'raydium_cpmm', 'meteora_dlmm', 'meteora_dyn')",
            name='check_pool_dex_type'
        ),
    )


class TokenMetadata(Base):
    __tablename__ = 'token_metadata'
    
    token_address = Column(String, primary_key=True)
    name = Column(String)
    symbol = Column(String)
    decimals = Column(Integer)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    first_pool_created_at = Column(DateTime(timezone=True))
    creator_address = Column(String, index=True)
    total_supply = Column(Numeric)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class StrategyConfig(Base):
    __tablename__ = 'strategy_configs'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    conditions = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationship
    backtest_results = relationship("BacktestResult", back_populates="strategy")


class BacktestResult(Base):
    __tablename__ = 'backtest_results'
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey('strategy_configs.id'))
    strategy_params = Column(JSON)
    date_range = Column(TSTZRANGE)
    total_signals = Column(Integer)
    trades_executed = Column(Integer)
    win_rate = Column(Numeric)
    total_pnl = Column(Numeric)
    sharpe_ratio = Column(Numeric)
    max_drawdown = Column(Numeric)
    status = Column(String, default='pending')
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    strategy = relationship("StrategyConfig", back_populates="backtest_results")
    trades = relationship("BacktestTrade", back_populates="backtest")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name='check_backtest_status'
        ),
        Index('idx_backtest_strategy', 'strategy_id'),
        Index('idx_backtest_status', 'status'),
    )


class BacktestTrade(Base):
    __tablename__ = 'backtest_trades'
    
    id = Column(Integer, primary_key=True)
    backtest_id = Column(Integer, ForeignKey('backtest_results.id'))
    token_address = Column(String, nullable=False, index=True)
    signal_time = Column(DateTime(timezone=True))
    entry_time = Column(DateTime(timezone=True))
    entry_price = Column(Numeric)
    exit_time = Column(DateTime(timezone=True))
    exit_price = Column(Numeric)
    pnl_percent = Column(Numeric)
    pnl_usd = Column(Numeric)
    hold_duration = Column(Interval)
    exit_reason = Column(String)
    signal_metrics = Column(JSON)
    
    # Relationship
    backtest = relationship("BacktestResult", back_populates="trades")
    
    __table_args__ = (
        Index('idx_trades_backtest', 'backtest_id'),
        Index('idx_trades_token', 'token_address'),
    )