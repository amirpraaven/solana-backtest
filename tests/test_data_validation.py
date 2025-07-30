"""Tests for data validation"""

import pytest
from datetime import datetime, timezone

from src.data.validation import DataValidator


class TestDataValidator:
    """Test data validation utilities"""
    
    def test_validate_transaction(self):
        """Test transaction validation"""
        
        # Valid transaction
        valid_tx = {
            'timestamp': datetime.now(timezone.utc),
            'signature': 'test_signature',
            'token_address': 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',
            'dex': 'pump.fun',
            'type': 'buy',
            'amount_token': 1000.5,
            'amount_usd': 100.0,
            'wallet_address': 'WalletkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
        }
        
        errors = DataValidator.validate_transaction(valid_tx)
        assert len(errors) == 0
        
        # Missing required field
        invalid_tx = valid_tx.copy()
        del invalid_tx['signature']
        errors = DataValidator.validate_transaction(invalid_tx)
        assert any('Missing required field: signature' in e for e in errors)
        
        # Invalid DEX
        invalid_tx = valid_tx.copy()
        invalid_tx['dex'] = 'invalid_dex'
        errors = DataValidator.validate_transaction(invalid_tx)
        assert any('Invalid DEX' in e for e in errors)
        
        # Negative amount
        invalid_tx = valid_tx.copy()
        invalid_tx['amount_usd'] = -100
        errors = DataValidator.validate_transaction(invalid_tx)
        assert any('Negative USD amount' in e for e in errors)
        
        # Invalid address
        invalid_tx = valid_tx.copy()
        invalid_tx['token_address'] = 'short'
        errors = DataValidator.validate_transaction(invalid_tx)
        assert any('Invalid token address' in e for e in errors)
        
    def test_validate_pool_state(self):
        """Test pool state validation"""
        
        # Valid pool state
        valid_state = {
            'time': datetime.now(timezone.utc),
            'token_address': 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',
            'dex': 'raydium_clmm',
            'liquidity_usd': 50000.0,
            'market_cap': 200000.0,
            'price': 0.001,
            'current_tick': 12345
        }
        
        errors = DataValidator.validate_pool_state(valid_state)
        assert len(errors) == 0
        
        # Missing required field
        invalid_state = valid_state.copy()
        del invalid_state['token_address']
        errors = DataValidator.validate_pool_state(invalid_state)
        assert any('Missing required field: token_address' in e for e in errors)
        
        # Negative liquidity
        invalid_state = valid_state.copy()
        invalid_state['liquidity_usd'] = -1000
        errors = DataValidator.validate_pool_state(invalid_state)
        assert any('Negative liquidity_usd' in e for e in errors)
        
        # DEX-specific validation
        invalid_state = valid_state.copy()
        invalid_state['current_tick'] = "not_an_int"
        errors = DataValidator.validate_pool_state(invalid_state)
        assert any('current_tick must be an integer' in e for e in errors)
        
    def test_validate_token_metadata(self):
        """Test token metadata validation"""
        
        # Valid metadata
        valid_metadata = {
            'token_address': 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',
            'name': 'Test Token',
            'symbol': 'TEST',
            'decimals': 9,
            'total_supply': 1000000000
        }
        
        errors = DataValidator.validate_token_metadata(valid_metadata)
        assert len(errors) == 0
        
        # Invalid decimals
        invalid_metadata = valid_metadata.copy()
        invalid_metadata['decimals'] = 20
        errors = DataValidator.validate_token_metadata(invalid_metadata)
        assert any('Invalid decimals' in e for e in errors)
        
        # Negative supply
        invalid_metadata = valid_metadata.copy()
        invalid_metadata['total_supply'] = -1000
        errors = DataValidator.validate_token_metadata(invalid_metadata)
        assert any('Negative total supply' in e for e in errors)
        
    def test_is_valid_solana_address(self):
        """Test Solana address validation"""
        
        # Valid addresses
        assert DataValidator._is_valid_solana_address(
            'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
        ) is True
        
        assert DataValidator._is_valid_solana_address(
            '11111111111111111111111111111111'
        ) is True
        
        # Invalid addresses
        assert DataValidator._is_valid_solana_address('') is False
        assert DataValidator._is_valid_solana_address('short') is False
        assert DataValidator._is_valid_solana_address('invalid@address') is False
        assert DataValidator._is_valid_solana_address(None) is False
        assert DataValidator._is_valid_solana_address(123) is False
        
    def test_sanitize_transaction(self):
        """Test transaction sanitization"""
        
        # Transaction with various data types
        tx = {
            'timestamp': 1234567890,  # Unix timestamp
            'signature': '  test_sig  ',  # Needs trimming
            'amount_token': '1000.5',  # String number
            'amount_usd': 100,
            'token_address': '  TokenAddr  '
        }
        
        sanitized = DataValidator.sanitize_transaction(tx)
        
        # Check timestamp conversion
        assert isinstance(sanitized['timestamp'], datetime)
        assert sanitized['timestamp'].tzinfo is not None
        
        # Check string trimming
        assert sanitized['signature'] == 'test_sig'
        assert sanitized['token_address'] == 'TokenAddr'
        
        # Check numeric conversion
        assert sanitized['amount_token'] == 1000.5
        assert isinstance(sanitized['amount_token'], float)
        
    def test_validate_batch(self):
        """Test batch validation"""
        
        transactions = [
            {
                'timestamp': datetime.now(timezone.utc),
                'signature': 'sig1',
                'token_address': 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',
                'dex': 'pump.fun',
                'type': 'buy'
            },
            {
                'timestamp': datetime.now(timezone.utc),
                'signature': 'sig2',
                # Missing token_address
                'dex': 'pump.fun',
                'type': 'buy'
            },
            {
                'timestamp': datetime.now(timezone.utc),
                'signature': 'sig3',
                'token_address': 'invalid',  # Invalid address
                'dex': 'pump.fun',
                'type': 'buy'
            }
        ]
        
        results = DataValidator.validate_batch(transactions, 'transaction')
        
        assert results['total'] == 3
        assert results['valid'] == 1
        assert results['invalid'] == 2
        assert results['validation_rate'] == pytest.approx(33.33, rel=0.1)
        assert len(results['errors']) == 2
        
        # Check error details
        error1 = results['errors'][0]
        assert error1['index'] == 1
        assert any('Missing required field' in e for e in error1['errors'])
        
        error2 = results['errors'][1]
        assert error2['index'] == 2
        assert any('Invalid token address' in e for e in error2['errors'])