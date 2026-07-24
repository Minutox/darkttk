# DarkTTK — Fase 5: publicação

## Objetivo

Conectar o fluxo aprovado e agendado à integração oficial do TikTok, mantendo autorização humana por envio, credenciais protegidas, idempotência, confirmação assíncrona e tratamento rastreável de falhas.

## Decisões técnicas

### Integração oficial e modos

O adaptador possui três modos:

- `disabled`: padrão seguro; nenhuma publicação é iniciada;
- `mock`: desenvolvimento e testes, sempre marcado como simulação;
- `official`: Login Kit e Content Posting API oficiais.

O modo mock termina em `mock_complete`, não cria `post_id` real e não marca projeto ou horário como publicado. O modo oficial depende de um aplicativo TikTok configurado, escopos aprovados e credenciais reais. Cliente não auditado fica restrito às limitações impostas pelo TikTok, incluindo visibilidade privada quando aplicável.

Referências oficiais:

- [Login Kit](https://developers.tiktok.com/doc/login-kit-overview)
- [Gerenciamento de access e refresh tokens](https://developers.tiktok.com/doc/oauth-user-access-token-management?enter_method=left_navigation)
- [Direct Post](https://developers.tiktok.com/doc/content-posting-api-reference-direct-post?enter_method=left_navigation&from_seo_redirect=1)
- [Upload de mídia](https://developers.tiktok.com/doc/content-posting-api-media-transfer-guide)
- [Diretrizes de compartilhamento](https://developers.tiktok.com/doc/content-sharing-guidelines?enter_method=left_navigation)

### OAuth e proteção de credenciais

O início do OAuth exige papel de administrador ou gestor. O `state` é aleatório, armazenado somente como hash, expira e pode ser consumido uma única vez. A troca do código ocorre no backend. Access e refresh tokens são criptografados com Fernet usando uma chave derivada de `ENCRYPTION_KEY`; produção recusa inicialização criptográfica sem essa variável.

Tokens são renovados antes de expirar e o refresh token rotacionado substitui o anterior. Desconectar tenta revogar o token no provedor e marca a conexão como revogada localmente. Senhas do TikTok nunca são solicitadas nem armazenadas.

### Consentimento e metadados

Imediatamente antes de montar um Direct Post, a API exige consulta recente a `creator_info`. A interface não define privacidade nem permissões de comentário, dueto ou costura por padrão. O usuário precisa:

- escolher uma opção de privacidade retornada pelo provedor;
- permitir ou bloquear cada interação;
- informar conteúdo de marca ou promoção própria;
- sinalizar conteúdo gerado por IA quando aplicável;
- confirmar direitos de uso de música e ativos;
- autorizar expressamente aquele envio.

Cada autorização cria evento e auditoria com data, usuário, conta, horário e parâmetros. Uma repetição manual após falha exige novo consentimento.

Referência oficial: [consulta de informações do criador](https://developers.tiktok.com/doc/content-posting-api-reference-query-creator-info?enter_method=left_navigation).

### Fila e confirmação

Jobs de publicação usam a fila Celery `social.publish`, separada da renderização. A chave de idempotência é isolada por organização e ligada a um hash canônico do payload. Reutilizar a chave com outro payload gera conflito.

Fluxo:

1. validar aprovação, horário, conexão, escopo, creator info e render MP4;
2. registrar autorização;
3. inicializar Direct Post ou upload para caixa de entrada;
4. transferir o arquivo em chunks quando necessário;
5. consultar o status até um estado terminal;
6. aceitar também eventos assinados por webhook;
7. registrar eventos, notificar o responsável e atualizar projeto/agenda somente após confirmação real.

Status do provedor é consultado pelo endpoint oficial [Get Post Status](https://developers.tiktok.com/doc/content-posting-api-reference-get-video-status?enter_method=left_navigation).

### Webhooks e falhas

O webhook valida `TikTok-Signature` com HMAC-SHA256 sobre `timestamp.raw_body`, aplica tolerância contra replay e deduplica entregas pelo hash do corpo. O processamento é idempotente porque webhooks podem ser entregues mais de uma vez.

Referências:

- [Verificação de webhooks](https://developers.tiktok.com/doc/webhooks-verification)
- [Visão geral de webhooks](https://developers.tiktok.com/doc/webhooks-overview?enter_method=left_navigation)

Falhas transitórias usam retentativas exponenciais controladas. Ao atingir `PUBLISHING_MAX_ATTEMPTS`, o job vai para `dead_letter`, o horário fica como falho e o usuário recebe notificação. Erros permanentes não são repetidos automaticamente. Administradores e gestores podem reenfileirar uma falha somente após uma nova confirmação explícita.

## Endpoints principais

| Método | Caminho | Finalidade |
|---|---|---|
| GET | `/v1/tiktok/oauth/authorize` | Iniciar OAuth oficial |
| GET | `/v1/tiktok/oauth/callback` | Trocar código e persistir conexão |
| POST | `/v1/tiktok/connections/mock` | Criar conexão de teste, somente em modo mock |
| GET | `/v1/tiktok/connections` | Listar conexões da organização |
| DELETE | `/v1/tiktok/connections/{id}` | Revogar/desconectar |
| POST | `/v1/tiktok/connections/{id}/creator-info` | Atualizar opções do criador |
| POST | `/v1/tiktok/schedule/{id}/publication-jobs` | Autorizar e criar job idempotente |
| GET | `/v1/tiktok/publication-jobs` | Listar jobs |
| GET | `/v1/tiktok/publication-jobs/{id}` | Consultar job e eventos |
| POST | `/v1/tiktok/publication-jobs/{id}/cancel` | Cancelar job não terminal |
| POST | `/v1/tiktok/publication-jobs/{id}/retry` | Repetir falha com novo consentimento |
| POST | `/v1/tiktok/webhooks` | Receber evento assinado do provedor |

## Dados e migrações

PostgreSQL:

- `services/api/migrations/0005_tiktok_publishing.sql`

D1:

- `drizzle/0005_tiktok_publishing.sql`

Entidades:

- `tiktok_oauth_states`;
- `tiktok_connections`;
- `publication_jobs`;
- `publication_events`;
- `tiktok_webhook_receipts`.

## Configuração

```dotenv
TIKTOK_MODE=disabled
TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=
TIKTOK_REDIRECT_URI=http://localhost:8000/v1/tiktok/oauth/callback
TIKTOK_APP_AUDITED=false
ENCRYPTION_KEY=
```

Para produção, gere uma `ENCRYPTION_KEY` independente do segredo da aplicação. Cadastre exatamente a redirect URI e a URL pública do webhook no portal do TikTok. Ative apenas os escopos aprovados para o aplicativo.

## Testes implementados

- conexão e creator info simulados;
- consentimento obrigatório;
- validação de opção de privacidade;
- idempotência do job;
- conclusão mock sem falso estado publicado;
- criptografia e descriptografia de token;
- plano de chunks para upload;
- compilação estática da API;
- build e teste de HTML do frontend;
- aplicação sequencial das migrações D1.

## Limitações conscientes

- O repositório não inclui credenciais nem aprovação de aplicativo TikTok.
- Publicação real não pode ser validada sem uma conta e um aplicativo oficialmente autorizados.
- A interface hospedada demonstra o fluxo; a autoridade operacional permanece na API autenticada.
- Métricas pós-publicação, relatórios e otimização pertencem à Fase 6.

## Próxima etapa

Fase 6 — métricas, relatórios, aprendizado, recomendações, variações e análise de retenção.
