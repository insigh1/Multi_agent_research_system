"""
Centralized model pricing configuration for the Multi-Agent Research System.

This module provides a single source of truth for all model pricing information,
eliminating duplication and ensuring consistency across the application.
"""

# Model pricing (per 1M tokens)
MODEL_COSTS = {
    # Core available models

    
    # Qwen models
    "qwen3-235b-a22b": {"input": 0.22, "output": 0.88},
    "qwen3-30b-a3b": {"input": 0.15, "output": 0.60},
    "qwen3-8b": {"input": 0.20, "output": 0.20},
    "qwq-32b": {"input": 0.90, "output": 0.90},
    "qwen2p5-vl-32b-instruct": {"input": 0.90, "output": 0.90},
    "qwen2p5-vl-7b-instruct": {"input": 0.20, "output": 0.20},
    "qwen2-vl-72b-instruct": {"input": 0.90, "output": 0.90},
    "qwen2p5-72b-instruct": {"input": 0.90, "output": 0.90},
    "qwen2-7b-instruct": {"input": 0.20, "output": 0.20},
    
    # DeepSeek models
    "deepseek-v3-0324": {"input": 0.90, "output": 0.90},
    "deepseek-v3": {"input": 0.90, "output": 0.90},
    "deepseek-r1-0528": {"input": 3.00, "output": 8.00},
    "deepseek-r1": {"input": 3.00, "output": 8.00},
    "deepseek-r1-basic": {"input": 0.55, "output": 2.19},
    
    # Meta Llama models
    "llama4-maverick-instruct-basic": {"input": 0.22, "output": 0.88},
    "llama4-scout-instruct-basic": {"input": 0.15, "output": 0.60},
    "llama-v3p3-70b-instruct": {"input": 0.9, "output": 0.9},
    "llama-v3p1-405b-instruct": {"input": 3.0, "output": 3.0},
    "llama-v3p1-70b-instruct": {"input": 0.9, "output": 0.9},
    "llama-v3p1-8b-instruct": {"input": 0.2, "output": 0.2},
    "llama-guard-3-8b": {"input": 0.20, "output": 0.20},

    # Mixtral models
    "mixtral-8x22b-instruct": {"input": 1.20, "output": 1.20},

    # Sentient models
    "dobby-mini-unhinged-plus-llama-3-1-8b": {"input": 0.20, "output": 0.20},
    "dobby-unhinged-llama-3-3-70b-new": {"input": 0.90, "output": 0.90},

    # Fireworks models
    "firesearch-ocr-v6": {"input": 0.20, "output": 0.20},

    # Databricks models
    "dbrx-instruct": {"input": 1.6, "output": 1.6},



    

}

def get_model_cost(model_name: str) -> dict:
    """
    Get the cost information for a specific model.
    
    Args:
        model_name: The name of the model (with or without provider prefix)
    
    Returns:
        Dictionary with 'input' and 'output' cost per 1M tokens
    """
    # Remove provider prefixes if present
    clean_model_name = model_name
    if "accounts/fireworks/models/" in model_name:
        clean_model_name = model_name.replace("accounts/fireworks/models/", "")
    elif "/" in model_name:
        # Handle other provider prefixes
        clean_model_name = model_name.split("/")[-1]
    
    return MODEL_COSTS.get(clean_model_name, {"input": 0.5, "output": 0.5})

def get_all_models() -> list:
    """
    Get a list of all available model names.
    
    Returns:
        List of model names
    """
    return list(MODEL_COSTS.keys())

def calculate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate the cost for a specific model and token usage.
    
    Args:
        model_name: The name of the model
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens generated
    
    Returns:
        Total cost in dollars
    """
    costs = get_model_cost(model_name)
    input_cost = (input_tokens / 1_000_000) * costs["input"]
    output_cost = (output_tokens / 1_000_000) * costs["output"]
    return input_cost + output_cost 