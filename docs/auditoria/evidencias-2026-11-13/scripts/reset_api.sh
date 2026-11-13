#!/bin/bash
# Restaura o banco descartável a partir do snapshot e reinicia a API isolada (porta 8765).
S=<scratch>
if [ -f $S/api.pid ]; then kill $(cat $S/api.pid) 2>/dev/null; sleep 1; fi
docker exec barberpro_auditoria_pg16 sh -c "dropdb -U audit --force audit_db && createdb -U audit audit_db"
docker exec -i barberpro_auditoria_pg16 pg_restore -U audit -d audit_db < $S/seed.dump
cd ~/arquivos_faculdade/saas_barbearia
PYTHONPATH=$S/audit_pkg nohup venv312/bin/python manage.py runserver 127.0.0.1:8765 --noreload --settings=audit_server_settings >> $S/logs/api-isolada.log 2>&1 &
echo $! > $S/api.pid
sleep 3
curl -s -o /dev/null -w "api=%{http_code}\n" http://127.0.0.1:8765/api/v1/services/
