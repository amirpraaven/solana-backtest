from base64 import b64decode
import struct
from typing import Dict, Optional
import logging

from .dex_base import BaseDEXParser

logger = logging.getLogger(__name__)


class RaydiumCPMMParser(BaseDEXParser):
    """Parser for Raydium Constant Product Market Maker (CPMM) transactions"""
    
    # Swap instruction discriminators
    SWAP_BASE_IN_DISCRIMINATOR = bytes([0x8f, 0x9a, 0xd9, 0x48, 0xe6, 0xfb, 0x0a, 0xfa])
    SWAP_BASE_OUT_DISCRIMINATOR = bytes([0x6f, 0x48, 0x7a, 0x0f, 0x96, 0xd8, 0x31, 0xfe])
    
    # Standard fee rate
    FEE_RATE = 0.0025  # 0.25%
    
    def get_program_id(self) -> str:
        return "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C"
        
    def get_dex_name(self) -> str:
        return "raydium_cpmm"
        
    def parse_swap(self, tx: Dict) -> Optional[Dict]:
        """Parse Raydium CPMM swap transaction"""
        
        try:
            # Get base transaction info
            base_info = self.extract_base_info(tx)
            
            # Find CPMM instruction
            cpmm_ix = None
            for ix in tx.get('instructions', []):
                if ix.get('programId') == self.program_id:
                    cpmm_ix = ix
                    break
                    
            if not cpmm_ix:
                return None
                
            # Decode instruction data
            data = b64decode(cpmm_ix.get('data', ''))
            if len(data) < 8:
                return None
                
            # Check discriminator and determine swap type
            discriminator = data[:8]
            is_base_in = None
            
            if discriminator == self.SWAP_BASE_IN_DISCRIMINATOR:
                is_base_in = True
            elif discriminator == self.SWAP_BASE_OUT_DISCRIMINATOR:
                is_base_in = False
            else:
                logger.debug(f"Unknown CPMM discriminator: {discriminator.hex()}")
                return None
                
            # Parse swap amounts
            # Layout: discriminator (8) + amount_in (8) + minimum_amount_out (8)
            if len(data) < 24:
                logger.error(f"Invalid CPMM swap data length: {len(data)}")
                return None
                
            amount_in = struct.unpack('<Q', data[8:16])[0]
            minimum_amount_out = struct.unpack('<Q', data[16:24])[0]
            
            # Parse accounts
            # Account layout varies but typically includes:
            # [authority, ammConfig, poolState, inputVault, outputVault, 
            #  inputTokenProgram, outputTokenProgram, inputTokenAccount, outputTokenAccount, ...]
            accounts = cpmm_ix.get('accounts', [])
            if len(accounts) < 9:
                logger.error(f"Insufficient CPMM accounts: {len(accounts)}")
                return None
                
            authority = accounts[0]
            pool_state = accounts[2]
            input_vault = accounts[3]
            output_vault = accounts[4]
            
            # Get token transfers to determine actual amounts and tokens
            transfers = self.extract_token_transfers(tx)
            
            # Determine token information from transfers
            token_info = self._determine_token_info_from_transfers(
                transfers,
                authority,
                input_vault,
                output_vault
            )
            
            # Calculate price
            if token_info['token_amount'] > 0:
                price = token_info['sol_amount'] / token_info['token_amount']
            else:
                price = 0
                
            result = {
                **base_info,
                'dex': self.dex_name,
                'type': 'buy' if token_info['is_buy'] else 'sell',
                'token_address': token_info['token_mint'],
                'token_amount': token_info['token_amount'],
                'sol_amount': token_info['sol_amount'],
                'amount_usd': token_info['sol_amount'] * token_info.get('sol_price', 0),
                'price': price,
                'wallet_address': authority,
                'pool_state': pool_state,
                'amount_in': amount_in,
                'minimum_amount_out': minimum_amount_out,
                'is_base_in': is_base_in,
                'fee_amount': amount_in * self.FEE_RATE / (10 ** token_info.get('decimals', 9))
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing CPMM transaction {tx.get('signature')}: {e}")
            return None
            
    def _determine_token_info_from_transfers(
        self,
        transfers: list,
        user_address: str,
        input_vault: str,
        output_vault: str
    ) -> Dict:
        """Determine token information from transfers and vaults"""
        
        sol_mint = 'So11111111111111111111111111111111111111112'
        token_mint = None
        token_amount = 0
        sol_amount = 0
        is_buy = None
        decimals = 9
        
        for transfer in transfers:
            mint = transfer.get('mint')
            source = transfer.get('source')
            destination = transfer.get('destination')
            amount = int(transfer.get('amount', 0))
            transfer_decimals = transfer.get('decimals', 9)
            
            # Check if this transfer involves the pool vaults
            involves_pool = source in [input_vault, output_vault] or destination in [input_vault, output_vault]
            
            if not involves_pool:
                continue
                
            if mint == sol_mint:
                # SOL transfer
                if source == user_address or destination == output_vault:
                    # User sending SOL or SOL going to output vault = buying token
                    sol_amount = amount / 1e9
                    is_buy = True
                elif destination == user_address or source == output_vault:
                    # User receiving SOL or SOL coming from output vault = selling token
                    sol_amount = amount / 1e9
                    is_buy = False
            else:
                # Token transfer
                token_mint = mint
                decimals = transfer_decimals
                if destination == user_address or source == input_vault:
                    # User receiving token or token coming from input vault = buying
                    token_amount = amount / (10 ** decimals)
                elif source == user_address or destination == input_vault:
                    # User sending token or token going to input vault = selling
                    token_amount = amount / (10 ** decimals)
                    
        return {
            'token_mint': token_mint,
            'token_amount': token_amount,
            'sol_amount': sol_amount,
            'is_buy': is_buy,
            'decimals': decimals
        }