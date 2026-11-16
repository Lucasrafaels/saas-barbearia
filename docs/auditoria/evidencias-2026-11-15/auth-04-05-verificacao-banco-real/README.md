# Verificação de colisões no banco real, somente leitura (15/11/2026)

O dono autorizou, só para esta etapa, rodar a consulta de colisões do AUTH-04 e do AUTH-05 no banco real. A autorização não inclui implementação, escrita, migração nem nenhuma outra operação. A análise está na seção 29 de [`docs/AUDITORIA_BARBERPRO.md`](../../../AUDITORIA_BARBERPRO.md). A pasta da investigação ([`../auth-04-05/`](../auth-04-05/README.md)) não foi alterada.

## O que foi executado

- **Arquivo autorizado:** `../auth-04-05/sql/verificacao-colisoes-somente-leitura.sql`. Foi lido por inteiro, e o hash conferia com o da investigação. Contém `\set` e `\echo` (só do psql), `BEGIN TRANSACTION READ ONLY`, `SET LOCAL statement_timeout`, só `SELECT` e `ROLLBACK`. Não há escrita nem mudança de configuração persistente.
- **Executada uma cópia sem o bloco 3:** `consulta-executada-sem-bloco-3.sql`. O bloco 3 só lê, mas devolve nomes e e-mails, e a autorização proíbe consultas que os exponham. A diferença para o arquivo autorizado está em `diferenca-para-o-arquivo-autorizado.txt`: só a remoção desse bloco e um comentário de cabeçalho.
- **Conexão** (`executar_somente_leitura.py`):
  - as credenciais vêm das settings da aplicação e vão para o psql por variáveis de ambiente do processo filho, nunca impressas;
  - o script se recusa a rodar se o banco não for `barbershop_db`, local, na porta 5432;
  - a sessão abre com `default_transaction_read_only=on`, `statement_timeout=30s`, `lock_timeout=5s` e `idle_in_transaction_session_timeout=60s`.
- **Duas conexões:** uma para identificar o banco (`identidade-do-banco.txt`) e outra para a consulta (`saida-da-consulta.txt`).
- **Não usados:** o PostgreSQL do Docker (porta 5433) e o banco antigo `barbershop`.

## Resultado

| Item | Valor |
|---|---|
| Banco | `barbershop_db`, PostgreSQL 18.3, `::1` (localhost), porta 5432; `datcollate` e `datctype` `pt_BR.UTF-8`, provedor libc |
| Contas verificadas | 8 |
| Contas que seriam normalizadas | 0 |
| Com espaços nas pontas | 0 |
| Com caracteres fora do ASCII | 0 |
| Grupos de colisão | **0** (nenhum id a decidir) |
| Fim da transação | `ROLLBACK`; psql com código 0 |

Os arquivos desta pasta não têm nomes, e-mails, senhas nem tokens. O aviso de versão de ordenação na saída é o DB-02, já registrado, e não foi tratado.
