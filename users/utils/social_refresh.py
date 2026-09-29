import logging

from django.conf import settings
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta, timezone

import requests

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


def get_two_windows(days_back: int = 28):
    now = datetime.now(timezone.utc)
    current_since = now - timedelta(days=days_back)
    previous_since = now - timedelta(days=days_back * 2)
    previous_until = current_since

    return {
        "current": (int(current_since.timestamp()), int(now.timestamp())),
        "previous": (int(previous_since.timestamp()), int(previous_until.timestamp())),
    }


def compute_change(current_value: int, previous_value: int) -> float:
    if previous_value == 0:
        return 0
    return round(((current_value - previous_value) / previous_value) * 100, 1)


def extract_time_series(response: dict, metric_name: str) -> list[dict]:
    metric_obj = next(
        (item for item in response.get("data", []) if item.get("name") == metric_name),
        None,
    )
    if not metric_obj:
        return []

    raw_values = metric_obj.get("values") or []

    return [
        {
            "date": entry.get("end_time", "")[:10],
            "value": entry.get("value", 0),
        }
        for entry in raw_values
        if "value" in entry
    ]


def parse_ig_timestamp(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z")


def extract_lifetime_value(data: list[dict], metric_name: str):
    return next(
        (
            item.get("values", [{}])[0].get("value")
            for item in data
            if item.get("name") == metric_name
        ),
        None,
    )


def average(values: list) -> float | None:
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 2) if values else None


def refresh_instagram_profile(ig_auth: InstagramAuth) -> InstagramPage:
    token = ig_auth.long_token

    profile_data = ig_graph_service.graph_get(
        "me",
        token,
        {
            "fields": "username,followers_count,follows_count,media_count,profile_picture_url"
        },
    )

    windows = get_two_windows(28)

    current_since, current_until = windows["current"]
    previous_since, previous_until = windows["previous"]

    current = ig_graph_service.graph_get(
        "me/insights",
        token,
        {
            "metric": "accounts_engaged,likes,total_interactions,views",
            "metric_type": "total_value",
            "period": "day",
            "since": current_since,
            "until": current_until,
        },
    )

    previous = ig_graph_service.graph_get(
        "me/insights",
        token,
        {
            "metric": "accounts_engaged,likes,total_interactions,views",
            "metric_type": "total_value",
            "period": "day",
            "since": previous_since,
            "until": previous_until,
        },
    )

    processed_insights = []

    for metric in current.get("data", []):
        metric_name = metric.get("name")
        current_value = metric.get("total_value", {}).get("value", 0)
        previous_value = next(
            (
                item.get("total_value", {}).get("value", 0)
                for item in previous.get("data", [])
                if item.get("name") == metric_name
            ),
            0,
        )
        change_percentage = compute_change(current_value, previous_value)
        processed_insights.append(
            {
                "name": metric_name,
                "title": metric.get("title", ""),
                "description": metric.get("description", ""),
                "value": current_value,
                "change": change_percentage,
            }
        )

    raw_reach = ig_graph_service.graph_get(
        "me/insights",
        token,
        {
            "metric": "reach",
            "metric_type": "time_series",
            "period": "day",
            "since": current_since,
        },
    )

    reach = extract_time_series(raw_reach, "reach")

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
    ig.insights = processed_insights
    ig.reach = reach

    ig.save(
        update_fields=[
            "username",
            "profile_picture_url",
            "followers",
            "followings",
            "media_count",
            "insights",
            "reach",
            "last_synced_at",
        ]
    )
    return ig


def refresh_instagram_media(ig_auth: InstagramAuth) -> None:
    METRIC_DISPLAY_NAMES = {
        "views": "Avg. Views",
        "ig_reels_avg_watch_time": "Avg. Watch Time",
        "reels_skip_rate": "Skip Rate",
        "total_interactions": "Avg. Interactions",
    }

    ig = InstagramPage.objects.get(ig_auth=ig_auth)
    token = ig_auth.long_token

    media = ig_graph_service.graph_get("me/media", token, {"limit": "12"})
    media_ids = [m["id"] for m in media.get("data", [])]  # newest first

    metric_names = list(METRIC_DISPLAY_NAMES.keys())
    per_media_metrics = []

    for m_id in media_ids:
        media_info = ig_graph_service.graph_get(
            m_id,
            token,
            {
                "fields": "id,media_type,media_url,thumbnail_url,permalink,caption,like_count,comments_count,timestamp"
            },
        )

        media_obj, _ = InstagramMedia.objects.update_or_create(
            media_id=media_info.get("id"),
            defaults={
                "owner": ig,
                "media_type": media_info.get("media_type"),
                "media_url": media_info.get("media_url")
                or media_info.get("thumbnail_url", ""),
                "thumbnail_url": media_info.get("thumbnail_url", ""),
                "link": media_info.get("permalink"),
                "caption": media_info.get("caption"),
                "like_count": media_info.get("like_count", 0),
                "comments_count": media_info.get("comments_count", 0),
                "timestamp": parse_ig_timestamp(media_info.get("timestamp", "")),
            },
        )

        try:
            if media_info.get("media_type", "") == "VIDEO":
                media_metric_values = dict()

                media_insights = ig_graph_service.graph_get(
                    f"{m_id}/insights", token, {"metric": ",".join(metric_names)}
                )
                data = media_insights.get("data", [])

                for metric_name in metric_names:
                    value = extract_lifetime_value(data, metric_name)
                    media_metric_values[metric_name] = value
                    if hasattr(media_obj, metric_name):
                        setattr(media_obj, metric_name, value)

                per_media_metrics.append(
                    {
                        "media_type": media_info.get("media_type"),
                        "metrics": media_metric_values,
                    }
                )

        except requests.exceptions.HTTPError as e:
            logger.warning(f"Insights fetch failed for media {m_id}: {e}")

        media_obj.save()

    reels_only = [m for m in per_media_metrics if m["media_type"] == "VIDEO"]
    
    if not reels_only:
        ig.media_insights = []
        ig.save(update_fields=["media_insights"])
        return

    midpoint = len(reels_only) // 2
    recent_half = reels_only[:midpoint] if midpoint else reels_only
    previous_half = reels_only[midpoint:] if midpoint else []

    media_insights_summary = []
    for metric_name in metric_names:
        recent_avg = average([r["metrics"][metric_name] for r in recent_half])
        previous_avg = average([r["metrics"][metric_name] for r in previous_half])
        media_insights_summary.append(
            {
                "name": METRIC_DISPLAY_NAMES[metric_name],
                "average": recent_avg,
                "change": (
                    compute_change(recent_avg, previous_avg)
                    if previous_avg is not None
                    else None
                ),
            }
        )

    ig.media_insights = media_insights_summary
    ig.save(update_fields=["media_insights"])


def refresh_instagram_account(ig_auth: InstagramAuth) -> None:
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
