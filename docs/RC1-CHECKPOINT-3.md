# RC1 — Checkpoint 3: inteligência editorial e recuperação operacional

## Resultado

Este checkpoint fecha as pendências funcionais de inteligência editorial da RC1 e torna operacional a entrega de recuperação de conta por um provedor real configurável.

## Recuperação por e-mail

- `ACCOUNT_DELIVERY_MODE=resend` ativa a entrega pela API oficial do Resend.
- O token continua armazenado somente por SHA-256 e nunca é registrado em log.
- A resposta permanece uniforme para contas existentes ou inexistentes.
- Falhas do provedor causam rollback do token, sem deixar um código não entregue ativo.
- Produção exige `RESEND_API_KEY`, `ACCOUNT_EMAIL_FROM` e `PASSWORD_RECOVERY_URL`.
- `disabled` continua sendo o padrão seguro; `mock` continua proibido em produção.

## Rotação de códigos 2FA

- `POST /v1/auth/mfa/recovery-codes` exige um TOTP ou código de recuperação válido.
- A rotação revoga imediatamente todos os códigos anteriores.
- Oito novos códigos são exibidos uma única vez e persistidos somente por hash.
- A ação gera registro de auditoria.
- A interface em Configurações permite executar a renovação autenticada.

## Tendências autorizadas

- Cadastro explícito de fontes por API, RSS ou importação manual.
- URL dos termos e confirmação de autorização são obrigatórias.
- O sistema não executa scraping.
- Cada sinal registra crescimento, volume, concorrência, retenção, compartilhamento, sensibilidade, saturação, abordagem, público e validade.
- Sinais só podem ser vinculados a fontes ativas da própria organização.
- A nova tela de Tendências diferencia dados persistidos de prévia controlada.

## Séries

- Séries editoriais são persistidas por organização e podem ser associadas a um nicho.
- Nome é único por organização.
- Cadência e quantidade-alvo possuem valores e limites validados.
- A criação é auditada e protegida por RBAC.
- A interface apresenta continuidade, cadência e meta de episódios.

## Editor visual

- `PATCH /v1/video/projects/{project_id}/scenes/{scene_id}` atualiza tempo, corte, movimento, transição e texto.
- Intervalos inválidos são bloqueados.
- A duração do projeto é recalculada.
- A edição marca o projeto para nova composição e gera auditoria.
- A mídia permanece vinculada ao ativo previamente licenciado.
- `/api/studio` mantém JWT e identidade fora do navegador.
- A interface oferece prévia 9:16, área segura e controles de cena.

## Migração

Aplicar `0009_intelligence_series.sql`, que adiciona `trend_sources`, `trends`, `content_series`, índices e restrições de isolamento organizacional.

## Validação

- ESLint aprovado.
- Build Vinext aprovado.
- Teste de renderização server-side aprovado.
- Compilação sintática da API e dos testes aprovada.
- Novos testes cobrem autorização de fonte, ingestão de sinal, série, rotação de códigos e atualização de cena.
- A instalação local de dependências Python ficou sem resposta e foi interrompida; a suíte continua configurada para o CI.

## Limitações honestas

- O Resend só opera depois da configuração de uma conta, domínio/remetente e chave válidos.
- Conectores externos ainda precisam de credenciais e contratos próprios; este checkpoint entrega o núcleo seguro de cadastro e ingestão.
- O editor altera cenas existentes; upload e licenciamento continuam no fluxo da Biblioteca.
- Publicação no Sites depende da identificação correta da conta pelo conector.

## Próximo checkpoint

1. Executar e acompanhar a jornada E2E completa no CI.
2. Adicionar conectores autorizados específicos para fontes contratadas.
3. Implementar relatório final de promoção, rollback e evidências.
4. Validar a publicação em ambiente hospedado com credenciais reais.
