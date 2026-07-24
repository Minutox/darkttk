# RC1 — Promoção e rollback

## Regra de decisão

A versão `1.0.0-rc.1` só pode ser promovida quando todos os gates obrigatórios do
`release-manifest.json` estiverem verdes na mesma revisão. Integrações externas
condicionais devem estar configuradas e validadas no ambiente-alvo ou permanecer
explicitamente desativadas.

## Pré-promoção

1. Fixar a revisão e uma imagem imutável para API e workers.
2. Confirmar backup PostgreSQL recente, checksum e teste de restauração.
3. Confirmar capacidade, latência e autenticação do PostgreSQL e Redis.
4. Validar secrets sem imprimir seus valores.
5. Aplicar `npm run release:check`.
6. Exigir CI, CodeQL, containers e RC E2E verdes.
7. Confirmar `AUTO_CREATE_SCHEMA=false`.
8. Registrar versão anterior, responsável, janela e critérios de abortar.

## Migrações

Aplicar `0001` até `0009` em ordem com parada no primeiro erro. A jornada RC E2E
repete essa cadeia em PostgreSQL vazio antes de iniciar a API.

As migrações desta RC são aditivas. Não executar downgrade destrutivo durante
rollback. Se uma correção de schema for necessária, usar nova migração
compatível para frente.

## Promoção

1. Aplicar migrações com bloqueio de concorrência.
2. Publicar API e workers com a mesma revisão.
3. Aguardar `/health/live` e `/health/ready`.
4. Executar a jornada autenticada: exchange, dashboard, operações, 2FA,
   inteligência editorial e rotação de token.
5. Publicar o frontend.
6. Verificar filas, erros, custos, auditoria e taxa de respostas 5xx.
7. Liberar tráfego gradualmente quando a plataforma suportar.
8. Registrar resultado e horário da decisão.

## Critérios de abortar

- Migração incompleta ou divergente.
- Readiness instável por mais de cinco minutos.
- Falha de autenticação, isolamento organizacional ou auditoria.
- Crescimento de 5xx, dead letters ou latência acima do SLO.
- Publicação sem aprovação humana.
- Divergência entre a revisão da API, workers e frontend.

## Rollback

1. Parar a promoção e preservar logs, revisão e imagem com falha.
2. Bloquear novas publicações e renders, sem apagar jobs.
3. Reativar a imagem imutável anterior da API e dos workers.
4. Reativar a versão anterior do frontend.
5. Não desfazer tabelas ou colunas; aplicar correção para frente se necessário.
6. Confirmar readiness, exchange autenticado, filas e uma consulta por
   organização.
7. Reabrir tráfego somente após os checks.
8. Registrar impacto, duração, decisão e ação corretiva.

## Pós-promoção

Monitorar por pelo menos uma hora: 5xx, P95, Redis, jobs falhos, custos,
recuperação de conta, auditoria e publicação. Depois, registrar a versão como
promovida ou voltar ao estado anterior.
