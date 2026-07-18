from supabase import create_client


def get_watchlist(supabase_url, supabase_service_key):
    client = create_client(supabase_url, supabase_service_key)
    response = client.table("watchlist").select("*").execute()
    return response.data
