from base64 import b64decode
import struct
from typing import Dict, Optional, Tuple
import logging
import math

from .dex_base import BaseDEXParser

logger = logging.getLogger(__name__)


class RaydiumCLMMParser(BaseDEXParser):
    """Parser for Raydium Concentrated Liquidity Market Maker (CLMM) transactions"""
    
    # Swap instruction discriminator
    SWAP_DISCRIMINATOR = bytes([0x2b, 0x1a, 0x5f, 0x5e, 0x1f, 0x35, 0x64, 0x77])
    
    # Constants
    TICK_SPACING_STABLE = 1  # For stable pairs
    TICK_SPACING_STANDARD = 10  # Standard fee tier
    TICK_SPACING_HIGH = 60  # High volatility
    
    def get_program_id(self) -> str:
        return "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK"
        
    def get_dex_name(self) -> str:
        return "raydium_clmm"
        
    def parse_swap(self, tx: Dict) -> Optional[Dict]:
        """Parse Raydium CLMM swap transaction"""
        
        try:
            # Get base transaction info
            base_info = self.extract_base_info(tx)
            
            # Find CLMM instruction
            clmm_ix = None
            for ix in tx.get('instructions', []):
                if ix.get('programId') == self.program_id:
                    clmm_ix = ix
                    break
                    
            if not clmm_ix:
                return None
                
            # Decode instruction data
            data = b64decode(clmm_ix.get('data', ''))
            if len(data) < 8:
                return None
                
            # Check discriminator
            discriminator = data[:8]
            if discriminator != self.SWAP_DISCRIMINATOR:
                return None
                
            # Parse swap instruction data
            # Layout: discriminator (8) + amount (8) + other_amount_threshold (8) + 
            #         sqrt_price_limit_x64 (16) + is_base_input (1)
            if len(data) < 41:
                logger.error(f"Invalid CLMM swap data length: {len(data)}")
                return None
                
            amount = struct.unpack('<Q', data[8:16])[0]
            other_amount_threshold = struct.unpack('<Q', data[16:24])[0]
            sqrt_price_limit_x64 = struct.unpack('<Q', data[24:32])[0] + (struct.unpack('<Q', data[32:40])[0] << 64)
            is_base_input = data[40] == 1
            
            # Parse accounts
            # [tokenProgram, tokenAuthority, ammConfig, poolState, tokenVault0, tokenVault1, 
            #  observationState, userTokenAccount0, userTokenAccount1, userAccount]
            accounts = clmm_ix.get('accounts', [])
            if len(accounts) < 10:
                logger.error(f"Insufficient CLMM accounts: {len(accounts)}")
                return None
                
            pool_state = accounts[3]
            token_vault_0 = accounts[4]
            token_vault_1 = accounts[5]
            user_account = accounts[9]
            
            # Get token transfers to determine actual amounts
            transfers = self.extract_token_transfers(tx)
            
            # Determine tokens and amounts from transfers
            token_info = self._determine_token_info(transfers, user_account)
            
            # Calculate price from sqrt price if available
            price = self._sqrt_price_x64_to_price(sqrt_price_limit_x64) if sqrt_price_limit_x64 > 0 else 0
            
            result = {
                **base_info,
                'dex': self.dex_name,
                'type': 'buy' if token_info['is_buy'] else 'sell',
                'token_address': token_info['token_mint'],
                'token_amount': token_info['token_amount'],
                'sol_amount': token_info['sol_amount'],
                'amount_usd': token_info['sol_amount'] * token_info.get('sol_price', 0),
                'price': price,
                'wallet_address': user_account,
                'pool_state': pool_state,
                'is_base_input': is_base_input,
                'amount_specified': amount,
                'other_amount_threshold': other_amount_threshold,
                'sqrt_price_limit': sqrt_price_limit_x64
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing CLMM transaction {tx.get('signature')}: {e}")
            return None
            
    def _determine_token_info(self, transfers: list, user_address: str) -> Dict:
        """Determine token mint and amounts from transfers"""
        
        sol_mint = 'So11111111111111111111111111111111111111112'
        token_mint = None
        token_amount = 0
        sol_amount = 0
        is_buy = None
        
        for transfer in transfers:
            mint = transfer.get('mint')
            source = transfer.get('source')
            destination = transfer.get('destination')
            amount = int(transfer.get('amount', 0))
            decimals = transfer.get('decimals', 9)
            
            if mint == sol_mint:
                # SOL transfer
                if source == user_address:
                    # User sending SOL = buying token
                    sol_amount = amount / 1e9
                    is_buy = True
                elif destination == user_address:
                    # User receiving SOL = selling token
                    sol_amount = amount / 1e9
                    is_buy = False
            else:
                # Token transfer
                if destination == user_address:
                    # User receiving token = buying
                    token_mint = mint
                    token_amount = amount / (10 ** decimals)
                elif source == user_address:
                    # User sending token = selling
                    token_mint = mint
                    token_amount = amount / (10 ** decimals)
                    
        return {
            'token_mint': token_mint,
            'token_amount': token_amount,
            'sol_amount': sol_amount,
            'is_buy': is_buy
        }
        
    def _sqrt_price_x64_to_price(self, sqrt_price_x64: int) -> float:
        """Convert sqrt price X64 to decimal price"""
        
        if sqrt_price_x64 == 0:
            return 0
            
        # sqrt_price_x64 is sqrt(price) * 2^64
        # price = (sqrt_price_x64 / 2^64)^2
        sqrt_price = sqrt_price_x64 / (2 ** 64)
        return sqrt_price ** 2
        
    def _tick_to_price(self, tick: int, decimals_0: int = 9, decimals_1: int = 9) -> float:
        """Convert tick to price"""
        
        # price = 1.0001^tick * 10^(decimals_1 - decimals_0)
        return math.pow(1.0001, tick) * math.pow(10, decimals_1 - decimals_0)