import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Job, Application, Question
from .serializers import (
    BrandJobSerializer,
    JobSerializer,
    JobDetailSerializer,
    QuestionSerializer,
    AnswerSerializer,
    RequirementSerializer,
)
from users.models import CreatorUser, Notification
from django.db import transaction


class JobListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if hasattr(user, "creatoruser"):
            excluded = user.blockings.all() | user.blockers.all()
            jobs = Job.objects.exclude(posted_by__user__in=excluded).order_by(
                "-created_at"
            )
            serializer = JobSerializer(jobs, many=True, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif hasattr(user, "businessuser"):
            jobs = Job.objects.filter(posted_by=user.businessuser).order_by(
                "-created_at"
            )
            serializer = BrandJobSerializer(jobs, many=True, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"message": "User type not recognized"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def post(self, request):
        user = request.user
        data = request.data.copy()

        if not hasattr(user, "businessuser"):
            return Response(
                {"message": "Only brands can post jobs"},
                status=status.HTTP_403_FORBIDDEN,
            )

        questions = data.pop("questions", [])
        questions = json.loads(questions[0])

        question_serializers = []
        for q in questions:
            q_serializer = QuestionSerializer(data={"content": q}, partial=True)
            if not q_serializer.is_valid():
                return Response(
                    {
                        "message": q_serializer.errors.get(
                            "content", ["Invalid question found"]
                        )[0]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            question_serializers.append(q_serializer)
            
        requirements = data.pop("requirements", [])
        requirements = json.loads(requirements[0])
        
        requirement_serializers = []
        for r in requirements:
            r_serializer = RequirementSerializer(data={"content": r}, partial=True)
            if not r_serializer.is_valid():
                return Response(
                    {
                        "message": r_serializer.errors.get(
                            "content", ["Invalid requirement found"]
                        )[0]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            requirement_serializers.append(r_serializer)

        serializer = JobDetailSerializer(data=data)
        if not serializer.is_valid():
            return Response(
                {
                    "message": serializer.errors.get(
                        "non_field_errors", ["Invalid field found"]
                    )[0]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            job = serializer.save(posted_by=user.businessuser)

            for q_serializer in question_serializers:
                q_serializer.save(job=job)

            for r_serializer in requirement_serializers:
                r_serializer.save(job=job)

            creators = CreatorUser.objects.all()
            for creator in creators:
                Notification.objects.create(
                    recipient=creator.user,
                    sender=request.user,
                    notification_type="job_posted",
                    message=f"A new job '{job.title}' has been posted by {request.user.name}.",
                )
                
        brand_serializer = BrandJobSerializer(job, context={"request": request})
        return Response(brand_serializer.data, status=status.HTTP_201_CREATED)


class JobDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        job = get_object_or_404(Job, pk=pk)
        serializer = JobDetailSerializer(job)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        job = get_object_or_404(Job, pk=pk)
        if job.posted_by.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = JobSerializer(job, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        job = get_object_or_404(Job, pk=pk)
        if job.posted_by.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)

        job.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApplyJobView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(Job, id=pk)
        creator_user = get_object_or_404(CreatorUser, user=request.user)
        answers = request.data.get("answers", {})

        if Application.objects.filter(job=job, creator=creator_user).exists():
            return Response(
                {"message": "You have already applied for this job."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if job.questions.exists() and not answers:
            return Response(
                {"message": "This job requires answers to the questions."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        answer_serializers = []
        for q_id, text in answers.items():
            try:
                question = Question.objects.get(id=int(q_id))
            except Question.DoesNotExist:
                return Response(
                    {"message": "Question does not exist in the database!"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = AnswerSerializer(data={"content": text})

            if not serializer.is_valid():
                return Response(
                    {
                        "message": serializer.errors.get(
                            "content", ["Invalid answer found"]
                        )[0]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            answer_serializers.append((serializer, question))

        with transaction.atomic():
            application = Application.objects.create(
                creator=creator_user,
                job=job,
            )

            for serializer, question in answer_serializers:
                serializer.save(application=application, question=question)

            Notification.objects.create(
                recipient=job.posted_by.user,
                sender=request.user,
                notification_type="job_applied",
                message=f"{request.user.username} has applied for your job '{job.title}'.",
            )

        return Response(
            {"message": "You have successfully applied for the job."},
            status=status.HTTP_200_OK,
        )
        
        

