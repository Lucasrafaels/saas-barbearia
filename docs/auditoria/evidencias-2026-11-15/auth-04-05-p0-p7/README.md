# Execução de P0 a P7 do plano da accounts.0006 (15/11/2026)

O dono autorizou executar **só** as etapas P0 a P7 do plano da seção 32 de [`docs/AUDITORIA_BARBERPRO.md`](../../../AUDITORIA_BARBERPRO.md). O registro está na seção 33. **P8 a P12 não foram executadas, e o banco real não recebeu nenhuma escrita:**

- toda sessão nele foi aberta com `default_transaction_read_only=on`;
- cada consulta rodou em `BEGIN TRANSACTION READ ONLY` … `ROLLBACK`;
- o `pg_dump` também rodou em sessão somente leitura;
- a conferência final mostra o banco idêntico ao do início.

## Recursos

| Recurso | Onde | Situação |
|---|---|---|
| Banco real | `barbershop_db`, PostgreSQL 18.3, `::1:5432`, usuário esperado, `pt_BR.UTF-8` (libc, versão de ordenação 2.43) | Só leitura |
| Backup novo | `/home/lucasrafael/backups/barberpro/accounts0006_20261115_224006/barbershop_db_20261115_224006_antes_accounts0006.dump` (63.004 bytes, 0600; SHA-256 `5eb831d6b973bd82337d3936efd1b8ef707329cb7e2f2f9f2707b31bbc21af95`) | **Preservado** |
| Retrato do código | O mesmo diretório, `codigo_20261115_224006.tar.gz` (349.115 bytes, 0600; SHA-256 `82793c83…62b1`), sem `.env*` | **Preservado** |
| Backup de 13/11 | `/home/lucasrafael/backups/barberpro/barbershop_db_20261113_220432.dump` | Intacto (hash conferido) |
| PostgreSQL descartável | `initdb --locale=pt_BR.UTF-8 --locale-provider=libc`, 18.3, glibc 2.44, só `127.0.0.1:55432`, no diretório temporário da sessão, com marca de identidade | **Apagado** depois da conferência |
| Cópia do código | Backend copiado (107 arquivos idênticos por hash), sem `.env`, no diretório temporário | **Apagada** |
| API do ensaio | `127.0.0.1:8899`, `SECRET_KEY` aleatória, e-mail em arquivo local | Encerrada |

Nenhum arquivo desta pasta contém senha, token, string de conexão, nome ou e-mail real: só contagens, ids e e-mails fictícios dos testes. O dump e o índice do backup **não** foram copiados para cá; estão só no diretório privado do backup.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `saidas/p0.txt`, `hashes-copia.txt`, `git-status-antes.txt` | P0: diretório do backup, cópia do código e retrato. Inclui o problema do primeiro retrato (seção 33.3) |
| `saidas/p1.txt` | P1: disco, servidor, ferramentas, locale, portas e identidade configurada antes de conectar |
| `saidas/prova-equivalencia-sql-python.txt` | O SQL da regra exata contra o Python em 3.336.202 casos, no banco descartável: 0 divergências |
| `saidas/p2*.txt` | P2 no banco real: identidade, pré-verificação do plano, regra exata, contagens e migrações |
| `saidas/p3-p4.txt`, `p4-contagens-depois.txt`, `backup/backup-metadados.txt` | P3 e P4: `pg_dump`, tamanho, SHA-256, `pg_restore --list`, tabelas presentes, contagens antes e depois e comparação com o backup de 13/11 |
| `saidas/descartavel-ambiente.txt`, `p5*.txt` | P5: ambiente descartável, restauração, isolamento, contagens, estrutura e pré-verificações na cópia |
| `saidas/p6.txt` | P6: migração, pós-verificação, `migrate --check`, `makemigrations --check`, reversão e reaplicação na cópia |
| `saidas/p7-fumaca.txt`, `p7-runserver.txt` | P7: os 12 testes do roteiro do plano e os 28 do complemento; log da API do ensaio (0 respostas 500) |
| `saidas/p-final-*.txt` | Conferência final no banco real, só leitura: idêntico à P2 |
| `saidas/limpeza.txt` | A limpeza, com a identidade de cada recurso conferida antes |
| `scripts/` | Todos os scripts desta execução. Os do plano (`com_credenciais_da_app.py`, `01/02/03-*.sql`, `ensaio_settings.py`, `fumaca.py`) estão em `../auth-04-05-revisao-e-plano/` e não foram alterados |
