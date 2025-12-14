"""
Supabase Client Configuration

Initializes and provides Supabase client instances for:
- Authentication
- Database operations
- Storage operations
"""

from supabase import create_client, Client
from typing import Optional

from app.core.config import settings

# Global Supabase client instances
_supabase_client: Optional[Client] = None
_supabase_service_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get Supabase client with anon key (for client-side operations).
    
    Returns:
        Client: Supabase client instance
    """
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            settings.SUPABASE_URL, settings.SUPABASE_KEY
        )
    return _supabase_client


def get_supabase_service_client() -> Client:
    """
    Get Supabase client with service key (for admin operations).
    
    WARNING: Service key bypasses Row Level Security.
    Use only for server-side admin operations.
    
    Returns:
        Client: Supabase service client instance
    """
    global _supabase_service_client
    if _supabase_service_client is None:
        _supabase_service_client = create_client(
            settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY
        )
    return _supabase_service_client

