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

from .utils import email_service, otp_service, graph_service, google_service
from .serializers import CreatorUserSerializer, BusinessUserSerializer, UserSerializer, NotificationSerializer, OTPSerializer, VerifyOTPSerializer
from .models import (
    CreatorUser, BusinessUser, 
    User, Notification,
    InstagramPage, OAuthTransaction,
    InstagramMedia, GoogleAuth, 
    YoutubeChannel, YoutubeMedia
)

class SchemeRedirectResponse(HttpResponse):
    status_code = 302

    def __init__(self, redirect_to, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Directly inject the custom deep-link URI into the header
        self['Location'] = redirect_to

#Instagram integration through facebook login
SCOPES = settings.FB_SCOPES

# class FacebookLoginStartView(APIView):
#     permission_classes = [AllowAny]
    
#     def get(self, request):        
#         raw_token = request.GET.get("token")
#         if not raw_token:
#             return HttpResponseBadRequest("Missing token")
        
#         medium = request.GET.get("medium")
#         if not medium:
#             medium = "web"
        
#         authenticator = JWTAuthentication()
#         try:
#             validated_token = authenticator.get_validated_token(raw_token)
#             user = authenticator.get_user(validated_token)
#         except Exception as e:
#             return HttpResponseBadRequest(f"Invalid token: {e}")
        
#         state = secrets.token_urlsafe(16)
        
#         OAuthTransaction.objects.create(
#             user = user,
#             state = state,
#             medium = medium
#         )
        
#         auth_url = (
#             f"https://www.facebook.com/{settings.FB_API_VERSION}/dialog/oauth?"
#             + urlencode({
#                 "client_id": settings.FB_APP_ID,
#                 "redirect_uri": settings.FB_REDIRECT_URI,
#                 "state": state,
#                 "scope": SCOPES,
#                 "auth_type": "rerequest",
#             })
#         )
        
#         return HttpResponseRedirect(auth_url)
    
   
# @method_decorator(csrf_exempt, name="dispatch")
# class FacebookLoginCallbackView(APIView):
#     permission_classes = [AllowAny]
    
#     def get(self, request):
#         error = request.GET.get("error")
#         if error:
#             return HttpResponseBadRequest(f"Facebook error: {error}")
        
#         state = request.GET.get("state")
#         if not state:
#             return HttpResponseBadRequest(f"Invalid state")
        
#         code = request.GET.get("code")
#         if not code:
#             return HttpResponseBadRequest("No code found!")
        
#         txn = OAuthTransaction.objects.get(state=state)
#         if not txn:
#             return HttpResponseBadRequest("Invalid or already-used state")
        
#         try:
#             creator = txn.user.creatoruser
#         except AttributeError:
#             return HttpResponseBadRequest("Only creator user can connect social accounts")
        
#         try:
#             medium = txn.medium
#         except Exception as e:
#             return HttpResponseBadRequest(f"Error determining medium: {e}")
        
#         short_token_response = graph_service.get_short_token(code)
#         short_token = short_token_response["access_token"]
        
#         long_token_response = graph_service.get_long_token(short_token)
#         long_token = long_token_response["access_token"]
        
#         me = graph_service.graph_get("me", long_token, {"fields": "id,name"})
#         fb_user_id = me["id"]
        
#         existing_auth = FacebookAuth.objects.filter(fb_user_id=fb_user_id).exclude(owner=creator)
#         if existing_auth:
#             return Response({"message": "This Facebook account is already connected to another Cloutgrid user."}, status=status.HTTP_403_FORBIDDEN)
        
#         try:
#             pages_response = graph_service.graph_get("me/accounts", long_token)
#             pages = pages_response.get("data", [])
#         except Exception as e:
#             return Response({"message": "An error has occured - " + str(e)})
        
#         if not pages:
#             return Response({"message": "No pages found. Make sure you are the admin and you choose the correct pages"}, 
#                             status=status.HTTP_400_BAD_REQUEST)
            
#         for page in pages:
#             page_id = page["id"]
#             page_token = page.get("access_token", "")
#             page_info = graph_service.graph_get(page_id, long_token, {"fields": "name,instagram_business_account"})
            
#             name = page_info.get("name", "")
#             ig = page_info.get("instagram_business_account", {})
#             if not ig:
#                 continue
            
#             fb_auth, _ = FacebookAuth.objects.update_or_create(
#                 owner=creator,
#                 defaults={
#                     "fb_user_id": fb_user_id,
#                     "long_lived_token": long_token,
#                 }
#             )
            
#             fb_page, _ = FacebookPage.objects.update_or_create(
#                 page_id = page_id,
#                 defaults={
#                     "owner": fb_auth,
#                     "name": name,
#                     "page_access_token": page_token or "",
#                 },
#             )
            
#             ig_user_id = ig.get("id")
#             ig_user = graph_service.graph_get(ig_user_id, long_token, {"fields": "username,profile_picture_url"})
#             ig_username = ig_user.get("username", "")
#             InstagramPage.objects.update_or_create(
#                 fb_page = fb_page,
#                 defaults={
#                     "ig_user_id": ig_user_id,
#                     "username": ig_username,
#                     "profile_picture_url": ig_user.get("profile_picture_url", ""),
#                 },
#             )
            
#             creator.instagram_connected = True
#             creator.save(update_fields=["instagram_connected"])
            
#             if medium == "web":
#                 return HttpResponseRedirect(settings.FB_FRONTEND_REDIRECT_URI)
#             else:
#                 return SchemeRedirectResponse("cloutgrid://profile?instagram=connected")
        
#         return Response({"message": "No Instagram pages connected"}, status=status.HTTP_400_BAD_REQUEST)


# class InstagramConnectView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         try:
#             creator = request.user.creatoruser
#         except AttributeError:
#             return Response({"message": "Only creator user can connect social accounts"}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             fb_auth = FacebookAuth.objects.get(owner=creator)
#         except ObjectDoesNotExist:
#             return Response({"message": "Facebook is not connected"}, status=status.HTTP_400_BAD_REQUEST)
        
#         token = fb_auth.long_lived_token
        
#         try:
#             pages_response = graph_service.graph_get("me/accounts", token)
#             pages = pages_response.get("data", [])
#         except Exception as e:
#             return Response({"message": "An error has occured - " + str(e)})
        
#         if not pages:
#             return Response({"message": "No pages found. Make sure you are the admin and you choose the correct pages"}, 
#                             status=status.HTTP_400_BAD_REQUEST)
            
#         for page in pages:
#             page_id = page["id"]
#             page_token = page.get("access_token", "")
#             page_info = graph_service.graph_get(page_id, token, {"fields": "name,instagram_business_account"})
            
#             name = page_info.get("name", "")
#             ig = page_info.get("instagram_business_account", {})
#             if not ig:
#                 continue
            
#             fb_page, _ = FacebookPage.objects.update_or_create(
#                 page_id = page_id,
#                 defaults={
#                     "owner": fb_auth,
#                     "name": name,
#                     "page_access_token": page_token or "",
#                 },
#             )
            
#             ig_user_id = ig.get("id")
#             ig_user = graph_service.graph_get(ig_user_id, token, {"fields": "username,profile_picture_url"})
#             ig_username = ig_user.get("username", "")
#             InstagramPage.objects.update_or_create(
#                 fb_page = fb_page,
#                 defaults={
#                     "ig_user_id": ig_user_id,
#                     "username": ig_username,
#                     "profile_picture_url": ig_user.get("profile_picture_url", ""),
#                 },
#             )
            
#             creator.instagram_connected = True
#             creator.save(update_fields=["instagram_connected"])

#             return Response({"fb_page": name, "ig_page": ig_username}, status=status.HTTP_200_OK)
            
#         creator.instagram_connected = False
#         creator.save(update_fields=["instagram_connected"])
#         return Response({"message": "No Instagram pages connected"}, status=status.HTTP_400_BAD_REQUEST)
    

# class InstagramProfileFetchView(APIView):
#     permission_classes = [IsAuthenticated]
    
#     def post(self, request):
#         try:
#             creator = request.user.creatoruser
#         except AttributeError:
#             return Response({"message": "Only creator user can connect social accounts"}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             fb_auth = FacebookAuth.objects.get(owner=creator)
#         except ObjectDoesNotExist:
#             return Response({"message": "Facebook is not connected"}, status=status.HTTP_400_BAD_REQUEST)
        
#         ig = InstagramPage.objects.filter(fb_page__owner=fb_auth).first()
#         if not ig:
#             return Response({"message": "Instagram page not found/connected"}, status=status.HTTP_400_BAD_REQUEST)
        
#         token = fb_auth.long_lived_token
        
#         try:
#             profile_data = graph_service.graph_get(ig.ig_user_id, token, {
#                 "fields": "username,followers_count,follows_count,media_count,profile_picture_url"
#             })
#         except Exception as e:
#             return Response({"message": f"Error fetching Instagram profile details - {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        
#         try:
#             profile_insights = graph_service.graph_get(
#                 f"{ig.ig_user_id}/insights",
#                 token,
#                 {
#                     "metric": "reach,profile_views,accounts_engaged,total_interactions,views", 
#                     "metric_type": "total_value", 
#                     "period": "day"
#                 }
#             )
#         except Exception as e:
#             return Response(
#                 {"message": f"Error fetching initial Instagram profile insights: {str(e)}"}, 
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         # 2. Re-structure initial data into a stable, name-keyed dictionary
#         # This completely solves the index mismatch bug.
#         weekly_totals = {}
#         for item in profile_insights.get("data", []):
#             metric_name = item.get("name")
#             # Handle cases where total_value or value keys might be missing
#             total_val_obj = item.get("total_value", {})
#             metric_value = total_val_obj.get("value", 0) if isinstance(total_val_obj, dict) else 0
            
#             weekly_totals[metric_name] = {
#                 "name": metric_name,
#                 "period": item.get("period"),
#                 "title": item.get("title"),
#                 "description": item.get("description"),
#                 "id": item.get("id"),
#                 "total_value": {"value": metric_value}
#             }

#         # 3. Defensive Pagination Loop
#         # Use safe navigation .get() for paging structure
#         insight_prev_url = profile_insights.get("paging", {}).get("previous")
        
#         for i in range(6):
#             # Break early if Meta runs out of historical pages
#             if not insight_prev_url:
#                 break 
                
#             try:
#                 temp_response = graph_service.graph_get(insight_prev_url, token, params={}, full_url=True)
#                 if not temp_response:
#                     break
                    
#                 temp_insight = temp_response.get("data", [])
                
#                 # Aggregate values safely matching by metric name, not array index
#                 for item in temp_insight:
#                     metric_name = item.get("name")
#                     if metric_name in weekly_totals:
#                         total_val_obj = item.get("total_value", {})
#                         new_value = total_val_obj.get("value", 0) if isinstance(total_val_obj, dict) else 0
                        
#                         weekly_totals[metric_name]["total_value"]["value"] += new_value
                
#                 # Prepare the next URL defensively
#                 insight_prev_url = temp_response.get("paging", {}).get("previous")
                
#             except Exception as e:
#                 # Log the error internally here if you have logging, 
#                 # but allow the code to keep the data it already successfully fetched.
#                 break 
            
#         final_data = list(weekly_totals.values())
        
#         ig.username = profile_data.get("username", ig.username)
#         ig.profile_picture_url = profile_data.get("profile_picture_url", ig.profile_picture_url)
#         ig.followers = profile_data.get("followers_count", ig.followers)
#         ig.followings = profile_data.get("follows_count", ig.followings)
#         ig.media_count = profile_data.get("media_count", ig.media_count)
#         ig.insights_raw = final_data

#         ig.save(update_fields=[
#             "username",
#             "profile_picture_url",
#             "followers",
#             "followings",
#             "media_count",
#             "insights_raw"
#         ])

#         return Response({"connected": True}, status=status.HTTP_200_OK)


# class InstagramProfileReadView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request, username):
#         try:
#             if username == "undefined":
#                 creator = request.user.creatoruser
#             else:
#                 creator = User.objects.get(username=username).creatoruser
#         except AttributeError:
#             return Response({"message": "Only creator user can connect social accounts"}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             fb_auth = FacebookAuth.objects.get(owner=creator)
#         except ObjectDoesNotExist:
#             return Response({"message": "Facebook is not connected"}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             ig = InstagramPage.objects.get(fb_page__owner=fb_auth)
#         except ObjectDoesNotExist:
#             return Response({"message": "No Instagram page found"}, status=status.HTTP_400_BAD_REQUEST)

#         return Response({"profile_data": model_to_dict(ig)}, status=status.HTTP_200_OK)


# class InstagramMediaFetchView(APIView):
#     permission_classes = [IsAuthenticated]
    
#     def post(self, request):
#         try:
#             creator = request.user.creatoruser
#         except AttributeError:
#             return Response({"message": "Only creator user can connect social accounts"}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             fb_auth = FacebookAuth.objects.get(owner=creator)
#         except ObjectDoesNotExist:
#             return Response({"message": "Facebook is not connected"}, status=status.HTTP_400_BAD_REQUEST)
        
#         try:
#             ig = InstagramPage.objects.get(fb_page__owner=fb_auth)
#         except ObjectDoesNotExist:
#             return Response({"message": "No Instagram page found"}, status=status.HTTP_400_BAD_REQUEST)
        
#         token = fb_auth.long_lived_token
        
#         media = graph_service.graph_get(f"{ig.ig_user_id}/media", token)
#         media_ids = [m["id"] for m in media.get("data", [])[:5]]
        
#         for m_id in media_ids:
#             media_info = graph_service.graph_get(f"{m_id}", token, {"fields": "id,media_type,media_url,thumbnail_url,permalink,caption,like_count,comments_count"})
#             media_obj, _ = InstagramMedia.objects.update_or_create(
#                 media_id = media_info.get("id"),
#                 defaults={
#                     "owner": ig,
#                     "media_type": media_info.get("media_type"),
#                     "media_url": media_info.get("media_url"),
#                     "thumbnail_url": media_info.get("thumbnail_url", ""),
#                     "link": media_info.get("permalink"),
#                     "caption": media_info.get("caption"),
#                     "like_count": media_info.get("like_count", 0),
#                     "comments_count": media_info.get("comments_count", 0),
#                 }
#             )
#             try:
#                 media_insights = graph_service.graph_get(f"{m_id}/insights", token, {"metric": "reach,views"})
#                 media_obj.insights_raw = media_insights.get("data", [])
#             except Exception as e:
#                 media_obj.insights_raw = []

#             media_obj.save()

#         return Response({"connected": True}, status=status.HTTP_200_OK)
    

# class InstagramMediaReadView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request, username):
#         try:
#             if username == "undefined":
#                 creator = request.user.creatoruser
#             else:
#                 creator = User.objects.get(username=username).creatoruser
#         except AttributeError:
#             return Response({"message": "Only creator user can connect social accounts"}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             fb_auth = FacebookAuth.objects.get(owner=creator)
#         except ObjectDoesNotExist:
#             return Response({"message": "Facebook is not connected"}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             ig = InstagramPage.objects.get(fb_page__owner=fb_auth)
#         except ObjectDoesNotExist:
#             return Response({"message": "No Instagram page found"}, status=status.HTTP_400_BAD_REQUEST)

#         media = InstagramMedia.objects.filter(owner=ig)
#         media_data = [model_to_dict(m) for m in media]
#         media_data.reverse()

#         return Response({"media": media_data}, status=status.HTTP_200_OK)


# class FacebookDisconnectView(APIView):
#     permission_classes = [IsAuthenticated]
    
#     def post(self, request):
#         try:
#             creator = request.user.creatoruser
#         except AttributeError:
#             return Response({"message": "Only creator user can connect/disconnect social accounts"}, status=status.HTTP_400_BAD_REQUEST)
        
#         try: 
#             fb_auth = FacebookAuth.objects.get(owner=creator)
#         except ObjectDoesNotExist:
#             return Response({"message": "No facebook connection found"}, status=status.HTTP_400_BAD_REQUEST)
        
#         token = fb_auth.long_lived_token
#         proof = graph_service.appsecret_proof(token)
        
#         url = f"https://graph.facebook.com/{settings.FB_API_VERSION}/me/permissions"
#         params = {"access_token": token, "appsecret_proof": proof}
        
#         try:
#             fb_auth.delete()
#             creator.instagram_connected = False
#             creator.save(update_fields=["instagram_connected"])
#         except Exception as e:
#             return Response({"message": "Failed to delete local credentials - " + str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        
#         try:
#             response = requests.delete(url, params=params, timeout=30)
#         except Exception as e:
#             return Response({"message": f"Network error contacting Meta - {str(e)}. Disconnecting local session."}, status=status.HTTP_502_BAD_GATEWAY)

#         if response.status_code == 200:
#             return Response({"message": "App deauthorized at Meta for this user."}, status=status.HTTP_200_OK)
        
#         return Response({"message": "Meta deauthorization failed" }, status=status.HTTP_400_BAD_REQUEST)


# class FacebookConnectionCheckView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         try:
#             creator = request.user.creatoruser
#         except AttributeError:
#             return Response({"message": "Only creator user can connect social accounts"}, status=status.HTTP_400_BAD_REQUEST)
        
#         try:
#             fb_auth = FacebookAuth.objects.get(owner=creator)
#         except ObjectDoesNotExist:
#             return Response({"connected": False}, status=status.HTTP_200_OK)

#         token = fb_auth.long_lived_token

#         if not token:
#             return Response({"connected": False}, status=status.HTTP_200_OK)

#         try:
#             response = graph_service.graph_get("me", token, {"fields": "id,name"})
#         except Exception as e:
#             return Response({"connected": False}, status=status.HTTP_200_OK)

#         if response.get("id"):
#             return Response({"connected": True}, status=status.HTTP_200_OK)

#         return Response({"connected": False}, status=status.HTTP_200_OK)
    
    
# class FacebookPurgeView(APIView):
#     permission_classes = [IsAuthenticated]
    
#     def post(self, request):
#         try:
#             creator = request.user.creatoruser
#         except AttributeError:
#             return Response({"message": "Only creator users can purge Instagram data."}, status=status.HTTP_400_BAD_REQUEST)
        
#         try: 
#             fb_auth = FacebookAuth.objects.get(owner=creator)
#         except ObjectDoesNotExist:
#             return Response({"message": "No facebook connection found"}, status=status.HTTP_400_BAD_REQUEST)
        
#         token = fb_auth.long_lived_token
#         proof = graph_service.appsecret_proof(token)
        
#         url = f"https://graph.facebook.com/{settings.FB_API_VERSION}/me/permissions"
#         params = {"access_token": token, "appsecret_proof": proof}
        
#         with transaction.atomic():
#             fb_auth.delete()

#             creator.instagram_connected = False
#             creator.save(update_fields=["instagram_connected"])
        
#         try:
#             response = requests.delete(url, params=params, timeout=30)
#         except Exception as e:
#             return Response({"message": f"Network error contacting Meta - {str(e)}. Deleting and disconnecting local session."}, status=status.HTTP_502_BAD_GATEWAY)

#         return Response({"message": "Facebook/Instagram connection and data purged"}, status=status.HTTP_200_OK)
    
    
# YouTube integration
class GoogleLoginStartView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):        
        raw_token = request.GET.get("token")
        if not raw_token:
            return HttpResponseBadRequest("Missing token")
        
        medium = request.GET.get("medium")
        if not medium:
            medium = "web"
        
        authenticator = JWTAuthentication()
        try:
            validated_token = authenticator.get_validated_token(raw_token)
            user = authenticator.get_user(validated_token)
        except Exception as e:
            return HttpResponseBadRequest(f"Invalid token: {e}")
        
        state = secrets.token_urlsafe(16)
        
        OAuthTransaction.objects.create(
            user = user,
            state = state,
            medium = medium
        )
        
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            + urlencode({
                "client_id": settings.G_CLIENT_ID,
                "redirect_uri": settings.G_REDIRECT_URI,
                "state": state,
                "scope": settings.G_SCOPES,
                "access_type": "offline",
                "response_type": "code",
                "prompt": "consent",
            })
        )
        
        return HttpResponseRedirect(auth_url)
    
    
