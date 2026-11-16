# Evidências da investigação do AUTH-04 e do AUTH-05 (15/11/2026)

Esta etapa foi **só diagnóstico e plano**. A análise está na seção 28 de [`docs/AUDITORIA_BARBERPRO.md`](../../../AUDITORIA_BARBERPRO.md). As pastas anteriores (`../ten-03/` e `../ten-03-mitigacao-d/`) não foram alteradas.

**Nenhum código foi alterado, nenhuma migração foi criada ou executada, e o banco real não foi consultado.** AUTH-04 e AUTH-05 continuam abertos.

## Como foi verificado

- **Código:** o atual, com a mitigação D do TEN-03, sem nenhuma mudança.
- **Banco:** um **PostgreSQL 18.3 descartável**, criado com `initdb` no diretório temporário e acessado só por TCP em `127.0.0.1:55432`. Ele já foi apagado. Foram usados dois bancos:
  - `a45_db`: API e demonstrações HTTP;
  - `a45_lab`: scripts no processo, conjunto de dados que imita estados antigos e testes de DDL em transação desfeita.
- **Bancos não usados:** o `barbershop_db` real e o PostgreSQL do Docker (porta 5433).
- **API de laboratório:** `runserver` em `127.0.0.1:8801`, com `DEBUG=False`. As settings descartáveis (`scripts/a45_settings.py`) mudam só:
  - o banco;
  - a mídia;
  - o backend de e-mail, que grava arquivos no diretório temporário para seguir os tokens de recuperação;
  - os limites de taxa, relaxados **só aqui**, porque esta etapa investiga o tratamento do e-mail, não a mitigação D.
- **Dados:** todos fictícios, em domínios `.test`.
  - As senhas do seed, os tokens de acesso e os e-mails de recuperação ficaram só no diretório temporário e foram apagados.
  - Os JSONs registram para qual conta cada token foi gerado (o `uid` decodificado) e o destinatário, **nunca o token**.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `demonstracoes/auth04-demonstracao.json`, `auth04-console.txt` | AUTH-04, passos A1 a A9: a variação de caixa desvia a recuperação, o uso do token troca a senha da conta do terceiro, o efeito da ordem pelo nome, a variação criada por um admin e a conta inativa. Inclui a conferência "token × destinatário" |
| `demonstracoes/auth05-matriz.json`, `auth05-console.txt` | AUTH-05: 3 fluxos de escrita × 10 variações (status, valor gravado, duplicata), login com a senha correta × 5 variações e recuperação × 4 variações |
| `demonstracoes/auth05-login-apos-cadastro.json` | O fluxo da tela de cadastro: cadastrar e entrar com o mesmo texto digitado |
| `demonstracoes/auth05-concorrencia.json` | 15 pares de pedidos simultâneos com o mesmo e-mail: cadastro, criação e troca |
| `demonstracoes/auth05-admin-e-unicode.json` | O formulário do Django Admin e o `full_clean`, o `EmailValidator` com endereços não ASCII, e o `str.lower()` do Python × o `lower()` do PostgreSQL |
| `sql/verificacao-colisoes-somente-leitura.sql` | **A consulta para o banco real**, só de leitura (`BEGIN TRANSACTION READ ONLY` … `ROLLBACK`). **Não executada no banco real** |
| `sql/colisoes-saida-banco-ficticio.txt` | O que essa consulta retorna, rodada no banco fictício `a45_lab` |
| `sql/laboratorio-ddl-em-transacao-desfeita.sql`, `laboratorio-ddl-saida.txt` | O que uma futura migração encontraria (índice, conversão e `CHECK`), com e sem colisões, sempre em transação desfeita |
| `api/runserver-8801.txt` | Log da API de laboratório, com os rastreamentos dos `IntegrityError` (500) |
| `scripts/` | Settings, seed, servidor, as demonstrações e o gerador do conjunto que imita dados antigos |

## Como reproduzir

1. Crie um PostgreSQL 18 descartável em `127.0.0.1:55432`, com os bancos `a45_db` e `a45_lab`, e aplique as migrações com `A45_DB=<banco> … migrate --settings=a45_settings`.
2. Ajuste os caminhos em `scripts/a45_servidor.sh` e rode-o **sozinho**.
3. Rode, nesta ordem:
   1. `a45_auth04.py`;
   2. `a45_auth05_matriz.py`;
   3. `a45_login_apos_cadastro.py`;
   4. `a45_concorrencia.py`.

   Os argumentos estão no cabeçalho de cada script.
4. Com `A45_DB=a45_lab`, rode `a45_admin_e_unicode.py` e `a45_dados_legados.py`. Depois rode `psql -f sql/verificacao-colisoes-somente-leitura.sql` e `psql -f sql/laboratorio-ddl-em-transacao-desfeita.sql` no `a45_lab`.

## Reprodução manual mínima do AUTH-04

1. Conta da vítima: `cliente.b@beta.test`, nome "Clara".
2. Um anônimo cadastra `Cliente.B@beta.test`, com nome "Aaron".
3. A vítima pede `POST /api/v1/auth/password/reset/` `{"email": "cliente.b@beta.test"}`.
4. O e-mail sai para `Cliente.B@beta.test` com o `uid` da conta do Aaron.
5. Ao usar esse token, a senha trocada é a do Aaron. A da vítima não muda.
