# Evidências da correção do AUTH-04 e do AUTH-05 (15/11/2026)

Esta etapa implementa a regra única do e-mail de login, aprovada na seção 30, e a migração `accounts.0006`. A análise está na seção 31 de [`docs/AUDITORIA_BARBERPRO.md`](../../../AUDITORIA_BARBERPRO.md).

A regra:

- tirar os espaços externos com a semântica de `str.strip()`;
- aceitar só ASCII imprimível (U+0021 a U+007E), checado **antes** de converter;
- converter o endereço inteiro para minúsculas.

O banco garante a regra com `CHECK (email = lower(email) AND email ~ '^[!-~]+$')` e `UNIQUE (LOWER(email))`.

As pastas anteriores (`ten-03`, `ten-03-mitigacao-d`, `auth-04-05`, `auth-04-05-verificacao-banco-real` e `auth-04-05-equivalencia`) não foram alteradas.

**Restrições cumpridas:**

- o banco real não foi acessado nesta etapa;
- a migração não foi aplicada nele;
- não houve REINDEX, deploy nem commit.

## Como foi verificado

- **Banco:** um **PostgreSQL 18.3 descartável**, criado com `initdb --locale=pt_BR.UTF-8 --locale-provider=libc`, na glibc 2.44. É a mesma ordenação e o mesmo provedor do banco real, e não `C.UTF-8`. Ficou só TCP em `127.0.0.1:55432` e já foi apagado (`testes/ambiente-postgresql.txt`).
- **Bancos não usados:** o banco real, o Docker (porta 5433) e o antigo `barbershop`.
- **Código anterior:** a árvore do início desta etapa, reconstruída fora do projeto a partir da cópia anterior à mitigação D mais o patch da mitigação D. Os 137 arquivos de código conferem com os hashes registrados no início.
- **APIs de laboratório:** `runserver` sobre bancos descartáveis, com os limites relaxados só ali:

  | Porta | Código | `DEBUG` |
  |---|---|---|
  | 8811 | corrigido | `False` |
  | 8812 | corrigido | `True` |
  | 8813 | anterior | `False` |

- **Demonstrações:** as mesmas da investigação (seção 28), com os scripts `h_*.py`.
- **Dados:** todos fictícios, em domínios `.test`. As senhas e tokens do seed e os e-mails de recuperação ficaram só no diretório temporário e foram apagados. Nenhum arquivo desta pasta contém senha, hash, token, `SECRET_KEY` ou string de conexão.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `diff/diff-somente-auth04-auth05.patch` | As alterações desta etapa, contra a árvore do início |
| `testes/suite-sqlite.txt` | Suíte completa: 521 testes, 14 pulados, os que exigem PostgreSQL |
| `testes/suite-postgresql18-ptbr.txt` | Suíte completa no PG 18.3 pt_BR: 521 OK |
| `testes/suite-postgresql18-ptbr-debug-false.txt` | Idem, com `DEBUG=False` também na importação das settings |
| `testes/testes-novos-postgresql18-ptbr.txt` | Os 41 testes novos, um por linha, no PG pt_BR, sem nenhum pulado |
| `testes/novos-isolamento-limites-postgresql18-ptbr-debug-mode.txt` | Novos, isolamento, permissões, PER-13, SEC-10, TEN-02, renderizadores, mitigação D e autenticação, com `DEBUG=True` (211 testes) |
| `testes/testes-novos-sqlite-debug-mode.txt` | Os novos no SQLite com `DEBUG=True` |
| `testes/testes-novos-codigo-anterior.txt` | Os novos no código anterior: falham na importação, porque `accounts.emails` não existia |
| `testes/django-check-migracoes.txt` | `check`, `makemigrations --check`, `migrate --plan` e `check --deploy` |
| `testes/frontend-testes-tipos-lint-build.txt` | `npm test` (45), `tsc -b`, ESLint e build |
| `testes/ambiente-postgresql.txt` | Versão, ordenação, provedor e `collversion` do banco descartável |
| `testes/django-admin-mensagens.txt`, `django-admin-mensagens-depois.txt` | O problema achado no Django Admin (dois erros, um com o nome interno da restrição) e o resultado depois do ajuste |
| `migracao/validacao-migracao-postgresql18-ptbr.txt` | A `accounts.0006` pelo comando real `migrate`, no PG pt_BR, nos cenários abaixo |
| `api/resumo-matriz-antes-e-depois.txt` | AUTH-05: 3 fluxos de escrita × 10 variações, mais login e recuperação, código anterior × corrigido (`DEBUG` True e False) |
| `api/auth04_88xx.json`, `console_auth04_88xx.txt` | AUTH-04, passos A1 a A9, nas três APIs |
| `api/concorrencia_88xx.json`, `console_concorrencia_88xx.txt` | 15 pares de pedidos simultâneos por API |
| `api/login_apos_cadastro_88xx.json` | Cadastro seguido de login com o mesmo texto digitado |
| `api/matriz_88xx.json`, `console_matriz_88xx.txt` | A matriz completa |
| `api/logs-runserver-3-instancias.tar.gz` | Logs das três APIs: os `IntegrityError` só aparecem na anterior |
| `scripts/` | Settings descartáveis, seed, servidores, demonstrações, dados antigos fictícios e o roteiro de validação da migração |

**Cenários da validação da migração** (`migracao/validacao-migracao-postgresql18-ptbr.txt`):

1. dados antigos gravados com o código anterior;
2. interrupção com colisões e e-mail fora da regra, mostrando só ids;
3. aplicação depois da simulação da decisão do dono;
4. reversão;
5. conversão de dados válidos;
6. o banco recusando, por fora da aplicação, variação de caixa, espaço, não ASCII e duplicata;
7. `sqlmigrate` no PostgreSQL.

## Como reproduzir

1. **Testes:** `venv/bin/python manage.py test accounts.test_auth04_auth05 --settings=config.test_settings`. No PostgreSQL, use as settings `scripts/ptbr_test_settings.py` num cluster criado com `initdb --locale=pt_BR.UTF-8 --locale-provider=libc`.
2. **Demonstrações:**
   1. Ajuste os caminhos em `scripts/h_servidores.sh` e rode-o **sozinho**.
   2. Para cada porta, rode com `H_BASE=http://127.0.0.1:<porta>` e `H_DB=<banco>`, nesta ordem, com os argumentos do cabeçalho de cada script:
      1. `h_auth05_matriz.py`;
      2. `h_login_apos_cadastro.py`;
      3. `h_concorrencia.py`;
      4. `h_auth04.py`.

   Rode a concorrência **antes** do AUTH-04. No código corrigido, a demonstração do AUTH-04 troca a senha da própria vítima, o que é o comportamento correto, e isso revoga o token que a corrida de troca de e-mail usa.
3. **Migração:** `bash scripts/m_validar_migracao.sh`, com a árvore anterior em `codigo-anterior/`.
