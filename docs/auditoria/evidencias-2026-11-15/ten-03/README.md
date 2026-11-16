# Evidências da investigação do TEN-03 (15/11/2026)

Esta etapa foi **só investigação**. O TEN-03 é a exposição da existência de e-mails usados em outras barbearias. A análise está na seção 26 de [`docs/AUDITORIA_BARBERPRO.md`](../../../AUDITORIA_BARBERPRO.md). As pastas das etapas anteriores não foram alteradas.

**Nenhum código de produção foi alterado e nenhuma migração foi criada ou aplicada.** O TEN-03 **não** está resolvido. A regra de unicidade aguarda a decisão do dono.

## Como foi verificado

- **Código:** o atual da branch `desenvolvimento`, com as alterações locais não commitadas (contenção, TEN-01, TEN-02, `exclude_appointment_id` e PER-13), sem nenhuma mudança.
- **Banco:** um **PostgreSQL 18.3 descartável**, criado com `initdb` no diretório temporário da sessão e acessado só por TCP em `127.0.0.1:55432`. Ele já foi apagado. Foram usados dois bancos:
  - `t3_db`: a sondagem HTTP;
  - `t3_lab`: as simulações e a suíte de testes.
- **Bancos não usados:** o `barbershop_db` real (PG 18 do host, porta 5432) e o PostgreSQL do Docker (porta 5433).
- **API de laboratório:** `runserver` em `127.0.0.1:8781`, com `DEBUG=False` e só JSON. As settings descartáveis (`scripts/t3_settings.py`) mudam só o banco, a pasta de mídia, o throttle (relaxado para a matriz) e o backend de e-mail (arquivo, no diretório temporário).
- **SQL do servidor:** o `t3_db` rodou com `log_statement = 'all'`, e cada pedido ficou entre dois marcadores no log. O log bruto não foi copiado. Os trechos copiados não têm hash de senha, token JWT, jti nem token de recuperação.
- **Dados:** todos fictícios, em domínios reservados `.test`. As senhas do seed eram aleatórias, ficaram só no diretório temporário e foram apagadas com ele. Os scripts trazem apenas duas senhas fictícias fixas, usadas como entrada de teste: `Navalha-Fict-2026!` e `12345678`.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `MATRIZ-TEN-03.md` | A matriz dos 58 cenários: pedido, papel, status, resposta integral, conta criada ou alterada, consulta de existência e se a conta encontrada estava fora do alcance do solicitante |
| `api/sondagem-http-sql.json` | A saída bruta da sondagem: corpo enviado (sem senha), resposta integral, tempo, fotografia do banco antes e depois, e-mails de recuperação gerados (destinatário e conta, sem o token) e o SQL do servidor de cada cenário |
| `api/console-sondagem.txt` | O resumo impresso durante a sondagem |
| `api/runserver-8781.txt` | Log da API de laboratório, com os dois rastreamentos do `IntegrityError` (500) |
| `sql/sql-por-cenario.txt` | O SQL registrado pelo PostgreSQL em cada cenário |
| `sql/esquema-accounts_user.txt` | `\d accounts_user`, as restrições e índices, o `sqlmigrate accounts 0001` e a ordenação do banco descartável |
| `arquitetura/validadores-por-serializer.txt` | `USERNAME_FIELD`, backends de autenticação e os validadores que o DRF gera para o campo `email` de cada serializer |
| `simulacoes/simulacao-alternativa-c.txt` / `.json` | Simulação de laboratório da Alternativa C, aplicada só no processo e numa transação desfeita: mensagem genérica (C1) e status e corpo padronizados em todo 400 (C2) |
| `simulacoes/simulacao-alternativa-b.json` | Simulação de laboratório da Alternativa B: `UNIQUE(email)` trocada por `UNIQUE(email, barbershop_id)` dentro de uma transação desfeita, para medir o login e a recuperação de senha atuais |
| `testes/suite-sqlite.txt`, `testes/suite-postgresql18.txt` | Suíte completa, sem alteração: 452 testes no SQLite e no PG 18.3 descartável |
| `testes/django-check.txt` | `check`, `makemigrations --check --dry-run` e `showmigrations accounts` |
| `scripts/` | Seed, sondagem, extração do SQL, servidor, inspeção dos validadores, simulações e as settings descartáveis |

## Como reproduzir

1. **Banco descartável:**
   1. Crie um PostgreSQL 18 com `initdb`, com `listen_addresses='127.0.0.1'`, `port=55432`, `unix_socket_directories=''` e `logging_collector=on`.
   2. Crie o banco `t3_db`.
   3. Rode `migrate --settings=t3_settings` com `PYTHONPATH=<pasta das settings>:<projeto>`.
2. **Seed:** `DJANGO_SETTINGS_MODULE=t3_settings venv/bin/python scripts/t3_seed.py <estado.json>`.
3. **API:** ajuste os caminhos absolutos em `scripts/t3_servidor.sh` e rode o script **sozinho**, não dentro de um comando maior. O `pkill -f` dele casa com qualquer linha de comando que contenha o texto do `runserver`.
4. **Sondagem:** `python3 -I scripts/t3_probe.py <estado.json> <saida.json> <pasta EMAIL_FILE_PATH>`.
5. **SQL e matriz:** `python3 -I scripts/t3_sql.py <pgdata/log/pg.log> <saida.json> <saida_com_sql.json> <matriz.md> <estado.json> <sql_por_cenario.txt>`.
6. **Simulações:** crie o banco `t3_lab`, aplique as migrações com `t3_lab_settings` e rode `scripts/t3_simulacao_alt_c.py` e `scripts/t3_simulacao_alt_b.py`. As duas desfazem tudo no fim; a B confirma isso relendo as restrições do banco.

## Reprodução manual mínima

Sem efeito colateral e sem login:

| Pedido (anônimo) | Resposta |
|---|---|
| `POST /api/v1/auth/register/` `{"nome":"X","email":"<e-mail de cliente de B>","password":"12345678"}` | 400 `{"email":["usuário com este e-mail já existe."]}` |
| O mesmo pedido, com um e-mail livre | 400 `{"password":["Esta senha é muito comum.","Esta senha é inteiramente numérica."]}` |
