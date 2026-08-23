from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        if not username:
            raise ValueError("The Username field must be set")

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=255, unique=True)
    profile_photo = models.ImageField(
        default="default_profile.png", upload_to="profile_pics"
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    bio = models.CharField(max_length=255, null=True, blank=True, default="")
    user_type = models.CharField(max_length=10, null=True, blank=True)
    followers = models.ManyToManyField(
        "self", symmetrical=False, related_name="following", blank=True
    )
    blockings = models.ManyToManyField(
        "self", symmetrical=False, related_name="blockers", blank=True
    )

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return f"{self.username} - {self.user_type}"


class CreatorUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    area = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.user.username} - {self.area}"

    @property
    def instagram_connected(self):
        return hasattr(self, "ig_auth")

    @property
    def youtube_connected(self):
        return hasattr(self, "g_auth")


class BusinessUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    website = models.CharField(max_length=255, blank=True, null=True, default="")
    target_audience = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.user.username} - {self.target_audience}"


class InstagramAuth(models.Model):
    owner = models.OneToOneField(
        CreatorUser, on_delete=models.CASCADE, related_name="ig_auth"
    )
    ig_user_id = models.CharField(max_length=255, unique=True)
    long_token = models.TextField(blank=True, null=True)


class InstagramPage(models.Model):
    ig_auth = models.OneToOneField(
        InstagramAuth, on_delete=models.CASCADE, related_name="ig_page"
    )
    ig_user_id = models.CharField(max_length=255, unique=True)
    username = models.CharField(max_length=255, blank=True)
    profile_picture_url = models.TextField(blank=True)
    followers = models.IntegerField(default=0)
    followings = models.IntegerField(default=0)
    media_count = models.IntegerField(default=0)
    insights_raw = models.JSONField(blank=True, null=True)
    last_synced_at = models.DateTimeField(auto_now=True)


class InstagramMedia(models.Model):
    owner = models.ForeignKey(
        InstagramPage, on_delete=models.CASCADE, related_name="ig_media"
    )
    media_id = models.CharField(max_length=255, unique=True)
    media_type = models.CharField(max_length=64)
    media_url = models.TextField(blank=True, null=True, default="")
    thumbnail_url = models.TextField(blank=True, null=True, default="")
    link = models.TextField()
    caption = models.TextField()
    like_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    insights_raw = models.JSONField(blank=True, null=True)


class GoogleAuth(models.Model):
    owner = models.OneToOneField(
        CreatorUser, on_delete=models.CASCADE, related_name="g_auth"
    )
    google_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    access_token = models.TextField()
    refresh_token = models.TextField()


class YoutubeChannel(models.Model):
    owner = models.OneToOneField(
        GoogleAuth, on_delete=models.CASCADE, related_name="yt_channel"
    )
    channel_id = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    profile_picture_url = models.URLField(null=True, blank=True)
    banner_url = models.URLField(null=True, blank=True)
    subscriber_count = models.BigIntegerField(default=0)
    view_count = models.BigIntegerField(default=0)
    video_count = models.IntegerField(default=0)


class YoutubeMedia(models.Model):
    owner = models.ForeignKey(
        YoutubeChannel, on_delete=models.CASCADE, related_name="yt_media"
    )
    media_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    thumbnail_url = models.URLField(null=True, blank=True)
    views = models.BigIntegerField(default=0)
    likes = models.BigIntegerField(default=0)
    comments = models.BigIntegerField(default=0)
    duration = models.CharField(max_length=20, null=True, blank=True)


class OAuthTransaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="oauth_txns")
    state = models.CharField(max_length=255, unique=True, db_index=True)
    medium = models.CharField(max_length=10, default="web")


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ("follow", "Followed You"),
        ("job_applied", "Applied for a Job"),
        ("job_posted", "Posted a Job"),
        ("new_account", "New Account Created"),
    )

    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.sender} - {self.notification_type}"

    class Meta:
        ordering = ["-created_at"]
