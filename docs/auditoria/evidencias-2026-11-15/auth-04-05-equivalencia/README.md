# Equivalência Python × PostgreSQL antes de implementar o AUTH-04 e o AUTH-05 (15/11/2026)

A etapa de implementação do AUTH-04 e do AUTH-05 exigia confirmar, **antes de criar as restrições**, que a normalização do e-mail em Python e as funções SQL do banco (`lower`, `btrim`) são equivalentes para **todos os caracteres aceitos**, na ordenação do banco real (`pt_BR.UTF-8`). Não são. Por isso a implementação foi **interrompida antes de qualquer alteração de código** (seção 30 de [`docs/AUDITORIA_BARBERPRO.md`](../../../AUDITORIA_BARBERPRO.md)).

## Como foi verificado

- **Banco:** um **PostgreSQL 18.3 descartável**, criado com `initdb --locale=pt_BR.UTF-8 --locale-provider=libc` (glibc 2.44, como o sistema do banco real), só TCP em `127.0.0.1:55432`. Já foi apagado.
- **Bancos não usados:** o banco real e o do Docker.
- **Abrangência:** todos os 1.112.063 pontos de código (U+0001 a U+10FFFF, sem os substitutos) passaram por:
  - `str.lower()` (Python 3.12, Unicode 15.0) × `lower()` do PostgreSQL;
  - o valor que o Python gravaria × o `lower()` do PostgreSQL sobre ele, que é o que um `CHECK (email = lower(email))` exigiria;
  - `str.strip()` e o `trim_whitespace` do DRF × `btrim()` × a classe `\s` do PostgreSQL;
  - a aceitação pelo `EmailValidator` do Django.
- **Frontend:** o esquema `z.string().trim().email()` do zod 3.25.76, o mesmo de todas as telas que enviam e-mail, e o `String.prototype.trim()` do JavaScript, executados com o `node` no `node_modules` do projeto. Nenhum arquivo do frontend foi alterado.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `resumo.txt` | O resultado em texto |
| `equivalencia-python-postgresql-pt_BR.json` | Resultado completo: banco, versões, divergências do `lower()` com amostras, conjuntos de espaços, invisíveis aceitos e a verificação da alternativa ASCII |
| `frontend-zod-e-trim.json` | O que o formulário do frontend aceita e o que o `trim()` do JavaScript remove |
| `scripts/equivalencia_python_postgresql.py`, `scripts/frontend_zod_email.mjs` | Os dois verificadores |

## Resultado

| Verificação | Resultado |
|---|---|
| `lower()` Python × PostgreSQL | **56** pontos de código divergem, todos aceitos pelo `EmailValidator` no domínio: `İ` (U+0130) e letras novas do Unicode 16, que a glibc 2.44 conhece e o Python 3.12 não. **No ASCII: 0** |
| E-mails aceitos que um `CHECK (email = lower(email))` recusaria | **55** |
| Espaços externos | Python e DRF removem 29 pontos; `btrim()` remove só U+0020; `\s` (pt_BR) cobre 21; o `trim()` do JavaScript remove 25 (inclui U+FEFF, que o Python não remove) |
| Invisíveis | O `EmailValidator` aceita, pelo caminho IDNA, U+00AD, U+034F, U+180B, U+200B a U+200D, U+2060, U+FE00, U+FE0F e U+FEFF no meio ou no fim do domínio (20 de 30 posições), e nenhuma normalização os remove |
| Frontend | Só aceita e-mails ASCII. Recusa acentos, `İ`, invisíveis e Unicode 16. Aceita punycode (`xn--…`) |
| Alternativa ASCII imprimível (U+0021 a U+007E) | `lower()` idêntico; `chr(c) ~ '^[!-~]$'` coincide exatamente com 33 ≤ c ≤ 126 em todos os pontos de código. **Equivalência garantida** |
