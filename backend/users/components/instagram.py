from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.forms.models import model_to_dict
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponse
import datetime, secrets
from urllib.parse import urlencode

from users.serializers import InstagramPageSerializer

from ..utils import ig_graph_service
from ..models import (
    User,
    InstagramPage,
    OAuthTransaction,
    InstagramMedia,
    InstagramAuth,
)
from ..utils.social_refresh import (
    refresh_instagram_profile,
    refresh_instagram_media,
)


class SchemeRedirectResponse(HttpResponse):
    status_code = 302

    def __init__(self, redirect_to, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["Location"] = redirect_to


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

        auth_url = "https://www.instagram.com/oauth/authorize?" + urlencode(
            {
                "client_id": settings.IG_APP_ID,
                "redirect_uri": settings.IG_REDIRECT_URI,
                "state": state,
                "scope": settings.IG_SCOPES,
                "response_type": "code",
            }
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
            creator = txn.user.creatoruser
        except AttributeError:
            return HttpResponseBadRequest(
                "Only creator user can connect social accounts"
            )

        medium = txn.medium

        short_token_response = ig_graph_service.get_short_token(code)
        short_token = short_token_response["access_token"]

        long_token_response = ig_graph_service.get_long_token(short_token)
        long_token = long_token_response["access_token"]

        me = ig_graph_service.graph_get("me", long_token, {"fields": "id"})

        existing_auth = InstagramAuth.objects.filter(ig_user_id=me["id"]).exclude(
            owner=creator
        )

        if existing_auth:
            return Response(
                {
                    "message": "This Instagram account is already connected to another Cloutgrid user."
                },
                status=status.HTTP_403_FORBIDDEN,
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
            return Response(
                {"message": "Only creator user can connect social accounts"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ig_auth = InstagramAuth.objects.get(owner=creator)
        except ObjectDoesNotExist:
            return Response(
                {"message": "Instagram is not connected"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh_instagram_profile(ig_auth)
        except Exception as e:
            return Response(
                {"message": f"Error fetching Instagram profile details - {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"connected": True}, status=status.HTTP_200_OK)


class InstagramMediaFetchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            creator = request.user.creatoruser
        except AttributeError:
            return Response(
                {"message": "Only creator user can connect social accounts"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ig_auth = InstagramAuth.objects.get(owner=creator)
        except ObjectDoesNotExist:
            return Response(
                {"message": "Instagram is not connected"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh_instagram_media(ig_auth)
        except InstagramPage.DoesNotExist:
            return Response(
                {"message": "No Instagram page found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"message": f"Error fetching Instagram media - {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
            return Response(
                {"message": "Only creator user can connect social accounts"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ig_auth = InstagramAuth.objects.get(owner=creator)
        except ObjectDoesNotExist:
            return Response(
                {"message": "Instagram is not connected"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ig = InstagramPage.objects.get(ig_auth=ig_auth)
        except ObjectDoesNotExist:
            return Response(
                {"message": "No Instagram page found. Please reload!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = InstagramPageSerializer(ig)
        return Response({"profile_data": serializer.data}, status=status.HTTP_200_OK)


class InstagramMediaReadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, username):
        try:
            if username == "undefined":
                creator = request.user.creatoruser
            else:
                creator = User.objects.get(username=username).creatoruser
        except AttributeError:
            return Response(
                {"message": "Only creator user can connect social accounts"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ig_auth = InstagramAuth.objects.get(owner=creator)
        except ObjectDoesNotExist:
            return Response(
                {"message": "Instagram is not connected"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ig = InstagramPage.objects.get(ig_auth=ig_auth)
        except ObjectDoesNotExist:
            return Response(
                {"message": "No Instagram page found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        media = InstagramMedia.objects.filter(owner=ig).order_by("-id")[:5]
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
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ig_auth = InstagramAuth.objects.get(owner=creator)
        except ObjectDoesNotExist:
            return Response(
                {"message": "Instagram is not connected"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ig_auth.delete()

        return Response(
            {"message": "Instagram disconnected successfully"},
            status=status.HTTP_200_OK,
        )
