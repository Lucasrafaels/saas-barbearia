-- CÓPIA DE EXECUÇÃO (15/11/2026): idêntica ao arquivo autorizado, SEM o bloco 3 (nomes e e-mails),
-- porque a autorização de execução no banco real proíbe consultas que exponham nomes ou e-mails.
-- AUTH-04 / AUTH-05 — o que a normalização planejada (endereço inteiro em minúsculas, sem espaços nas pontas)
-- faria colidir, e quantas contas ela mudaria.
--
-- SOMENTE LEITURA: a transação é READ ONLY e termina em ROLLBACK. Nada é gravado.
-- NO BANCO REAL (barbershop_db), RODAR SÓ COM AUTORIZAÇÃO DO DONO.
-- As consultas 0, 1, 2, 4 e 5 não mostram e-mails nem nomes. A 3 mostra, porque é a que o dono usa para decidir
-- cada conflito. A saída dela NÃO deve ir para as evidências.
--
-- Uso: psql -X -v ON_ERROR_STOP=1 -d <banco> -f verificacao-colisoes-somente-leitura.sql
\set ON_ERROR_STOP on
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '30s';

\echo '== 0. Ambiente: o lower() do PostgreSQL depende do LC_CTYPE deste banco'
SELECT current_database() AS banco, datcollate, datctype, datlocprovider, split_part(version(), ' on ', 1) AS versao
FROM pg_database WHERE datname = current_database();

\echo '== 1. Resumo (sem dados pessoais)'
SELECT count(*)                                                                  AS total_de_contas,
       count(*) FILTER (WHERE email <> lower(btrim(email)))                      AS mudariam_com_a_normalizacao,
       count(*) FILTER (WHERE email <> btrim(email))                             AS com_espacos_nas_pontas,
       count(*) FILTER (WHERE octet_length(email) <> char_length(email))         AS com_caracteres_nao_ascii,
       (SELECT count(*) FROM (SELECT 1 FROM accounts_user
                              GROUP BY lower(btrim(email)) HAVING count(*) > 1) g) AS grupos_que_colidiriam,
       (SELECT coalesce(sum(n), 0) FROM (SELECT count(*) AS n FROM accounts_user
                              GROUP BY lower(btrim(email)) HAVING count(*) > 1) g) AS contas_nesses_grupos
FROM accounts_user;

\echo '== 2. Grupos que colidiriam (sem e-mail nem nome): o grupo é identificado pelo menor id'
SELECT min(u.id)                                                              AS grupo,
       count(*)                                                               AS contas,
       array_agg(u.id ORDER BY u.id)                                          AS ids,
       array_agg(coalesce(u.barbershop_id::text, '-') ORDER BY u.id)          AS barbearias,
       array_agg(u.tipo_perfil ORDER BY u.id)                                 AS papeis,
       array_agg(u.is_active ORDER BY u.id)                                   AS ativas,
       array_agg(u.is_superuser ORDER BY u.id)                                AS superusuarios,
       array_agg(coalesce(to_char(u.last_login, 'YYYY-MM-DD'), '-') ORDER BY u.id) AS ultimo_login,
       array_agg(to_char(u.date_joined, 'YYYY-MM-DD') ORDER BY u.id)          AS criada_em,
       array_agg((SELECT count(*) FROM appointments_appointment a WHERE a.cliente_id = u.id) ORDER BY u.id)
                                                                              AS agendamentos_como_cliente,
       array_agg(EXISTS (SELECT 1 FROM barbershops_barber b WHERE b.user_id = u.id) ORDER BY u.id)
                                                                              AS tem_perfil_de_barbeiro,
       array_agg(u.email = lower(btrim(u.email)) ORDER BY u.id)               AS ja_esta_normalizado
FROM accounts_user u
GROUP BY lower(btrim(u.email))
HAVING count(*) > 1
ORDER BY contas DESC, grupo;

\echo '== 4. Contas que a normalização mudaria (sem e-mail): só ids e o tipo de mudança'
SELECT id,
       email <> btrim(email)                                                  AS espacos_nas_pontas,
       split_part(btrim(email), '@', 1) <> lower(split_part(btrim(email), '@', 1)) AS maiusculas_na_parte_local,
       split_part(btrim(email), '@', 2) <> lower(split_part(btrim(email), '@', 2)) AS maiusculas_no_dominio,
       lower(btrim(email)) IN (SELECT lower(btrim(email)) FROM accounts_user GROUP BY 1 HAVING count(*) > 1)
                                                                              AS em_grupo_de_colisao
FROM accounts_user
WHERE email <> lower(btrim(email))
ORDER BY id;

\echo '== 5. Contas com caracteres não ASCII (onde o lower() do PostgreSQL e o do Python podem divergir)'
SELECT id, lower(btrim(email)) = btrim(email) AS ja_minusculo
FROM accounts_user
WHERE octet_length(email) <> char_length(email)
ORDER BY id;

ROLLBACK;
