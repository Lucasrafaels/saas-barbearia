"""P1 — identidade do banco CONFIGURADO na aplicação (settings/.env), ANTES de conectar. Não conecta e não imprime
credenciais: mostra nome, host e porta, e só se o usuário confere com o esperado. Rodar na raiz do projeto original."""
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
from django.conf import settings  # noqa: E402

db = settings.DATABASES['default']
esperado = {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'barbershop_db', 'HOST': 'localhost', 'PORT': '5432', 'USER': 'barbershop_user'}
confere = {k: str(db.get(k)) == v for k, v in esperado.items()}
print(f"motor={db.get('ENGINE', '').rsplit('.', 1)[-1]} banco={db.get('NAME')} host={db.get('HOST')} porta={db.get('PORT')} "
      f"usuario_confere={confere['USER']} senha_definida={bool(db.get('PASSWORD'))}")
print('IDENTIDADE CONFIGURADA:', 'CONFERE' if all(confere.values()) else f'DIVERGE {confere}')
sys.exit(0 if all(confere.values()) else 1)
