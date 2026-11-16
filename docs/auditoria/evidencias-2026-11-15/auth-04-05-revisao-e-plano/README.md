# Revisão final do AUTH-04 e do AUTH-05 e plano de implantação da accounts.0006 (15/11/2026)

Esta etapa foi **só leitura, análise e planejamento**. A revisão e o plano estão na seção 32 de [`docs/AUDITORIA_BARBERPRO.md`](../../../AUDITORIA_BARBERPRO.md). As pastas anteriores não foram alteradas.

**O que não foi feito:**

- nenhuma conexão ao banco real;
- nenhuma migração aplicada;
- nenhum código, teste ou migração alterado;
- nenhum dos comandos do plano executado.

Os arquivos de `sql/` e `scripts/` **ainda não foram executados**. Só passaram por análise de sintaxe Python (`ast.parse`). O plano manda rodar cada um primeiro na cópia descartável (ensaio) e só depois, com autorização, no banco real.

## Arquivos

| Arquivo | Uso no plano (seção 32) | Leitura ou escrita | Banco |
|---|---|---|---|
| `testes/reconfirmacao-sqlite.txt` | Revisão: suíte completa (521 OK, 14 pulados), `makemigrations --check` e `check`, reexecutados nesta etapa | Testes em banco em memória | SQLite em memória (nunca o real) |
| `scripts/com_credenciais_da_app.py` | P2, P3, P9: roda `psql`, `pg_dump` ou `pg_restore --list` com as credenciais da aplicação, sem imprimi-las. Recusa se o banco não for o `barbershop_db` local na porta 5432. `--somente-leitura` liga `default_transaction_read_only` e limites de tempo | Leitura (o `pg_dump` grava só o arquivo de backup) | Real |
| `sql/01-pre-verificacao-somente-leitura.sql` | P2 e P5: identidade, migrações, restrições, a regra exata do `CHECK` futuro (só ids), sessões e travas | Leitura (`READ ONLY` + `ROLLBACK`) | Cópia, depois real |
| `sql/02-pos-verificacao-somente-leitura.sql` | P6 e P9: `accounts.0006` registrada, `CHECK` validado, índice único válido, nenhuma conta fora da regra | Leitura | Cópia, depois real |
| `sql/03-contagem-de-linhas-somente-leitura.sql` | P2 e P5: contagens para comparar o banco real com a cópia restaurada | Leitura | Real e cópia |
| `scripts/ensaio_settings.py` | P6 e P7: a aplicação apontando para a cópia restaurada no PostgreSQL descartável, com o e-mail em `locmem` (nada sai) | Escrita só na cópia | Descartável |
| `scripts/fumaca.py` | P7 (modo `completo`, só na cópia) e P11 (modo `sem-escrita`, no real) | `completo`: escrita na cópia. `sem-escrita`: nenhum pedido grava no banco | Cópia ou real |
