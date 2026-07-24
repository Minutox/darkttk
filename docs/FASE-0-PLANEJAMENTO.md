# DarkTTK — Fase 0: planejamento técnico e arquitetura

## 1. Resumo executivo

O DarkTTK é uma plataforma multi-organização para planejar, produzir, revisar, aprovar, agendar e analisar conteúdo vertical. A proposta central é automação com supervisão humana: o sistema reduz trabalho repetitivo, mas mantém decisões editoriais, de conformidade e publicação sob controle explícito do usuário.

O MVP cobre o caminho crítico `pauta → roteiro → verificação → composição → aprovação → agenda → publicação assistida/oficial → métricas`. O produto não promete desempenho nem monetização. Recomendações serão explicáveis, baseadas em dados e reversíveis.

## 2. Escopo do produto

### Dentro do MVP

- Organizações, usuários e RBAC.
- Nichos, bloqueios personalizados e moderação em duas camadas.
- Ideias e roteiros com provedor de IA substituível.
- Registro de fontes e verificação de afirmações críticas.
- Projetos de vídeo 9:16, voz, mídia licenciada, legendas e renderização assíncrona.
- Central de aprovação obrigatória, calendário e limite inicial de cinco posts/dia.
- Publicação via integração oficial quando habilitada; exportação assistida caso contrário.
- Biblioteca, custos, auditoria, notificações internas e métricas essenciais.

### Fora do MVP

- Editor equivalente a ferramentas profissionais.
- Clonagem de voz sem consentimento verificável.
- Scraping contrário a termos de serviço.
- Publicação totalmente automática.
- Geração de vídeo proprietária; o MVP integra provedores.
- Garantia de crescimento ou monetização.

## 3. Personas

1. **Criador solo** — precisa manter consistência sem montar uma equipe completa.
2. **Gestor de conteúdo** — coordena calendário, orçamento, contas e aprovações.
3. **Editor/revisor** — corrige roteiro, cenas, voz e legendas com rastreabilidade.
4. **Analista** — interpreta retenção, formatos, séries e experimentos.
5. **Administrador** — controla integrações, segurança, usuários e limites.

## 4. Jornada principal

1. Entrar em uma organização e escolher a conta social.
2. Selecionar nicho, objetivo, quantidade e período.
3. Avaliar tendências autorizadas e ideias evergreen.
4. Aprovar uma pauta; moderação prévia bloqueia temas restritos.
5. Gerar roteiro e registrar fontes.
6. Verificar afirmações factuais e marcar incertezas.
7. Gerar voz, selecionar mídia licenciada e compor cenas.
8. Renderizar prévia 1080×1920 com legendas e áudio normalizado.
9. Calcular qualidade e riscos sem tratar a nota como garantia.
10. Revisar artefatos, fontes, licenças, alertas e custo.
11. Aprovar e reservar horário dentro das políticas editoriais.
12. Publicar via API oficial ou exportar pacote de publicação assistida.
13. Coletar métricas, analisar retenção e recomendar próximos testes.

## 5. Requisitos funcionais

| ID | Requisito | Prioridade |
|---|---|---|
| RF-01 | Autenticar usuários, revogar sessões e aplicar RBAC por organização | P0 |
| RF-02 | Gerenciar nichos, palavras e temas bloqueados | P0 |
| RF-03 | Criar ideias por tendência, evergreen, série ou histórico | P0 |
| RF-04 | Gerar e versionar roteiros verticais | P0 |
| RF-05 | Moderar entrada e artefato final | P0 |
| RF-06 | Registrar fontes, confiança e decisão de verificação | P0 |
| RF-07 | Integrar TTS, mídia e IA por interfaces substituíveis | P0 |
| RF-08 | Renderizar vídeo em worker desacoplado e idempotente | P0 |
| RF-09 | Gerar, editar e exportar legendas | P0 |
| RF-10 | Exigir aprovação humana antes de publicar | P0 |
| RF-11 | Agendar no máximo cinco posts/dia com intervalo configurável | P0 |
| RF-12 | Publicar por API oficial ou fluxo assistido | P0 |
| RF-13 | Registrar auditoria, falhas, custos e uso de provedores | P0 |
| RF-14 | Exibir métricas por nicho, formato, horário e gancho | P1 |
| RF-15 | Executar experimentos não-spam | P1 |
| RF-16 | Gerenciar séries e continuidade editorial | P1 |

