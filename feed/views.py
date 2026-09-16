from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import CursorPagination
from django.shortcuts import get_object_or_404
from .models import Post, Like, Comment
from .serializers import PostSerializer, LikeSerializer, CommentSerializer
from users.models import User, BusinessUser
from better_profanity import profanity


class FeedCursorPagination(CursorPagination):
    page_size = 10
    ordering = "-created_at"


class PostListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        excluded = request.user.blockings.all() | request.user.blockers.all()
        posts = Post.objects.exclude(author__in=excluded).order_by("-created_at")

        paginator = FeedCursorPagination()
        paginated_posts = paginator.paginate_queryset(posts, request)
        serializer = PostSerializer(
            paginated_posts, many=True, context={"request": request}
        )
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        user = request.user
        data = request.data

        aspect = data["aspect"]
        collab_username = data["collaboration"]

        if not aspect or aspect == "":
            return Response(
                {"message": "Image aspect not found!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not data["caption"] or data["caption"] == "":
            return Response(
                {"message": "You must add a caption to your post!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if profanity.contains_profanity(data["caption"]):
            return Response(
                {"message": "Caption contains inappropriate language."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if hasattr(user, "creatoruser"):
            if collab_username != "null":
                try:
                    data["collaboration"] = BusinessUser.objects.get(
                        user__username=collab_username
                    )
                except BusinessUser.DoesNotExist:
                    return Response(
                        {"message": "Invalid business user for collaboration."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                data["collaboration"] = None

        elif hasattr(user, "businessuser"):
            if collab_username != "null":
                return Response(
                    {"message": "Business users cannot add a collaboration field."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            data["collaboration"] = None

        else:
            return Response(
                {"message": "Not a valid user type."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PostSerializer(data=data, context={"request": request})
        if serializer.is_valid():
            serializer.save(author=request.user, collaboration=data["collaboration"])
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(
            {"message": str(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST
        )


class PostDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        serializer = PostSerializer(post)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        post = get_object_or_404(Post, pk=pk, author=request.user)
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LikePostView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        like, created = Like.objects.get_or_create(user=request.user, post=post)
        if created:
            return Response(
                {"message": "Post liked", "liked": True, "like_count": post.like_count},
                status=status.HTTP_201_CREATED,
            )
        else:
            like.delete()
            return Response(
                {
                    "message": "Like removed",
                    "liked": False,
                    "like_count": post.like_count,
                },
                status=status.HTTP_200_OK,
            )


class CommentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        excluded = request.user.blockings.all() | request.user.blockers.all()
        post = get_object_or_404(Post, pk=pk)
        comments = (
            post.comments.all().exclude(user__in=excluded).order_by("commented_at")
        )
        serializer = CommentSerializer(
            comments, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        serializer = CommentSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save(user=request.user, post=post)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentDetailView(APIView):
    def delete(self, request, post_id, comment_id):
        post = Post.objects.get(id=post_id)
        comment = Comment.objects.get(id=comment_id, post=post)
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserFeedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, username):
        user = get_object_or_404(User, username=username)
        posts = Post.objects.filter(author=user).order_by("-created_at")
        serializer = PostSerializer(posts, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserCollaborationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if hasattr(user, "businessuser"):
            business_user = user.businessuser
            collaborations = business_user.collaborations.all()
            serializer = PostSerializer(
                collaborations, many=True, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "Not a business user!"}, status=status.HTTP_403_FORBIDDEN
            )


class ProfileCollaborationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, username):
        user = get_object_or_404(User, username=username)
        business_user = user.businessuser
        collaborations = business_user.collaborations.all()
        serializer = PostSerializer(
            collaborations, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
