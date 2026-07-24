# DarkTTK

Plataforma de operações e inteligência para conteúdo vertical, com automação supervisionada, aprovação humana, rastreabilidade e integrações substituíveis.

## Estado da entrega

- Fase 0 concluída em `docs/FASE-0-PLANEJAMENTO.md`.
- Fase 1 concluída: dashboard responsivo, autenticação de workspace, API com login seguro, organizações, RBAC, auditoria, schema persistente, migrações, containers, seed e testes.
- Fase 2 concluída: nichos, bloqueios personalizados, ideias, roteiros versionados, provedores substituíveis, moderação, fontes, verificação factual e histórico.
- Fase 3 concluída: TTS substituível, biblioteca de mídia licenciada, legendas SRT/VTT, projetos 9:16, composição FFmpeg, fila Celery e prévia mock identificada.
- Fase 4 concluída: central de aprovação, revisão versionada, edição supervisionada, calendário, regras de agendamento e notificações internas.
- Fase 5 concluída em código: OAuth oficial TikTok, tokens criptografados e rotacionados, fila isolada de publicação, Direct Post ou upload assistido, confirmação por status/webhook, retentativas e dead letter.
- Fase 6 concluída: snapshots de métricas públicas, estatísticas de conta, retenção importada com origem explícita, recomendações supervisionadas e experimentos A/B anti-spam.
- Fase 7 concluída: segurança de borda, rate limit distribuído, observabilidade, incidentes, FinOps, checkpoints de auditoria, backup/restore, CI/CD, perfil de produção e testes de carga.
- A publicação real permanece **desativada por padrão** e só opera com credenciais, escopos e aprovação fornecidos pelo TikTok. O adaptador mock é sempre identificado.

## Execução do frontend

Requer Node.js 22.13 ou superior.

```bash
npm ci
npm run dev
```

## Execução da API

Requer Python 3.12.

```bash
cd services/api
python -m venv .venv
pip install -r requirements.txt
uvicorn darkttk.main:app --reload
```

A documentação interativa da API fica disponível em `/docs`. Para criar uma conta, use `POST /v1/auth/register`; a resposta contém os tokens de acesso e renovação. O token de acesso deve ser enviado como `Authorization: Bearer <token>`.

## Ambiente completo

Copie `.env.example` para `.env` e execute:

```bash
docker compose up --build
```

Serviços locais: PostgreSQL, Redis, API FastAPI, worker Celery de renderização e worker Celery dedicado à publicação. O frontend hospedado usa bindings gerenciados D1/R2 para a experiência inicial.

## Testes

```bash
npm test
cd services/api && pytest
```

## Segurança

Não grave chaves no repositório. Tokens sociais devem ser obtidos por OAuth oficial, criptografados e rotacionados. A publicação automática permanece desativada até a conta possuir permissão oficial compatível.

Senhas usam Argon2. Access tokens expiram rapidamente; refresh tokens são armazenados apenas por hash, rotacionados a cada uso e podem ser revogados. Cinco tentativas de login inválidas bloqueiam temporariamente a conta.

## Provedores da Fase 2

Os adaptadores `mock-local-v1` e `mock-fact-check-v1` mantêm o fluxo executável sem inventar conexões externas. Toda resposta identifica `provider_is_mock`. Para ativar um fornecedor real, implemente os contratos em `darkttk/providers/`, mantenha segredos fora do banco e registre o adaptador na camada de seleção.

## Produção de vídeo da Fase 3

O adaptador `mock-tts-v1` produz WAV silencioso somente para desenvolvimento. Com `RENDER_MODE=mock`, a API gera um manifesto de prévia marcado como mock; com `RENDER_MODE=ffmpeg`, o job segue para o worker Celery, que valida licenças novamente e executa FFmpeg sem shell. Consulte `docs/FASE-3-VIDEO.md`.

## Aprovação e calendário da Fase 4

Projetos renderizados entram em revisão humana versionada. Aprovar, reprovar ou pedir alterações registra evento e auditoria; decisões negativas exigem justificativa. Somente a última versão aprovada pode ser reservada no calendário, com limite de cinco publicações diárias e intervalo mínimo de 15 minutos. As notificações desta fase são internas e não simulam envio por e-mail ou push. Consulte `docs/FASE-4-WORKFLOW.md`.

