# DarkTTK — Fase 1: fundação

## Objetivo

Entregar uma base executável e segura para as próximas fases: identidade visual, API, autenticação, organizações, autorização, persistência, auditoria, containers e testes.

## Decisões técnicas

- O frontend hospedado usa a identidade encaminhada pelo workspace OpenAI. Não implementa uma segunda tela de login desnecessária nesse ambiente.
- A API comercial possui autenticação própria para clientes externos: senha Argon2, access token curto e refresh token rotativo.
- O backend começa como monólito modular FastAPI. Geração, renderização, análise e publicação serão workers independentes.
- PostgreSQL é o banco de produção. D1/R2 sustentam a superfície hospedada do protótipo.
- Toda autorização é executada no servidor e vinculada simultaneamente a usuário e organização.

## Funcionalidades implementadas

### Autenticação

- Cadastro de proprietário com criação atômica de organização.
- Login por e-mail normalizado.
- Política de senha com 12 caracteres e diversidade de classes.
- Hash Argon2.
- Access token com expiração de 15 minutos.
- Refresh token rotativo, persistido apenas por SHA-256.
- Detecção de replay de refresh token.
- Logout e revogação de sessão.
- Bloqueio por 15 minutos após cinco falhas consecutivas.

### Organizações e RBAC

| Papel | Capacidades principais |
|---|---|
| Administrador | Acesso total, integrações, segurança e membros |
| Gestor | Conteúdo, aprovações, calendário, métricas e leitura de membros |
| Editor | Criar/editar conteúdo e biblioteca |
| Revisor | Ler conteúdo, fontes e decidir aprovações |
| Analista | Métricas e experimentos |
| Visualizador | Leitura de conteúdo e métricas |

Controles adicionais:

- Gestor não cria ou altera administradores.
- O último administrador não pode ser rebaixado.
- E-mail é único globalmente; participação é única por usuário/organização.
- Alterações de função e convites geram auditoria.

### Banco e auditoria

Entidades da fundação:

- `users`
- `organizations`
- `organization_members`
- `refresh_tokens`
- `audit_logs`
- `system_settings`

A migração PostgreSQL está em `services/api/migrations/0001_foundation.sql`. O backend pode criar o schema automaticamente apenas em desenvolvimento; produção deve executar migrações como etapa controlada.

## Endpoints

| Método | Caminho | Autorização |
|---|---|---|
| GET | `/health` | Pública |
| POST | `/v1/auth/register` | Pública, com rate limit na infraestrutura |
| POST | `/v1/auth/login` | Pública, com proteção contra força bruta |
| POST | `/v1/auth/refresh` | Refresh token |
| POST | `/v1/auth/logout` | Access + refresh token |
| GET | `/v1/auth/me` | Access token |
| GET | `/v1/dashboard` | Access token |
| GET | `/v1/organizations/current/members` | Membro |
| GET | `/v1/organizations/current/permissions` | Membro |
| POST | `/v1/organizations/current/members` | Administrador ou gestor |
| PATCH | `/v1/organizations/current/members/{id}` | Administrador ou gestor |

## Dados iniciais

`python -m darkttk.seed` cria uma organização local, um administrador e configurações seguras:

- limite de cinco publicações diárias;
- aprovação obrigatória;
- fuso `America/Sao_Paulo`.

O seed é idempotente e destinado ao ambiente local.

## Testes

A suíte cobre:

- health check e headers de segurança;
- cadastro, login e identidade atual;
- rotação e rejeição de replay do refresh token;
- convite de editor;
- proteção do último administrador;
- autenticação obrigatória do dashboard.

## Segurança e limitações

- Rate limiting distribuído será ligado ao Redis no hardening de infraestrutura.
- 2FA e recuperação de senha entram antes da abertura pública.
- Convites criam usuários no estado `invited`; envio de e-mail e definição inicial de senha dependem do módulo de notificações.
- Tokens OAuth do TikTok ainda não existem nesta fase e nenhum endpoint externo é simulado como ativo.

## Critérios de aceite atendidos

- Cadastro cria usuário, organização e associação administrativa.
- Credencial incorreta não revela se o e-mail existe.
- Refresh token usado não pode ser reutilizado.
- Endpoint protegido rejeita usuário anônimo.
- Autorização respeita papel e organização.
- Organização mantém pelo menos um administrador.
- Ações sensíveis geram auditoria.
- Schema possui constraints, índices e migração versionada.
- Ambiente local inicia com Docker Compose.

## Próxima etapa

Fase 2 — Conteúdo: nichos, bloqueios personalizados, ideias, roteiros versionados, abstração de provedores de IA, moderação e verificação factual.
