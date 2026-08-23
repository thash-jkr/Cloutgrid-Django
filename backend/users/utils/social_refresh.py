import datetime
import logging

from django.conf import settings
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from ..models import (
    InstagramAuth,
    InstagramPage,
    InstagramMedia,
    GoogleAuth,
    YoutubeChannel,
    YoutubeMedia,
)
from . import ig_graph_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Instagram
# ---------------------------------------------------------------------------


def refresh_instagram_profile(ig_auth: InstagramAuth) -> InstagramPage:
    """
    Refetch profile + 28-day insights for one connected Instagram account.
    Raises on API failure — caller decides how to handle/report it.
    """
    token = ig_auth.long_token

    profile_data = ig_graph_service.graph_get(
        "me",
        token,
        {
            "fields": "username,followers_count,follows_count,media_count,profile_picture_url"
        },
    )

    since = int(
        (
            datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=28)
        ).timestamp()
    )
    profile_insights = ig_graph_service.graph_get(
        "me/insights",
        token,
        {
            "metric": "reach,profile_views,accounts_engaged,total_interactions,views",
            "metric_type": "total_value",
            "period": "day",
            "since": since,
        },
    )

    ig, _ = InstagramPage.objects.get_or_create(
        ig_auth=ig_auth,
        defaults={
            "ig_user_id": ig_auth.ig_user_id,
            "username": profile_data.get("username", ""),
            "profile_picture_url": profile_data.get("profile_picture_url", ""),
        },
    )

    ig.username = profile_data.get("username", ig.username)
    ig.profile_picture_url = profile_data.get(
        "profile_picture_url", ig.profile_picture_url
    )
    ig.followers = profile_data.get("followers_count", ig.followers)
    ig.followings = profile_data.get("follows_count", ig.followings)
    ig.media_count = profile_data.get("media_count", ig.media_count)
    ig.insights_raw = profile_insights.get("data", [])

    ig.save(
        update_fields=[
            "username",
            "profile_picture_url",
            "followers",
            "followings",
            "media_count",
            "insights_raw",
        ]
    )
    return ig


def refresh_instagram_media(ig_auth: InstagramAuth) -> None:
    """
    Refetch latest media + per-media insights.
    Requires an InstagramPage to already exist for this ig_auth
    (raises InstagramPage.DoesNotExist otherwise — caller decides how to handle it).
    """
    ig = InstagramPage.objects.get(ig_auth=ig_auth)
    token = ig_auth.long_token

    media = ig_graph_service.graph_get("me/media", token, {"limit": "5"})
    media_ids = [m["id"] for m in media.get("data", [])]

    for m_id in media_ids:
        media_info = ig_graph_service.graph_get(
            m_id,
            token,
            {
                "fields": "id,media_type,media_url,thumbnail_url,permalink,caption,like_count,comments_count"
            },
        )

        media_obj, _ = InstagramMedia.objects.update_or_create(
            media_id=media_info.get("id"),
            defaults={
                "owner": ig,
                "media_type": media_info.get("media_type"),
                "media_url": media_info.get("media_url") or media_info.get("thumbnail_url", ""),
                "thumbnail_url": media_info.get("thumbnail_url", ""),
                "link": media_info.get("permalink"),
                "caption": media_info.get("caption"),
                "like_count": media_info.get("like_count", 0),
                "comments_count": media_info.get("comments_count", 0),
            },
        )

        try:
            media_insights = ig_graph_service.graph_get(
                f"{m_id}/insights", token, {"metric": "reach,views"}
            )
            media_obj.insights_raw = media_insights.get("data", [])
        except Exception:
            media_obj.insights_raw = []

        media_obj.save()


def refresh_instagram_account(ig_auth: InstagramAuth) -> None:
    """
    Full refresh for one Instagram account: profile, then media.
    Catches and logs failures rather than raising — intended for batch/cron use
    where one bad account shouldn't stop the rest. For the manual-refresh view,
    call refresh_instagram_profile / refresh_instagram_media directly instead,
    so the view can turn the exception into a proper error Response.
    """
    try:
        refresh_instagram_profile(ig_auth)
        refresh_instagram_media(ig_auth)
    except Exception:
        logger.exception("Instagram refresh failed for ig_auth id=%s", ig_auth.pk)


