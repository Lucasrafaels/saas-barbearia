-- P2 — identidade do banco conectado. SOMENTE LEITURA. Não mostra o nome do usuário nem credenciais.
\set ON_ERROR_STOP on
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '30s';
SELECT current_database() AS banco, current_database() = 'barbershop_db' AS banco_confere,
       current_setting('server_version') AS versao, inet_server_addr() AS endereco, inet_server_port() AS porta,
       current_user = 'barbershop_user' AS usuario_confere,
       current_setting('transaction_read_only') AS transacao_somente_leitura,
       current_setting('default_transaction_read_only') AS sessao_somente_leitura,
       d.datcollate, d.datctype, d.datlocprovider, d.datcollversion
FROM pg_database d WHERE d.datname = current_database();
ROLLBACK;
