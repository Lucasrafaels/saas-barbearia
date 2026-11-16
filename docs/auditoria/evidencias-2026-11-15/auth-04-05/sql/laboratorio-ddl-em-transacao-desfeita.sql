-- AUTH-04/05 — LABORATÓRIO, só no banco DESCARTÁVEL a45_lab, com as contas FICTÍCIAS de a45_dados_legados.py.
-- Mostra o que uma futura migração encontraria. Cada bloco roda numa transação terminada em ROLLBACK: nada fica gravado.
-- NÃO é uma migração e NÃO deve ser rodado no banco real.
\set ON_ERROR_STOP off
\echo '== L1. Criar o índice único em lower(email) com as colisões presentes'
BEGIN;
CREATE UNIQUE INDEX lab_email_lower_unico ON accounts_user (lower(email));
ROLLBACK;
\echo '== L2. Converter os e-mails para minúsculas antes de resolver as colisões'
BEGIN;
UPDATE accounts_user SET email = lower(btrim(email)) WHERE email <> lower(btrim(email));
ROLLBACK;
\echo '== L3. Exigir e-mail já normalizado (CHECK) com os dados atuais'
BEGIN;
ALTER TABLE accounts_user ADD CONSTRAINT lab_email_normalizado CHECK (email = lower(btrim(email)));
ROLLBACK;
\echo '== L4. Com as colisões resolvidas (simulação: o dono escolheu manter a conta de menor id de cada grupo)'
BEGIN;
UPDATE accounts_user SET email = 'conflito+' || id || '@resolver.invalid' WHERE id IN (4, 5, 7, 10);
UPDATE accounts_user SET email = lower(btrim(email)) WHERE email <> lower(btrim(email));
CREATE UNIQUE INDEX lab_email_lower_unico ON accounts_user (lower(email));
ALTER TABLE accounts_user ADD CONSTRAINT lab_email_normalizado CHECK (email = lower(btrim(email)));
SELECT count(*) AS contas, count(DISTINCT lower(email)) AS emails_distintos FROM accounts_user;
\echo '== L5. Depois disso, o banco recusa variações de caixa e e-mail fora do padrão, venha de onde vier'
SAVEPOINT s1;
INSERT INTO accounts_user (password, is_superuser, is_staff, is_active, date_joined, created_at, updated_at, email, nome, tipo_perfil)
VALUES ('!', false, false, true, now(), now(), now(), 'cliente.b@beta.test ', 'Teste', 'cliente');
ROLLBACK TO SAVEPOINT s1;
INSERT INTO accounts_user (password, is_superuser, is_staff, is_active, date_joined, created_at, updated_at, email, nome, tipo_perfil)
VALUES ('!', false, false, true, now(), now(), now(), 'CLIENTE.B@beta.test', 'Teste', 'cliente');
ROLLBACK TO SAVEPOINT s1;
UPDATE accounts_user SET email = 'Cliente.B@beta.test' WHERE id = 3;
ROLLBACK;
\echo '== L6. Conferência: nada ficou gravado'
SELECT count(*) AS contas, count(*) FILTER (WHERE email <> lower(btrim(email))) AS fora_do_padrao,
       (SELECT count(*) FROM pg_indexes WHERE indexname = 'lab_email_lower_unico') AS indice_de_laboratorio,
       (SELECT count(*) FROM pg_constraint WHERE conname = 'lab_email_normalizado') AS check_de_laboratorio
FROM accounts_user;
