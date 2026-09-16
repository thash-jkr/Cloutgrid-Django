import requests, datetime
from django.conf import settings

from ..models import GoogleAuth

def refresh_access_token(user):
  g_auth = GoogleAuth.objects.get(owner=user)
  refresh_token = g_auth.refresh_token

  data = {
    "client_id": settings.G_CLIENT_ID,
    "client_secret": settings.G_CLIENT_SECRET,
    "refresh_token": refresh_token,
    "grant_type": "refresh_token",
  }

  response = requests.post("https://oauth2.googleapis.com/token", data=data)

  if response.status_code == 200:
    token_data = response.json()
    new_access = token_data.get("access_token")
    expires_in = token_data.get("expires_in")
    expires_at = datetime.datetime.now() + datetime.timedelta(seconds=expires_in)

    g_auth.access_token = new_access
    g_auth.expires_at = expires_at
    g_auth.save()

    return new_access
  else:
    raise Exception(f"Failed to refresh token: {response.json()}")
