from django.urls import path

from .views import (
    RegisterCreatorUserView, DeleteCreatorUserView,
    RegisterBusinessUserView, DeleteBusinessUserView,
    CreatorUserLoginView, BusinessUserLoginView,
    UserDetailView, LogoutView,
    CreatorUserProfileView, BusinessUserProfileView,
    UserSearchView, ProfileView,
    FollowUserView, UnfollowUserView,
    BlockUserView, UnblockUserView,
    IsFollowingView, NotificationListView,
    MarkNotificationAsReadView, GetAllUsersView,
    SendOTPView, VerifyOTPView,
    PasswrdResetRequestView, PasswordResetConfirmView,
    BusinessSearchView, 
)

from .components.instagram import (
    InstagramLoginStartView, InstagramLoginCallbackView,
    InstagramProfileFetchView, InstagramProfileReadView,
    InstagramMediaFetchView, InstagramMediaReadView,
    InstagramDisconnectView
)

from .components.youtube import (
    GoogleLoginStartView,
    GoogleLoginCallbackView, YoutubeChannelFetchView,
    YoutubeChannelReadView, YoutubeMediaFetchView,
    YoutubeMediaReadView, GoogleDisconnectView,
    GoogleConnectionCheckView
)

urlpatterns = [
    path('', UserDetailView.as_view(), name='user-detail'),
    path('register/creator/', RegisterCreatorUserView.as_view(),name='register-creator'),
    path('delete/creator/', DeleteCreatorUserView.as_view(), name='delete-creator'),
    path('register/business/', RegisterBusinessUserView.as_view(),name='register-business'),
    path('delete/business/', DeleteBusinessUserView.as_view(), name='delete-business'),
    
    path('login/creator/', CreatorUserLoginView.as_view(), name='login-creator'),
    path('login/business/', BusinessUserLoginView.as_view(), name='login-business'),
    path('logout/', LogoutView.as_view(), name="user-logout"),
    
    path('profile/creator/', CreatorUserProfileView.as_view(),name='creator-profile'),
    path('profile/business/', BusinessUserProfileView.as_view(),name='business-profile'),
    
    path('search/', UserSearchView.as_view(), name='user-search'),
    path('search-business/', BusinessSearchView.as_view(), name='business-search'),
    
    path('profiles/<str:username>/', ProfileView.as_view(), name='profile'),
    path('profiles/<str:username>/follow/', FollowUserView.as_view(), name='follow-user'),
    path('profiles/<str:username>/unfollow/', UnfollowUserView.as_view(), name='unfollow-user'),
    path('profiles/<str:username>/block/', BlockUserView.as_view(), name='block-user'),
    path('profiles/<str:username>/unblock/', UnblockUserView.as_view(), name='unblock-user'),
    path('profiles/<str:username>/is_following/', IsFollowingView.as_view(), name='is-following'),
    
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('notifications/<int:pk>/mark_as_read/', MarkNotificationAsReadView.as_view(), name='mark-notification-as-read'),
    path('users/', GetAllUsersView.as_view(), name='get-all-creators'),
    
    path('otp/send/', SendOTPView.as_view(), name='send-otp'),
    path('otp/verify/', VerifyOTPView.as_view(), name='verify-otp'),
    
    path('password-reset/', PasswrdResetRequestView.as_view(), name='password-reset'),
    path('password-reset-confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    
    path('auth/instagram/start/', InstagramLoginStartView.as_view(), name='instagram-login-start'),
    path('auth/instagram/callback/', InstagramLoginCallbackView.as_view(), name='instagram-login-callback'),
    path('auth/instagram/disconnect/', InstagramDisconnectView.as_view(), name='instagram-login-disconnect'),
    path('auth/instagram/purge/', InstagramDisconnectView.as_view(), name='instagram-login-purge'),
    path('instagram/profile/fetch/', InstagramProfileFetchView.as_view(), name='instagram-profile-fetch'),
    path('instagram/profile/read/<str:username>/', InstagramProfileReadView.as_view(), name='instagram-profile-read'),
    path('instagram/media/fetch/', InstagramMediaFetchView.as_view(), name='instagram-media-fetch'),
    path('instagram/media/read/<str:username>/', InstagramMediaReadView.as_view(), name='instagram-media-read'),
    
    path('auth/google/start/', GoogleLoginStartView.as_view(), name='google-login-start'),
    path('auth/google/callback/', GoogleLoginCallbackView.as_view(), name='google-login-callback'),
    path('auth/google/disconnect/', GoogleDisconnectView.as_view(), name='google-login-disconnect'),
    path('auth/google/check/', GoogleConnectionCheckView.as_view(), name='google-login-check'),
    path('youtube/channel/fetch/', YoutubeChannelFetchView.as_view(), name='youtube-channel-fetch'),
    path('youtube/channel/read/<str:username>/', YoutubeChannelReadView.as_view(), name='youtube-channel-read'),
    path('youtube/media/fetch/', YoutubeMediaFetchView.as_view(), name='youtube-media-fetch'),
    path('youtube/media/read/<str:username>/', YoutubeMediaReadView.as_view(), name='youtube-media-read'),
]
