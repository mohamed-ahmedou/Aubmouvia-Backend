from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


def account_payload(user):
    return {
        'id': user.pk,
        'username': user.get_username(),
        'name': user.first_name,
        'email': user.email,
        'superuser': user.is_superuser,
    }


class LedgerTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = account_payload(self.user)
        return data
