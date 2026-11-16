-- Plano da accounts.0006 (seção 32), passo P9 — PÓS-VERIFICAÇÃO. SOMENTE LEITURA (READ ONLY + ROLLBACK).
-- NÃO EXECUTADO na etapa de planejamento.
\set ON_ERROR_STOP on
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '30s';

\echo '== 1. accounts.0006 registrada como aplicada'
SELECT app, name, applied FROM django_migrations WHERE app = 'accounts' ORDER BY id DESC LIMIT 2;

\echo '== 2. Restrições (esperado: accounts_user_email_key UNIQUE e accounts_user_email_normalizado CHECK, convalidated = t)'
SELECT conname, contype, convalidated, pg_get_constraintdef(oid) AS definicao
FROM pg_constraint WHERE conrelid = 'accounts_user'::regclass AND contype IN ('u', 'c') ORDER BY conname;

\echo '== 3. Índices (esperado: accounts_user_email_lower_unico único, válido e pronto, sobre lower(email))'
SELECT c.relname AS indice, i.indisunique AS unico, i.indisvalid AS valido, i.indisready AS pronto,
       pg_get_indexdef(i.indexrelid) AS definicao
FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid WHERE i.indrelid = 'accounts_user'::regclass ORDER BY 1;

\echo '== 4. Nenhuma conta fora da regra (esperado: fora_da_regra = 0; contas igual à pré-verificação)'
SELECT count(*) AS contas, count(*) FILTER (WHERE NOT (email = lower(email) AND email ~ '^[!-~]+$')) AS fora_da_regra
FROM accounts_user;

ROLLBACK;
