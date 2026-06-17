from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import serializers

from .models import User

username_validator = UnicodeUsernameValidator()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_username(self, value):
        try:
            username_validator(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            password=validated_data["password"],
        )


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        identifier = attrs.get("identifier", "").strip()
        password = attrs.get("password", "")

        user_obj = User.objects.filter(
            Q(email__iexact=identifier) | Q(username__iexact=identifier)
        ).first()
        username = user_obj.username if user_obj else None

        user = authenticate(
            request=self.context.get("request"),
            username=username,
            password=password,
        ) if username else None

        if user is None:
            raise serializers.ValidationError(
                {"non_field_errors": ["Email or username and password are incorrect."]},
                code="authentication",
            )

        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username", "date_joined"]
