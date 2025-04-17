import os
import json
import time
import random
import string
import hashlib
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

class CFSession:
    def __init__(self):
        self.handle = os.getenv("CF_HANDLE")
        self.api_key = os.getenv("CF_API_KEY")
        self.api_secret = os.getenv("CF_API_SECRET")
        self.session = requests.Session()
        self.csrf_token = None
        self.logged_in = False
        
        # Constants
        self.CF_API_BASE = "https://codeforces.com/api/"
        self.CF_BASE_URL = "https://codeforces.com/"
        self.CACHE_DIR = Path.home() / ".cfcli" / "cache"
        self.CACHE_TTL = 300  # 5 minutes
        
        # Ensure cache directory exists
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def is_authenticated(self) -> bool:
        return self.handle and self.api_key and self.api_secret

    def _get_from_cache(self, key: str) -> Optional[Dict]:
        """Get data from cache if valid"""
        cache_file = self.CACHE_DIR / f"{key}.json"
        if not cache_file.exists():
            return None
            
        # Check if cache is still valid
        file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - file_time > timedelta(seconds=self.CACHE_TTL):
            return None
            
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def _save_to_cache(self, key: str, data: Dict) -> None:
        """Save data to cache"""
        cache_file = self.CACHE_DIR / f"{key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f)
        except IOError:
            print(f"Warning: Could not cache data.")

    def _generate_signature(self, method: str, params: Dict[str, str]) -> str:
        """Generate API signature for request"""
        # Sort parameters by key
        sorted_keys = sorted(params.keys())
        signature_string = f"{method}?"
        
        # Construct signature string
        for key in sorted_keys:
            signature_string += f"{key}={params[key]}&"
        
        # Remove trailing '&' and append API secret
        signature_string = signature_string.rstrip('&') + f"#{self.api_secret}"
        
        # Calculate SHA512 hash
        signature = hashlib.sha512(signature_string.encode('utf-8')).hexdigest()
        
        # Add random prefix
        prefix = str(random.randint(100000, 999999))
        return f"{prefix}{signature}"

    def call_api(self, method: str, params: Optional[Dict[str, str]] = None) -> Dict:
        """Make an authenticated call to the Codeforces API"""
        if params is None:
            params = {}

        cache_key = f"{method}_{hash(frozenset(params.items()))}"
        cached_data = self._get_from_cache(cache_key)
        
        if cached_data:
            return cached_data

        url = urljoin(self.CF_API_BASE, method)
        
        if self.is_authenticated():
            # Convert all parameter values to strings
            params = {k: str(v) for k, v in params.items()}
            
            # Add authentication parameters
            current_time = str(int(time.time()))
            rand = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))
            
            params.update({
                "apiKey": self.api_key,
                "time": current_time,
                "rand": rand
            })
            
            # Add signature
            params["apiSig"] = self._generate_signature(method, params)

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "OK":
                self._save_to_cache(cache_key, data)
                return data
            else:
                raise Exception(f"API Error: {data.get('comment', 'Unknown error')}")
        except requests.RequestException as e:
            print(f"Network error: {e}")
            raise
        except Exception as e:
            print(f"Error: {e}")
            raise 