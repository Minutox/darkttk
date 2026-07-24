# DarkTTK — Fase 2: conteúdo

## Objetivo

Implementar o ciclo editorial anterior à produção audiovisual: configuração de nichos, bloqueios personalizados, criação de ideias, roteiros versionados, moderação, fontes, verificação factual, provedores substituíveis e histórico.

## Entregas

### Nichos

O seed cria 16 categorias iniciais:

- Saúde e bem-estar
- Educação
- Disciplina
- Compromisso
- Motivação
- Curiosidades
- História
- Ciência
- Engenharia
- Finanças pessoais
- Tecnologia
- Desenvolvimento pessoal
- Produtividade
- Cinema e entretenimento
- Resumos e análises de filmes
- Conteúdo personalizado

Cada nicho pertence a uma organização e pode ser desativado. Saúde, finanças e ciência passam para revisão quando aparecem em uma pauta.

### Bloqueios personalizados

Administradores e gestores cadastram palavra, tema ou categoria. Os termos são normalizados sem acentos e aplicados antes da geração. A exclusão é lógica para preservar rastreabilidade.

### Ideias

Uma ideia registra:

- tema e ângulo criativo;
- promessa e gancho;
- estrutura narrativa;
- informação principal;
- chamada para ação;
- sugestão visual;
- duração, audiência e objetivo;
- modo, provedor, risco e estado.

O fluxo aceita autoria manual e geração assistida. Toda entrada passa pela moderação pré-geração.

### Roteiros

Roteiros são imutáveis por versão. Uma correção cria a próxima versão e guarda motivo, autor e relação com a pauta. Estilos são validados por enum. O roteiro gerado passa por nova moderação antes da aprovação.

### Fontes e fact-check

Fontes possuem URL única por organização, título, publicador, confiança e nota de licença. A associação roteiro–fonte é relacional. Cada verificação registra:

- afirmação;
- veredito;
- confiança de 0 a 100;
- evidência;
- fonte;
- provedor e revisor.

O adaptador mock nunca afirma que verificou a internet. Sem fonte, retorna `needs_review`; com fonte fornecida, informa apenas que existe suporte indicado pelo usuário.

## Moderação em duas camadas

### Pré-geração

Bloqueia política, religião, conteúdo sexual, ódio, violência gráfica, extremismo, automutilação, drogas ilícitas, golpes, aconselhamento médico prescritivo, retorno garantido e violação autoral explícita.

### Pré-aprovação

O roteiro completo é analisado novamente. Resultado:

- `allow`: segue no fluxo;
- `review`: exige revisão humana e fontes;
- `block`: não pode ser aprovado.

Cada decisão guarda versão da política, regras acionadas, etapa e provedor.

## Provedores

Contratos implementados:

- `LanguageModelPort`
- `FactCheckerPort`

Adaptadores locais:

- `mock-local-v1`
- `mock-fact-check-v1`

Esses adaptadores são determinísticos, próprios para desenvolvimento e identificados como mock em banco, API e histórico. Chaves reais nunca são armazenadas: o cadastro guarda somente referência ao segredo.

## Histórico

Eventos append-only registram criação de ideia, geração/revisão de roteiro, anexação de fonte, fact-check e alterações na lista de bloqueio. O histórico sempre é filtrado pela organização autenticada.

## Endpoints principais

| Método | Caminho | Finalidade |
|---|---|---|
| GET | `/v1/content/niches` | Listar nichos |
| PATCH | `/v1/content/niches/{id}` | Ativar/desativar |
| GET/POST | `/v1/content/blocked-topics` | Consultar/criar bloqueios |
| DELETE | `/v1/content/blocked-topics/{id}` | Desativar bloqueio |
| GET/POST | `/v1/content/ideas` | Listar/criar manualmente |
| POST | `/v1/content/ideas/generate` | Gerar ideia assistida |
| POST | `/v1/content/ideas/{id}/scripts/generate` | Gerar roteiro |
| POST | `/v1/content/scripts/{id}/versions` | Criar revisão |
| GET | `/v1/content/ideas/{id}/scripts` | Consultar versões |
| POST | `/v1/content/scripts/{id}/sources` | Anexar fonte |
| POST | `/v1/content/scripts/{id}/fact-checks/run` | Verificar afirmações |
| GET | `/v1/content/history/{tipo}/{id}` | Consultar histórico |
| GET/PATCH | `/v1/providers` | Consultar/configurar adaptadores |

## Dados e migrações

PostgreSQL:

- `services/api/migrations/0002_content.sql`

D1:

- migrações Drizzle versionadas em `drizzle/`

Novas entidades:

- `content_niches`
- `blocked_topics`
- `ai_providers`
- `content_ideas`
- `scripts`
- `sources`
- `script_sources`
- `fact_checks`
- `moderation_checks`
- `content_events`

## Testes implementados

- criação dos 16 nichos;
- bloqueio de política;
- aplicação de lista personalizada;
- geração por provedor mock explicitamente identificado;
- criação de roteiro e versão;
- fact-check conservador;
- histórico de eventos;
- revisão manual cria versão subsequente.

## Limitações conscientes

- Nenhum provedor externo está conectado sem credenciais e aprovação.
- O mock de fact-check não acessa a internet e não valida conteúdo de URLs.
- Busca de tendências entra em um conector dedicado na evolução da Fase 2/Fase 3.
- Afirmações médicas, financeiras ou científicas permanecem bloqueadas para aprovação enquanto não houver fonte e revisão adequadas.

## Próxima etapa

Fase 3 — Vídeo: TTS, biblioteca de mídia, licenças, legendas, composição FFmpeg, renderização assíncrona e prévia.
