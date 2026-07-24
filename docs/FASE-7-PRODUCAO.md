# Fase 7 — escala e produção

Esta fase transforma o DarkTTK em uma base operável: controles de segurança no caminho de cada requisição, prontidão verificável, métricas, registro de falhas, orçamento, backup, recuperação, auditoria verificável, CI/CD e teste de carga.

## O que foi implementado

- Rate limit distribuído via Redis, com janela separada para autenticação e fallback local em degradação.
- Resolução de IP sem confiar em `X-Forwarded-For` por padrão; proxies só são considerados quando `TRUSTED_PROXY_HOPS` é configurado.
- Limite de payload, CSP restritiva, HSTS em produção, `no-store`, `nosniff`, política de referer e política de permissões.
- Falha imediata no boot de produção quando segredos/métricas não estão configurados ou criação automática de schema está ativa.
- `/health/live` para processo, `/health/ready` para dependências e `/metrics` protegido por token em produção.
- Registro sanitizado e agrupado de erros operacionais, sem stack trace nem segredo persistido.
- Ledger de custos idempotente, orçamento mensal, alerta e opção de bloqueio rígido.
- Checkpoints SHA-256 da trilha de auditoria, com endpoint de verificação posterior.
- Registro persistente de execuções de backup e status consolidado da operação.
- Tela responsiva **Operações** para readiness, incidentes, FinOps, segurança, backup e auditoria.
- Compose de produção com serviços internos sem portas públicas, healthcheck, reinício, filesystem somente leitura e limites.
- CI para frontend, API e imagem; CodeQL `security-extended`; Dependabot semanal.
- Scripts de backup/restore com checksum e confirmação explícita para ambiente isolado.
- Cenário k6 com ramp-up, erro abaixo de 1%, p95 abaixo de 500 ms e p99 abaixo de 1 s.

## Endpoints operacionais

| Endpoint | Finalidade |
| --- | --- |
| `GET /health/live` | Confirma que o processo responde. |
| `GET /health/ready` | Verifica banco e, quando exigido, Redis. |
| `GET /metrics` | Formato Prometheus; token obrigatório em produção. |
| `GET /v1/operations/status` | Consolida readiness funcional do workspace. |
| `GET/PATCH /v1/operations/errors` | Lista e resolve incidentes com ação corretiva. |
| `GET /v1/operations/costs/summary` | Consumo real do mês contra orçamento. |
| `PUT /v1/operations/costs/budget` | Altera limites; admin ou manager. |
| `POST /v1/operations/costs/entries` | Registra custo idempotente por `source_ref`. |
| `GET /v1/operations/audit` | Consulta trilha do workspace. |
| `POST /v1/operations/audit/checkpoints` | Sela novo intervalo de auditoria. |
| `GET /v1/operations/audit/checkpoints/{id}/verify` | Recalcula integridade. |

## Critérios de promoção

Uma versão só pode seguir para produção quando:

1. lint, testes, build e compilação da API passarem;
2. migração `0007_scale_production.sql` for aplicada por job explícito;
3. `APP_ENV=production`, `AUTO_CREATE_SCHEMA=false`, segredos fortes e `METRICS_TOKEN` estiverem configurados;
4. `/health/ready` permanecer estável;
5. backup e restore forem testados em ambiente isolado;
6. teste k6 atender aos thresholds;
7. não houver erro crítico aberto nem fila `dead_letter` sem ação corretiva;
8. rollback da versão anterior estiver disponível.

## Limites honestos

O dashboard hospedado continua sendo uma demonstração visual e identifica essa origem. Disponibilidade, latência, custos e backups exibidos na prévia não são tratados como telemetria real. O Compose descreve o perfil de execução; o balanceador, o cofre de segredos, o agendador de backup e o armazenamento externo dependem da infraestrutura escolhida.
