from datetime import timedelta
import jwt

from django.db import models
from django.conf import settings
from django.utils import timezone as dj_timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class UserManager(BaseUserManager):
    def create_user(self, email, username=None, password=None):
        if email is None:
            raise TypeError('Users must have an email address')

        email = self.normalize_email(email)
        user = self.model(email=email, username=username)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username=None, password=None):
        if password is None:
            raise TypeError('Superusers must have a password.')

        user = self.create_user(email=email, username=username, password=password)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=255, unique=True, null=True, blank=True)
    email = models.EmailField(db_index=True, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def token(self):
        return self._generate_jwt_token()

    def get_full_name(self):
        return self.username or self.email

    def get_short_name(self):
        return self.username or self.email

    def _generate_jwt_token(self):
        expiry = dj_timezone.now() + timedelta(days=1)
        payload = {
            'id': self.pk,
            'exp': expiry.isoformat()
        }

        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

        if isinstance(token, bytes):
            token = token.decode('utf-8')
        return token
