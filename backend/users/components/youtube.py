from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponse
import secrets, requests
from urllib.parse import urlencode
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as id_token_request

from ..models import (
    CreatorUser,
    OAuthTransaction,
    GoogleAuth,
    YoutubeChannel,
    YoutubeMedia,
)


class SchemeRedirectResponse(HttpResponse):
    status_code = 302

    def __init__(self, redirect_to, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["Location"] = redirect_to


class GoogleLoginStartView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        raw_token = request.GET.get("token")
        if not raw_token:
            return HttpResponseBadRequest("Missing token")

        medium = request.GET.get("medium") or "web"

        authenticator = JWTAuthentication()
        try:
            validated_token = authenticator.get_validated_token(raw_token)
            user = authenticator.get_user(validated_token)
        except Exception as e:
            return HttpResponseBadRequest(f"Invalid token: {e}")

        state = secrets.token_urlsafe(16)

        OAuthTransaction.objects.create(user=user, state=state, medium=medium)

        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(
            {
                "client_id": settings.G_CLIENT_ID,
                "redirect_uri": settings.G_REDIRECT_URI,
                "state": state,
                "scope": settings.G_SCOPES,
                "access_type": "offline",
                "response_type": "code",
                "prompt": "consent",
            }
        )

        return HttpResponseRedirect(auth_url)


class GoogleLoginCallbackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        error = request.GET.get("error")
        if error:
            return Response(
                {"message": f"Google error: {error}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        state = request.GET.get("state")
        if not state:
            return Response(
                {"message": "Invalid Google OAuth state"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        code = request.GET.get("code")
        if not code:
            return Response(
                {"message": "No code found!"}, status=status.HTTP_400_BAD_REQUEST
            )

        txn = OAuthTransaction.objects.get(state=state)
        if not txn:
            return Response(
                {"message": "Invalid or already-used state"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            creator = txn.user.creatoruser
        except AttributeError:
            return Response(
                {"message": "Only creator user can connect social accounts"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            medium = txn.medium
        except Exception:
            return Response(
                {"message": "Medium not found"}, status=status.HTTP_400_BAD_REQUEST
            )

        if medium == "app":
            redirect_uri = settings.G_APP_REDIRECT_URI
        else:
            redirect_uri = settings.G_FRONTEND_REDIRECT_URI

        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": settings.G_CLIENT_ID,
            "client_secret": settings.G_CLIENT_SECRET,
            "redirect_uri": settings.G_REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        response = requests.post(token_url, data=data)
        if response.status_code != 200:
            return Response(
                {"message": "Failed to exchange code for token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token_data = response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        id_token = token_data.get("id_token")

        if not access_token or not refresh_token:
            return Response(
                {"message": "Missing tokens in response."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        google_id = None

        if id_token:
            try:
                info = id_token_request.verify_oauth2_token(
                    id_token, google_requests.Request(), settings.G_CLIENT_ID
                )
                google_id = info.get("sub")
            except Exception:
                pass

        if not google_id:
            user_info = requests.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )

            if user_info.status_code == 200:
                user_info_json = user_info.json()
                google_id = user_info_json.get("sub")

        if not google_id:
            return Response(
                {
                    "message": "Unable to retrieve Google account ID. Ensure 'openid email profile' scopes are included."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_auth = GoogleAuth.objects.filter(google_id=google_id).exclude(
            owner=creator
        )
        if existing_auth.exists():
            return Response(
                {
                    "message": "This Google account is already connected to another Cloutgrid user."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        GoogleAuth.objects.update_or_create(
            owner=creator,
            defaults={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "google_id": google_id,
            },
        )

        return SchemeRedirectResponse(redirect_uri)


class YoutubeChannelFetchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        g_auth = GoogleAuth.objects.get(owner=request.user.creatoruser)

        try:
            credentials = Credentials(
                token=g_auth.access_token,
                refresh_token=g_auth.refresh_token,
                client_id=settings.G_CLIENT_ID,
                client_secret=settings.G_CLIENT_SECRET,
                token_uri="https://oauth2.googleapis.com/token",
            )
            youtube = build("youtube", "v3", credentials=credentials)

            response = (
                youtube.channels()
                .list(part="snippet,statistics,brandingSettings", mine=True)
                .execute()
            )

            if credentials.token != g_auth.access_token:
                g_auth.access_token = credentials.token
                g_auth.save()

        except:
            return Response(
                {"message": "Something went wrong"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not response["items"]:
            return Response(
                {"message": "No channel found"}, status=status.HTTP_400_BAD_REQUEST
            )

        channel = response["items"][0]
        snippet = channel["snippet"]
        stats = channel["statistics"]
        banner_url = (
            channel.get("brandingSettings", {})
            .get("image", {})
            .get("bannerExternalUrl")
        )

        YoutubeChannel.objects.update_or_create(
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

        return Response({"connected": True}, status=status.HTTP_200_OK)


class YoutubeChannelReadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, username):
        try:
            if username == "undefined":
                creator = request.user.creatoruser
            else:
                creator = CreatorUser.objects.get(user__username=username)
        except CreatorUser.DoesNotExist:
            return Response(
                {"message": "Only creator user can do this operation"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            g_auth = GoogleAuth.objects.get(owner=creator)
            channel = YoutubeChannel.objects.get(owner=g_auth)
        except GoogleAuth.DoesNotExist or YoutubeChannel.DoesNotExist:
            return Response(
                {"message": "No channel found"}, status=status.HTTP_404_NOT_FOUND
            )

        data = {
            "id": channel.id,
            "title": channel.title,
            "channel_id": channel.channel_id,
            "description": channel.description,
            "profile_picture_url": channel.profile_picture_url,
            "banner_url": channel.banner_url,
            "subscriber_count": channel.subscriber_count,
            "view_count": channel.view_count,
            "video_count": channel.video_count,
        }

        return Response({"channel_data": data}, status=status.HTTP_200_OK)


class YoutubeMediaFetchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            creator = request.user.creatoruser
        except CreatorUser.DoesNotExist:
            return Response(
                {"message": "Only creator user can do this operation"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            g_auth = GoogleAuth.objects.get(owner=creator)
            channel = g_auth.yt_channel
        except GoogleAuth.DoesNotExist:
            return Response(
                {"message": "Google account not connected"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except YoutubeChannel.DoesNotExist:
            return Response(
                {"message": "Youtube channel not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            credentials = Credentials(
                token=g_auth.access_token,
                refresh_token=g_auth.refresh_token,
                client_id=settings.G_CLIENT_ID,
                client_secret=settings.G_CLIENT_SECRET,
                token_uri="https://oauth2.googleapis.com/token",
            )

            if credentials.token != g_auth.access_token:
                g_auth.access_token = credentials.token
                g_auth.save()

            youtube = build("youtube", "v3", credentials=credentials)

            response = (
                youtube.channels()
                .list(part="contentDetails", id=channel.channel_id)
                .execute()
            )

            uploads_playlist_id = response["items"][0]["contentDetails"][
                "relatedPlaylists"
            ]["uploads"]

            playlist_items = (
                youtube.playlistItems()
                .list(
                    part="snippet,contentDetails",
                    playlistId=uploads_playlist_id,
                    maxResults=5,
                )
                .execute()
            )

            video_ids = [
                item["contentDetails"]["videoId"] for item in playlist_items["items"]
            ]

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

        except Exception as e:
            return Response(
                {"message": "Something went wrong" + e},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"connected": True}, status=status.HTTP_200_OK)


class YoutubeMediaReadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, username):
        try:
            if username == "undefined":
                creator = request.user.creatoruser
            else:
                creator = CreatorUser.objects.get(user__username=username)
        except CreatorUser.DoesNotExist:
            return Response(
                {"message": "Only creator user can do this operation"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            g_auth = GoogleAuth.objects.get(owner=creator)
            channel = g_auth.yt_channel
        except GoogleAuth.DoesNotExist:
            return Response(
                {"message": "This user has no google authentication!"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except YoutubeChannel.DoesNotExist:
            return Response(
                {"message": "This user has no youtube channel connected!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        media_queries = YoutubeMedia.objects.filter(owner=channel)

        media_data = []
        for media in media_queries:
            media_data.append(
                {
                    "id": media.id,
                    "media_id": media.media_id,
                    "title": media.title,
                    "description": media.description,
                    "thumbnail_url": media.thumbnail_url,
                    "views": media.views,
                    "likes": media.likes,
                    "comments": media.comments,
                    "duration": media.duration,
                }
            )

        return Response({"media_data": media_data}, status=status.HTTP_200_OK)


class GoogleDisconnectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            creator = request.user.creatoruser
        except CreatorUser.DoesNotExist:
            return Response(
                {"message": "Only creator user can do this operation"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            g_auth = GoogleAuth.objects.get(owner=creator)
        except GoogleAuth.DoesNotExist:
            return Response(
                {"message": "No google connection found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            response = requests.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": g_auth.refresh_token},
                headers={"content-type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
        except Exception as e:
            return Response(
                {"message": "Failed to revoke token - " + str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            g_auth.delete()
        except Exception as e:
            return Response(
                {"message": "Failed to delete local credentials - " + str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {"message": "Google account disconnected and local data deleted"},
            status=status.HTTP_200_OK,
        )


class GoogleConnectionCheckView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            creator = request.user.creatoruser
        except CreatorUser.DoesNotExist:
            return Response(
                {"message": "Only creator user can do this operation"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            g_auth = GoogleAuth.objects.get(owner=creator)
        except GoogleAuth.DoesNotExist:
            return Response(
                {"connected": False, "message": "No google connection found"},
                status=status.HTTP_200_OK,
            )

        try:
            response = requests.get(
                "https://www.googleapis.com/oauth2/v1/tokeninfo",
                params={"access_token": g_auth.access_token},
                timeout=10,
            )

            if response.status_code == 200:
                return Response({"connected": True}, status=status.HTTP_200_OK)

            else:
                refresh_data = {
                    "client_id": settings.G_CLIENT_ID,
                    "client_secret": settings.G_CLIENT_SECRET,
                    "refresh_token": g_auth.refresh_token,
                    "grant_type": "refresh_token",
                }
                refresh_response = requests.post(
                    "https://oauth2.googleapis.com/token", data=refresh_data, timeout=10
                )

                if refresh_response.status_code == 200:
                    token_json = refresh_response.json()
                    g_auth.access_token = token_json.get("access_token")
                    g_auth.save(update_fields=["access_token"])
                    return Response({"connected": True}, status=status.HTTP_200_OK)
                else:
                    g_auth.delete()
                    return Response(
                        {"connected": False, "message": "Token revoked or expired"},
                        status=status.HTTP_200_OK,
                    )

        except Exception as e:
            return Response(
                {"connected": False, "message": f"Error - {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