## 6. Requisitos não funcionais

- **Disponibilidade:** 99,5% no MVP, excluindo dependências externas.
- **Desempenho:** API p95 abaixo de 400 ms para operações sem geração; dashboard LCP abaixo de 2,5 s em conexão típica.
- **Escala:** serviços stateless; workers escaláveis por profundidade de fila.
- **Segurança:** OWASP ASVS nível 2 como referência; secrets em cofre; TLS; menor privilégio.
- **Confiabilidade:** idempotência em jobs e publicação; DLQ; retry com backoff e jitter.
- **Rastreabilidade:** correlation ID do pedido à publicação; auditoria append-only.
- **Privacidade:** minimização de dados, retenção configurável e exportação/exclusão por organização.
- **Acessibilidade:** WCAG 2.2 AA nas jornadas críticas.
- **Portabilidade:** adaptadores para IA, mídia, voz, storage e publicação.
- **Observabilidade:** logs estruturados, métricas RED/USE, tracing e alertas por SLO.

## 7. Arquitetura proposta

Adota-se um **monólito modular com workers especializados** no início. Isso reduz custo operacional e complexidade transacional sem impedir extração futura de serviços. O backend possui módulos por domínio, banco relacional compartilhado com ownership explícito e comunicação assíncrona para trabalhos pesados.

### Stack escolhida

- **Frontend:** Next.js, React, TypeScript e Tailwind/CSS tokens. Entrega SSR, acessibilidade, tipagem e boa produtividade.
- **Backend:** FastAPI/Python. A escolha favorece integrações com IA, processamento de mídia, validação Pydantic e APIs assíncronas. NestJS seria igualmente viável, mas criaria uma ponte adicional para o ecossistema Python usado em IA e FFmpeg.
- **Banco:** PostgreSQL em produção; D1/SQLite no protótipo hospedado. PostgreSQL oferece constraints, JSONB, índices parciais, RLS opcional e maturidade operacional.
- **Fila:** Redis + Celery. Filas por classe de carga, retries declarativos e ecossistema Python consolidado.
- **Mídia:** S3/R2; metadados no banco; URLs temporárias.
- **Renderização:** FFmpeg em containers independentes, com templates versionados.
- **Observabilidade:** OpenTelemetry, métricas Prometheus e logs JSON.

## 8. Diagrama textual de componentes

```text
[Browser / Next.js]
        |
        | HTTPS + sessão/OAuth
        v
[API Gateway / FastAPI] -----> [PostgreSQL]
    |       |  |                    |
    |       |  +-----> [Audit log]  +-----> [Outbox]
    |       |
    |       +--------> [S3/R2: mídia, áudio, renders]
    |
    +-----> [Redis / Broker]
              |-- content.generate --> [AI Orchestrator] --> [LLM / Search / Moderation]
              |-- media.prepare -----> [Media Worker] -----> [TTS / Stocks / Image]
              |-- video.render ------> [FFmpeg Workers]
              |-- publish.social ----> [TikTok Official Adapter]
              |-- metrics.collect ---> [Analytics Worker]
              `-- dead-letter.* -----> [Operations Console]
