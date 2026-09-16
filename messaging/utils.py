import jwt
import datetime
from django.conf import settings

def generate_stream_token(user_id):
    payload = {
        "user_id": str(user_id),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        "iat": datetime.datetime.utcnow()
    }
    
    token = jwt.encode(
        payload,
        settings.STREAM_API_SECRET,
        algorithm="HS256"
    )
    
    return token