"""Utilities for handling different token decimal places"""

from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Known token decimals
KNOWN_DECIMALS = {
    'So11111111111111111111111111111111111111112': 9,  # SOL
    'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v': 6,  # USDC
    'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB': 6,  # USDT
    # Add more as needed
}

# DEX-specific defaults
DEX_DEFAULTS = {
    'pump.fun': 6,  # pump.fun always uses 6 decimals
    'raydium_clmm': 9,
    'raydium_cpmm': 9,
    'meteora_dlmm': 9,
    'meteora_dyn': 9
}


class TokenDecimalHandler:
    """Handle token decimal conversions"""
    
    def __init__(self):
        self.decimal_cache: Dict[str, int] = KNOWN_DECIMALS.copy()
        
    def get_decimals(
        self,
        token_address: str,
        dex: Optional[str] = None
    ) -> int:
        """Get token decimals with fallback to DEX defaults"""
        
        # Check cache first
        if token_address in self.decimal_cache:
            return self.decimal_cache[token_address]
            
        # Use DEX-specific default if available
        if dex and dex in DEX_DEFAULTS:
            logger.debug(f"Using DEX default decimals for {token_address} on {dex}")
            return DEX_DEFAULTS[dex]
            
        # Default to 9 (most common)
        logger.warning(f"Unknown decimals for {token_address}, defaulting to 9")
        return 9
        
    def add_token_decimals(self, token_address: str, decimals: int):
        """Add token decimals to cache"""
        self.decimal_cache[token_address] = decimals
        
    def amount_to_ui(
        self,
        amount: int,
        token_address: str,
        dex: Optional[str] = None
    ) -> float:
        """Convert raw amount to UI amount"""
        
        decimals = self.get_decimals(token_address, dex)
        return amount / (10 ** decimals)
        
    def amount_to_raw(
        self,
        ui_amount: float,
        token_address: str,
        dex: Optional[str] = None
    ) -> int:
        """Convert UI amount to raw amount"""
        
        decimals = self.get_decimals(token_address, dex)
        return int(ui_amount * (10 ** decimals))
        
    def normalize_amounts(
        self,
        amount1: int,
        token1: str,
        amount2: int,
        token2: str,
        target_decimals: int = 9
    ) -> tuple:
        """Normalize two amounts to same decimal base"""
        
        decimals1 = self.get_decimals(token1)
        decimals2 = self.get_decimals(token2)
        
        # Convert to target decimals
        normalized1 = amount1 * (10 ** (target_decimals - decimals1))
        normalized2 = amount2 * (10 ** (target_decimals - decimals2))
        
        return normalized1, normalized2
        
    def calculate_price(
        self,
        base_amount: int,
        base_token: str,
        quote_amount: int,
        quote_token: str
    ) -> float:
        """Calculate price accounting for decimals"""
        
        if base_amount == 0:
            return 0
            
        base_ui = self.amount_to_ui(base_amount, base_token)
        quote_ui = self.amount_to_ui(quote_amount, quote_token)
        
        return quote_ui / base_ui if base_ui > 0 else 0


# Global instance
decimal_handler = TokenDecimalHandler()