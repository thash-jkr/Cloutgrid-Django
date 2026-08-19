from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.forms.models import model_to_dict
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponse
from better_profanity import profanity
import json, time, datetime, secrets, requests
from urllib.parse import urlencode
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as id_token_request

from ..utils import email_service, otp_service, graph_service, google_service, ig_graph_service
from ..serializers import CreatorUserSerializer, BusinessUserSerializer, UserSerializer, NotificationSerializer, OTPSerializer, VerifyOTPSerializer
from ..models import (
    CreatorUser, BusinessUser, 
    User, Notification,
    InstagramPage, OAuthTransaction,
    InstagramMedia, GoogleAuth, 
    YoutubeChannel, YoutubeMedia,
    InstagramAuth
)

class SchemeRedirectResponse(HttpResponse):
    status_code = 302

    def __init__(self, redirect_to, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self['Location'] = redirect_to

class InstagramLoginStartView(APIView):
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

        OAuthTransaction.objects.create(
            user=user,
            state=state,
            medium=medium,
        )

        auth_url = (
            "https://api.instagram.com/oauth/authorize?"
            + urlencode({
                "client_id": settings.IG_APP_ID,
                "redirect_uri": settings.IG_REDIRECT_URI,
                "state": state,
                "scope": settings.IG_SCOPES,
                "response_type": "code",
            })
        )

        return HttpResponseRedirect(auth_url)


@method_decorator(csrf_exempt, name="dispatch")
class InstagramLoginCallbackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        error = request.GET.get("error")
        if error:
            return HttpResponseBadRequest(f"Instagram error: {error}")

        state = request.GET.get("state")
        if not state:
            return HttpResponseBadRequest("Invalid state")

        code = request.GET.get("code")
        if not code:
            return HttpResponseBadRequest("No code found!")

        txn = OAuthTransaction.objects.get(state=state)
        if not txn:
            return HttpResponseBadRequest("Invalid or already-used state")

        try:
            creator = txn.user.creatoruser # type: ignore
        except AttributeError:
            return HttpResponseBadRequest("Only creator user can connect social accounts")

        medium = txn.medium

        short_token_response = ig_graph_service.get_short_token(code)
        short_token = short_token_response["access_token"]

        long_token_response = ig_graph_service.get_long_token(short_token)
        long_token = long_token_response["access_token"]

        me = ig_graph_service.graph_get(
            "me", long_token,
            {"fields": "id"}
        )

        existing_auth = InstagramAuth.objects.filter(
            ig_user_id=me["id"]
        ).exclude(owner=creator)
        
        if existing_auth:
            return Response(
                {"message": "This Instagram account is already connected to another Cloutgrid user."},
                status=status.HTTP_403_FORBIDDEN
            )

        InstagramAuth.objects.update_or_create(
            owner=creator,
            defaults={
                "ig_user_id": me["id"],
                "long_token": long_token,
            },
        )

        if medium == "web":
            return HttpResponseRedirect(settings.IG_FRONTEND_REDIRECT_URI)
        else:
            return SchemeRedirectResponse(settings.IG_APP_REDIRECT_URI)
        
        
class InstagramProfileFetchView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            creator = request.user.creatoruser
        except AttributeError:
            return Response({"message": "Only creator user can connect social accounts"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ig_auth = InstagramAuth.objects.get(owner=creator)
        except ObjectDoesNotExist:
            return Response({"message": "Instagram is not connected"}, status=status.HTTP_400_BAD_REQUEST)
        
        token = ig_auth.long_token
        
        try:
            profile_data = ig_graph_service.graph_get(
                "me", 
                token, 
                {
                    "fields": "username,followers_count,follows_count,media_count,profile_picture_url"
                }
            )
        except Exception as e:
            return Response({"message": f"Error fetching Instagram profile details - {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        
        since = int((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=28)).timestamp())
        
        try:
            profile_insights = ig_graph_service.graph_get(
                f"me/insights",
                token,
                {
                    "metric": "reach,profile_views,accounts_engaged,total_interactions,views", 
                    "metric_type": "total_value", 
                    "period": "day",
                    "since": since
                }
            )
        except Exception as e:
            return Response(
                {"message": f"Error fetching initial Instagram profile insights: {str(e)}"}, 
                status=status.HTTP_400_BAD_REQUEST
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
        ig.profile_picture_url = profile_data.get("profile_picture_url", ig.profile_picture_url)
        ig.followers = profile_data.get("followers_count", ig.followers)
        ig.followings = profile_data.get("follows_count", ig.followings)
        ig.media_count = profile_data.get("media_count", ig.media_count)
        ig.insights_raw = profile_insights.get("data", [])

        ig.save(update_fields=[
            "username",
            "profile_picture_url",
            "followers",
            "followings",
            "media_count",
            "insights_raw"
        ])

        return Response({"connected": True}, status=status.HTTP_200_OK)
    
    
class InstagramProfileReadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, username):
        try:
            if username == "undefined":
                creator = request.user.creatoruser
            else:
                creator = User.objects.get(username=username).creatoruser
        except AttributeError:
            return Response({"message": "Only creator user can connect social accounts"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ig_auth = InstagramAuth.objects.get(owner=creator)
        except ObjectDoesNotExist:
            return Response({"message": "Instagram is not connected"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ig = InstagramPage.objects.get(ig_auth=ig_auth)
        except ObjectDoesNotExist:
            return Response({"message": "No Instagram page found. Please reload!"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"profile_data": model_to_dict(ig)}, status=status.HTTP_200_OK)
    
    
class InstagramMediaFetchView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            creator = request.user.creatoruser
        except AttributeError:
            return Response({"message": "Only creator user can connect social accounts"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ig_auth = InstagramAuth.objects.get(owner=creator)
        except ObjectDoesNotExist:
            return Response({"message": "Instagram is not connected"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            ig = InstagramPage.objects.get(ig_auth=ig_auth)
        except ObjectDoesNotExist:
            return Response({"message": "No Instagram page found"}, status=status.HTTP_400_BAD_REQUEST)
        
        token = ig_auth.long_token
        
        media = ig_graph_service.graph_get(
            f"me/media", 
            token,
            {
                "limit": "5",
            }
        )
        media_ids = [m["id"] for m in media.get("data", [])]
        
        for m_id in media_ids:
            media_info = ig_graph_service.graph_get(
                f"{m_id}", 
                token, 
                {
                    "fields": "id,media_type,media_url,thumbnail_url,permalink,caption,like_count,comments_count"
                }
            )
            
            media_obj, _ = InstagramMedia.objects.update_or_create(
                media_id = media_info.get("id"),
                defaults={
                    "owner": ig,
                    "media_type": media_info.get("media_type"),
                    "media_url": media_info.get("media_url"),
                    "thumbnail_url": media_info.get("thumbnail_url", ""),
                    "link": media_info.get("permalink"),
                    "caption": media_info.get("caption"),
                    "like_count": media_info.get("like_count", 0),
                    "comments_count": media_info.get("comments_count", 0),
                }
            )
            
            try:
                media_insights = ig_graph_service.graph_get(
                    f"{m_id}/insights", 
                    token, 
                    {"metric": "reach,views"}
                )
                media_obj.insights_raw = media_insights.get("data", [])
            except Exception as _:
                media_obj.insights_raw = []

            media_obj.save()

        return Response({"connected": True}, status=status.HTTP_200_OK)
    
    
class InstagramMediaReadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, username):
        try:
            if username == "undefined":
                creator = request.user.creatoruser
            else:
                creator = User.objects.get(username=username).creatoruser
        except AttributeError:
            return Response({"message": "Only creator user can connect social accounts"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ig_auth = InstagramAuth.objects.get(owner=creator)
        except ObjectDoesNotExist:
            return Response({"message": "Instagram is not connected"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ig = InstagramPage.objects.get(ig_auth=ig_auth)
        except ObjectDoesNotExist:
            return Response({"message": "No Instagram page found"}, status=status.HTTP_400_BAD_REQUEST)

        media = InstagramMedia.objects.filter(owner=ig)
        media_data = [model_to_dict(m) for m in media]
        media_data.reverse()

        return Response({"media": media_data}, status=status.HTTP_200_OK)
    
    
class InstagramDisconnectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            creator = request.user.creatoruser
        except AttributeError:
            return Response(
                {"message": "Only creator user can disconnect social accounts"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            ig_auth = InstagramAuth.objects.get(owner=creator)
        except ObjectDoesNotExist:
            return Response(
                {"message": "Instagram is not connected"},
                status=status.HTTP_400_BAD_REQUEST
            )

        ig_auth.delete()

        return Response({"message": "Instagram disconnected successfully"}, status=status.HTTP_200_OK)