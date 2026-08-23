import logging

from .models import InstagramAuth, GoogleAuth
from .utils.social_refresh import (
    refresh_instagram_profile,
    refresh_instagram_media,
    refresh_youtube_channel,
    refresh_youtube_media,
)

logger = logging.getLogger(__name__)


def refresh_instagram_account(ig_auth: InstagramAuth):
    try:
        refresh_instagram_profile(ig_auth)
        refresh_instagram_media(ig_auth)
    except Exception:
        logger.exception("Instagram refresh failed for ig_auth id=%s", ig_auth.pk)


def refresh_youtube_account(g_auth: GoogleAuth):
    try:
        refresh_youtube_channel(g_auth)
        refresh_youtube_media(g_auth)
    except Exception:
        logger.exception("YouTube refresh failed for g_auth id=%s", g_auth.pk)


def refresh_all_social_integrations():
    ig_auths = InstagramAuth.objects.all()
    logger.info("Starting Instagram refresh for %d accounts", ig_auths.count())
    for ig_auth in ig_auths:
        refresh_instagram_account(ig_auth)

    g_auths = GoogleAuth.objects.all()
    logger.info("Starting YouTube refresh for %d accounts", g_auths.count())
    for g_auth in g_auths:
        refresh_youtube_account(g_auth)

    logger.info("Social integration refresh complete")