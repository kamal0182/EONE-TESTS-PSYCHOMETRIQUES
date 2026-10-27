from rest_framework import serializers

from app.models import Answer, CoreValue, Question, Version


class CoreValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoreValue
        fields = ["id", "name", "modifie_par_nom", "modifie_le"]
        read_only_fields = ["id", "modifie_par_nom", "modifie_le"]
        # Unicité contrôlée par CoreValueService.
        extra_kwargs = {"name": {"validators": []}}


class VersionSerializer(serializers.ModelSerializer):
    core_value_id = serializers.UUIDField()

    class Meta:
        model = Version
        fields = ["id", "name", "core_value_id", "modifie_par_nom", "modifie_le"]
        read_only_fields = ["id", "modifie_par_nom", "modifie_le"]
        # Unicité (core_value, name) contrôlée par VersionService.
        validators = []


class QuestionSerializer(serializers.ModelSerializer):
    version_id = serializers.UUIDField()

    class Meta:
        model = Question
        fields = [
            "id",
            "text",
            "ponderation",
            "version_id",
            "modifie_par_nom",
            "modifie_le",
        ]
        read_only_fields = ["id", "modifie_par_nom", "modifie_le"]


class AnswerSerializer(serializers.ModelSerializer):
    question_id = serializers.UUIDField()

    class Meta:
        model = Answer
        fields = [
            "id",
            "question_id",
            "text",
            "percentage",
            "modifie_par_nom",
            "modifie_le",
        ]
        read_only_fields = ["id", "modifie_par_nom", "modifie_le"]


class TestCreateSerializer(serializers.Serializer):
    prenom = serializers.CharField(max_length=150)
    nom = serializers.CharField(max_length=150)
    email = serializers.EmailField()


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)
