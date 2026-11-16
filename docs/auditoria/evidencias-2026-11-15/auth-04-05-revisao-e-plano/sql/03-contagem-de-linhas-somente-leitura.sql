-- Plano da accounts.0006 (seção 32), passos P2 e P5 — contagem de linhas para comparar o banco real com a cópia
-- restaurada do backup. SOMENTE LEITURA. NÃO EXECUTADO na etapa de planejamento.
\set ON_ERROR_STOP on
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '30s';
SELECT 'accounts_user' AS tabela, count(*) AS linhas FROM accounts_user
UNION ALL SELECT 'appointments_appointment', count(*) FROM appointments_appointment
UNION ALL SELECT 'barbershops_barber', count(*) FROM barbershops_barber
UNION ALL SELECT 'barbershops_barbershop', count(*) FROM barbershops_barbershop
UNION ALL SELECT 'django_migrations', count(*) FROM django_migrations
UNION ALL SELECT 'services_service', count(*) FROM services_service
UNION ALL SELECT 'token_blacklist_blacklistedtoken', count(*) FROM token_blacklist_blacklistedtoken
UNION ALL SELECT 'token_blacklist_outstandingtoken', count(*) FROM token_blacklist_outstandingtoken
ORDER BY 1;
ROLLBACK;