class GoogleLoginCallbackView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        error = request.GET.get("error")
        if error:
            return Response({"message": f"Google error: {error}"}, status=status.HTTP_400_BAD_REQUEST)
        
        state = request.GET.get("state")
        if not state:
            return Response({"message": "Invalid Google OAuth state"}, status=status.HTTP_400_BAD_REQUEST)

        code = request.GET.get("code")
        if not code:
            return Response({"message": "No code found!"}, status=status.HTTP_400_BAD_REQUEST)

        txn = OAuthTransaction.objects.get(state=state)
        if not txn:
            return Response({"message": "Invalid or already-used state"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            creator = txn.user.creatoruser
        except AttributeError:
            return Response({"message": "Only creator user can connect social accounts"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            medium = txn.medium
        except Exception:
            return Response({"message": "Medium not found"}, status=status.HTTP_400_BAD_REQUEST)

        if medium == "app":
            redirect_uri = "cloutgrid://profile?youtube=connected"
        else:
            redirect_uri = settings.G_FRONTEND_REDIRECT_URI

        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": settings.G_CLIENT_ID,
            "client_secret": settings.G_CLIENT_SECRET,
            "redirect_uri": settings.G_REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code != 200:
            return Response({"message": "Failed to exchange code for token."}, status=status.HTTP_400_BAD_REQUEST)
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        id_token = token_data.get("id_token")
        
        if not access_token or not refresh_token:
            return Response({"message": "Missing tokens in response."}, status=status.HTTP_400_BAD_REQUEST)
        
        google_id = None
        
        if id_token:
            try:
                info = id_token_request.verify_oauth2_token(
                    id_token,
                    google_requests.Request(),
                    settings.G_CLIENT_ID
                )
                google_id = info.get("sub")
            except Exception:
                pass
            
        if not google_id:
            user_info = requests.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10
            )

            if user_info.status_code == 200:
                user_info_json = user_info.json()
                google_id = user_info_json.get("sub")
                
        if not google_id:
            return Response({"message": "Unable to retrieve Google account ID. Ensure 'openid email profile' scopes are included."}, status=status.HTTP_400_BAD_REQUEST)
        
        existing_auth = GoogleAuth.objects.filter(google_id=google_id).exclude(owner=creator)
        if existing_auth.exists():
            return Response({"message": "This Google account is already connected to another Cloutgrid user."}, status=status.HTTP_403_FORBIDDEN)
        
        GoogleAuth.objects.update_or_create(
            owner = creator,
            defaults = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "google_id": google_id,
            }
        )

        return SchemeRedirectResponse(redirect_uri) 
    

class YoutubeChannelFetchView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        g_auth = GoogleAuth.objects.get(owner=request.user.creatoruser)
        
        try:
            credentials = Credentials(
                token = g_auth.access_token, 
                refresh_token = g_auth.refresh_token,
                client_id = settings.G_CLIENT_ID,
                client_secret = settings.G_CLIENT_SECRET,
                token_uri = "https://oauth2.googleapis.com/token"
            )
            youtube = build("youtube", "v3", credentials=credentials)
        
            response = youtube.channels().list(
                part="snippet,statistics,brandingSettings",
                mine=True
            ).execute()
            
            if credentials.token != g_auth.access_token:
                g_auth.access_token = credentials.token
                g_auth.save()
            
        except:
            return Response({"message": "Something went wrong"}, status=status.HTTP_400_BAD_REQUEST)

        if not response["items"]:
            return Response({"message": "No channel found"}, status=status.HTTP_400_BAD_REQUEST)

        channel = response["items"][0]
        snippet = channel["snippet"]
        stats = channel["statistics"]
        banner_url = channel.get("brandingSettings", {}).get("image", {}).get("bannerExternalUrl")
        
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
            }
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
            return Response({"message": "Only creator user can do this operation"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            g_auth = GoogleAuth.objects.get(owner=creator)
            channel = YoutubeChannel.objects.get(owner=g_auth)
        except GoogleAuth.DoesNotExist or YoutubeChannel.DoesNotExist:
            return Response({"message": "No channel found"}, status=status.HTTP_404_NOT_FOUND)
        
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
            return Response({"message": "Only creator user can do this operation"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            g_auth = GoogleAuth.objects.get(owner=creator)
            channel = g_auth.yt_channel
        except GoogleAuth.DoesNotExist:
            return Response({"message": "Google account not connected"}, status=status.HTTP_400_BAD_REQUEST)
        except YoutubeChannel.DoesNotExist:
            return Response({"message": "Youtube channel not found"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            credentials = Credentials(
                token = g_auth.access_token, 
                refresh_token = g_auth.refresh_token,
                client_id = settings.G_CLIENT_ID,
                client_secret = settings.G_CLIENT_SECRET,
                token_uri = "https://oauth2.googleapis.com/token"
            )
            
            if credentials.token != g_auth.access_token:
                g_auth.access_token = credentials.token
                g_auth.save()   
            
            youtube = build("youtube", "v3", credentials=credentials)
        
            response = youtube.channels().list(
                part="contentDetails",
                id=channel.channel_id
            ).execute()
            
            uploads_playlist_id = response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            
            playlist_items = youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=5
            ).execute()
            
            video_ids = [item["contentDetails"]["videoId"] for item in playlist_items["items"]]
            
            videos_response = youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(video_ids)
            ).execute()
            
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
                    }
                )
            
        except Exception as e:
            return Response({"message": "Something went wrong" + e}, status=status.HTTP_400_BAD_REQUEST)
        
        
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
            return Response({"message": "Only creator user can do this operation"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            g_auth = GoogleAuth.objects.get(owner=creator)
            channel = g_auth.yt_channel
        except GoogleAuth.DoesNotExist:
            return Response({"message": "This user has no google authentication!"}, status=status.HTTP_400_BAD_REQUEST)
        except YoutubeChannel.DoesNotExist:
            return Response({"message": "This user has no youtube channel connected!"}, status=status.HTTP_400_BAD_REQUEST)
        
        media_queries = YoutubeMedia.objects.filter(owner=channel)
        
        media_data = []
        for media in media_queries:
            media_data.append({
                "id": media.id,
                "media_id": media.media_id,
                "title": media.title,
                "description": media.description,
                "thumbnail_url": media.thumbnail_url,
                "views": media.views,
                "likes": media.likes,
                "comments": media.comments,
                "duration": media.duration,
            })
            
        return Response({"media_data": media_data}, status=status.HTTP_200_OK)
    
    
class GoogleDisconnectView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            creator = request.user.creatoruser
        except CreatorUser.DoesNotExist:
            return Response({"message": "Only creator user can do this operation"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            g_auth = GoogleAuth.objects.get(owner=creator)
        except GoogleAuth.DoesNotExist:
            return Response({"message": "No google connection found"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            response = requests.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": g_auth.refresh_token},
                headers={"content-type": "application/x-www-form-urlencoded"},
                timeout=10
            )
        except Exception as e:
            return Response({"message": "Failed to revoke token - " + str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        
        try:
            g_auth.delete()
        except Exception as e:
            return Response({"message": "Failed to delete local credentials - " + str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        
        return Response({"message": "Google account disconnected and local data deleted"}, status=status.HTTP_200_OK)
    
    
class GoogleConnectionCheckView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            creator = request.user.creatoruser
        except CreatorUser.DoesNotExist:
            return Response({"message": "Only creator user can do this operation"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            g_auth = GoogleAuth.objects.get(owner=creator)
        except GoogleAuth.DoesNotExist:
            return Response({"connected": False, "message": "No google connection found"}, status=status.HTTP_200_OK)
        
        try:
            response = requests.get(
                "https://www.googleapis.com/oauth2/v1/tokeninfo",
                params={"access_token": g_auth.access_token},
                timeout=10
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
                refresh_response = requests.post("https://oauth2.googleapis.com/token", data=refresh_data, timeout=10)

                if refresh_response.status_code == 200:
                    token_json = refresh_response.json()
                    g_auth.access_token = token_json.get("access_token")
                    g_auth.save(update_fields=["access_token"])
                    return Response({"connected": True}, status=status.HTTP_200_OK)
                else:
                    g_auth.delete()
                    return Response({"connected": False, "message": "Token revoked or expired"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"connected": False, "message": f"Error - {str(e)}"}, status=status.HTTP_502_BAD_GATEWAY)


# OTP verification and mail sending using zepto
class SendOTPView(APIView):
    def post(self, request):
        serializer = OTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        name = serializer.validated_data.get('name')
        username = serializer.validated_data.get('username')
        email = serializer.validated_data.get('email')
        
        if profanity.contains_profanity(name) or profanity.contains_profanity(username) or profanity.contains_profanity(email):
            return Response({"message": "One or more fields contain inappropriate language."}, status=status.HTTP_400_BAD_REQUEST)

        if username and User.objects.filter(username=username).exists():
            return Response({"message": "This username is already taken."}, status=status.HTTP_400_BAD_REQUEST)

        if email and User.objects.filter(email=email).exists():
            return Response({"message": "This email is already in use. Try logging in or use a different email"}, status=status.HTTP_400_BAD_REQUEST)

        otp = otp_service.generate_otp()
        otp_service.store_otp(username, otp)

        api_key = settings.ZEPTO_API_KEY
        template_key = settings.OTP_TEMPLATE_KEY
        placeholders = {
            "OTP": otp,
            "name": name
        }

        status_code, response = email_service.send_otp_email(
            api_key, email, template_key, placeholders)

        if 200 <= status_code <= 299:
            return Response({"message": "OTP sent successfully"}, status=status.HTTP_200_OK)
        
        return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyOTPView(APIView):
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"message": "Invalid input"}, status=status.HTTP_400_BAD_REQUEST)

        username = serializer.validated_data.get('username')
        otp = serializer.validated_data.get('otp')

        is_verified, message = otp_service.verify_otp(username, otp)
        if is_verified:
            return Response({"message": message}, status=status.HTTP_200_OK)
        return Response({"message": message}, status=status.HTTP_400_BAD_REQUEST)


class PasswrdResetRequestView(APIView):
    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_link = f"reset-password/{uid}/{token}"
            api_key = settings.ZEPTO_API_KEY
            template_key = settings.RESET_TEMPLATE_KEY
            placeholders = {
                "date_time": "1 hour",
                "reset_link": reset_link,
                "username": user.username
            }

            status_code, response = email_service.send_password_reset_email(
                api_key, email, template_key, placeholders)

            if 200 <= status_code <= 299:
                return Response({"message": "Password reset link sent successfully"}, status=status.HTTP_200_OK)
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except User.DoesNotExist:
            return Response({"message": "No user found with this email"}, status=status.HTTP_404_NOT_FOUND)


class PasswordResetConfirmView(APIView):
    def post(self, request, uidb64, token):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
            if default_token_generator.check_token(user, token):
                new_password = request.data.get('password')
                user.set_password(new_password)
                user.save()
                return Response({"message": "Password reset successful"}, status=status.HTTP_200_OK)
            else:
                print("Invalid token")
                return Response({"message": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
        except (User.DoesNotExist, ValueError, TypeError, UnicodeDecodeError):
            return Response({"message": "Invalid user id"}, status=status.HTTP_400_BAD_REQUEST)


class RegisterCreatorUserView(APIView):
    def post(self, request):
        serializer = CreatorUserSerializer(data=request.data)
        
        if serializer.is_valid():
            creator_user = serializer.save()
            refresh = RefreshToken.for_user(creator_user.user)

            existing_creators = CreatorUser.objects.exclude(
                user=creator_user.user)
            notifications = [
                Notification(
                    recipient=creator.user,
                    sender=creator_user.user,
                    notification_type='new_account',
                    message=f"{creator_user.user.name} has joined Cloutgrid!"
                )
                for creator in existing_creators
            ]
            Notification.objects.bulk_create(notifications)

            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(creator_user.user).data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteCreatorUserView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user

        if not hasattr(user, 'creatoruser'):
            return Response({"message": "user is not a creator user"}, status=status.HTTP_403_FORBIDDEN)

        user.delete()
        return Response({"message": "Your creator account has been deleted successfully."}, status=status.HTTP_200_OK)


class RegisterBusinessUserView(APIView):
    def post(self, request):
        serializer = BusinessUserSerializer(data=request.data)
        
        if serializer.is_valid():
            business_user = serializer.save()
            refresh = RefreshToken.for_user(business_user.user)

            existing_businesses = BusinessUser.objects.exclude(
                user=business_user.user)
            notifications = [
                Notification(
                    recipient=business.user,
                    sender=business_user.user,
                    notification_type='new_account',
                    message=f"{business_user.user.name} has joined Cloutgrid!"
                )
                for business in existing_businesses
            ]
            Notification.objects.bulk_create(notifications)

            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(business_user.user).data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteBusinessUserView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user

        if not hasattr(user, 'businessuser'):
            return Response({"message": "user is not a business user"}, status=status.HTTP_403_FORBIDDEN)

        user.delete()
        return Response({"message": "Your business account has been deleted successfully."}, status=status.HTTP_200_OK)


class CreatorUserLoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(request, email=email, password=password)
        
        if not user:
            return Response({'message': 'Invalid Credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            creator_user = user.creatoruser
        except CreatorUser.DoesNotExist:
            return Response({'message': 'This email is registered as a business user. Please login as a Business!'}, status=status.HTTP_401_UNAUTHORIZED)
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': CreatorUserSerializer(creator_user).data
        }, status=status.HTTP_200_OK)


class BusinessUserLoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(request, email=email, password=password)
        
        if not user:
            return Response({'message': 'Invalid Credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            business_user = user.businessuser
        except BusinessUser.DoesNotExist:
            return Response({'message': 'This email is registered as a creator user. Please login as a Creator!'}, status=status.HTTP_401_UNAUTHORIZED)
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': BusinessUserSerializer(business_user).data
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({'message': f'Logout failed - {e}'}, status=status.HTTP_400_BAD_REQUEST)


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if hasattr(user, 'creatoruser'):
            serializer = CreatorUserSerializer(user.creatoruser)
        elif hasattr(user, 'businessuser'):
            serializer = BusinessUserSerializer(user.businessuser)
        else:
            serializer = UserSerializer(user)
        return Response(serializer.data)


class CreatorUserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if hasattr(user, 'creatoruser'):
            serializer = CreatorUserSerializer(user.creatoruser)
            return Response(serializer.data)
        return Response({'error': 'Not a creator user'}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        user = request.user
        if hasattr(user, 'creatoruser'):
            creator_user = user.creatoruser
            data = request.data
            user_data = {
                'name': data.get('user[name]'),
                'bio': data.get('user[bio]'),
            }

            profile_photo = data.get('user[profile_photo]', None)
            if profile_photo is not None:
                user_data['profile_photo'] = profile_photo

            user_serializer = UserSerializer(
                user, data=user_data, partial=True)
            if user_serializer.is_valid():
                user_serializer.save()
            else:
                return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            creator_serializer = CreatorUserSerializer(creator_user, data={
                'area': data.get('area')
            }, partial=True)
            
            if creator_serializer.is_valid():
                creator_serializer.save()
                response_data = {
                    'user': user_serializer.data,
                    'area': creator_serializer.data.get('area')
                }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response(creator_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': 'Not a creator user'}, status=status.HTTP_400_BAD_REQUEST)


class BusinessUserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if hasattr(user, 'businessuser'):
            serializer = BusinessUserSerializer(user.businessuser)
            return Response(serializer.data)
        return Response({'error': 'Not a business user'}, status=400)

    def put(self, request):
        user = request.user
        if hasattr(user, 'businessuser'):
            business_user = user.businessuser
            data = request.data
            user_data = {
                'name': data.get('user[name]'),
                'bio': data.get('user[bio]'),
            }

            profile_photo = data.get('user[profile_photo]', None)
            if profile_photo is not None:
                user_data['profile_photo'] = profile_photo

            user_serializer = UserSerializer(
                user, data=user_data, partial=True)
            if user_serializer.is_valid():
                user_serializer.save()
            else:
                return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            business_serializer = BusinessUserSerializer(business_user, data={
                'website': data.get('website'),
                'target_audience': data.get('target_audience')
            }, partial=True)
            
            if business_serializer.is_valid():
                business_serializer.save()
                response_data = {
                    'user': user_serializer.data,
                    'website': business_serializer.data.get('website'),
                    'target_audience': business_serializer.data.get('target_audience')
                }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response(business_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({'error': 'Not a business user'}, status=status.HTTP_400_BAD_REQUEST)


class UserSearchView(APIView):
    def get(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response({"error": "No search query provided"}, status=status.HTTP_400_BAD_REQUEST)

        users = User.objects.filter(username__icontains=query) | User.objects.filter(
            email__icontains=query) | User.objects.filter(name__icontains=query)
        creators = CreatorUser.objects.filter(user__in=users)
        businesses = BusinessUser.objects.filter(user__in=users)

        creator_serializer = CreatorUserSerializer(creators, many=True)
        business_serializer = BusinessUserSerializer(businesses, many=True)

        return Response({
            "creators": creator_serializer.data,
            "businesses": business_serializer.data
        }, status=status.HTTP_200_OK)


class BusinessSearchView(APIView):
    def get(self, request):
        query = request.query_params.get("q", "")
        if not query:
            return Response({"error": "No search query found"}, status=status.HTTP_400_BAD_REQUEST)

        users = User.objects.filter(username__icontains=query) | User.objects.filter(
            email__icontains=query) | User.objects.filter(name__icontains=query)
        results = BusinessUser.objects.filter(user__in=users)
        serialized_results = BusinessUserSerializer(results, many=True)

        return Response(serialized_results.data, status=status.HTTP_200_OK)


class ProfileView(APIView):
    def get(self, request, username):
        user = get_object_or_404(User, username=username)
        is_following = request.user.following.filter(id=user.id).exists()
        is_blocking = request.user.blockings.filter(id=user.id).exists()
        is_blocker = request.user.blockers.filter(id=user.id).exists()

        try:
            creator = CreatorUser.objects.get(user=user)
            serializer = CreatorUserSerializer(creator)
        except CreatorUser.DoesNotExist:
            try:
                business = BusinessUser.objects.get(user=user)
                serializer = BusinessUserSerializer(business)
            except BusinessUser.DoesNotExist:
                return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({**serializer.data, "is_following": is_following, "is_blocking": is_blocking, "is_blocker": is_blocker}, status=status.HTTP_200_OK)


class FollowUserView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, username):
        user_to_follow = get_object_or_404(User, username=username)
        if request.user == user_to_follow:
            return Response({"message": "You cannot follow yourself."}, status=status.HTTP_400_BAD_REQUEST)

        request.user.following.add(user_to_follow)
        user_to_follow.followers.add(request.user)

        Notification.objects.create(
            recipient=user_to_follow,
            sender=request.user,
            notification_type='follow',
            message=f"{request.user.name} has followed you!"
        )

        return Response({"message": "Successfully followed user."}, status=status.HTTP_200_OK)


class UnfollowUserView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, username):
        user_to_unfollow = get_object_or_404(User, username=username)
        if request.user == user_to_unfollow:
            return Response({"detail": "You cannot unfollow yourself."}, status=status.HTTP_400_BAD_REQUEST)

        request.user.following.remove(user_to_unfollow)
        user_to_unfollow.followers.remove(request.user)

        return Response({"detail": "Successfully unfollowed user."}, status=status.HTTP_200_OK)


class BlockUserView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, username):
        user_to_block = get_object_or_404(User, username=username)

        if request.user == user_to_block:
            return Response({"message": "You cannot block yourself."}, status=status.HTTP_400_BAD_REQUEST)

        if user_to_block in request.user.blockings.all():
            return Response({"message": "You already blocked this user."}, status=status.HTTP_400_BAD_REQUEST)

        request.user.blockings.add(user_to_block)

        return Response({"message": "Successfully blocked user."}, status=status.HTTP_200_OK)


class UnblockUserView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, username):
        user_to_unblock = get_object_or_404(User, username=username)

        if request.user == user_to_unblock:
            return Response({"message": "You cannot unblock yourself"}, status=status.HTTP_400_BAD_REQUEST)

        if user_to_unblock not in request.user.blockings.all():
            return Response({"message": "You haven't blocked this user"}, status=status.HTTP_400_BAD_REQUEST)

        request.user.blockings.remove(user_to_unblock)

        return Response({"message": "Successfully unblocked user."}, status=status.HTTP_200_OK)


class IsFollowingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, username):
        user_to_check = get_object_or_404(User, username=username)
        is_following = request.user.following.filter(
            id=user_to_check.id).exists()
        return Response({"is_following": is_following}, status=status.HTTP_200_OK)


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        show_all = request.query_params.get('all', False) == 'true'
        notifications = Notification.objects.filter(recipient=request.user).order_by(
            '-created_at') if show_all else Notification.objects.filter(recipient=request.user, is_read=False).order_by('-created_at')
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MarkNotificationAsReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = Notification.objects.get(
                pk=pk, recipient=request.user)
            notification.is_read = True
            notification.save()
            return Response({"status": "Notification marked as read"}, status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response({"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)


class GetAllUsersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        creators = CreatorUser.objects.exclude(user=request.user)
        businesses = BusinessUser.objects.exclude(user=request.user)
        creator_serializer = CreatorUserSerializer(creators, many=True)
        business_serializer = BusinessUserSerializer(businesses, many=True)
        return Response({
            "creators": creator_serializer.data,
            "businesses": business_serializer.data
        }, status=status.HTTP_200_OK)
