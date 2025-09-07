"""
Environment variable utilities for safe configuration loading.
"""
import os
from typing import Any, Optional, Union
from django.core.exceptions import ImproperlyConfigured


def get_env_var(
    key: str, 
    default: Optional[Any] = None, 
    required: bool = False,
    cast_type: type = str
) -> Any:
    """
    Safely get an environment variable with type casting and validation.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        required: Whether the variable is required
        cast_type: Type to cast the value to
        
    Returns:
        Environment variable value, cast to specified type
        
    Raises:
        ImproperlyConfigured: If required variable is missing
    """
    value = os.getenv(key)
    
    if value is None:
        if required:
            raise ImproperlyConfigured(f"Required environment variable {key} is not set")
        return default
    
    try:
        if cast_type == bool:
            return value.lower() in ('true', '1', 'yes', 'on')
        return cast_type(value)
    except (ValueError, TypeError) as e:
        raise ImproperlyConfigured(
            f"Environment variable {key} cannot be cast to {cast_type.__name__}: {e}"
        )


def get_database_url() -> str:
    """Get database URL from environment."""
    return get_env_var(
        'DATABASE_URL', 
        required=True,
        cast_type=str
    )


def get_redis_url() -> str:
    """Get Redis URL from environment."""
    return get_env_var(
        'REDIS_URL',
        default='redis://localhost:6379/0',
        cast_type=str
    )


def get_openai_config() -> dict[str, Any]:
    """Get OpenAI configuration from environment."""
    return {
        'api_key': get_env_var('OPENAI_API_KEY', required=True),
        'model': get_env_var('OPENAI_MODEL', default='gpt-4o-mini'),
        'max_tokens': get_env_var('OPENAI_MAX_TOKENS', default=4000, cast_type=int),
        'temperature': get_env_var('OPENAI_TEMPERATURE', default=0.0, cast_type=float),
    }


def get_supabase_config() -> dict[str, Any]:
    """Get Supabase configuration from environment."""
    return {
        'url': get_env_var('SUPABASE_URL', required=True),
        'anon_key': get_env_var('SUPABASE_ANON_KEY', required=True),
        'service_role_key': get_env_var('SUPABASE_SERVICE_ROLE_KEY', required=True),
    }

def env_str(key, default=None): return os.getenv(key, default)
def env_int(key, default=0): return int(os.getenv(key, default))
def env_float(key, default=0.0): return float(os.getenv(key, default))
def env_bool(key, default=False): return os.getenv(key, str(default)).lower() in ("1","true","yes","y")