# ---------------------------------------------------------------------------
# YouTube
# ---------------------------------------------------------------------------


def _build_youtube_client(g_auth: GoogleAuth):
    credentials = Credentials(
        token=g_auth.access_token,
        refresh_token=g_auth.refresh_token,
        client_id=settings.G_CLIENT_ID,
        client_secret=settings.G_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    youtube = build("youtube", "v3", credentials=credentials)

    if credentials.token != g_auth.access_token:
        g_auth.access_token = credentials.token
        g_auth.save(update_fields=["access_token"])

    return youtube


def refresh_youtube_channel(g_auth: GoogleAuth) -> YoutubeChannel | None:
    """
    Refetch channel snippet/stats/branding. Returns None if the Google
    account has no channel (mirrors the original view's "no items" check).
    """
    youtube = _build_youtube_client(g_auth)

    response = (
        youtube.channels()
        .list(part="snippet,statistics,brandingSettings", mine=True)
        .execute()
    )

    if not response["items"]:
        return None

    channel = response["items"][0]
    snippet = channel["snippet"]
    stats = channel["statistics"]
    banner_url = (
        channel.get("brandingSettings", {}).get("image", {}).get("bannerExternalUrl")
    )

    yt_channel, _ = YoutubeChannel.objects.update_or_create(
        owner=g_auth,
        defaults={
            "channel_id": channel["id"],
            "title": snippet["title"],
            "description": snippet.get("description", ""),
            "profile_picture_url": snippet["thumbnails"]["default"]["url"],
            "banner_url": banner_url,
            "subscriber_count": stats.get("subscriberCount", 0),
            "view_count": stats.get("viewCount", 0),
            "video_count": stats.get("videoCount", 0),
        },
    )
    return yt_channel


def refresh_youtube_media(g_auth: GoogleAuth) -> None:
    """
    Refetch latest videos + stats.
    Requires g_auth.yt_channel to already exist (raises YoutubeChannel.DoesNotExist
    otherwise — caller decides how to handle it).
    """
    channel = g_auth.yt_channel
    youtube = _build_youtube_client(g_auth)

    response = (
        youtube.channels().list(part="contentDetails", id=channel.channel_id).execute()
    )
    uploads_playlist_id = response["items"][0]["contentDetails"]["relatedPlaylists"][
        "uploads"
    ]

    playlist_items = (
        youtube.playlistItems()
        .list(
            part="snippet,contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=5,
        )
        .execute()
    )

    video_ids = [item["contentDetails"]["videoId"] for item in playlist_items["items"]]
    if not video_ids:
        return

    videos_response = (
        youtube.videos()
        .list(part="snippet,statistics,contentDetails", id=",".join(video_ids))
        .execute()
    )

    for item in videos_response.get("items", []):
        vid = item["id"]
        snippet = item["snippet"]
        stats = item.get("statistics", {})
        content = item.get("contentDetails", {})

        thumbnails = snippet.get("thumbnails", {})
        thumbnail_url = (
            thumbnails.get("maxres", {}).get("url")
            or thumbnails.get("standard", {}).get("url")
            or thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
        )

        YoutubeMedia.objects.update_or_create(
            owner=channel,
            media_id=vid,
            defaults={
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "thumbnail_url": thumbnail_url,
                "views": stats.get("viewCount", 0),
                "likes": stats.get("likeCount", 0),
                "comments": stats.get("commentCount", 0),
                "duration": content.get("duration", ""),
            },
        )


def refresh_youtube_account(g_auth: GoogleAuth) -> None:
    """
    Full refresh for one YouTube account: channel, then media.
    Catches and logs failures rather than raising — intended for batch/cron use.
    For the manual-refresh view, call refresh_youtube_channel / refresh_youtube_media
    directly instead, so the view can turn the exception into a proper error Response.
    """
    try:
        refresh_youtube_channel(g_auth)
        refresh_youtube_media(g_auth)
    except Exception:
        logger.exception("YouTube refresh failed for g_auth id=%s", g_auth.pk)
