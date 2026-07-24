# DarkTTK — Fase 4: aprovação e calendário

## Objetivo

Implementar a supervisão humana entre a produção audiovisual e a futura publicação: revisão, decisão, correção, reenvio, calendário editorial, regras de agendamento e notificações internas.

## Entregas

### Central de aprovação

Projetos com render concluído ou prévia mock podem ser enviados para aprovação. Cada envio cria uma versão própria, impedindo que uma decisão antiga seja aplicada silenciosamente a um conteúdo alterado.

Estados de aprovação:

- `pending`: aguardando decisão humana;
- `approved`: liberado para o calendário;
- `changes_requested`: precisa de ajustes e reenvio;
- `rejected`: reprovado;
- `cancelled`: encerrado sem decisão.

Somente uma revisão pode permanecer pendente para cada projeto. Administrador, gestor e editor enviam projetos; administrador, gestor e revisor decidem.

### Decisões e histórico

Aprovação, reprovação e pedido de alterações criam eventos append-only. Reprovação e pedido de alterações exigem justificativa. O registro guarda:

- projeto e versão;
- solicitante e decisor;
- observações;
- data da decisão;
- eventos de envio, reenvio, edição e decisão;
- auditoria da organização.

O projeto não pode ser editado enquanto existe decisão pendente. Após alterações solicitadas ou reprovação, título e template podem ser corrigidos. O reenvio cria a próxima versão da aprovação.

### Calendário editorial

Somente projetos com uma aprovação válida podem ser reservados. A API aplica:

- antecedência mínima de cinco minutos;
- fuso horário IANA validado;
- intervalo mínimo de 15 minutos entre publicações;
- limite operacional de cinco publicações por dia;
- apenas um horário ativo por projeto;
- período máximo de consulta de 180 dias.

Reservas podem ser reagendadas ou canceladas. Cancelar devolve o projeto ao estado aprovado. Nenhuma reserva é apresentada como publicação real; a conexão oficial com o TikTok pertence à Fase 5.

### Notificações

Notificações internas são persistentes e destinadas ao usuário:

- nova solicitação para revisores;
- decisão para o solicitante;
- criação ou mudança de horário para o responsável pelo projeto.

O usuário consulta apenas as próprias notificações, marca uma individual como lida ou encerra todas de uma vez. E-mail, push e integrações externas não estão simulados.

### Interface

A navegação agora possui superfícies operacionais reais:

- visão geral com indicadores e fila;
- central de aprovação com filtros;
- modal de revisão com prévia, conformidade e justificativa;
- decisões de aprovação, alteração e reprovação;
- calendário semanal;
- reserva de horário com verificação de conflito;
- central de notificações e contagem de não lidas;
- comportamento responsivo para desktop, tablet e celular.

Prévia mock permanece identificada para evitar confusão com um vídeo final.

## Endpoints principais

| Método | Caminho | Finalidade |
|---|---|---|
| GET | `/v1/workflow/approvals` | Listar a central |
| GET | `/v1/workflow/approvals/{id}` | Consultar revisão e histórico |
| POST | `/v1/workflow/projects/{id}/approval-requests` | Enviar ou reenviar |
| POST | `/v1/workflow/approvals/{id}/decision` | Aprovar, reprovar ou pedir alterações |
| PATCH | `/v1/workflow/projects/{id}` | Editar após devolução |
| GET | `/v1/workflow/calendar` | Consultar calendário |
| POST | `/v1/workflow/projects/{id}/schedule` | Reservar horário |
| PATCH | `/v1/workflow/schedule/{id}` | Reagendar |
| DELETE | `/v1/workflow/schedule/{id}` | Cancelar reserva |
| GET | `/v1/workflow/notifications` | Listar notificações próprias |
| PATCH | `/v1/workflow/notifications/{id}/read` | Marcar uma como lida |
| POST | `/v1/workflow/notifications/read-all` | Marcar todas como lidas |

## Dados e migrações

PostgreSQL:

- `services/api/migrations/0004_workflow.sql`

D1:

- `drizzle/0004_workflow.sql`

Entidades:

- `approval_requests`;
- `approval_events`;
- `scheduled_slots`;
- `notifications`.

O estado do dashboard passa a ser calculado a partir das tabelas persistentes, em vez de números fixos.

## Segurança e consistência

- Todas as consultas aplicam isolamento por organização.
- Notificações também são filtradas pelo destinatário.
- Decisão e agendamento usam RBAC específico.
- Alterações são bloqueadas durante uma revisão pendente.
- Agendamento depende de aprovação válida.
- Reutilização de horário é rejeitada.
- Decisões e movimentações de agenda são auditadas.
- Nenhuma reserva dispara publicação automática.

## Testes implementados

- submissão de revisão;
- bloqueio de revisão pendente duplicada;
- justificativa obrigatória para decisão negativa;
- pedido de alterações e edição;
- reenvio com incremento de versão;
- aprovação e mudança de estado do projeto;
- criação, consulta e cancelamento de reserva;
- consulta e leitura de notificações;
- compilação e renderização da interface;
- aplicação sequencial das migrações D1.

## Limitações conscientes

- Notificações são apenas internas nesta fase.
- Reservas não publicam no TikTok.
- A interface hospedada demonstra o fluxo; a autoridade de dados permanece na API autenticada e nos bancos configurados.
- O worker de publicação, OAuth e confirmação remota pertencem à Fase 5.

## Próxima etapa

Fase 5 — integração oficial com TikTok, OAuth, fila de publicação, confirmação e tratamento de falhas.
