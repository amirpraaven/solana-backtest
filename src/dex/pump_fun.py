from base64 import b64decode
import struct
from typing import Dict, Optional
import logging

from .dex_base import BaseDEXParser

logger = logging.getLogger(__name__)


class PumpFunParser(BaseDEXParser):
    """Parser for pump.fun transactions"""
    
    # Instruction discriminators
    BUY_DISCRIMINATOR = 16927863322537952870
    SELL_DISCRIMINATOR = 12502976635542562355
    
    # pump.fun specific constants
    TOKEN_DECIMALS = 6  # pump.fun tokens always have 6 decimals
    BONDING_CURVE_SEED = b"bonding-curve"
    FEE_RATE = 0.01  # 1% fee
    
    def get_program_id(self) -> str:
        return "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
        
    def get_dex_name(self) -> str:
        return "pump.fun"
        
    def parse_swap(self, tx: Dict) -> Optional[Dict]:
        """Parse pump.fun swap transaction"""
        
        try:
            # Get base transaction info
            base_info = self.extract_base_info(tx)
            
            # Find pump.fun instruction
            pump_ix = None
            for ix in tx.get('instructions', []):
                if ix.get('programId') == self.program_id:
                    pump_ix = ix
                    break
                    
            if not pump_ix:
                return None
                
            # Decode instruction data
            data = b64decode(pump_ix.get('data', ''))
            if len(data) < 8:
                logger.error(f"Invalid instruction data length: {len(data)}")
                return None
                
            discriminator = struct.unpack('<Q', data[:8])[0]
            
            # Determine transaction type
            is_buy = discriminator == self.BUY_DISCRIMINATOR
            is_sell = discriminator == self.SELL_DISCRIMINATOR
            
            if not is_buy and not is_sell:
                logger.debug(f"Unknown discriminator: {discriminator}")
                return None
                
            # Parse amounts based on transaction type
            if is_buy:
                # Buy transaction structure: discriminator (8) + sol_amount (8) + min_tokens (8)
                if len(data) >= 24:
                    sol_amount = struct.unpack('<Q', data[8:16])[0] / 1e9
                    min_tokens = struct.unpack('<Q', data[16:24])[0] / (10 ** self.TOKEN_DECIMALS)
                    token_amount = min_tokens  # Approximate, actual may be higher
                else:
                    return None
            else:
                # Sell transaction structure: discriminator (8) + token_amount (8) + min_sol (8)
                if len(data) >= 24:
                    token_amount = struct.unpack('<Q', data[8:16])[0] / (10 ** self.TOKEN_DECIMALS)
                    min_sol = struct.unpack('<Q', data[16:24])[0] / 1e9
                    sol_amount = min_sol  # Approximate, actual may be higher
                else:
                    return None
                    
            # Get token mint from accounts
            # Account order: [token_mint, bonding_curve, bonding_curve_token_account, user, user_token_account, ...]
            accounts = pump_ix.get('accounts', [])
            if len(accounts) < 5:
                logger.error(f"Insufficient accounts: {len(accounts)}")
                return None
                
            token_mint = accounts[0]
            user_address = accounts[3]
            
            # Calculate price
            price = sol_amount / token_amount if token_amount > 0 else 0
            
            # Extract additional info from logs if available
            logs_info = self._parse_logs(tx.get('meta', {}).get('logMessages', []))
            
            result = {
                **base_info,
                'dex': self.dex_name,
                'type': 'buy' if is_buy else 'sell',
                'token_address': token_mint,
                'token_amount': token_amount,
                'sol_amount': sol_amount,
                'amount_usd': sol_amount * logs_info.get('sol_price', 0),  # Need SOL price
                'price': price,
                'wallet_address': user_address,
                'token_decimals': self.TOKEN_DECIMALS,
                'fee_amount': sol_amount * self.FEE_RATE,
                'discriminator': discriminator,
                **logs_info
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing pump.fun transaction {tx.get('signature')}: {e}")
            return None
            
    def _parse_logs(self, log_messages: list) -> Dict:
        """Parse additional information from transaction logs"""
        
        info = {}
        
        for log in log_messages:
            # Look for pump.fun specific logs
            if "Program log: Instruction: Buy" in log:
                info['instruction_type'] = 'buy'
            elif "Program log: Instruction: Sell" in log:
                info['instruction_type'] = 'sell'
            elif "remaining_tokens:" in log:
                # Extract bonding curve state
                try:
                    parts = log.split()
                    for i, part in enumerate(parts):
                        if part == "remaining_tokens:" and i + 1 < len(parts):
                            info['bonding_curve_tokens'] = int(parts[i + 1])
                except:
                    pass
                    
        return info
        
    def is_token_graduated(self, market_cap: float) -> bool:
        """Check if token has graduated to Raydium"""
        # pump.fun tokens graduate at approximately $69k market cap
        return market_cap >= 69000