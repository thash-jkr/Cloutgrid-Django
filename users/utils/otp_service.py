import random
from datetime import datetime, timedelta
from django.core.cache import cache

def generate_otp(length=6):
    return ''.join([str(random.randint(1, 9)) for _ in range(length)])

def store_otp(username, otp, expiry_minutes=5):
    cache_key = f"otp_{username}"
    otp_value = str(otp)
    
    timeout_seconds = expiry_minutes * 60
    cache.set(cache_key, otp_value, timeout=timeout_seconds)

def verify_otp(username, input_otp):
    cache_key = f"otp_{username}"
    otp_data = cache.get(cache_key)
    
    if not otp_data:
        return False, "OTP expired or not found."
    
    if str(otp_data) != str(input_otp):
        return False, "Invalid OTP"
    
    cache.delete(cache_key)
    
    return True, "OTP verified successfully."
