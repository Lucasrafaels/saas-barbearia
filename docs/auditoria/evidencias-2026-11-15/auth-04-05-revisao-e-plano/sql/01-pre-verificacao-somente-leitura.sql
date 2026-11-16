-- Plano da accounts.0006 (seção 32), passo P2 — PRÉ-VERIFICAÇÃO. SOMENTE LEITURA (READ ONLY + ROLLBACK).
-- Roda primeiro na cópia restaurada (ensaio) e depois no banco real, pelo com_credenciais_da_app.py --somente-leitura.
-- NÃO EXECUTADO na etapa de planejamento. Não mostra e-mails, nomes nem papéis de banco.
\set ON_ERROR_STOP on
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '30s';

\echo '== 1. Identidade (esperado: barbershop_db, 18.3, porta 5432, pt_BR.UTF-8, libc)'
SELECT current_database() AS banco, current_setting('server_version') AS versao, inet_server_port() AS porta,
       datcollate, datctype, datlocprovider, datcollversion, pg_size_pretty(pg_database_size(current_database())) AS tamanho
FROM pg_database WHERE datname = current_database();

\echo '== 2. Migrações (esperado: accounts até 0005; barbershops.0006 e auth.0012 aplicadas; accounts.0006 AUSENTE)'
SELECT app, name, applied FROM django_migrations
WHERE app = 'accounts'
   OR (app = 'barbershops' AND name = '0006_barbershop_dias_funcionamento')
   OR (app = 'auth' AND name = '0012_alter_user_first_name_max_length')
ORDER BY app, name;

\echo '== 3. Restrições e índices de accounts_user (esperado: UNIQUE accounts_user_email_key; nenhuma das novas)'
SELECT conname, contype, pg_get_constraintdef(oid) AS definicao
FROM pg_constraint WHERE conrelid = 'accounts_user'::regclass AND contype IN ('u', 'c') ORDER BY conname;
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'accounts_user' ORDER BY indexname;

\echo '== 4. Regra exata do CHECK futuro (esperado: violariam_o_check = 0, vazios = 0, grupos = 0)'
SELECT count(*) AS contas,
       count(*) FILTER (WHERE NOT (email = lower(email) AND email ~ '^[!-~]+$')) AS violariam_o_check,
       count(*) FILTER (WHERE email = '') AS vazios,
       (SELECT count(*) FROM (SELECT 1 FROM accounts_user GROUP BY lower(email) HAVING count(*) > 1) g) AS grupos_lower_iguais
FROM accounts_user;
\echo '   ids que violariam o CHECK (a migração normaliza o que puder; o resto a interrompe):'
SELECT id FROM accounts_user WHERE NOT (email = lower(email) AND email ~ '^[!-~]+$') ORDER BY id;
\echo '   grupos com o mesmo lower(email) (ids):'
SELECT array_agg(id ORDER BY id) AS ids FROM accounts_user GROUP BY lower(email) HAVING count(*) > 1;

\echo '== 5. Outras sessões neste banco (esperado na janela: nenhuma da aplicação; nenhuma "idle in transaction")'
SELECT pid, application_name, client_addr, state, backend_start, xact_start, now() - xact_start AS transacao_aberta_ha,
       wait_event_type
FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid() ORDER BY xact_start NULLS LAST;

\echo '== 6. Travas em accounts_user de outras sessões (esperado: nenhuma)'
SELECT l.pid, l.mode, l.granted FROM pg_locks l JOIN pg_class c ON c.oid = l.relation
WHERE c.relname = 'accounts_user' AND l.pid <> pg_backend_pid();

ROLLBACK;