```

## 9. Fluxo completo de criação

Cada execução nasce como `content_idea` e recebe um `correlation_id`. A moderação avalia tema e contexto antes de qualquer geração. O roteiro é versionado e afirmações são transformadas em itens verificáveis. Só fontes aceitas liberam alegações sensíveis. O orquestrador gera plano de cenas, voz e legendas; ativos recebem proveniência e licença. O render job cria um manifesto imutável e produz prévia. A avaliação calcula qualidade e risco. A central de aprovação apresenta tudo ao revisor; apenas uma decisão aprovada cria slot de publicação. O publicador valida novamente idempotência, autorização OAuth e política de frequência antes de transmitir.

## 10. Modelo inicial de dados

### Núcleo e acesso

`users`, `organizations`, `organization_members`, `roles`, `permissions`, `audit_logs`, `user_preferences`, `system_settings`.

### Conteúdo

`content_niches`, `blocked_topics`, `trend_sources`, `trends`, `content_ideas`, `content_series`, `scripts`, `fact_checks`, `sources`, `hashtags`.

### Produção

`voice_profiles`, `media_assets`, `media_licenses`, `video_projects`, `video_scenes`, `captions`, `templates`, `render_jobs`.

### Aprovação e publicação

`approval_requests`, `approval_history`, `scheduled_slots`, `publication_queue`, `publications`, `social_accounts`, `integration_credentials`.

### Inteligência e operação

`publication_metrics`, `experiments`, `experiment_variants`, `ai_providers`, `provider_usage`, `costs`, `notifications`, `errors`.

Regras centrais: todas as entidades de negócio possuem `organization_id`; relacionamentos relevantes usam FKs; estados são enums; e-mail e idempotency keys são únicos; assets não são excluídos antes de suas referências; soft delete é aplicado apenas onde há exigência de recuperação/auditoria.

## 11. Estratégia de filas

- `content.generate`: ideias, roteiros e metadados; concorrência alta, timeout curto.
- `factcheck.run`: pesquisa e consolidação de fontes; limites por domínio/provedor.
- `media.prepare`: TTS, busca e geração de ativos.
- `video.render`: CPU/GPU intensivo, baixa concorrência por worker.
- `quality.analyze`: áudio, legenda, repetição e riscos.
- `publish.social`: serializada por conta, prioridade por horário.
- `metrics.collect`: processamento periódico e tolerante a atraso.
- `dead-letter.*`: falhas não recuperáveis com contexto sanitizado.

Jobs usam chave de idempotência, lease, heartbeat, backoff exponencial com jitter, máximo de tentativas por tipo e compensação explícita. Publicação nunca é repetida apenas porque houve timeout; primeiro consulta-se o estado remoto.

## 12. Armazenamento

Objetos seguem `org/{org_id}/content/{content_id}/{asset_type}/{version}/{uuid}`. O banco guarda hash SHA-256, MIME, tamanho, licença, origem, autor, validade e retenção. Uploads usam URL assinada curta, validação de magic bytes, antivírus e limites. Renders finais são imutáveis; temporários expiram automaticamente.

## 13. Segurança

- Sessão HTTP-only/SameSite ou JWT curto com refresh rotativo e revogável.
- OAuth oficial para contas sociais; tokens criptografados com envelope encryption.
- RBAC server-side; checagem de organização em toda consulta.
- CSRF para mutações baseadas em cookie; CSP, escaping e headers de segurança.
- Rate limiting por usuário, organização, IP e operação cara.
- Upload isolado, content sniffing, limites e varredura.
- Webhooks assinados, timestampados e idempotentes.
- Segredos fora do repositório e rotação operacional.
- Proteção de prompt injection: conteúdo externo é dado não confiável, separado de instruções; ferramentas têm allowlists; saídas são validadas por schema e moderadas.

## 14. Integração TikTok

Um `TikTokPublisherPort` desacopla o domínio do fornecedor. O adaptador real só usa OAuth, escopos e endpoints oficiais aprovados para a conta/região. A aplicação armazena token criptografado, expiração, escopos e identificador da conta — nunca senha. Antes de publicar, valida aprovação, slot, hash de vídeo, duplicidade, direitos e regras. Sem permissão oficial, gera pacote com MP4, descrição, hashtags e checklist para publicação manual. O mock jamais se apresenta como integração ativa.

## 15. Integração com IA

Interfaces independentes: `LanguageModel`, `TextToSpeech`, `SpeechToText`, `ImageGenerator`, `VideoGenerator`, `Moderator`, `TrendSource`, `MediaSearch` e `FactChecker`. O roteador seleciona provedor por capacidade, custo, latência, região e saúde. Cada chamada registra modelo, versão, tokens/segundos, custo, latência, resultado sanitizado e fallback. Prompts são versionados e avaliados.

## 16. Moderação

1. **Pré-geração:** nicho, tema, intenção, palavras bloqueadas e categorias proibidas.
2. **Durante:** filtros por fornecedor, validação factual e política específica do domínio.
3. **Pré-aprovação:** análise multimodal do roteiro, áudio, frames, legendas, metadados e licenças.
4. **Pré-publicação:** revalidação curta para detectar alterações após aprovação.

Resultado padronizado: `allow`, `review`, `block`, motivos, evidências e versão da política. Saúde, finanças e ciência exigem fontes fortes e linguagem não prescritiva.

## 17. Direitos autorais

Todo ativo precisa de proveniência e base de uso: licença comercial, domínio público, material próprio ou permissão documentada. Filmes são tratados por análise, comentário e edição transformativa, sem automatizar alegação de fair use. Um ativo com licença ausente/expirada bloqueia publicação. Hash perceptual e comparação com biblioteca interna reduzem reutilização repetitiva. O revisor recebe relatório de licenças e alertas.

## 18. Métricas e aprendizado

O sistema registra impressões, visualizações, watch time, conclusão, retenção por intervalo, curtidas, comentários, compartilhamentos, salvamentos e seguidores, respeitando o que a API oficial disponibilizar. Features editoriais (gancho, duração, voz, legenda, CTA, horário) são versionadas. Recomendações exigem amostra mínima e intervalo de confiança; mudanças estratégicas dependem de aprovação.

## 19. Custos

Cada chamada externa e job registra unidade, quantidade, preço efetivo e centro de custo. Há limites por vídeo, dia, mês, organização e provedor. Ações: aviso em 70%, solicitação em 90% e bloqueio em 100%, configuráveis. Estimativa é exibida antes de iniciar uma produção. Fallback nunca pode ultrapassar limite sem autorização.

## 20. Roadmap

| Fase | Entrega | Saída verificável |
|---|---|---|
| 0 | Produto, arquitetura, riscos e aceite | Este documento e ADRs |
| 1 | Fundação | Repo, dashboard, API, auth, DB, containers e testes |
| 2 | Conteúdo | Nichos, ideias, roteiro, moderação e fact-check |
| 3 | Vídeo | Voz, mídia, legenda, FFmpeg, preview e biblioteca |
| 4 | Aprovação | Central, histórico, calendário e notificações |
| 5 | Publicação | OAuth, adaptador oficial, fila e fluxo assistido |
| 6 | Otimização | Métricas, recomendações, séries e experimentos |
| 7 | Produção | Hardening, SLOs, backup, CI/CD, carga e custos |

## 21. Riscos técnicos

| Risco | Impacto | Mitigação |
|---|---|---|
| Acesso limitado à API social | Alto | Fluxo assistido; capability matrix por conta |
| Custo/latência de geração | Alto | Orçamento, cache, roteamento e prévia barata |
| Alucinação factual | Alto | Extração de claims, fontes, confiança e revisão |
| Infração autoral | Alto | Proveniência obrigatória e bloqueio conservador |
| Job duplicado/publicação dupla | Crítico | Idempotência, outbox e reconciliação remota |
| Variação de qualidade entre provedores | Médio | Contratos, avaliações e fallback controlado |
| Carga de renderização | Alto | Workers isolados, autoscaling e quotas |
| Vazamento entre organizações | Crítico | Escopo obrigatório, testes e RLS opcional |

## 22. Critérios de aceite do MVP

- Usuário autenticado acessa apenas sua organização e papel.
- Admin convida membro e altera permissão com auditoria.
- Usuário cria pauta em um nicho permitido.
- Tema proibido é bloqueado antes da geração.
- Roteiro possui versão, fontes e estado de verificação.
- Um projeto gera prévia vertical com voz e legenda sincronizada.
- Ativo sem licença válida bloqueia a aprovação.
- Revisor aprova/reprova com motivo; histórico é imutável.
- Agenda recusa sexto post diário e duplicidade.
- Publicador oficial é ativado somente com credencial/escopo válidos; caso contrário oferece exportação assistida.
- Falha recuperável usa retry; falha final chega à DLQ e notificação.
- Custos respeitam limites e interrompem antes de ultrapassar bloqueio.
- Dashboard mostra estado operacional e métricas disponíveis.
- Testes unitários/integrados cobrem autenticação, permissão, moderação, idempotência e agenda.

## 23. Estrutura inicial do repositório

```text
DarkTTK/
├── app/                 # frontend Next.js e experiência operacional
├── db/                  # schema persistente do protótipo hospedado
├── services/
│   └── api/             # API FastAPI modular
├── docs/                # arquitetura, ADRs e operação
├── tests/               # testes do frontend/render
├── .openai/             # declaração de hosting, D1 e R2
├── docker-compose.yml   # PostgreSQL, Redis e API local
├── .env.example
└── README.md
```

## 24. Decisões e limitações desta entrega

O dashboard hospedado é uma fundação navegável e responsiva, com identidade DarkTTK e interações críticas demonstráveis. D1/R2 sustentam a evolução do protótipo. A API FastAPI, PostgreSQL, Redis/Celery e FFmpeg são a arquitetura de produto comercial, mas as integrações externas continuam intencionalmente desconectadas até existirem credenciais e aprovações oficiais.
