import hashlib, hmac, requests, time
from urllib.parse import urlencode
from django.conf import settings

FB_BASE_URL = f"https://graph.facebook.com/{settings.FB_API_VERSION}"

def appsecret_proof(access_token):
  digest = hmac.new(settings.FB_APP_SECRET.encode("utf-8"),
                    msg=access_token.encode("utf-8"),
                    digestmod=hashlib.sha256).hexdigest()
  
  return digest

def graph_get(path, access_token, params={}, full_url=False):
  params["access_token"] = access_token
  params["appsecret_proof"] = appsecret_proof(access_token)
  
  if full_url:
    url = path
  else:
    url = f"{FB_BASE_URL}/{path.lstrip("/")}"
  
  response = requests.get(url, params=params, timeout=30)
  response.raise_for_status()
  return response.json()

def get_short_token(code):
  url = f"{FB_BASE_URL}/oauth/access_token"
  params = dict(
    client_id = settings.FB_APP_ID,
    redirect_uri = settings.FB_REDIRECT_URI,
    client_secret = settings.FB_APP_SECRET,
    code=code
  )
  
  response = requests.get(url, params=params, timeout=30)
  response.raise_for_status()
  return response.json()

def get_long_token(short_token):
  url = f"{FB_BASE_URL}/oauth/access_token"
  params = dict(
    grant_type = "fb_exchange_token",
    client_id = settings.FB_APP_ID,
    client_secret = settings.FB_APP_SECRET,
    fb_exchange_token = short_token
  )
  
  response = requests.get(url, params=params, timeout=30)
  response.raise_for_status()
  return response.json()
  