## Publicação da Fase 5

O modo `TIKTOK_MODE=official` habilita Login Kit e Content Posting API quando `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REDIRECT_URI` e `ENCRYPTION_KEY` estão configurados. O frontend nunca recebe tokens do provedor. Antes de cada envio, a API consulta as opções atuais da conta, exige seleção manual de privacidade/interações, confirmação de direitos musicais e consentimento explícito.

Use `TIKTOK_MODE=mock` apenas em desenvolvimento e testes. Nesse modo o job termina em `mock_complete` e nunca muda o projeto para publicado. Consulte `docs/FASE-5-PUBLICACAO.md`.

## Métricas e otimização da Fase 6

A sincronização oficial usa somente campos públicos autorizados pela TikTok Display API (`video.list`) e estatísticas de perfil autorizadas (`user.info.stats`). Visualizações, curtidas, comentários e compartilhamentos são armazenados como snapshots históricos. Retenção, conclusão e salvamentos não são atribuídos à Display API: entram apenas por importação identificada do painel do criador.

Recomendações guardam evidências e confiança, mas nunca alteram automaticamente a estratégia. Experimentos aceitam exatamente duas variantes, dois projetos distintos e uma variável declarada. Consulte `docs/FASE-6-METRICAS.md`.

## Escala e produção da Fase 7

A API separa liveness de readiness, exporta métricas compatíveis com Prometheus e exige token para esse endpoint em produção. Falhas não tratadas são agrupadas por fingerprint e persistidas sem detalhes sensíveis. Custos reais entram em um ledger idempotente e são comparados ao orçamento do workspace. A auditoria pode ser selada e verificada por checkpoints SHA-256.

Use `docker-compose.prod.yml` sobre o Compose base somente com segredos externos e migrações explícitas. Os scripts de backup geram checksum e o restore exige confirmação nominal de ambiente isolado. Consulte `docs/FASE-7-PRODUCAO.md` e `docs/RUNBOOK-PRODUCAO.md`.

## Release Candidate 1

Após o encerramento do roadmap na Fase 7, o projeto entrou no ciclo de integração RC1. A identidade autenticada do workspace pode ser trocada no servidor por uma sessão curta da API usando HMAC-SHA256, sem armazenar tokens no navegador. Quando `DARKTTK_API_URL` e `WORKSPACE_IDENTITY_SECRET` estão configurados, o dashboard e a tela de Operações carregam contagens, readiness e orçamento reais; caso contrário, a origem demonstrativa ou indisponível permanece explícita.

Consulte `docs/RELEASE-CANDIDATE-1.md` para a matriz honesta de cobertura e os bloqueadores restantes.

### Checkpoint 2

Recuperação de conta agora usa tokens de uso único armazenados somente por hash e revoga sessões após a troca. O login próprio suporta TOTP com segredo criptografado, prevenção de replay e códigos de recuperação consumíveis. Aprovação e agendamento na interface passam por rotas server-side que preservam a identidade do workspace sem expor tokens da API ao navegador.

O canal externo de recuperação continua desativado até existir um adaptador real; o modo mock é proibido em produção. Consulte `docs/RC1-CHECKPOINT-2.md`.

### Checkpoint 3

O canal real de recuperação agora pode usar Resend, códigos 2FA podem ser
renovados com autenticação forte, e a inteligência editorial passa a contar com
fontes autorizadas, tendências persistidas, séries e edição segura de cenas.
Consulte `docs/RC1-CHECKPOINT-3.md`.

### Checkpoint 4

A RC1 foi consolidada como `1.0.0-rc.1`, com manifesto, verificador automático,
E2E sobre migrações PostgreSQL reais, auditoria de dependências, plano de
promoção e rollback e matriz final de evidências. A promoção permanece
condicionada aos gates remotos e às credenciais externas do ambiente.

Consulte `docs/RC1-CHECKPOINT-4.md`, `docs/RC1-PROMOTION-ROLLBACK.md` e
`docs/RC1-FINAL-EVIDENCE.md`.
