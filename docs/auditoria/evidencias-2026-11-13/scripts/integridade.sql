\pset footer off
\pset tuples_only on
\echo '-- sessão somente leitura'
SET default_transaction_read_only = on;
BEGIN READ ONLY;
SELECT 'barbearias', count(*) FROM barbershops_barbershop
UNION ALL SELECT 'barbearias inativas', count(*) FROM barbershops_barbershop WHERE NOT ativo
UNION ALL SELECT 'usuarios', count(*) FROM accounts_user
UNION ALL SELECT 'usuarios por perfil: admin', count(*) FROM accounts_user WHERE tipo_perfil='admin'
UNION ALL SELECT 'usuarios por perfil: barbeiro', count(*) FROM accounts_user WHERE tipo_perfil='barbeiro'
UNION ALL SELECT 'usuarios por perfil: cliente', count(*) FROM accounts_user WHERE tipo_perfil='cliente'
UNION ALL SELECT 'usuarios sem barbearia (nao superusuario)', count(*) FROM accounts_user WHERE barbershop_id IS NULL AND NOT is_superuser
UNION ALL SELECT 'barbeiros (perfil)', count(*) FROM barbershops_barber
UNION ALL SELECT 'servicos', count(*) FROM services_service
UNION ALL SELECT 'agendamentos', count(*) FROM appointments_appointment
UNION ALL SELECT 'agendamentos sem preco_historico', count(*) FROM appointments_appointment WHERE preco_historico IS NULL
UNION ALL SELECT 'agendamentos vencidos agendado/confirmado', count(*) FROM appointments_appointment WHERE status IN ('agendado','confirmado') AND data_hora < now()
UNION ALL SELECT 'realizados no futuro', count(*) FROM appointments_appointment WHERE status='realizado' AND data_hora > now()
UNION ALL SELECT 'cliente do agendamento sem perfil cliente', count(*) FROM appointments_appointment a JOIN accounts_user u ON u.id=a.cliente_id WHERE u.tipo_perfil<>'cliente'
UNION ALL SELECT 'agendamento com barbeiro/servico/cliente de outra barbearia', count(*) FROM appointments_appointment a JOIN barbershops_barber b ON b.id=a.barbeiro_id JOIN services_service s ON s.id=a.servico_id JOIN accounts_user c ON c.id=a.cliente_id WHERE b.barbershop_id<>a.barbershop_id OR s.barbershop_id<>a.barbershop_id OR c.barbershop_id<>a.barbershop_id
UNION ALL SELECT 'barbeiro ativo com usuario sem perfil barbeiro', count(*) FROM barbershops_barber b JOIN accounts_user u ON u.id=b.user_id WHERE b.ativo AND u.tipo_perfil<>'barbeiro'
UNION ALL SELECT 'usuario barbeiro sem perfil ativo', count(*) FROM accounts_user u LEFT JOIN barbershops_barber b ON b.user_id=u.id AND b.ativo WHERE u.tipo_perfil='barbeiro' AND b.id IS NULL
UNION ALL SELECT 'barbeiro em barbearia diferente do usuario', count(*) FROM barbershops_barber b JOIN accounts_user u ON u.id=b.user_id WHERE b.barbershop_id<>u.barbershop_id
UNION ALL SELECT 'servicos com duracao <= 0', count(*) FROM services_service WHERE duracao <= 0
UNION ALL SELECT 'barbearias com fechamento <= abertura', count(*) FROM barbershops_barbershop WHERE horario_fechamento <= horario_abertura
UNION ALL SELECT 'e-mails duplicados ignorando maiusculas', count(*) FROM (SELECT lower(email) FROM accounts_user GROUP BY 1 HAVING count(*)>1) d
UNION ALL SELECT 'barbearias sem admin ativo', count(*) FROM barbershops_barbershop s WHERE NOT EXISTS (SELECT 1 FROM accounts_user u WHERE u.barbershop_id=s.id AND u.tipo_perfil='admin' AND u.is_active)
UNION ALL SELECT 'sobreposicoes ativas do mesmo barbeiro', count(*) FROM appointments_appointment a JOIN services_service sa ON sa.id=a.servico_id JOIN appointments_appointment b ON b.barbeiro_id=a.barbeiro_id AND b.id>a.id JOIN services_service sb ON sb.id=b.servico_id WHERE a.status<>'cancelado' AND b.status<>'cancelado' AND a.data_hora < b.data_hora + make_interval(mins=>sb.duracao) AND b.data_hora < a.data_hora + make_interval(mins=>sa.duracao)
UNION ALL SELECT 'tokens emitidos (outstanding)', count(*) FROM token_blacklist_outstandingtoken
UNION ALL SELECT 'tokens expirados ainda na tabela', count(*) FROM token_blacklist_outstandingtoken WHERE expires_at < now()
UNION ALL SELECT 'migracoes aplicadas (apps do projeto)', count(*) FROM django_migrations WHERE app IN ('accounts','barbershops','services','appointments');
SELECT 'ultima migracao ' || app || ': ' || max(name) FROM django_migrations WHERE app IN ('accounts','barbershops','services','appointments') GROUP BY app ORDER BY app;
SELECT 'collation do banco: registrada=' || coalesce(datcollversion,'?') || ' sistema=' || coalesce(pg_database_collation_actual_version(oid),'?') FROM pg_database WHERE datname=current_database();
SELECT 'versao do servidor: ' || current_setting('server_version');
ROLLBACK;
