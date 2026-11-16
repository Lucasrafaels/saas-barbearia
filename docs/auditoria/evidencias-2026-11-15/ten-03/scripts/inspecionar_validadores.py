"""Mostra, sem tocar em banco nenhum, os validadores que o DRF gera para o campo `email` de cada serializer."""
import django
django.setup()
from django.conf import settings
from django.contrib.auth import get_user_model
from accounts import serializers as s
from rest_framework.validators import UniqueValidator

User = get_user_model()
print('AUTH_USER_MODEL =', settings.AUTH_USER_MODEL)
print('USERNAME_FIELD  =', User.USERNAME_FIELD)
print('REQUIRED_FIELDS =', User.REQUIRED_FIELDS)
f = User._meta.get_field('email')
print('Model email: unique=%s, max_length=%s, db_index=%s, error_messages[unique]=%r' % (f.unique, f.max_length, f.db_index, str(f.error_messages['unique'])))
print('Meta.constraints =', User._meta.constraints, '| unique_together =', User._meta.unique_together)
print('AUTHENTICATION_BACKENDS =', getattr(settings, 'AUTHENTICATION_BACKENDS', None))
print('REST_FRAMEWORK auth =', settings.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'])
print('SIMPLE_JWT USER_ID_FIELD/CLAIM =', s.api_settings.USER_ID_FIELD, s.api_settings.USER_ID_CLAIM)
print()
for cls in (s.PublicRegistrationSerializer, s.UserCreateSerializer, s.UserSerializer, s.CustomTokenObtainPairSerializer, s.PasswordResetRequestSerializer):
    ser = cls()
    fld = ser.fields.get('email') or ser.fields.get(User.USERNAME_FIELD)
    print('==', cls.__name__)
    if fld is None:
        print('   (sem campo email)'); continue
    print('   tipo:', type(fld).__name__, '| read_only:', fld.read_only, '| trim_whitespace:', getattr(fld, 'trim_whitespace', None))
    for v in fld.validators:
        if isinstance(v, UniqueValidator):
            print('   UniqueValidator: queryset=%s._default_manager (filtro: %r), lookup=%r, message=%r' % (v.queryset.model.__name__, str(v.queryset.all().query.where) or 'nenhum', v.lookup, str(v.message)))
        else:
            print('  ', type(v).__name__)
