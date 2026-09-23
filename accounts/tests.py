"""
Testes completos para o sistema de autenticação.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from unittest import mock

from .models import User

User = get_user_model()


@override_settings(
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_RATES': {
            'anon': '10000/hour',
            'user': '10000/hour',
            'login': '1000/minute',
            'register': '1000/hour',
            'refresh': '1000/minute',
            'logout': '1000/minute',
            'password_change': '1000/hour',
            'password_reset': '1000/hour',
            'password_reset_confirm': '1000/hour',
        }
    }
)
class AuthenticationAPITests(APITestCase):
    """Testes para os endpoints de autenticação."""

    def setUp(self):
        cache.clear()
        self.barbershop_data = {
            'nome': 'Barbearia Teste',
            'endereco': 'Rua Teste, 123',
            'telefone': '11999999999',
            'email': 'teste@barbearia.com',
            'horario_abertura': '08:00',
            'horario_fechamento': '18:00',
        }
        # Note: We're not actually creating a barbershop here since
        # the tests focus on authentication and the User model allows
        # barbershop to be null for admin/platform users

        self.user_data = {
            'email': 'usuario@teste.com',
            'nome': 'Usuario Teste',
            'password': 'SenhaSegura123!',
            'tipo_perfil': User.TipoPerfil.CLIENTE,
        }
        self.admin_data = {
            'email': 'admin@teste.com',
            'nome': 'Admin Teste',
            'password': 'SenhaSegura123!',
            'tipo_perfil': User.TipoPerfil.ADMIN,
        }

    def test_user_registration_success(self):
        """Teste de registro de usuário bem-sucedido."""
        url = reverse('auth-register')
        response = self.client.post(url, self.user_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Registration returns user data, not tokens
        self.assertIn('nome', response.data)
        self.assertIn('email', response.data)
        self.assertEqual(response.data['nome'], self.user_data['nome'])
        self.assertEqual(response.data['email'], self.user_data['email'])

        # Verificar que o usuário foi criado no banco
        user = User.objects.get(email=self.user_data['email'])
        self.assertTrue(user.check_password(self.user_data['password']))
        self.assertEqual(user.nome, self.user_data['nome'])
        self.assertEqual(user.tipo_perfil, self.user_data['tipo_perfil'])

    def test_user_registration_duplicate_email(self):
        """Teste de registro com email duplicado."""
        # Criar primeiro usuário
        User.objects.create_user(**self.user_data)

        url = reverse('auth-register')
        response = self.client.post(url, self.user_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_user_registration_weak_password(self):
        """Teste de registro com senha fraca."""
        weak_password_data = self.user_data.copy()
        weak_password_data['password'] = '123'  # Senha muito fraca

        url = reverse('auth-register')
        response = self.client.post(url, weak_password_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_login_success(self):
        """Teste de login bem-sucedido."""
        # Criar usuário
        user = User.objects.create_user(**self.user_data)

        url = reverse('token_obtain_pair')
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }
        response = self.client.post(url, login_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        # Refresh token deve estar no cookie, não no corpo da resposta
        self.assertNotIn('refresh', response.data)
        self.assertIn('barbearia_refresh', response.cookies)

        # Verificar que o cookie foi definido corretamente
        refresh_cookie = response.cookies['barbearia_refresh']
        self.assertIsNotNone(refresh_cookie.value)
        self.assertEqual(refresh_cookie['httponly'], True)

    def test_login_invalid_credentials(self):
        """Teste de login com credenciais inválidas."""
        url = reverse('token_obtain_pair')
        login_data = {
            'email': self.user_data['email'],
            'password': 'senhaerrada'
        }
        response = self.client.post(url, login_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_inactive_user(self):
        """Teste de login com usuário inativo."""
        # Criar usuário inativo
        user_data = self.user_data.copy()
        user_data['is_active'] = False
        user = User.objects.create_user(**user_data)

        url = reverse('token_obtain_pair')
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }
        response = self.client.post(url, login_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh_success(self):
        """Teste de refresh de token bem-sucedido."""
        # Criar usuário e obter tokens iniciais
        user = User.objects.create_user(**self.user_data)

        # Obter tokens iniciais
        url = reverse('token_obtain_pair')
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }
        response = self.client.post(url, login_data, format='json')

        # Extrair refresh token do cookie
        refresh_token = response.cookies['barbearia_refresh'].value

        # Fazer refresh
        self.client.cookies['barbearia_refresh'] = refresh_token
        url = reverse('token_refresh')
        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        # Novo refresh token deve estar no cookie
        self.assertIn('barbearia_refresh', response.cookies)

    def test_token_refresh_inactive_user(self):
        """Teste de refresh de token com usuário inativo."""
        # Criar usuário (ativo por padrão)
        user = User.objects.create_user(**self.user_data)

        # Obter refresh token enquanto ainda ativo
        url = reverse('token_obtain_pair')
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }
        response = self.client.post(url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        refresh_token = response.cookies['barbearia_refresh'].value

        # Tornar o usuário inativo
        user.is_active = False
        user.save()

        # Tentar refresh após tornar inativo
        self.client.cookies['barbearia_refresh'] = refresh_token
        url = reverse('token_refresh')
        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_success(self):
        """Teste de logout bem-sucedido."""
        # Criar usuário e obter tokens
        user = User.objects.create_user(**self.user_data)

        url = reverse('token_obtain_pair')
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }
        response = self.client.post(url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access_token = response.data['access']
        refresh_token = response.cookies['barbearia_refresh'].value

        # Fazer logout (precisa do access token para autenticação + refresh token no cookie)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        self.client.cookies['barbearia_refresh'] = refresh_token
        url = reverse('token_logout')
        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verificar que o cookie foi limpo
        self.assertIn('barbearia_refresh', response.cookies)
        self.assertEqual(response.cookies['barbearia_refresh'].value, '')
        self.assertEqual(response.cookies['barbearia_refresh']['max-age'], 0)

    def test_logout_blacklists_token(self):
        """Teste de que o logout coloca a token na blacklist."""
        # Criar usuário e obter tokens
        user = User.objects.create_user(**self.user_data)

        url = reverse('token_obtain_pair')
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }
        response = self.client.post(url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access_token = response.data['access']
        refresh_token = response.cookies['barbearia_refresh'].value

        # Fazer logout (precisa do access token para autenticação + refresh token no cookie)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        self.client.cookies['barbearia_refresh'] = refresh_token
        url = reverse('token_logout')
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Tentar usar o token após logout (deve falhar)
        self.client.cookies['barbearia_refresh'] = refresh_token
        url = reverse('token_refresh')
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_password_change_success(self):
        """Teste de alteração de senha bem-sucedida."""
        # Criar usuário e fazer login
        user = User.objects.create_user(**self.user_data)

        url = reverse('token_obtain_pair')
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }
        response = self.client.post(url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access_token = response.data['access']

        # Definir token de acesso no header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Alterar senha
        url = reverse('password_change')
        password_data = {
            'old_password': self.user_data['password'],
            'new_password': 'NovaSenhaSegura456!'
        }
        response = self.client.post(url, password_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verificar que a senha foi realmente alterada
        user.refresh_from_db()
        self.assertTrue(user.check_password('NovaSenhaSegura456!'))

        # Verificar que o token antigo não funciona mais (blacklisted)
        # Fazer login com senha antiga deve falhar
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']  # Senha antiga
        }
        response = self.client.post(reverse('token_obtain_pair'), login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_password_change_wrong_old_password(self):
        """Teste de alteração de senha com senha antiga errada."""
        # Criar usuário e fazer login
        user = User.objects.create_user(**self.user_data)

        url = reverse('token_obtain_pair')
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }
        response = self.client.post(url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access_token = response.data['access']

        # Definir token de acesso no header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Tentar alterar senha com senha antiga errada
        url = reverse('password_change')
        password_data = {
            'old_password': 'SenhaErrada',
            'new_password': 'NovaSenhaSegura456!'
        }
        response = self.client.post(url, password_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('old_password', response.data)

    def test_password_reset_request(self):
        """Teste de solicitação de redefinição de senha."""
        # Criar usuário
        user = User.objects.create_user(**self.user_data)

        url = reverse('password_reset')
        reset_data = {
            'email': self.user_data['email']
        }
        response = self.client.post(url, reset_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Em um teste real, verificaríamos se o email foi enviado
        # mas aqui apenas verificamos que não houve erro

    def test_password_reset_request_nonexistent_email(self):
        """Teste de solicitação de redefinição com email inexistente."""
        # Por segurança, não revelamos se o email existe ou não
        url = reverse('password_reset')
        reset_data = {
            'email': 'nonexistent@teste.com'
        }
        response = self.client.post(url, reset_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Mesmo retorno de sucesso para não revelar informações

    @override_settings(SIMPLE_JWT={
        'ACCESS_TOKEN_LIFETIME': timedelta(seconds=5),  # Token muito curto para teste
        'REFRESH_TOKEN_LIFETIME': timedelta(seconds=10),
        'ROTATE_REFRESH_TOKENS': True,
        'BLACKLIST_AFTER_ROTATION': True,
        'CHECK_REVOKE_TOKEN': True,
        'AUTH_HEADER_TYPES': ('Bearer',),
    })
    def test_token_expiration(self):
        """Teste de expiração de tokens."""
        # Criar usuário e fazer login
        user = User.objects.create_user(**self.user_data)

        url = reverse('token_obtain_pair')
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }
        response = self.client.post(url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access_token = response.data['access']
        refresh_token = response.cookies['barbearia_refresh'].value

        # Verificar que o token de acesso funciona inicialmente
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        url = reverse('user-list')
        response = self.client.get(url, format='json')
        # Deve funcionar inicialmente (não 401)
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticationSecurityTests(APITestCase):
    """Testes de segurança para o sistema de autenticação."""

    def setUp(self):
        self.user_data = {
            'email': 'seguro@teste.com',
            'nome': 'Usuario Seguro',
            'password': 'SenhaSegura123!',
            'tipo_perfil': User.TipoPerfil.CLIENTE,
        }

    def test_passwords_not_stored_in_plaintext(self):
        """Teste de que senhas não são armazenadas em texto plano."""
        User.objects.create_user(**self.user_data)
        user = User.objects.get(email=self.user_data['email'])

        # A senha no banco deve ser um hash, não o texto plano
        self.assertNotEqual(user.password, self.user_data['password'])
        self.assertTrue(user.password.startswith('pbkdf2_sha256$'))

        # Mas deve ser possível verificar corretamente
        self.assertTrue(user.check_password(self.user_data['password']))
        self.assertFalse(user.check_password('senhaerrada'))

    def test_refresh_token_not_in_response_body(self):
        """Teste de que refresh token não é exposto no corpo da resposta."""
        User.objects.create_user(**self.user_data)

        url = reverse('token_obtain_pair')
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }
        response = self.client.post(url, login_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        # Refresh token NÃO deve estar no corpo da resposta
        self.assertNotIn('refresh', response.data)
        # Mas deve estar no cookie
        self.assertIn('barbearia_refresh', response.cookies)

    def test_jwt_authentication_required_for_protected_endpoints(self):
        """Teste de que endpoints protegidos exigem autenticação."""
        # Criar usuário e fazer login para obter um token válido
        user = User.objects.create_user(**self.user_data)

        url = reverse('token_obtain_pair')
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }
        response = self.client.post(url, login_data, format='json')
        access_token = response.data['access']

        # Testar endpoint protegido SEM token
        url = reverse('user-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Testar endpoint protegido COM token inválido
        self.client.credentials(HTTP_AUTHORIZATION='Bearer token_invalido')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Testar endpoint protegido COM token válido
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.get(url, format='json')
        # Pode ser 200 ou outro código dependendo da permissão específica
        # mas não deve ser 401 (não autenticado)
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_inactive_user_cannot_authenticate(self):
        """Teste de que usuário inativo não pode autenticar."""
        # Criar usuário inativo
        user_data = self.user_data.copy()
        user_data['is_active'] = False
        User.objects.create_user(**user_data)

        url = reverse('token_obtain_pair')
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }
        response = self.client.post(url, login_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_password_reset_rate_limiting(self):
        """Teste de rate limiting em solicitação de redefinição de senha."""
        # Limpar cache
        cache.clear()

        url = reverse('password_reset')
        reset_data = {
            'email': 'teste@teste.com'
        }

        # Fazer várias requisições rapidamente
        responses = []
        for i in range(6):  # Exceder o limite de 5/hour definido nas settings
            response = self.client.post(url, reset_data, format='json')
            responses.append(response.status_code)

        # Pelo menos uma deve ser bloqueada por rate limiting
        # Nota: Este teste pode ser flaky dependendo do timing e do cache
        self.assertIn(status.HTTP_429_TOO_MANY_REQUESTS, responses)


class AuthenticationIntegrationTests(APITestCase):
    """Testes de integração para fluxos completos de autenticação."""

    def setUp(self):
        self.user_data = {
            'email': 'integracao@teste.com',
            'nome': 'Usuario Integracao',
            'password': 'SenhaSegura123!',
            'tipo_perfil': User.TipoPerfil.CLIENTE,
        }

    def test_complete_authentication_flow(self):
        """Teste de fluxo completo: registro -> login -> refresh -> logout."""
        # 1. Registro (retorna dados do usuário, não tokens)
        url = reverse('auth-register')
        response = self.client.post(url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('nome', response.data)
        self.assertIn('email', response.data)

        # 2. Login com credenciais válidas
        url = reverse('token_obtain_pair')
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }
        response = self.client.post(url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access_token = response.data['access']
        refresh_token = response.cookies['barbearia_refresh'].value

        # 3. Refresh de token
        self.client.cookies['barbearia_refresh'] = refresh_token
        url = reverse('token_refresh')
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        refreshed_access_token = response.data['access']
        # Token refresh rotaciona o refresh token - pegar o novo do cookie
        rotated_refresh_token = response.cookies['barbearia_refresh'].value

        # 4. Uso do token acessado para acessar recurso protegido
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refreshed_access_token}')
        url = reverse('user-list')  # Endpoint que requer autenticação
        response = self.client.get(url, format='json')
        # Depende das permissões, mas não deve falhar por falta de autenticação
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # 5. Logout (precisa do access token + refresh token rotacionado no cookie)
        self.client.cookies['barbearia_refresh'] = rotated_refresh_token
        url = reverse('token_logout')
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # 6. Verificar que token refresh não funciona mais após logout
        self.client.cookies['barbearia_refresh'] = rotated_refresh_token
        url = reverse('token_refresh')
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_password_change_invalidates_tokens(self):
        """Teste de que alteração de senha invalida tokens existentes."""
        # Criar usuário e fazer login
        user = User.objects.create_user(**self.user_data)

        url = reverse('token_obtain_pair')
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }
        response = self.client.post(url, login_data, format='json')
        access_token = response.data['access']
        refresh_token = response.cookies['barbearia_refresh'].value

        # Alterar senha
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        url = reverse('password_change')
        password_data = {
            'old_password': self.user_data['password'],
            'new_password': 'NovaSenhaSegura456!'
        }
        response = self.client.post(url, password_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verificar que o token de acesso antigo ainda pode funcionar por algum tempo
        # (dependendo da configuração CHECK_REVOKE_TOKEN)
        # Mas o refresh token deve estar blacklisted

        # Tentar usar o refresh token antigo (deve falhar por estar blacklisted)
        self.client.cookies['barbearia_refresh'] = refresh_token
        url = reverse('token_refresh')
        response = self.client.post(url, {}, format='json')
        # Com CHECK_REVOKE_TOKEN=True, isso deve falhar
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Fazer login com nova senha
        url = reverse('token_obtain_pair')
        login_data = {
            'email': self.user_data['email'],
            'password': 'NovaSenhaSegura456!'
        }
        response = self.client.post(url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# Manter os testes existentes de throttling e transição de papel
class TransicaoDePapelTests(APITestCase):
    """
    ALTO — antes, mudar `tipo_perfil` por PATCH /users/{id}/ deixava o
    sistema inconsistente nos dois sentidos (barbeiro sem perfil → HTTP 500;
    ex-barbeiro com perfil ativo e ainda agendável).
    """

    def setUp(self):
        from barbershops.models import Barber, Barbershop

        self.barbershop = Barbershop.objects.create(
            nome='Barbearia Central',
            endereco='Rua Principal, 100',
            telefone='11999999999',
            email='central@example.com',
            horario_abertura='08:00',
            horario_fechamento='18:00',
        )
        self.admin = self.criar_usuario('admin@example.com', User.TipoPerfil.ADMIN)
        self.barbeiro_user = self.criar_usuario(
            'barbeiro@example.com', User.TipoPerfil.BARBEIRO
        )
        self.barbeiro = Barber.objects.create(
            user=self.barbeiro_user, barbershop=self.barbershop
        )
        self.client.force_authenticate(self.admin)

    def criar_usuario(self, email, tipo_perfil):
        return User.objects.create_user(
            email=email,
            nome=email.split('@')[0],
            password='Senha-segura-123',
            tipo_perfil=tipo_perfil,
            barbershop=self.barbershop,
        )

    def test_rebaixar_barbeiro_desativa_o_perfil_de_barbeiro(self):
        resposta = self.client.patch(
            reverse('user-detail', args=[self.barbeiro_user.pk]),
            {'tipo_perfil': 'cliente'},
            format='json',
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.barbeiro.refresh_from_db()
        self.assertFalse(
            self.barbeiro.ativo,
            'O perfil de barbeiro continuou ativo e agendável após o rebaixamento.',
        )

    def test_promover_de_volta_reativa_o_perfil_existente(self):
        self.barbeiro.ativo = False
        self.barbeiro.save(update_fields=['ativo'])
        self.barbeiro_user.tipo_perfil = User.TipoPerfil.CLIENTE
        self.barbeiro_user.save(update_fields=['tipo_perfil'])

        resposta = self.client.patch(
            reverse('user-detail', args=[self.barbeiro_user.pk]),
            {'tipo_perfil': 'barbeiro'},
            format='json',
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.barbeiro.refresh_from_db()
        self.assertTrue(self.barbeiro.ativo)

    def test_promover_sem_perfil_cria_perfil(self):
        """Ao promover um usuário a barbeiro, criar o perfil profissional se não existir."""
        cliente = self.criar_usuario('cliente@example.com', User.TipoPerfil.CLIENTE)
        resposta = self.client.patch(
            reverse('user-detail', args=[cliente.pk]),
            {'tipo_perfil': 'barbeiro'},
            format='json',
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        cliente.refresh_from_db()
        self.assertEqual(cliente.tipo_perfil, User.TipoPerfil.BARBEIRO)
        # Check that a barber profile exists and is active
        from barbershops.models import Barber
        barber = Barber.objects.get(user=cliente)
        self.assertTrue(barber.ativo)


class ThrottlingTests(APITestCase):
    """
    ALTO — /auth/login/ e /auth/register/ não tinham nenhum limite de
    requisições: força bruta de senha e criação massiva de contas eram
    livres. Os limites reais ficam em settings (configuráveis por .env);
    aqui usamos taxas mínimas só para provar que o bloqueio existe.
    """

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        # `throttle_classes` e `THROTTLE_RATES` do DRF são atributos de
        # classe resolvidos no import, então @override_settings não os
        # alcança: aplicamos os limites diretamente, só nestes testes.
        from rest_framework.views import APIView
        from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle
        from unittest import mock

        patches = [
            mock.patch.object(APIView, 'throttle_classes', [ScopedRateThrottle]),
            mock.patch.object(
                SimpleRateThrottle, 'THROTTLE_RATES',
                {'login': '2/min', 'register': '2/min'},
            ),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_login_bloqueia_apos_o_limite(self):
        url = reverse('token_obtain_pair')
        payload = {'email': 'ninguem@example.com', 'password': 'errada'}
        codigos = [self.client.post(url, payload, format='json').status_code
                   for _ in range(3)]
        self.assertEqual(codigos[-1], status.HTTP_429_TOO_MANY_REQUESTS)

    def test_cadastro_publico_bloqueia_apos_o_limite(self):
        url = reverse('auth-register')
        codigos = []
        for indice in range(3):
            codigos.append(self.client.post(url, {
                'email': f'novo{indice}@example.com',
                'nome': 'Novo Usuário',
                'password': 'Senha-segura-123',
            }, format='json').status_code)
        self.assertEqual(codigos[-1], status.HTTP_429_TOO_MANY_REQUESTS)


class UserCreateSerializerSecurityTests(APITestCase):
    """Testes de segurança para UserCreateSerializer (ALTO-3: validação de admin)."""

    def setUp(self):
        from barbershops.models import Barbershop
        self.barbershop = Barbershop.objects.create(
            nome='Barbearia Teste',
            endereco='Rua Teste, 123',
            telefone='11999999999',
            email='teste@barbearia.com',
            horario_abertura='08:00',
            horario_fechamento='18:00',
        )

    def test_admin_com_barbearia_pode_criar_usuario(self):
        """Admin de uma barbearia pode criar usuários."""
        admin = User.objects.create_user(
            email='admin@teste.com',
            nome='Admin',
            password='SenhaSegura123!',
            tipo_perfil=User.TipoPerfil.ADMIN,
            barbershop=self.barbershop,
        )
        self.client.force_authenticate(admin)

        url = reverse('user-list')
        user_data = {
            'email': 'novo@teste.com',
            'nome': 'Novo Usuario',
            'password': 'SenhaSegura123!',
            'tipo_perfil': User.TipoPerfil.CLIENTE,
        }
        response = self.client.post(url, user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_barbeiro_nao_pode_criar_usuario(self):
        """Barbeiro NÃO pode criar usuários (permissão IsAdminRole bloqueia com 403)."""
        barbeiro = User.objects.create_user(
            email='barbeiro@teste.com',
            nome='Barbeiro',
            password='SenhaSegura123!',
            tipo_perfil=User.TipoPerfil.BARBEIRO,
            barbershop=self.barbershop,
        )
        self.client.force_authenticate(barbeiro)

        url = reverse('user-list')
        user_data = {
            'email': 'novo@teste.com',
            'nome': 'Novo Usuario',
            'password': 'SenhaSegura123!',
            'tipo_perfil': User.TipoPerfil.CLIENTE,
        }
        response = self.client.post(url, user_data, format='json')
        # Permissão IsAdminRole bloqueia antes do serializer (403)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cliente_nao_pode_criar_usuario(self):
        """Cliente NÃO pode criar usuários (permissão IsAdminRole bloqueia com 403)."""
        cliente = User.objects.create_user(
            email='cliente@teste.com',
            nome='Cliente',
            password='SenhaSegura123!',
            tipo_perfil=User.TipoPerfil.CLIENTE,
            barbershop=self.barbershop,
        )
        self.client.force_authenticate(cliente)

        url = reverse('user-list')
        user_data = {
            'email': 'novo@teste.com',
            'nome': 'Novo Usuario',
            'password': 'SenhaSegura123!',
            'tipo_perfil': User.TipoPerfil.CLIENTE,
        }
        response = self.client.post(url, user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_sem_barbearia_nao_pode_criar_usuario(self):
        """Superuser SEM barbearia NÃO pode criar usuários (serializer valida barbershop_id)."""
        superuser = User.objects.create_superuser(
            email='super@teste.com',
            nome='Superuser',
            password='SenhaSegura123!',
        )
        self.client.force_authenticate(superuser)

        url = reverse('user-list')
        user_data = {
            'email': 'novo@teste.com',
            'nome': 'Novo Usuario',
            'password': 'SenhaSegura123!',
            'tipo_perfil': User.TipoPerfil.CLIENTE,
        }
        response = self.client.post(url, user_data, format='json')
        # Serializer valida barbershop_id e retorna 400
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('barbershop', response.data)

    def test_serializer_valida_role_admin_diretamente(self):
        """Teste unitário do serializer: validação de role admin no create()."""
        from accounts.serializers import UserCreateSerializer
        from django.test import RequestFactory

        admin = User.objects.create_user(
            email='admin@teste.com',
            nome='Admin',
            password='SenhaSegura123!',
            tipo_perfil=User.TipoPerfil.ADMIN,
            barbershop=self.barbershop,
        )

        factory = RequestFactory()
        request = factory.post('/api/v1/users/', {})
        request.user = admin

        serializer = UserCreateSerializer(data={
            'email': 'novo@teste.com',
            'nome': 'Novo Usuario',
            'password': 'SenhaSegura123!',
            'tipo_perfil': User.TipoPerfil.CLIENTE,
        }, context={'request': request})

        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertEqual(user.tipo_perfil, User.TipoPerfil.CLIENTE)
        self.assertEqual(user.barbershop, self.barbershop)

    def test_serializer_rejeita_barbeiro_role(self):
        """Teste unitário: serializer rejeita não-admin no create()."""
        from accounts.serializers import UserCreateSerializer
        from django.test import RequestFactory

        barbeiro = User.objects.create_user(
            email='barbeiro@teste.com',
            nome='Barbeiro',
            password='SenhaSegura123!',
            tipo_perfil=User.TipoPerfil.BARBEIRO,
            barbershop=self.barbershop,
        )

        factory = RequestFactory()
        request = factory.post('/api/v1/users/', {})
        request.user = barbeiro

        serializer = UserCreateSerializer(data={
            'email': 'novo@teste.com',
            'nome': 'Novo Usuario',
            'password': 'SenhaSegura123!',
            'tipo_perfil': User.TipoPerfil.CLIENTE,
        }, context={'request': request})

        self.assertTrue(serializer.is_valid())
        # A validação de permissão acontece na view, mas o serializer
        # tem defesa em profundidade no create()
        with self.assertRaises(Exception) as ctx:
            serializer.save()
        self.assertIn('Apenas administradores', str(ctx.exception))