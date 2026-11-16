# Evidências da mitigação D do TEN-03 (15/11/2026)

Esta etapa implementa a **mitigação D** do TEN-03: um limite de tentativas específico nos fluxos que consultam a unicidade do e-mail. A análise está na seção 27 de [`docs/AUDITORIA_BARBERPRO.md`](../../../AUDITORIA_BARBERPRO.md). A investigação está na seção 26 e em [`../ten-03/`](../ten-03/README.md). Nenhuma pasta anterior foi alterada.

**O TEN-03 continua aberto.** O limite reduz a velocidade da sondagem, mas não a elimina. A correção definitiva planejada é a C3.

## Como foi verificado

- **Alteração:** `diff/diff-somente-mitigacao-d.patch` traz só esta etapa:
  - **Código:** `accounts/throttles.py` (novo), `accounts/views.py` e `config/settings.py`.
  - **Taxas nas settings de teste:** `config/test_settings.py` e `config/test_postgres_settings.py`.
  - **Teste novo:** `accounts/test_ten03_limites.py`.
  - **Testes antigos:** a taxa nova acrescentada em dois deles.
- **Base da comparação:** a árvore anterior, que já tinha a contenção, o TEN-01, o TEN-02, o `exclude_appointment_id` e o PER-13. Ela foi copiada para fora do projeto, sem comandos destrutivos do Git. Os mesmos testes e a mesma sondagem rodaram nas duas versões.
- **Bancos:** SQLite em memória e um **PostgreSQL 18.3 descartável** (`initdb` no diretório temporário, só TCP em `127.0.0.1:55432`), já apagado.
  - O banco real (`barbershop_db`) e o PostgreSQL do Docker (porta 5433) não foram usados.
  - Nenhuma migração foi criada nem aplicada.
- **API:** quatro instâncias do `runserver`, cada uma com seu banco descartável e **as taxas reais** de cada versão do código, sem relaxar:

  | Porta | Código | `DEBUG` |
  |---|---|---|
  | 8791 | corrigido | `True` |
  | 8792 | corrigido | `False` |
  | 8793 | anterior | `True` |
  | 8794 | anterior | `False` |

- **SQL do servidor:** cada banco rodou com `log_statement = 'all'`, e cada pedido ficou entre dois marcadores no log. O log bruto não foi copiado. Nos JSONs, cada pedido traz o SQL higienizado e o campo `consultou_unicidade`.
- **Tokens:** o seed emitiu os tokens de acesso diretamente (`AccessToken.for_user`), para a sondagem não gastar a cota de login que ela mesma verifica.
- **Dados:** todos fictícios.
  - Domínios `.test`.
  - Faixas de IP reservadas para documentação: `198.51.100.0/24` e `203.0.113.0/24`.
  - Senhas do seed aleatórias, apagadas com o diretório temporário.
  - Nenhum arquivo desta pasta contém senha do seed, hash de senha, token, `SECRET_KEY` ou string de conexão.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `diff/diff-somente-mitigacao-d.patch` | As alterações desta etapa |
| `testes/suite-sqlite.txt`, `suite-postgresql18.txt`, `suite-postgresql18-debug-false.txt` | Suíte completa (480 testes): SQLite, PG 18.3, e PG com `DEBUG=False` também na importação das settings |
| `testes/testes-novos-e-isolamento-postgresql18-debug-mode.txt` | Os 28 testes novos e os de isolamento, permissões, PER-13, SEC-10, TEN-02 e renderizadores (132 no total), com o executor em `--debug-mode` (`DEBUG=True`) |
| `testes/testes-novos-codigo-anterior.txt` | Os testes novos no código anterior: falham na importação, porque `accounts.throttles` não existia |
| `testes/django-check-migracoes.txt` | `check`, `makemigrations --check --dry-run`, `migrate --plan` e `check --deploy` |
| `testes/frontend-testes-tipos-lint-build.txt` | `npm test`, `tsc -b`, ESLint e build (para um diretório temporário). O frontend não foi alterado |
| `api/resumo-antes-e-depois.txt` | Resumo da sondagem por etapa e instância: sequência de status, `Retry-After`, se a unicidade foi consultada e se os 429 de e-mail existente e livre são iguais |
| `api/sondagem_879x_com_sql.json` | Saída bruta de cada instância (98 pedidos), com o SQL do servidor |
| `api/console_879x.txt` | O que a sondagem imprimiu |
| `api/logs-runserver-4-instancias.tar.gz` | Logs de acesso das quatro instâncias |
| `laboratorio/xff-identidade.txt` | A limitação SEC-13: a chave de origem calculada pelo DRF sem `NUM_PROXIES`, para um IP direto e para valores forjados de `X-Forwarded-For` |
| `scripts/` | Settings descartáveis, seed com tokens, servidores, sondagem, resumo e a demonstração do `X-Forwarded-For` |

## Como reproduzir

1. **Testes:**
   - `venv/bin/python manage.py test accounts.test_ten03_limites --settings=config.test_settings`;
   - com `--debug-mode`, para `DEBUG=True`.
2. **Sondagem:**
   1. Crie um PostgreSQL 18 descartável em `127.0.0.1:55432`, com `logging_collector = on`.
   2. Copie a árvore anterior para `codigo-anterior/`.
   3. Ajuste os caminhos absolutos em `scripts/d_servidores.sh` e rode-o **sozinho**. O `pkill -f` do script casa com qualquer linha de comando que contenha o texto do `runserver`.
   4. Para cada porta, rode `python3 -I scripts/d_probe.py http://127.0.0.1:<porta> <banco> <estado.json> <saída.json>`.
   5. Rode `python3 -I scripts/d_resumo.py <pgdata/log/pg.log> <pasta> <resumo.txt>`.

## Reprodução manual mínima

Com um cliente autenticado, envie `PATCH /api/v1/users/<próprio id>/` `{"nome": "", "email": "<qualquer e-mail diferente do atual>"}` 11 vezes:

| Pedido | Corrigido | Anterior |
|---|---|---|
| 1º ao 10º | 400 (a validação responde) | 400 |
| 11º em diante | **429** `{"detail":"Pedido foi limitado. Expected available in 3600 seconds."}`, com `Retry-After`, sem consultar o e-mail | 400 |
