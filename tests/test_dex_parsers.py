"""Tests for DEX parsers"""

import pytest
from datetime import datetime
from base64 import b64encode
import struct

from src.dex import (
    get_dex_parser,
    PumpFunParser,
    RaydiumCLMMParser,
    RaydiumCPMMParser,
    MeteoraDLMMParser,
    MeteoraDynParser,
    SUPPORTED_DEXES
)


class TestDEXParsers:
    """Test DEX-specific transaction parsers"""
    
    def test_get_dex_parser(self):
        """Test parser factory function"""
        
        # Test each supported DEX
        pump_parser = get_dex_parser(SUPPORTED_DEXES['pump.fun'])
        assert isinstance(pump_parser, PumpFunParser)
        
        clmm_parser = get_dex_parser(SUPPORTED_DEXES['raydium_clmm'])
        assert isinstance(clmm_parser, RaydiumCLMMParser)
        
        cpmm_parser = get_dex_parser(SUPPORTED_DEXES['raydium_cpmm'])
        assert isinstance(cpmm_parser, RaydiumCPMMParser)
        
        dlmm_parser = get_dex_parser(SUPPORTED_DEXES['meteora_dlmm'])
        assert isinstance(dlmm_parser, MeteoraDLMMParser)
        
        dyn_parser = get_dex_parser(SUPPORTED_DEXES['meteora_dyn'])
        assert isinstance(dyn_parser, MeteoraDynParser)
        
        # Test unknown program ID
        with pytest.raises(ValueError, match="No parser found"):
            get_dex_parser("UnknownProgramID123")
            
    def test_pump_fun_parser_buy(self):
        """Test pump.fun buy transaction parsing"""
        
        parser = PumpFunParser()
        
        # Create buy instruction data
        buy_discriminator = 16927863322537952870
        sol_amount = int(1.5 * 1e9)  # 1.5 SOL in lamports
        min_tokens = int(1000 * 1e6)  # 1000 tokens (6 decimals)
        
        instruction_data = struct.pack('<QQQ', buy_discriminator, sol_amount, min_tokens)
        
        tx = {
            'signature': 'test_buy_sig',
            'timestamp': int(datetime.utcnow().timestamp()),
            'slot': 12345678,
            'err': None,
            'instructions': [
                {
                    'programId': '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P',
                    'data': b64encode(instruction_data).decode('utf-8'),
                    'accounts': [
                        'token_mint_address',
                        'bonding_curve_address',
                        'bonding_curve_token_account',
                        'user_wallet_address',
                        'user_token_account'
                    ]
                }
            ],
            'meta': {
                'logMessages': ['Program log: Instruction: Buy']
            }
        }
        
        result = parser.parse_swap(tx)
        
        assert result is not None
        assert result['dex'] == 'pump.fun'
        assert result['type'] == 'buy'
        assert result['token_address'] == 'token_mint_address'
        assert result['wallet_address'] == 'user_wallet_address'
        assert result['sol_amount'] == pytest.approx(1.5, rel=0.01)
        assert result['token_amount'] == pytest.approx(1000, rel=0.01)
        assert result['token_decimals'] == 6
        
    def test_pump_fun_parser_sell(self):
        """Test pump.fun sell transaction parsing"""
        
        parser = PumpFunParser()
        
        # Create sell instruction data
        sell_discriminator = 12502976635542562355
        token_amount = int(500 * 1e6)  # 500 tokens (6 decimals)
        min_sol = int(0.75 * 1e9)  # 0.75 SOL in lamports
        
        instruction_data = struct.pack('<QQQ', sell_discriminator, token_amount, min_sol)
        
        tx = {
            'signature': 'test_sell_sig',
            'timestamp': int(datetime.utcnow().timestamp()),
            'slot': 12345679,
            'err': None,
            'instructions': [
                {
                    'programId': '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P',
                    'data': b64encode(instruction_data).decode('utf-8'),
                    'accounts': [
                        'token_mint_address',
                        'bonding_curve_address',
                        'bonding_curve_token_account',
                        'user_wallet_address',
                        'user_token_account'
                    ]
                }
            ]
        }
        
        result = parser.parse_swap(tx)
        
        assert result is not None
        assert result['type'] == 'sell'
        assert result['token_amount'] == pytest.approx(500, rel=0.01)
        assert result['sol_amount'] == pytest.approx(0.75, rel=0.01)
        
    def test_parser_base_info_extraction(self):
        """Test base transaction info extraction"""
        
        parser = PumpFunParser()
        
        tx = {
            'signature': 'test_sig',
            'timestamp': 1234567890,
            'slot': 12345678,
            'err': None,
            'fee': 5000,
            'feePayer': 'fee_payer_address'
        }
        
        base_info = parser.extract_base_info(tx)
        
        assert base_info['signature'] == 'test_sig'
        assert isinstance(base_info['timestamp'], datetime)
        assert base_info['slot'] == 12345678
        assert base_info['success'] is True
        assert base_info['fee'] == pytest.approx(0.000005, rel=0.01)
        assert base_info['signer'] == 'fee_payer_address'
        
    def test_token_transfer_extraction(self):
        """Test token transfer extraction"""
        
        parser = RaydiumCLMMParser()
        
        tx = {
            'innerInstructions': [
                {
                    'instructions': [
                        {
                            'programId': 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',
                            'parsed': {
                                'type': 'transfer',
                                'info': {
                                    'amount': '1000000000',
                                    'source': 'source_account',
                                    'destination': 'dest_account',
                                    'authority': 'authority_account'
                                }
                            }
                        },
                        {
                            'programId': 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',
                            'parsed': {
                                'type': 'transferChecked',
                                'info': {
                                    'tokenAmount': {
                                        'amount': '500000000',
                                        'decimals': 6
                                    },
                                    'mint': 'token_mint',
                                    'source': 'source2',
                                    'destination': 'dest2'
                                }
                            }
                        }
                    ]
                }
            ]
        }
        
        transfers = parser.extract_token_transfers(tx)
        
        assert len(transfers) == 2
        assert transfers[0]['amount'] == '1000000000'
        assert transfers[0]['source'] == 'source_account'
        assert transfers[1]['amount'] == '500000000'
        assert transfers[1]['decimals'] == 6
        assert transfers[1]['mint'] == 'token_mint'
        
    def test_is_dex_transaction(self):
        """Test DEX transaction identification"""
        
        pump_parser = PumpFunParser()
        clmm_parser = RaydiumCLMMParser()
        
        # pump.fun transaction
        pump_tx = {
            'instructions': [
                {'programId': '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P'},
                {'programId': 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'}
            ]
        }
        
        assert pump_parser.is_dex_transaction(pump_tx) is True
        assert clmm_parser.is_dex_transaction(pump_tx) is False
        
        # Raydium CLMM transaction
        clmm_tx = {
            'instructions': [
                {'programId': 'CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK'}
            ]
        }
        
        assert pump_parser.is_dex_transaction(clmm_tx) is False
        assert clmm_parser.is_dex_transaction(clmm_tx) is True
        
    def test_calculate_amounts_from_transfers(self):
        """Test amount calculation from transfers"""
        
        parser = RaydiumCPMMParser()
        
        transfers = [
            {
                'mint': 'So11111111111111111111111111111111111111112',  # SOL
                'amount': '1000000000',  # 1 SOL
                'source': 'user_wallet',
                'destination': 'pool_account'
            },
            {
                'mint': 'token_mint_address',
                'amount': '5000000000',  # 5000 tokens (9 decimals)
                'decimals': 9,
                'source': 'pool_account',
                'destination': 'user_wallet'
            }
        ]
        
        result = parser.calculate_amounts_from_transfers(
            transfers,
            'token_mint_address',
            'user_wallet'
        )
        
        assert result['sol_amount'] == pytest.approx(1.0, rel=0.01)
        assert result['token_amount'] == pytest.approx(5000.0, rel=0.01)
        assert result['is_buy'] is True  # User sent SOL, received tokens