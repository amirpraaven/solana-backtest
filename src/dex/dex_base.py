from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BaseDEXParser(ABC):
    """Base class for DEX-specific transaction parsers"""
    
    def __init__(self):
        self.program_id = self.get_program_id()
        self.dex_name = self.get_dex_name()
        
    @abstractmethod
    def get_program_id(self) -> str:
        """Return the program ID for this DEX"""
        pass
        
    @abstractmethod
    def get_dex_name(self) -> str:
        """Return the DEX name for database storage"""
        pass
        
    def is_dex_transaction(self, tx: Dict) -> bool:
        """Check if transaction belongs to this DEX"""
        return any(
            ix.get('programId') == self.program_id
            for ix in tx.get('instructions', [])
        )
        
    @abstractmethod
    def parse_swap(self, tx: Dict) -> Optional[Dict]:
        """Parse swap transaction into standardized format"""
        pass
        
    def extract_token_transfers(self, tx: Dict) -> List[Dict]:
        """Extract token transfer information from transaction"""
        transfers = []
        
        # Look for token transfer instructions
        for ix in tx.get('innerInstructions', []):
            for inner_ix in ix.get('instructions', []):
                if inner_ix.get('programId') == 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA':
                    # This is a token program instruction
                    parsed = inner_ix.get('parsed', {})
                    if parsed.get('type') in ['transfer', 'transferChecked']:
                        info = parsed.get('info', {})
                        transfers.append({
                            'amount': info.get('amount') or info.get('tokenAmount', {}).get('amount'),
                            'decimals': info.get('tokenAmount', {}).get('decimals'),
                            'mint': info.get('mint'),
                            'source': info.get('source'),
                            'destination': info.get('destination'),
                            'authority': info.get('authority')
                        })
                        
        return transfers
        
    def calculate_amounts_from_transfers(
        self,
        transfers: List[Dict],
        token_mint: str,
        user_address: str
    ) -> Dict:
        """Calculate buy/sell amounts from transfers"""
        
        sol_amount = 0
        token_amount = 0
        is_buy = None
        
        for transfer in transfers:
            # Identify SOL transfers (native SOL has specific mint)
            if transfer['mint'] == 'So11111111111111111111111111111111111111112':
                # User sending SOL = buy
                if transfer['source'] == user_address:
                    sol_amount = int(transfer['amount']) / 1e9
                    is_buy = True
                # User receiving SOL = sell
                elif transfer['destination'] == user_address:
                    sol_amount = int(transfer['amount']) / 1e9
                    is_buy = False
                    
            # Token transfers
            elif transfer['mint'] == token_mint:
                decimals = transfer.get('decimals', 9)
                # User receiving tokens = buy
                if transfer['destination'] == user_address:
                    token_amount = int(transfer['amount']) / (10 ** decimals)
                # User sending tokens = sell
                elif transfer['source'] == user_address:
                    token_amount = int(transfer['amount']) / (10 ** decimals)
                    
        return {
            'sol_amount': sol_amount,
            'token_amount': token_amount,
            'is_buy': is_buy
        }
        
    def extract_base_info(self, tx: Dict) -> Dict:
        """Extract base transaction information"""
        return {
            'signature': tx.get('signature'),
            'timestamp': datetime.fromtimestamp(tx.get('timestamp', 0)),
            'slot': tx.get('slot'),
            'success': tx.get('err') is None,
            'fee': tx.get('fee', 0) / 1e9,  # Convert lamports to SOL
            'signer': tx.get('feePayer') or (tx.get('accounts', [{}])[0] if tx.get('accounts') else None)
        }