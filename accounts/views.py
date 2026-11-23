from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import get_object_or_404
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import History
from .serializers import LedgerTokenObtainPairSerializer, account_payload

User = get_user_model()


class IsSuperuser(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_superuser)


class LedgerTokenObtainPairView(TokenObtainPairView):
    serializer_class = LedgerTokenObtainPairSerializer


class MeView(APIView):
    def get(self, request):
        return Response(account_payload(request.user))


class AccountListView(APIView):
    permission_classes = [IsSuperuser]

    def get(self, request):
        accounts = User.objects.order_by('username')
        return Response([account_payload(account) for account in accounts])

    def post(self, request):
        username = str(request.data.get('username', '')).strip()
        name = str(request.data.get('name', '')).strip()
        email = str(request.data.get('email', '')).strip().lower()
        password = str(request.data.get('password', ''))
        superuser = bool(request.data.get('superuser'))
        if not username or not name or not email or not password:
            return Response(
                {'detail': 'Indique le username, le nom, l’e-mail et le mot de passe.'},
                status=400,
            )
        error = identity_error(username, email)
        if error:
            return Response({'detail': error}, status=400)
        candidate = User(username=username, email=email, first_name=name)
        try:
            validate_password(password, candidate)
        except ValidationError as error:
            return Response({'detail': ' '.join(error.messages)}, status=400)
        account = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=name,
        )
        apply_role(account, superuser)
        account.save(update_fields=['is_superuser', 'is_staff'])
        return Response(account_payload(account), status=201)


class AccountDetailView(APIView):
    permission_classes = [IsSuperuser]

    def patch(self, request, pk):
        account = get_object_or_404(User, pk=pk)
        if 'superuser' in request.data:
            superuser = bool(request.data.get('superuser'))
            if account.pk == request.user.pk and not superuser:
                return Response(
                    {'detail': 'Tu ne peux pas retirer ton propre rôle d’administrateur.'},
                    status=400,
                )
            if account.is_superuser and not superuser and superuser_count() <= 1:
                return Response(
                    {'detail': 'Il doit rester au moins un administrateur.'},
                    status=400,
                )
            apply_role(account, superuser)
        if 'username' in request.data:
            username = str(request.data.get('username', '')).strip()
            if not username:
                return Response({'detail': 'Indique le username.'}, status=400)
            if User.objects.filter(username=username).exclude(pk=account.pk).exists():
                return Response({'detail': 'Ce username existe déjà.'}, status=400)
            account.username = username
        if 'name' in request.data:
            name = str(request.data.get('name', '')).strip()
            if not name:
                return Response({'detail': 'Indique le nom.'}, status=400)
            account.first_name = name
        if 'email' in request.data:
            email = str(request.data.get('email', '')).strip().lower()
            error = email_error(email, account.pk)
            if error:
                return Response({'detail': error}, status=400)
            account.email = email
        password = request.data.get('password')
        if password:
            try:
                validate_password(str(password), account)
            except ValidationError as error:
                return Response({'detail': ' '.join(error.messages)}, status=400)
            account.set_password(str(password))
        account.save()
        return Response(account_payload(account))

    def delete(self, request, pk):
        account = get_object_or_404(User, pk=pk)
        if account.pk == request.user.pk:
            return Response({'detail': 'Tu ne peux pas supprimer ton propre compte.'}, status=400)
        if account.is_superuser and superuser_count() <= 1:
            return Response(
                {'detail': 'Il doit rester au moins un administrateur.'},
                status=400,
            )
        account.delete()
        return Response(status=204)


class HistoryView(APIView):
    def get(self, request):
        entries = History.objects.select_related('user')[:200]
        return Response([history_payload(entry) for entry in entries])

    def post(self, request):
        kind = request.data.get('kind')
        file_name = str(request.data.get('fileName', '')).strip()
        detail = str(request.data.get('detail', '')).strip()
        if kind not in (History.IMPORT, History.EXPORT) or not file_name:
            return Response({'detail': 'Indique un import ou un export et le nom du fichier.'}, status=400)
        try:
            lines = int(request.data.get('lines'))
        except (TypeError, ValueError):
            return Response({'detail': 'Nombre de lignes invalide.'}, status=400)
        if lines < 0:
            return Response({'detail': 'Nombre de lignes invalide.'}, status=400)
        entry = History.objects.create(
            user=request.user,
            kind=kind,
            file_name=file_name[:255],
            detail=detail[:255],
            lines=lines,
        )
        return Response(history_payload(entry), status=201)


def history_payload(entry):
    return {
        'id': entry.pk,
        'kind': entry.kind,
        'fileName': entry.file_name,
        'detail': entry.detail,
        'lines': entry.lines,
        'username': entry.user.get_username(),
        'createdAt': entry.created_at.isoformat(),
    }


def identity_error(username, email):
    if User.objects.filter(username=username).exists():
        return 'Ce username existe déjà.'
    return email_error(email)


def email_error(email, ignore_pk=None):
    try:
        validate_email(email)
    except ValidationError:
        return 'L’e-mail n’est pas valide.'
    if User.objects.filter(email__iexact=email).exclude(pk=ignore_pk).exists():
        return 'Cet e-mail est déjà utilisé.'
    return ''


def apply_role(account, superuser):
    account.is_superuser = superuser
    account.is_staff = superuser


def superuser_count():
    return User.objects.filter(is_superuser=True).count()
