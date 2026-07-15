from supabase import create_client, Client
from flask import current_app, g

def get_supabase() -> Client:
    """Get or create a Supabase client per request."""
    if 'supabase' not in g:
        g.supabase = create_client(
            current_app.config['SUPABASE_URL'],
            current_app.config['SUPABASE_KEY']
        )
    return g.supabase

def init_supabase(app):
    """Initialize Supabase client (optional, for app-level usage)."""
    app.supabase = create_client(
        app.config['SUPABASE_URL'],
        app.config['SUPABASE_KEY']
    )
    
    