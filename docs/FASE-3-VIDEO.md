# DarkTTK — Fase 3: vídeo

## Objetivo

Implementar a primeira cadeia audiovisual do DarkTTK: narração, biblioteca de mídia, licenciamento, legendas, composição vertical, renderização desacoplada e prévia rastreável.

## Entregas

### Narração

O contrato `TextToSpeechPort` desacopla a aplicação do fornecedor. Perfis de voz registram idioma, velocidade, pitch, emoção, gênero descritivo e referência de consentimento.

O adaptador inicial `mock-tts-v1` gera um WAV silencioso determinístico. Ele é identificado como mock no provedor, perfil e ativo; portanto, nunca aparenta ser uma narração real. A troca por um TTS externo exige implementar o contrato e manter a chave fora do banco.

Clonagem de voz não foi habilitada. Vozes de pessoas reais exigem autorização e uma referência de consentimento auditável.

### Biblioteca de mídia e licenças

Uploads aceitos inicialmente:

- imagens PNG e JPEG;
- vídeos MP4;
- áudio WAV e MP3.

O armazenamento local usa chaves aleatórias por organização, limite configurável, hash SHA-256 e validação de assinatura mágica. Nome enviado pelo usuário nunca define o caminho final.

Todo ativo visual exige um registro de licença. Tipos suportados:

- material próprio;
- banco licenciado;
- domínio público;
- permissão explícita;
- geração por IA.

Fontes externas licenciadas, de domínio público ou autorizadas exigem URL de origem. A licença é validada ao inserir a cena e novamente no worker, inclusive validade temporal. Isso reduz o risco de uma autorização revogada chegar ao render final.

### Legendas

Legendas são divididas em blocos curtos, possuem palavras de destaque, idioma, estilo e área segura. Os sete estilos previstos estão representados:

- minimalista;
- dinâmica;
- palavra por palavra;
- cinematográfica;
- educativa;
- destaque central;
- destaque inferior.

As trilhas podem ser exportadas em SRT ou WebVTT. No render FFmpeg, a legenda é incorporada ao vídeo com contraste e margem inferior para a zona segura.

### Projetos e cenas

Um projeto referencia roteiro, narração, legenda e perfil de voz. A composição padrão é:

- 1080 × 1920;
- proporção 9:16;
- 30 fps;
- template `dark-minimal-v1`.

Cenas armazenam ordem, início, fim, trim, transição, movimento e texto sobreposto. Somente imagens e vídeos com licença válida podem ser adicionados.

### Renderização

O render é idempotente: a mesma chave e o mesmo conteúdo retornam o job existente; reutilizar a chave com outro conteúdo gera conflito.

Em produção, a API publica o job na fila Redis/Celery `video.render`. O worker:

1. revalida projeto, cenas, mídia, narração, legenda e licenças;
2. monta os argumentos do FFmpeg sem interpolação de shell;
3. escala e recorta para 9:16;
4. concatena as cenas;
5. incorpora a legenda;
6. normaliza o áudio para alvo de -14 LUFS;
7. exporta H.264/AAC com `faststart`;
8. grava o resultado como ativo do projeto.

O serviço `render-worker` possui volume compartilhado com a API no ambiente Docker.

### Prévia local

`RENDER_MODE=mock` executa o fluxo completo de validação, mas produz um manifesto JSON em vez de fingir que existe um MP4. O job termina como `mock_ready`, o projeto como `preview_mock` e a resposta expõe `preview_is_mock=true`.

Para render real:

```env
RENDER_MODE=ffmpeg
FFMPEG_PATH=ffmpeg
```

O container da API e do worker instala FFmpeg. Em produção, a imagem deve continuar versionada e passar por varredura de vulnerabilidades.

## Endpoints principais

| Método | Caminho | Finalidade |
|---|---|---|
| GET/POST | `/v1/video/voices` | Listar/criar perfis de voz |
| POST | `/v1/video/scripts/{id}/narration` | Gerar narração |
| GET/POST | `/v1/video/assets` | Biblioteca e upload licenciado |
| POST | `/v1/video/scripts/{id}/captions` | Gerar trilha de legendas |
| GET | `/v1/video/captions/{id}` | Consultar trilha |
| GET | `/v1/video/captions/{id}/export/{format}` | Exportar SRT/VTT |
| POST | `/v1/video/projects` | Criar projeto |
| GET | `/v1/video/projects/{id}` | Consultar projeto e cenas |
| POST | `/v1/video/projects/{id}/scenes` | Adicionar cena licenciada |
| POST | `/v1/video/projects/{id}/render` | Solicitar render idempotente |
| GET | `/v1/video/render-jobs/{id}` | Consultar job |

## Dados e migrações

PostgreSQL:

- `services/api/migrations/0003_video.sql`

D1:

- `drizzle/0003_video_pipeline.sql`

Entidades:

- `voice_profiles`;
- `media_assets`;
- `media_licenses`;
- `caption_tracks`;
- `caption_cues`;
- `video_projects`;
- `video_scenes`;
- `render_jobs`.

## Segurança e conformidade

- RBAC limita mutações a administrador, gestor e editor.
- Todas as consultas são filtradas por organização.
- Uploads têm tamanho, MIME e assinatura verificados.
- Caminhos de armazenamento são normalizados e confinados à raiz configurada.
- FFmpeg recebe uma lista de argumentos e `shell=False`.
- Licenças são obrigatórias e revalidadas no momento do render.
- Nenhuma mídia de banco, música ou voz externa é apresentada como conectada sem credenciais reais.

## Testes implementados

- geração e exportação monotônica de legendas;
- WAV mock válido e explicitamente identificado;
- rejeição de upload com assinatura incompatível;
- criação de perfil, narração, legenda e ativo licenciado;
- criação do projeto e da cena;
- render idempotente em modo mock;
- estado de prévia explicitamente marcado.

## Limitações conscientes

- O mock de TTS não produz fala audível.
- O modo mock não produz vídeo.
- Metadados técnicos de uploads (duração e dimensões) serão extraídos com `ffprobe` no endurecimento de produção.
- Integrações com bancos de mídia, músicas e TTS reais dependem de contratos, credenciais e licenças.
- A implantação produtiva deve fixar a imagem por digest e homologar a versão empacotada do FFmpeg.

## Próxima etapa

Fase 4 — central de aprovação, edição, reprovação, calendário, agendamento e notificações.
