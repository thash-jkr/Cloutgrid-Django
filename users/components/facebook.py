# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from rest_framework.permissions import IsAuthenticated, AllowAny
# from rest_framework_simplejwt.tokens import RefreshToken
# from rest_framework_simplejwt.authentication import JWTAuthentication
# from django.contrib.auth import authenticate
# from django.contrib.auth.tokens import default_token_generator
# from django.forms.models import model_to_dict
# from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
# from django.utils.encoding import force_bytes
# from django.utils.decorators import method_decorator
# from django.views.decorators.csrf import csrf_exempt
# from django.shortcuts import get_object_or_404
# from django.core.exceptions import ObjectDoesNotExist
# from django.conf import settings
# from django.db import transaction
# from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponse
# from better_profanity import profanity
# import json, time, datetime, secrets, requests
# from urllib.parse import urlencode
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError
# from google.auth.exceptions import RefreshError
# from google.oauth2.credentials import Credentials
# from google.auth.transport import requests as google_requests
# from google.oauth2 import id_token as id_token_request

# from ..utils import email_service, otp_service, graph_service, google_service
# from ..serializers import CreatorUserSerializer, BusinessUserSerializer, UserSerializer, NotificationSerializer, OTPSerializer, VerifyOTPSerializer
# from ..models import (
#     CreatorUser, BusinessUser, 
#     User, Notification,
#     InstagramPage, OAuthTransaction,
#     InstagramMedia, GoogleAuth, 
#     YoutubeChannel, YoutubeMedia
# )

# class SchemeRedirectResponse(HttpResponse):
#     status_code = 302

#     def __init__(self, redirect_to, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # Directly inject the custom deep-link URI into the header
#         self['Location'] = redirect_to

# #Instagram integration through facebook login
# SCOPES = settings.FB_SCOPES


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