import requests
import os
from dotenv import load_dotenv

load_dotenv()

def get_visitor_location(ip_address):
    """
    Get location data from IP address using ipapi.co or ip-api.com.
    Returns a dict with location info.
    """
    if not ip_address or ip_address in ['127.0.0.1', 'localhost']:
        return {
            'city': 'Local',
            'region': 'Local',
            'country': 'Local',
            'country_code': 'XX',
            'latitude': None,
            'longitude': None,
            'timezone': 'UTC',
            'isp': 'Local'
        }
    
    # Try ipapi.co (free, requires no API key for basic usage)
    try:
        response = requests.get(f'https://ipapi.co/{ip_address}/json/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                'city': data.get('city', 'Unknown'),
                'region': data.get('region', 'Unknown'),
                'country': data.get('country_name', 'Unknown'),
                'country_code': data.get('country_code', 'XX'),
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'timezone': data.get('timezone', 'UTC'),
                'isp': data.get('org', 'Unknown')
            }
    except:
        pass
    
    # Fallback to ip-api.com
    try:
        response = requests.get(f'http://ip-api.com/json/{ip_address}', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return {
                    'city': data.get('city', 'Unknown'),
                    'region': data.get('regionName', 'Unknown'),
                    'country': data.get('country', 'Unknown'),
                    'country_code': data.get('countryCode', 'XX'),
                    'latitude': data.get('lat'),
                    'longitude': data.get('lon'),
                    'timezone': data.get('timezone', 'UTC'),
                    'isp': data.get('isp', 'Unknown')
                }
    except:
        pass
    
    return {
        'city': 'Unknown',
        'region': 'Unknown',
        'country': 'Unknown',
        'country_code': 'XX',
        'latitude': None,
        'longitude': None,
        'timezone': 'UTC',
        'isp': 'Unknown'
    }
    
    