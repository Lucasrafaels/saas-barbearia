-- Contadores de escrita por tabela (inserções, atualizações, exclusões) desde o último reset de estatísticas.
-- SOMENTE LEITURA. Usado para provar que P10 e P11 não gravaram nada (os contadores não podem mudar).
\set ON_ERROR_STOP on
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '30s';
SELECT relname, n_tup_ins, n_tup_upd, n_tup_del, n_tup_hot_upd FROM pg_stat_user_tables ORDER BY relname;
ROLLBACK;
