-- P2 — pré-verificação com a REGRA EXATA da accounts.0006 (accounts.emails.forma_canonica). SOMENTE LEITURA.
-- Gerado por gerar_e_validar_regra_exata.py; a equivalência com o Python foi provada antes, no banco descartável.
-- Não mostra e-mails, nomes nem papéis: só contagens e ids.
\set ON_ERROR_STOP on
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '30s';

\echo '== R1. Classificação pela regra exata (esperado: fora_da_regra = 0 e grupos_de_colisao = 0)'
WITH espacos AS (SELECT U&'\0009\000A\000B\000C\000D\001C\001D\001E\001F\0020\0085\00A0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000'::text AS w),
c AS (SELECT u.id, u.email, btrim(u.email, espacos.w) AS sem_espacos FROM accounts_user u, espacos),
r AS (SELECT id, email, (sem_espacos ~ '^[!-~]+$') AS cabe_na_regra,
             CASE WHEN sem_espacos ~ '^[!-~]+$' THEN lower(sem_espacos) END AS canonico FROM c)
SELECT count(*) AS contas,
       count(*) FILTER (WHERE cabe_na_regra AND canonico = email) AS ja_canonicas,
       count(*) FILTER (WHERE cabe_na_regra AND canonico <> email) AS a_normalizar,
       count(*) FILTER (WHERE NOT cabe_na_regra) AS fora_da_regra,
       (SELECT count(*) FROM (SELECT 1 FROM r WHERE cabe_na_regra GROUP BY canonico HAVING count(*) > 1) g) AS grupos_de_colisao
FROM r;

\echo '== R2. ids fora da regra (interromperiam a migração)'
WITH espacos AS (SELECT U&'\0009\000A\000B\000C\000D\001C\001D\001E\001F\0020\0085\00A0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000'::text AS w),
c AS (SELECT u.id, u.email, btrim(u.email, espacos.w) AS sem_espacos FROM accounts_user u, espacos),
r AS (SELECT id, email, (sem_espacos ~ '^[!-~]+$') AS cabe_na_regra,
             CASE WHEN sem_espacos ~ '^[!-~]+$' THEN lower(sem_espacos) END AS canonico FROM c)
SELECT id FROM r WHERE NOT cabe_na_regra ORDER BY id;

\echo '== R3. ids que a migração normalizaria'
WITH espacos AS (SELECT U&'\0009\000A\000B\000C\000D\001C\001D\001E\001F\0020\0085\00A0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000'::text AS w),
c AS (SELECT u.id, u.email, btrim(u.email, espacos.w) AS sem_espacos FROM accounts_user u, espacos),
r AS (SELECT id, email, (sem_espacos ~ '^[!-~]+$') AS cabe_na_regra,
             CASE WHEN sem_espacos ~ '^[!-~]+$' THEN lower(sem_espacos) END AS canonico FROM c)
SELECT id FROM r WHERE cabe_na_regra AND canonico <> email ORDER BY id;

\echo '== R4. grupos de colisão após a normalização (ids)'
WITH espacos AS (SELECT U&'\0009\000A\000B\000C\000D\001C\001D\001E\001F\0020\0085\00A0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000'::text AS w),
c AS (SELECT u.id, u.email, btrim(u.email, espacos.w) AS sem_espacos FROM accounts_user u, espacos),
r AS (SELECT id, email, (sem_espacos ~ '^[!-~]+$') AS cabe_na_regra,
             CASE WHEN sem_espacos ~ '^[!-~]+$' THEN lower(sem_espacos) END AS canonico FROM c)
SELECT array_agg(id ORDER BY id) AS ids FROM r WHERE cabe_na_regra GROUP BY canonico HAVING count(*) > 1;

ROLLBACK;
