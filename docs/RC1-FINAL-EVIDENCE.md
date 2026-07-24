# RC1 — Matriz final de evidências

Data da consolidação: 24 de julho de 2026.

| Gate | Evidência | Estado |
| --- | --- | --- |
| Frontend lint | `npm run lint` | Aprovado localmente |
| Build e render SSR | `npm test` | Aprovado localmente |
| Verificador de release | `npm run release:check` | Aprovado localmente |
| Dependências de produção | `npm audit --omit=dev --audit-level=high` | Aprovado localmente, zero vulnerabilidades |
| Sintaxe da API e testes | `python -m compileall` | Aprovado localmente |
| Testes Python | `pytest services/api/tests` no CI | Configurado; execução remota ainda não observada |
| Migrações PostgreSQL | `0001`–`0009` aplicadas no RC E2E | Configurado; execução remota ainda não observada |
| Jornada RC | exchange, 2FA, tendências, séries, operações, custos e refresh | Configurada; execução remota ainda não observada |
| Container API | build imutável no CI | Configurado |
| Compose produção | validação sem criação automática de schema | Configurado |
| CodeQL | workflow dedicado | Configurado |
| Publicação Sites | registro da conta e versão | Bloqueado por identidade da conta |

## Cobertura funcional consolidada

- Identidade do workspace trocada no servidor por sessão curta da API.
- RBAC e isolamento por organização.
- Conteúdo, moderação, fontes e verificação factual.
- Mídia licenciada, narração, legendas, cenas, render e editor visual.
- Aprovação humana, calendário, publicação e tratamento de falhas.
- Métricas, experimentos, custos, operações e auditoria.
- Recuperação por token, adaptador Resend, TOTP e códigos de recuperação.
- Tendências de fontes autorizadas e séries editoriais.
- Backups, restore protegido, readiness e runbook de rollback.

## Integrações condicionais

Não são representadas como operacionais sem credenciais e aprovação:

- TikTok exige aplicativo auditado, OAuth e escopos válidos.
- Resend exige chave e remetente/domínio verificado.
- Fontes de tendência exigem autorização e contrato próprios.
- Sites exige identidade válida da conta e registro do projeto.

## Decisão atual

**RC tecnicamente preparada, promoção condicionada.**

A promoção para produção permanece bloqueada até a mesma revisão obter todos os
gates remotos verdes e as integrações necessárias ao ambiente serem validadas.
Essa decisão evita declarar produção com evidências ainda não observadas.
