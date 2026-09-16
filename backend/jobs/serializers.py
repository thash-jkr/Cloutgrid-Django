from rest_framework import serializers
from .models import Job, Application, Question, Answer, Requirement
from users.models import CreatorUser
from users.serializers import BusinessUserSerializer, CreatorUserSerializer
from better_profanity import profanity


class JobSerializer(serializers.ModelSerializer):
    posted_by = BusinessUserSerializer(read_only=True)
    questions = serializers.SerializerMethodField()
    requirements = serializers.SerializerMethodField()
    is_applied = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = "__all__"

    def get_questions(self, obj):
        questions = obj.questions.all()
        return QuestionSerializer(questions, many=True).data

    def get_requirements(self, obj):
        requirements = obj.requirements.all()
        return RequirementSerializer(requirements, many=True).data

    def get_is_applied(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            user = request.user
            creator = CreatorUser.objects.get(user=user)
            return Application.objects.filter(job=obj, creator=creator).exists()

        return False


class BrandJobSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()
    applications = serializers.SerializerMethodField()
    requirements = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = "__all__"

    def get_questions(self, obj):
        questions = obj.questions.all()
        return QuestionSerializer(questions, many=True).data

    def get_applications(self, obj):
        applications = obj.applications.all()
        return ApplicationSerializer(applications, many=True, context=self.context).data

    def get_requirements(self, obj):
        requirements = obj.requirements.all()
        return RequirementSerializer(requirements, many=True).data


class JobDetailSerializer(serializers.ModelSerializer):
    posted_by = BusinessUserSerializer(read_only=True)

    class Meta:
        model = Job
        fields = "__all__"

    def validate(self, data):
        fields = ["title", "description"]

        for field in fields:
            if field in data and profanity.contains_profanity(data[field]):
                data[field] = profanity.censor(data[field])

        return data


class ApplicationSerializer(serializers.ModelSerializer):
    creator = CreatorUserSerializer(read_only=True)
    answers = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = "__all__"

    def get_answers(self, obj):
        answers = obj.answers.all()
        return AnswerSerializer(answers, many=True).data


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = "__all__"

    def validate_content(self, value):
        return profanity.censor(value)


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = "__all__"
        extra_kwargs = {
            "application": {"read_only": True},
            "question": {"read_only": True},
        }

    def validate_content(self, value):
        return profanity.censor(value)


class RequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requirement
        fields = (
            "id",
            "content",
        )

    def validate_content(self, value):
        return profanity.censor(value)
