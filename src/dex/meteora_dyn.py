from base64 import b64decode
import struct
from typing import Dict, Optional
import logging

from .dex_base import BaseDEXParser

logger = logging.getLogger(__name__)


class MeteoraDynParser(BaseDEXParser):
    """Parser for Meteora Dynamic Pools (DYN2) transactions"""
    
    # Swap instruction discriminator (example - actual may differ)
    SWAP_DISCRIMINATOR = bytes([0x70, 0xe9, 0x3c, 0x6b, 0xd8, 0x7f, 0x33, 0x05])
    
    def get_program_id(self) -> str:
        return "Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB"
        
    def get_dex_name(self) -> str:
        return "meteora_dyn"
        
    def parse_swap(self, tx: Dict) -> Optional[Dict]:
        """Parse Meteora Dynamic Pool swap transaction"""
        
        try:
            # Get base transaction info
            base_info = self.extract_base_info(tx)
            
            # Find Dynamic Pool instruction
            dyn_ix = None
            for ix in tx.get('instructions', []):
                if ix.get('programId') == self.program_id:
                    dyn_ix = ix
                    break
                    
            if not dyn_ix:
                return None
                
            # Decode instruction data
            data = b64decode(dyn_ix.get('data', ''))
            if len(data) < 8:
                return None
                
            # Check discriminator
            discriminator = data[:8]
            # Dynamic pools may have different discriminators for different swap types
            
            # Parse basic swap data
            # Layout varies but typically includes amount_in and min_amount_out
            if len(data) < 24:
                logger.error(f"Invalid Dynamic Pool swap data length: {len(data)}")
                return None
                
            amount_in = struct.unpack('<Q', data[8:16])[0]
            min_amount_out = struct.unpack('<Q', data[16:24])[0]
            
            # Parse accounts
            accounts = dyn_ix.get('accounts', [])
            if len(accounts) < 6:
                logger.error(f"Insufficient Dynamic Pool accounts: {len(accounts)}")
                return None
                
            # Account layout varies by instruction type
            pool = accounts[0]
            
            # Find user account
            user_account = None
            for account in accounts:
                # User account is typically not a program ID and not the pool
                if not self._is_program_id(account) and account != pool:
                    user_account = account
                    break
                    
            # Get token transfers to determine swap details
            transfers = self.extract_token_transfers(tx)
            
            # Analyze transfers to determine swap direction and amounts
            swap_info = self._analyze_dynamic_swap(transfers, user_account)
            
            # Calculate price
            price = swap_info['sol_amount'] / swap_info['token_amount'] if swap_info['token_amount'] > 0 else 0
            
            # Extract dynamic parameters from logs if available
            dynamic_params = self._extract_dynamic_params(tx.get('meta', {}).get('logMessages', []))
            
            result = {
                **base_info,
                'dex': self.dex_name,
                'type': 'buy' if swap_info['is_buy'] else 'sell',
                'token_address': swap_info['token_mint'],
                'token_amount': swap_info['token_amount'],
                'sol_amount': swap_info['sol_amount'],
                'amount_usd': swap_info['sol_amount'] * swap_info.get('sol_price', 0),
                'price': price,
                'wallet_address': user_account,
                'pool': pool,
                'amount_in': amount_in,
                'min_amount_out': min_amount_out,
                **dynamic_params
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing Dynamic Pool transaction {tx.get('signature')}: {e}")
            return None
            
    def _analyze_dynamic_swap(self, transfers: list, user_address: str) -> Dict:
        """Analyze transfers to determine swap details for dynamic pools"""
        
        sol_mint = 'So11111111111111111111111111111111111111112'
        
        token_mint = None
        token_amount = 0
        sol_amount = 0
        is_buy = None
        
        # Track all transfers involving the user
        user_transfers = {
            'tokens_in': {},
            'tokens_out': {},
            'sol_in': 0,
            'sol_out': 0
        }
        
        for transfer in transfers:
            mint = transfer.get('mint')
            source = transfer.get('source')
            destination = transfer.get('destination')
            amount = int(transfer.get('amount', 0))
            decimals = transfer.get('decimals', 9)
            
            # Only process user-related transfers
            if source != user_address and destination != user_address:
                continue
                
            if mint == sol_mint:
                # SOL transfer
                if source == user_address:
                    user_transfers['sol_out'] += amount / 1e9
                else:
                    user_transfers['sol_in'] += amount / 1e9
            else:
                # Token transfer
                if source == user_address:
                    if mint not in user_transfers['tokens_out']:
                        user_transfers['tokens_out'][mint] = 0
                    user_transfers['tokens_out'][mint] += amount / (10 ** decimals)
                else:
                    if mint not in user_transfers['tokens_in']:
                        user_transfers['tokens_in'][mint] = 0
                    user_transfers['tokens_in'][mint] += amount / (10 ** decimals)
                    
        # Determine swap type based on transfers
        if user_transfers['sol_out'] > 0 and len(user_transfers['tokens_in']) > 0:
            # User sent SOL and received tokens = BUY
            is_buy = True
            sol_amount = user_transfers['sol_out']
            # Get the token with highest amount received
            token_mint = max(user_transfers['tokens_in'].items(), key=lambda x: x[1])[0]
            token_amount = user_transfers['tokens_in'][token_mint]
            
        elif user_transfers['sol_in'] > 0 and len(user_transfers['tokens_out']) > 0:
            # User received SOL and sent tokens = SELL
            is_buy = False
            sol_amount = user_transfers['sol_in']
            # Get the token with highest amount sent
            token_mint = max(user_transfers['tokens_out'].items(), key=lambda x: x[1])[0]
            token_amount = user_transfers['tokens_out'][token_mint]
            
        else:
            # Token-to-token swap or unable to determine
            logger.warning("Unable to determine swap type for Dynamic Pool")
            
        return {
            'token_mint': token_mint,
            'token_amount': token_amount,
            'sol_amount': sol_amount,
            'is_buy': is_buy
        }
        
    def _extract_dynamic_params(self, log_messages: list) -> Dict:
        """Extract dynamic pool parameters from transaction logs"""
        
        params = {}
        
        for log in log_messages:
            # Look for dynamic pool specific logs
            if "fee_rate:" in log:
                try:
                    # Extract fee rate
                    parts = log.split("fee_rate:")
                    if len(parts) > 1:
                        fee_rate = float(parts[1].split()[0])
                        params['dynamic_fee_rate'] = fee_rate
                except:
                    pass
                    
            elif "volatility:" in log:
                try:
                    # Extract volatility parameter
                    parts = log.split("volatility:")
                    if len(parts) > 1:
                        volatility = float(parts[1].split()[0])
                        params['volatility'] = volatility
                except:
                    pass
                    
            elif "concentration:" in log:
                try:
                    # Extract concentration parameter
                    parts = log.split("concentration:")
                    if len(parts) > 1:
                        concentration = float(parts[1].split()[0])
                        params['concentration'] = concentration
                except:
                    pass
                    
        return params
        
    def _is_program_id(self, address: str) -> bool:
        """Check if address is a known program ID"""
        
        known_programs = [
            'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',  # Token Program
            'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb',  # Token-2022
            '11111111111111111111111111111111',  # System Program
            'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL',  # Associated Token Program
            self.program_id
        ]
        
        return address in known_programs