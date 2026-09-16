from django.contrib.auth import get_user_model
from rest_framework import serializers
from better_profanity import profanity

from .models import CreatorUser, BusinessUser, InstagramPage, Notification

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "name",
            "email",
            "username",
            "profile_photo",
            "bio",
            "type",
            "password",
            "followers_count",
            "following_count",
        )
        extra_kwargs = {"password": {"write_only": True}}

    def get_followers_count(self, obj):
        return obj.followers.count()

    def get_following_count(self, obj):
        return obj.following.count()

    def to_representation(self, instance):
        rep = super().to_representation(instance)

        if isinstance(self.parent, (CreatorUserSerializer, BusinessUserSerializer)):
            return rep

        if hasattr(instance, "creatoruser"):
            rep["category"] = instance.creatoruser.category
            rep["instagram_connected"] = instance.creatoruser.instagram_connected
            rep["youtube_connected"] = instance.creatoruser.youtube_connected
        elif hasattr(instance, "businessuser"):
            rep["category"] = instance.businessuser.category
            rep["website"] = instance.businessuser.website

        return rep

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)

        if password:
            if password.strip():
                instance.set_password(password)
            else:
                raise serializers.ValidationError(
                    {"message": "This field may not be blank."}
                )

        for key, value in validated_data.items():
            if key != "profile_photo" and profanity.contains_profanity(value):
                raise serializers.ValidationError(
                    {"message": "One or more fields contain inappropriate language."}
                )
            setattr(instance, key, value)

        instance.save()
        return instance


class CreatorUserSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    instagram_connected = serializers.SerializerMethodField()
    youtube_connected = serializers.SerializerMethodField()

    class Meta:
        model = CreatorUser
        fields = ("user", "category", "instagram_connected", "youtube_connected")

    def get_instagram_connected(self, obj):
        return obj.instagram_connected

    def get_youtube_connected(self, obj):
        return obj.youtube_connected

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        user_rep = rep.pop("user")
        return {**user_rep, **rep}

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        user_data["type"] = "creator"
        user = User.objects.create_user(**user_data)
        creator_user = CreatorUser.objects.create(user=user, **validated_data)
        return creator_user

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", None)
        if user_data:
            user_serializer = UserSerializer(
                instance=instance.user, data=user_data, partial=True
            )
            if user_serializer.is_valid():
                user_serializer.save()
            else:
                raise serializers.ValidationError(user_serializer.errors)

        instance.category = validated_data.get("category", instance.category)
        instance.save()
        return instance


class BusinessUserSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = BusinessUser
        fields = ("user", "website", "category")

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        user_rep = rep.pop("user")
        return {**user_rep, **rep}

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        user_data["type"] = "business"
        user = User.objects.create_user(**user_data)
        business_user = BusinessUser.objects.create(user=user, **validated_data)
        return business_user

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", None)
        if user_data:
            user_serializer = UserSerializer(
                instance=instance.user, data=user_data, partial=True
            )
            if user_serializer.is_valid():
                user_serializer.save()
            else:
                raise serializers.ValidationError(user_serializer.errors)

        if profanity.contains_profanity(
            validated_data.get("website", instance.website)
        ):
            raise serializers.ValidationError(
                {
                    "message": "Your given website address contain inappropriate language."
                }
            )
        instance.website = validated_data.get("website", instance.website)
        instance.category = validated_data.get("category", instance.category)
        instance.save()
        return instance


class NotificationSerializer(serializers.ModelSerializer):
    sender = serializers.StringRelatedField()
    recipient = serializers.StringRelatedField()
    photo = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = "__all__"

    def get_photo(self, obj):
        photo = obj.sender.profile_photo
        if not photo:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(photo.url) if request else photo.url


class OTPSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    username = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)


class VerifyOTPSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    otp = serializers.IntegerField(required=True)


class InstagramPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstagramPage
        fields = "__all__"
