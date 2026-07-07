from django.contrib import admin
from .models import (
  User, CreatorUser, 
  BusinessUser, Notification,
  InstagramPage, InstagramMedia,
  GoogleAuth, YoutubeChannel,
  YoutubeMedia, OAuthTransaction,
  InstagramAuth
)

admin.site.register(User)
admin.site.register(CreatorUser)
admin.site.register(BusinessUser)
admin.site.register(Notification)
admin.site.register(InstagramPage)
admin.site.register(InstagramMedia)
admin.site.register(GoogleAuth)
admin.site.register(YoutubeChannel)
admin.site.register(YoutubeMedia)
admin.site.register(OAuthTransaction)
admin.site.register(InstagramAuth)
