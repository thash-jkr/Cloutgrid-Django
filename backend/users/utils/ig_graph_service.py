import requests

from django.conf import settings

def get_short_token(code):
    resp = requests.post(
        "https://api.instagram.com/oauth/access_token",
        data={
            "client_id": settings.IG_APP_ID,
            "client_secret": settings.IG_APP_SECRET,
            "grant_type": "authorization_code",
            "redirect_uri": settings.IG_REDIRECT_URI,
            "code": code,
        },
    )
    resp.raise_for_status()
    return resp.json()

def get_long_token(short_token):
    resp = requests.get(
        "https://graph.instagram.com/access_token",
        params={
            "grant_type": "ig_exchange_token",
            "client_secret": settings.IG_APP_SECRET,
            "access_token": short_token,
        },
    )
    resp.raise_for_status()
    return resp.json()

def graph_get(node, token, params=None):
    params = params or {}
    params["access_token"] = token
    resp = requests.get(
        f"https://graph.instagram.com/{node}", 
        params=params,
        headers={"Accept-Language": "en-US"}
    )
    resp.raise_for_status()
    return resp.json()