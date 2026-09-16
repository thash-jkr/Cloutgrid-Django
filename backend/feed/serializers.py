from rest_framework import serializers
from .models import Post, Like, Comment
from django.contrib.auth import get_user_model
from users.serializers import UserSerializer, BusinessUserSerializer, CreatorUserSerializer
from better_profanity import profanity

User = get_user_model()


class PostSerializer(serializers.ModelSerializer):
    collaboration = BusinessUserSerializer(read_only=True)
    like_count = serializers.ReadOnlyField()
    comment_count = serializers.ReadOnlyField()
    is_liked = serializers.SerializerMethodField()
    posted_by = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Post
        exclude = ("author",)

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False
    
    def get_posted_by(self, obj):
        if hasattr(obj.author, "creatoruser"):
            return CreatorUserSerializer(obj.author.creatoruser, context=self.context).data
        else:
            return BusinessUserSerializer(obj.author.businessuser, context=self.context).data
        
    def get_is_owner(self, obj):
        request = self.context.get('request')
        user = request.user
        if request and user.is_authenticated:
            return obj.author.username == user.username
        return False


class LikeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    post = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all())

    class Meta:
        model = Like
        fields = ['id', 'user', 'post', 'liked_at']


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'user', 'content', 'commented_at']

    def validate_content(self, value):
        return profanity.censor(value)
