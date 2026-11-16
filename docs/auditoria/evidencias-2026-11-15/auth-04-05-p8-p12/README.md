# Aplicação da accounts.0006 no banco real (P8) e etapas P9 a P12 (15/11/2026)

O registro está na seção 34 de [`docs/AUDITORIA_BARBERPRO.md`](../../../AUDITORIA_BARBERPRO.md). As autorizações vieram em duas mensagens separadas:

1. **P8:** pré-verificações, backup imediato e aplicação **só** da `accounts.0006` no banco real.
2. **P9, P10, P11 e P12:**
   - P9: pós-verificação somente leitura;
   - P10: subir a aplicação;
   - P11: testes **somente de leitura** (sem POST, PUT, PATCH ou DELETE e sem login);
   - P12: este registro.

**A única escrita no banco real foi a própria `accounts.0006`, na P8.** Os contadores de inserção, atualização e exclusão do PostgreSQL ficaram idênticos desde o fim da P9 até o fim da P11 (`saidas/p9/estatisticas-s0-depois-p9.txt` × `saidas/p10/…s1…`, `saidas/p11/…s2…` e `…s3-final.txt`).

Nenhum arquivo desta pasta contém senha, token, string de conexão, nome ou e-mail real: só contagens, ids, definições de restrições e e-mails fictícios (`.test`). O backup e o seu índice **não** estão aqui; ficam só no diretório privado.

## Recursos

| Recurso | Onde | Situação |
|---|---|---|
| Banco real | `barbershop_db`, PostgreSQL 18.3, `::1:5432`, usuário esperado, `pt_BR.UTF-8` (libc, versão de ordenação 2.43) | `accounts.0006` **aplicada** às 22:56:22 |
| Backup da P8 | `/home/lucasrafael/backups/barberpro/accounts0006_p8_20261115_225552/barbershop_db_20261115_225552_p8_antes_accounts0006.dump` (63.004 bytes, arquivo 0600, diretório 0700; SHA-256 `5a4c028b39b4f2c4274e24042b47e863ca9fd7318a17c376453ab9ceed513279`) | **Preservado** |
| Registro privado da P8 | O mesmo diretório, `registro-p8/` (0700, arquivos 0600). As cópias estão em `saidas/p8/` e `scripts/` | Preservado |
| Backups anteriores | `accounts0006_20261115_224006/` (ensaio) e `barbershop_db_20261113_220432.dump` | Intactos (hash conferido) |
| Aplicação | Backend `runserver` em `127.0.0.1:8000` e frontend Vite em `localhost:5173`, iniciados às 23:01 pelo procedimento do README, sem `migrate` e sem `npm install` | **No ar** ao fim da P12 |

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `saidas/p8/a-pre-verificacoes.txt` e `a3`…`a6` | P8, etapa A: identidade, código idêntico ao do ensaio, pré-verificação do plano, regra exata, contagens e plano de migrações. Tudo comparado com a P2 do ensaio, **sem divergências** |
| `saidas/p8/b-backup.txt`, `b-contagens-depois.txt` | P8, etapa B: `pg_dump -Fc`, tamanho, permissões, SHA-256, `pg_restore --list`, origem, tabelas e contagens antes e depois |
| `saidas/p8/c-migracao.txt` | P8, etapa C: checagens na própria conexão da migração (identidade, `lock_timeout=5s`, nenhuma outra sessão ou trava, plano = só a 0006) e a saída do `migrate accounts 0006` |
| `saidas/p8/hashes-codigo-agora.txt` | Os 107 arquivos do backend, idênticos por SHA-256 aos do ensaio |
| `saidas/p9/` | P9: identidade, `02-pos-verificacao`, regra exata, contagens, `showmigrations`, `migrate --plan`, `migrate --check` e a linha de base dos contadores de escrita |
| `saidas/p10/` | P10: código comparado com o retrato da P0 (199 arquivos, 0 diferenças), análise de escrita automática na inicialização, logs do backend e do frontend e contadores depois de subir |
| `saidas/p11/` | P11: 19 pedidos HTTP (GET e OPTIONS, sem login), 7 verificações internas em sessão somente leitura e contadores depois dos testes e no fim |
| `scripts/` | Todos os scripts desta etapa. Os do plano (`com_credenciais_da_app.py`, `01/02/03-*.sql`) estão em `../auth-04-05-revisao-e-plano/`, e os da regra exata e da identidade em `../auth-04-05-p0-p7/scripts/`. Nenhum deles foi alterado |
