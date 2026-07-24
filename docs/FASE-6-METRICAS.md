# DarkTTK — Fase 6: métricas e otimização

## Objetivo

Transformar resultados publicados em aprendizado editorial rastreável, sem inventar métricas, prometer crescimento ou aplicar mudanças estratégicas sem decisão humana.

## Fontes oficiais e limites

A integração oficial usa a TikTok Display API:

- `video.list` autoriza a leitura dos vídeos públicos da conta;
- `/v2/video/query/` retorna, entre outros campos, `view_count`, `like_count`, `comment_count` e `share_count`;
- `user.info.stats` autoriza `follower_count`, `following_count`, `likes_count` e `video_count`.

Referências:

- [Display API — visão geral](https://developers.tiktok.com/doc/display-api-overview/)
- [Consulta de vídeos](https://developers.tiktok.com/doc/tiktok-api-v2-video-query/)
- [Objeto de vídeo](https://developers.tiktok.com/doc/tiktok-api-v2-video-object/)
- [Informações e estatísticas da conta](https://developers.tiktok.com/doc/tiktok-api-v2-get-user-info?enter_method=left_navigation)
- [Escopos oficiais](https://developers.tiktok.com/doc/tiktok-api-scopes?enter_method=left_navigation)

Retenção, tempo médio assistido, taxa de conclusão e salvamentos não aparecem nesses contratos públicos da Display API. O DarkTTK não os apresenta como coleta oficial automática. Esses dados entram por importação identificada como `manual_tiktok_analytics_export` ou `manual_creator_report`, com usuário e data auditados.

## Entregas

### Snapshots de desempenho

Cada sincronização cria um snapshot append-only por publicação:

- visualizações;
- curtidas;
- comentários;
- compartilhamentos;
- identificador do vídeo;
- fonte;
- data da coleta;
- indicador mock.

O relatório usa o snapshot mais recente de cada publicação, enquanto o histórico permite calcular evolução. Métricas mock são marcadas e nunca misturadas silenciosamente com resultados reais.

### Estatísticas de conta

Quando o escopo `user.info.stats` está autorizado, a sincronização também registra seguidores, contas seguidas, curtidas acumuladas e quantidade de vídeos. O delta de seguidores depende de pelo menos dois snapshots.

### Retenção importada

A API aceita:

- tempo médio assistido;
- taxa de conclusão;
- taxa de visualização completa;
- salvamentos;
- curva normalizada de retenção.

Taxas e pontos da curva precisam estar entre zero e um. Cada importação guarda fonte, responsável, data observada e registro de auditoria.

### Recomendações supervisionadas

O motor determinístico gera recomendações a partir de evidências agregadas. Exemplos:

- coletar mais dados quando a amostra é pequena;
- testar gancho direto quando a interação está baixa;
- explorar série quando a taxa de compartilhamento é relevante;
- antecipar a entrega quando a conclusão importada está baixa.

Recomendações possuem confiança, evidência deduplicada e estado `open`, `accepted` ou `dismissed`. Aceitar significa levar ao planejamento; não altera templates, agenda ou publicação automaticamente.

### Experimentos A/B

Cada experimento exige:

- exatamente duas variantes;
- projetos distintos;
- valores distintos;
- uma variável declarada;
- uma métrica principal.

Variáveis permitidas incluem gancho, descrição, legenda, voz, duração, horário, CTA e estrutura. Métricas principais: visualizações, engajamento, compartilhamento ou conclusão. Estados seguem `draft → running → completed`, com cancelamento permitido. O vencedor só é indicado quando as duas variantes possuem dados comparáveis; sua adoção continua manual.

## Endpoints

| Método | Caminho | Finalidade |
|---|---|---|
| GET | `/v1/analytics/overview` | Agregado atual e origem dos dados |
| POST | `/v1/analytics/publications/{id}/sync` | Sincronizar métricas |
| GET | `/v1/analytics/publications/{id}/metrics` | Histórico de snapshots |
| POST | `/v1/analytics/publications/{id}/retention` | Importar retenção identificada |
| POST | `/v1/analytics/recommendations/generate` | Gerar recomendações deduplicadas |
| GET | `/v1/analytics/recommendations` | Listar recomendações |
| PATCH | `/v1/analytics/recommendations/{id}` | Aceitar ou arquivar |
| POST | `/v1/analytics/experiments` | Criar teste com duas variantes |
| GET | `/v1/analytics/experiments` | Listar testes e resultados |
| PATCH | `/v1/analytics/experiments/{id}` | Avançar o estado |

Leitura é destinada a administrador, gestor, analista e visualizador. Sincronização, importação, recomendações e experimentos exigem administrador, gestor ou analista.

## Filas e dados

O worker `social.metrics` fica separado de publicação e renderização. O modo oficial exige `video.list`; estatísticas de conta exigem `user.info.stats`. O modo mock produz uma série determinística e explicitamente simulada.

Entidades:

- `publication_metric_snapshots`;
- `account_metric_snapshots`;
- `retention_observations`;
- `analytics_recommendations`;
- `content_experiments`;
- `experiment_variants`.

Migrações:

- PostgreSQL: `services/api/migrations/0006_analytics_optimization.sql`;
- D1: `drizzle/0006_analytics_optimization.sql`.

## Interface

O menu inclui:

- Métricas: alcance, engajamento, seguidores, ranking, curva de retenção e recomendações;
- Experimentos: hipótese, variável, métrica principal, comparação A/B, amostra e decisão.

Toda visualização demonstrativa é rotulada. Retenção exibe a origem importada e recomendações informam que nenhuma mudança é automática.

## Testes

- sincronização mock identificada;
- snapshot de vídeo e conta;
- overview agregado;
- importação e validação de retenção;
- recomendação baseada em evidência;
- criação de experimento com duas variantes;
- transição de estado;
- build e renderização do frontend;
- aplicação sequencial das migrações D1.

## Limitações conscientes

- Credenciais e aprovação de escopos TikTok não acompanham o código.
- A Display API não oferece o conjunto completo do painel Analytics do TikTok.
- Não há inferência causal apenas por correlação.
- Uma variante vencedora não é aplicada nem publicada automaticamente.
- Monitoramento avançado, backups, CI/CD e escala pertencem à Fase 7.

## Próxima etapa

Fase 7 — escala e produção: segurança avançada, monitoramento, backups, CI/CD, testes de carga, auditoria e custos.
