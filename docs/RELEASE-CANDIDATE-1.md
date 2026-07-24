# DarkTTK — Release Candidate 1

## Objetivo

O roadmap funcional terminou na Fase 7. A RC1 é o ciclo de integração e evidência necessário para transformar as fases implementadas em uma versão promovível, sem criar uma fase artificial fora do escopo original.

## Primeiro checkpoint concluído

- Criado exchange server-to-server entre a identidade autenticada do workspace e a API.
- Assinatura HMAC-SHA256 com validade máxima de 60 segundos.
- Segredo compartilhado mantido apenas nos ambientes de servidor.
- Provisionamento idempotente de usuário, organização, papel administrador e dados iniciais.
- Access e refresh tokens continuam sendo geridos pela API; o frontend não persiste token no navegador.
- Dashboard passa a consumir contagens reais quando `DARKTTK_API_URL` e `WORKSPACE_IDENTITY_SECRET` estão configurados.
- Tela de Operações passa a consumir readiness funcional e orçamento real.
- Falha de integração é mostrada como indisponibilidade; ausência de configuração permanece claramente identificada como demonstração.

## Cobertura auditada

| Área | Estado RC1 | Observação |
| --- | --- | --- |
| Fundação, organizações e RBAC | Implementado | Exchange adiciona a fronteira segura com o frontend hospedado. |
| Conteúdo, moderação e fontes | API implementada | Jornada visual completa ainda precisa consumir os endpoints reais. |
| Vídeo, mídia, legendas e render | API/worker implementados | Editor visual continua simplificado. |
| Aprovação e calendário | Integrado | Decisões e agendamentos reais passam por rotas server-side e permanecem sujeitos ao RBAC da API. |
| TikTok | Adaptador oficial + mock | Credenciais, escopos e aprovação externa continuam obrigatórios. |
| Métricas e experimentos | API implementada | Parte dos gráficos da interface ainda é demonstrativa. |
| Operações, custos e auditoria | Integrado para leitura | Mutações administrativas ainda precisam de ações server-side. |
| Recuperação de senha | Núcleo implementado | Token, expiração e revogação estão prontos; falta conectar um canal real de entrega. |
| 2FA | Implementado | TOTP, replay protection e códigos de recuperação; workspace mantém autenticação da plataforma. |
| Tendências autorizadas | Arquitetura pendente | Não deve usar scraping incompatível com termos. |
| Séries de conteúdo | Pendente | Entidades e telas ainda não implementadas. |
| E2E real | Pipeline criado | CI sobe PostgreSQL, Redis e API e valida exchange, dashboard, operações, custos e rotação de token. |

## Configuração

Os dois serviços devem receber o mesmo valor forte e aleatório:

```env
WORKSPACE_IDENTITY_SECRET=valor-aleatorio-com-pelo-menos-32-caracteres
```

O frontend também deve receber:

```env
DARKTTK_API_URL=https://api.exemplo.com
```

Nunca exponha `WORKSPACE_IDENTITY_SECRET` como variável pública nem a envie ao navegador.

## Próximo checkpoint

1. Conectar um provedor real para entrega de recuperação.
2. Acompanhar a primeira execução da jornada E2E com PostgreSQL e Redis no CI.
3. Implementar tendências autorizadas, séries e o fechamento do editor visual.
4. Gerar relatório final de promoção e rollback.

## Terceiro checkpoint concluído

- Adaptador real de recuperação por e-mail via Resend, com configuração obrigatória e rollback em falha.
- Regeneração autenticada e auditada de códigos de recuperação 2FA.
- Fontes de tendência autorizadas, sinais persistidos e nenhuma dependência de scraping.
- Séries editoriais persistentes por organização.
- Editor visual com atualização server-side de cenas, duração recalculada e trilha de auditoria.
- Telas específicas para Tendências, Séries e Editor visual.
- Migração `0009_intelligence_series.sql` e testes de contrato adicionados.

## Quarto checkpoint concluído

- Versão consolidada `1.0.0-rc.1` e manifesto de release legível por máquina.
- Gate automatizado para versão, schema, migrações, ambiente e documentação.
- RC E2E aplica as nove migrações no PostgreSQL antes de iniciar a API.
- Jornada ampliada para identidade, 2FA, inteligência editorial, operações,
  custos e rotação de token.
- Framework e dependências transitivas atualizados; auditoria de produção sem
  vulnerabilidades conhecidas.
- Plano de promoção e rollback e matriz final de evidências.
- Decisão honesta: RC preparada, promoção condicionada aos gates remotos e às
  integrações externas necessárias.
