from .dex_base import BaseDEXParser
from .pump_fun import PumpFunParser
from .raydium_clmm import RaydiumCLMMParser
from .raydium_cpmm import RaydiumCPMMParser
from .meteora_dlmm import MeteoraDLMMParser
from .meteora_dyn import MeteoraDynParser

# Factory function to get appropriate parser
def get_dex_parser(program_id: str) -> BaseDEXParser:
    """Get the appropriate DEX parser for a given program ID"""
    
    parsers = {
        "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": PumpFunParser,
        "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK": RaydiumCLMMParser,
        "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C": RaydiumCPMMParser,
        "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo": MeteoraDLMMParser,
        "Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB": MeteoraDynParser
    }
    
    parser_class = parsers.get(program_id)
    if parser_class:
        return parser_class()
    
    raise ValueError(f"No parser found for program ID: {program_id}")

# List of all supported DEX program IDs
SUPPORTED_DEXES = {
    "pump.fun": "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
    "raydium_clmm": "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK",
    "raydium_cpmm": "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C",
    "meteora_dlmm": "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo",
    "meteora_dyn": "Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB"
}

__all__ = [
    "BaseDEXParser",
    "PumpFunParser",
    "RaydiumCLMMParser",
    "RaydiumCPMMParser",
    "MeteoraDLMMParser",
    "MeteoraDynParser",
    "get_dex_parser",
    "SUPPORTED_DEXES"
]