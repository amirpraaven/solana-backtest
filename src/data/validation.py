"""Data validation utilities"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class DataValidator:
    """Validate data quality and consistency"""
    
    @staticmethod
    def validate_transaction(tx: Dict) -> List[str]:
        """Validate transaction data"""
        errors = []
        
        # Required fields
        required_fields = ['timestamp', 'signature', 'token_address', 'dex', 'type']
        for field in required_fields:
            if field not in tx or tx[field] is None:
                errors.append(f"Missing required field: {field}")
                
        # Validate timestamp
        if 'timestamp' in tx:
            if isinstance(tx['timestamp'], str):
                try:
                    datetime.fromisoformat(tx['timestamp'])
                except ValueError:
                    errors.append(f"Invalid timestamp format: {tx['timestamp']}")
            elif isinstance(tx['timestamp'], (int, float)):
                # Unix timestamp
                if tx['timestamp'] < 1000000000 or tx['timestamp'] > 2000000000:
                    errors.append(f"Invalid unix timestamp: {tx['timestamp']}")
                    
        # Validate DEX
        if 'dex' in tx:
            valid_dexes = ['pump.fun', 'raydium_clmm', 'raydium_cpmm', 'meteora_dlmm', 'meteora_dyn']
            if tx['dex'] not in valid_dexes:
                errors.append(f"Invalid DEX: {tx['dex']}")
                
        # Validate transaction type
        if 'type' in tx:
            valid_types = ['buy', 'sell', 'swap']
            if tx['type'] not in valid_types:
                errors.append(f"Invalid transaction type: {tx['type']}")
                
        # Validate amounts
        if 'amount_token' in tx and tx['amount_token'] is not None:
            try:
                amount = float(tx['amount_token'])
                if amount < 0:
                    errors.append(f"Negative token amount: {amount}")
            except (ValueError, TypeError):
                errors.append(f"Invalid token amount: {tx['amount_token']}")
                
        if 'amount_usd' in tx and tx['amount_usd'] is not None:
            try:
                amount = float(tx['amount_usd'])
                if amount < 0:
                    errors.append(f"Negative USD amount: {amount}")
            except (ValueError, TypeError):
                errors.append(f"Invalid USD amount: {tx['amount_usd']}")
                
        # Validate addresses
        if 'token_address' in tx:
            if not DataValidator._is_valid_solana_address(tx['token_address']):
                errors.append(f"Invalid token address: {tx['token_address']}")
                
        if 'wallet_address' in tx and tx['wallet_address']:
            if not DataValidator._is_valid_solana_address(tx['wallet_address']):
                errors.append(f"Invalid wallet address: {tx['wallet_address']}")
                
        return errors
        
    @staticmethod
    def validate_pool_state(state: Dict) -> List[str]:
        """Validate pool state data"""
        errors = []
        
        # Required fields
        required_fields = ['time', 'token_address', 'dex']
        for field in required_fields:
            if field not in state or state[field] is None:
                errors.append(f"Missing required field: {field}")
                
        # Validate numeric fields
        numeric_fields = ['liquidity_usd', 'market_cap', 'price']
        for field in numeric_fields:
            if field in state and state[field] is not None:
                try:
                    value = float(state[field])
                    if value < 0:
                        errors.append(f"Negative {field}: {value}")
                except (ValueError, TypeError):
                    errors.append(f"Invalid {field}: {state[field]}")
                    
        # DEX-specific validation
        if state.get('dex') == 'raydium_clmm' and 'current_tick' in state:
            if not isinstance(state['current_tick'], int):
                errors.append("current_tick must be an integer for Raydium CLMM")
                
        if state.get('dex') == 'meteora_dlmm' and 'active_bin_id' in state:
            if not isinstance(state['active_bin_id'], int):
                errors.append("active_bin_id must be an integer for Meteora DLMM")
                
        return errors
        
    @staticmethod
    def validate_token_metadata(metadata: Dict) -> List[str]:
        """Validate token metadata"""
        errors = []
        
        # Required fields
        if 'token_address' not in metadata:
            errors.append("Missing token_address")
        elif not DataValidator._is_valid_solana_address(metadata['token_address']):
            errors.append(f"Invalid token address: {metadata['token_address']}")
            
        # Validate decimals
        if 'decimals' in metadata:
            if not isinstance(metadata['decimals'], int):
                errors.append("Decimals must be an integer")
            elif metadata['decimals'] < 0 or metadata['decimals'] > 18:
                errors.append(f"Invalid decimals: {metadata['decimals']}")
                
        # Validate supply
        if 'total_supply' in metadata and metadata['total_supply'] is not None:
            try:
                supply = float(metadata['total_supply'])
                if supply < 0:
                    errors.append(f"Negative total supply: {supply}")
            except (ValueError, TypeError):
                errors.append(f"Invalid total supply: {metadata['total_supply']}")
                
        return errors
        
    @staticmethod
    def _is_valid_solana_address(address: str) -> bool:
        """Check if string is a valid Solana address"""
        if not address or not isinstance(address, str):
            return False
            
        # Solana addresses are base58 encoded and typically 32-44 characters
        if len(address) < 32 or len(address) > 44:
            return False
            
        # Check for valid base58 characters
        valid_chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
        return all(c in valid_chars for c in address)
        
    @staticmethod
    def sanitize_transaction(tx: Dict) -> Dict:
        """Sanitize transaction data"""
        sanitized = tx.copy()
        
        # Ensure timestamp is datetime
        if 'timestamp' in sanitized:
            if isinstance(sanitized['timestamp'], (int, float)):
                sanitized['timestamp'] = datetime.fromtimestamp(
                    sanitized['timestamp'],
                    tz=timezone.utc
                )
            elif isinstance(sanitized['timestamp'], str):
                sanitized['timestamp'] = datetime.fromisoformat(
                    sanitized['timestamp']
                )
                
        # Ensure numeric fields are proper types
        for field in ['amount_token', 'amount_usd']:
            if field in sanitized and sanitized[field] is not None:
                try:
                    sanitized[field] = float(sanitized[field])
                except (ValueError, TypeError):
                    sanitized[field] = None
                    
        # Normalize addresses
        for field in ['token_address', 'wallet_address', 'signature']:
            if field in sanitized and sanitized[field]:
                sanitized[field] = str(sanitized[field]).strip()
                
        return sanitized
        
    @staticmethod
    def validate_batch(
        data: List[Dict],
        data_type: str = 'transaction'
    ) -> Dict[str, Any]:
        """Validate a batch of data"""
        
        validation_func = {
            'transaction': DataValidator.validate_transaction,
            'pool_state': DataValidator.validate_pool_state,
            'token_metadata': DataValidator.validate_token_metadata
        }.get(data_type)
        
        if not validation_func:
            raise ValueError(f"Unknown data type: {data_type}")
            
        results = {
            'total': len(data),
            'valid': 0,
            'invalid': 0,
            'errors': []
        }
        
        for i, item in enumerate(data):
            errors = validation_func(item)
            if errors:
                results['invalid'] += 1
                results['errors'].append({
                    'index': i,
                    'errors': errors,
                    'data': item
                })
            else:
                results['valid'] += 1
                
        results['validation_rate'] = (
            results['valid'] / results['total'] * 100
            if results['total'] > 0 else 0
        )
        
        return results