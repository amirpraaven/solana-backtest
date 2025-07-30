from base64 import b64decode
import struct
from typing import Dict, Optional
import logging

from .dex_base import BaseDEXParser

logger = logging.getLogger(__name__)


class MeteoraDLMMParser(BaseDEXParser):
    """Parser for Meteora Dynamic Liquidity Market Maker (DLMM) transactions"""
    
    # Swap instruction discriminator
    SWAP_DISCRIMINATOR = bytes([0x3f, 0xa9, 0xb3, 0xa2, 0x8f, 0x3f, 0x56, 0xb8])
    
    # Bin constants
    BASIS_POINT_MAX = 10000
    
    def get_program_id(self) -> str:
        return "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo"
        
    def get_dex_name(self) -> str:
        return "meteora_dlmm"
        
    def parse_swap(self, tx: Dict) -> Optional[Dict]:
        """Parse Meteora DLMM swap transaction"""
        
        try:
            # Get base transaction info
            base_info = self.extract_base_info(tx)
            
            # Find DLMM instruction
            dlmm_ix = None
            for ix in tx.get('instructions', []):
                if ix.get('programId') == self.program_id:
                    dlmm_ix = ix
                    break
                    
            if not dlmm_ix:
                return None
                
            # Decode instruction data
            data = b64decode(dlmm_ix.get('data', ''))
            if len(data) < 8:
                return None
                
            # Check discriminator
            discriminator = data[:8]
            if discriminator != self.SWAP_DISCRIMINATOR:
                logger.debug(f"Unknown DLMM discriminator: {discriminator.hex()}")
                return None
                
            # Parse swap data
            # Layout: discriminator (8) + amount_in (8) + min_amount_out (8) + active_bin_id (4)
            if len(data) < 28:
                logger.error(f"Invalid DLMM swap data length: {len(data)}")
                return None
                
            amount_in = struct.unpack('<Q', data[8:16])[0]
            min_amount_out = struct.unpack('<Q', data[16:24])[0]
            active_bin_id = struct.unpack('<i', data[24:28])[0]
            
            # Parse accounts
            # [lbPair, binArrayBitmapExtension (optional), reserveX, reserveY, 
            #  userTokenX, userTokenY, tokenXMint, tokenYMint, oracle (optional),
            #  hostFeeIn (optional), userAccount, tokenXProgram, tokenYProgram, eventAuthority]
            accounts = dlmm_ix.get('accounts', [])
            if len(accounts) < 8:
                logger.error(f"Insufficient DLMM accounts: {len(accounts)}")
                return None
                
            lb_pair = accounts[0]
            
            # Token mints are typically at fixed positions
            token_x_mint_idx = 6
            token_y_mint_idx = 7
            
            if len(accounts) > token_y_mint_idx:
                token_x_mint = accounts[token_x_mint_idx]
                token_y_mint = accounts[token_y_mint_idx]
            else:
                logger.error("Cannot determine token mints from accounts")
                return None
                
            # Find user account (usually near the end before token programs)
            user_account = None
            for i in range(len(accounts) - 1, -1, -1):
                account = accounts[i]
                # Skip known program IDs
                if not self._is_program_id(account):
                    user_account = account
                    break
                    
            # Get token transfers to determine actual amounts and direction
            transfers = self.extract_token_transfers(tx)
            
            # Determine swap details from transfers
            swap_info = self._analyze_dlmm_swap(
                transfers,
                user_account,
                token_x_mint,
                token_y_mint
            )
            
            # Calculate price based on bin
            price = self._calculate_price_from_bin(active_bin_id, swap_info['is_x_to_y'])
            
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
                'lb_pair': lb_pair,
                'amount_in': amount_in,
                'min_amount_out': min_amount_out,
                'active_bin_id': active_bin_id,
                'is_x_to_y': swap_info['is_x_to_y']
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing DLMM transaction {tx.get('signature')}: {e}")
            return None
            
    def _analyze_dlmm_swap(
        self,
        transfers: list,
        user_address: str,
        token_x_mint: str,
        token_y_mint: str
    ) -> Dict:
        """Analyze transfers to determine swap details"""
        
        sol_mint = 'So11111111111111111111111111111111111111112'
        
        # Initialize tracking variables
        token_mint = None
        token_amount = 0
        sol_amount = 0
        is_buy = None
        is_x_to_y = None
        
        # Track transfers by mint
        x_transfers = {'in': 0, 'out': 0}
        y_transfers = {'in': 0, 'out': 0}
        
        for transfer in transfers:
            mint = transfer.get('mint')
            source = transfer.get('source')
            destination = transfer.get('destination')
            amount = int(transfer.get('amount', 0))
            decimals = transfer.get('decimals', 9)
            
            # Skip if not user related
            if source != user_address and destination != user_address:
                continue
                
            if mint == token_x_mint:
                if source == user_address:
                    x_transfers['out'] += amount / (10 ** decimals)
                else:
                    x_transfers['in'] += amount / (10 ** decimals)
            elif mint == token_y_mint:
                if source == user_address:
                    y_transfers['out'] += amount / (10 ** decimals)
                else:
                    y_transfers['in'] += amount / (10 ** decimals)
                    
        # Determine swap direction
        if x_transfers['out'] > 0 and y_transfers['in'] > 0:
            # X -> Y swap
            is_x_to_y = True
            amount_in = x_transfers['out']
            amount_out = y_transfers['in']
            
            # Check which token is SOL
            if token_x_mint == sol_mint:
                sol_amount = amount_in
                token_mint = token_y_mint
                token_amount = amount_out
                is_buy = True
            else:
                sol_amount = amount_out
                token_mint = token_x_mint
                token_amount = amount_in
                is_buy = False
                
        elif y_transfers['out'] > 0 and x_transfers['in'] > 0:
            # Y -> X swap
            is_x_to_y = False
            amount_in = y_transfers['out']
            amount_out = x_transfers['in']
            
            # Check which token is SOL
            if token_y_mint == sol_mint:
                sol_amount = amount_in
                token_mint = token_x_mint
                token_amount = amount_out
                is_buy = True
            else:
                sol_amount = amount_out
                token_mint = token_y_mint
                token_amount = amount_in
                is_buy = False
        else:
            # Unable to determine swap direction
            logger.warning("Unable to determine DLMM swap direction from transfers")
            
        return {
            'token_mint': token_mint,
            'token_amount': token_amount,
            'sol_amount': sol_amount,
            'is_buy': is_buy,
            'is_x_to_y': is_x_to_y
        }
        
    def _calculate_price_from_bin(self, bin_id: int, is_x_to_y: bool) -> float:
        """Calculate approximate price from bin ID"""
        
        # Meteora DLMM uses a bin step parameter that determines price ranges
        # This is a simplified calculation
        # Actual price depends on the bin step configured for the pool
        
        # Base price at bin 0 is 1
        # Each bin represents a small percentage change
        bin_step_bps = 20  # 20 basis points = 0.2% (example, varies by pool)
        
        # Calculate price multiplier
        price_multiplier = (1 + bin_step_bps / self.BASIS_POINT_MAX) ** bin_id
        
        # Adjust for swap direction
        if is_x_to_y:
            return price_multiplier
        else:
            return 1 / price_multiplier if price_multiplier > 0 else 0
            
    def _is_program_id(self, address: str) -> bool:
        """Check if address is a known program ID"""
        
        known_programs = [
            'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',  # Token Program
            'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb',  # Token-2022
            '11111111111111111111111111111111',  # System Program
            self.program_id
        ]
        
        return address in known_programs