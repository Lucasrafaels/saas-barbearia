# Evidências da auditoria de isolamento multi-tenant (13/11/2026)

Somente diagnóstico. A análise está na seção 20 de [`docs/AUDITORIA_BARBERPRO.md`](../../../AUDITORIA_BARBERPRO.md). A matriz completa, com as 217 verificações, está em [`MATRIZ.md`](MATRIZ.md).

## Como foi verificado

- **Código auditado:** branch `desenvolvimento`, commit `051b00a`, árvore limpa. Nenhum arquivo de código, configuração, migração, dependência ou `.env` foi alterado.
- **Banco:** PostgreSQL 18.3 descartável, criado com `initdb` no diretório temporário da sessão e acessível só por TCP em `127.0.0.1:55432`. Recebeu as 52 migrações e o seed fictício da auditoria: 2 barbearias, 14 usuários e 419 agendamentos. Ao final, foi parado e apagado. **O banco real (`barbershop_db`) e o PostgreSQL do Docker (porta 5433) não foram usados.**
- **API:** o mesmo código do projeto, servido por `runserver` em `127.0.0.1:8767`. A única diferença está nas settings (`scripts/iso_settings.py`): o banco descartável, `MEDIA_ROOT` fora do projeto e limites de taxa altos, porque a sondagem faz muitos logins. Para o vazamento principal (TEN-01), uma segunda instância com `DEBUG=False` (`scripts/iso_prod_settings.py`) confirmou o mesmo comportamento.
- **Conferência no banco:** depois de cada tentativa de escrita, a sondagem compara a linha-alvo diretamente no banco descartável. Também tira uma "fotografia" (md5 de todas as linhas) da barbearia B antes e depois de todos os ataques de A, e da barbearia A antes e depois dos ataques de B.
- **Segredos:** nenhum arquivo desta pasta contém senha, token ou `SECRET_KEY`. As credenciais fictícias do seed ficaram só no diretório temporário. Os nomes que aparecem são todos fictícios.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `MATRIZ.md` | As 217 verificações: ID, área, recurso, papel, origem → destino, operação, esperado, observado, evidência e severidade |
| `resultados/isolamento.json` | Saída bruta da sondagem (fonte da matriz), com amostras do texto exposto no HTML |
| `resultados/html-debug-false.txt` | TEN-01 reproduzido numa instância com `DEBUG=False` |
| `resultados/html-anonimo.txt` | Sem autenticação, a API navegável responde 401 e não renderiza formulários |
| `resultados/api-isolada.log` | Log de acesso do `runserver` (método, caminho e status) durante a sondagem |
| `scripts/iso_probe.py` | Sondagem: HTTP com a biblioteca padrão e conferência no banco com `psycopg2` |
| `scripts/reset_iso.sh` | Recria o banco descartável, aplica as migrações, roda o seed e reinicia a API isolada |
| `scripts/seed_pg18.py` | Seed fictício da auditoria (`../scripts/seed.py`), com a trava de porta ajustada para 55432 |
| `scripts/iso_settings.py`, `scripts/iso_prod_settings.py` | Settings da API isolada (`DEBUG` do `.env` e `DEBUG=False`) |

## Como reproduzir

1. Crie um PostgreSQL 18 descartável em `127.0.0.1:55432`, com o usuário `smoke` e autenticação `trust` só local:
   - `initdb -U smoke --auth=trust`;
   - no `postgresql.conf`, `listen_addresses='127.0.0.1'` e `unix_socket_directories=''`.
2. Ajuste os caminhos absolutos do diretório temporário em `reset_iso.sh` e em `iso_settings.py`, e rode `reset_iso.sh`.
3. `venv/bin/python -I scripts/iso_probe.py <estado_seed.json> <saida.json>`

Reprodução manual do TEN-01, sem script:

1. `POST /api/v1/auth/register/` com e-mail, nome e senha. É o cadastro público e não exige convite.
2. `POST /api/v1/auth/login/` para obter o token de acesso.
3. `GET /api/v1/appointments/` com `Authorization: Bearer <token>` e `Accept: text/html`, ou com `?format=api`.
4. Os `<select name="cliente">`, `<select name="barbeiro">` e `<select name="servico">` listam registros de **todas** as barbearias.
