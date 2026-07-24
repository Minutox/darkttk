# Runbook de produção

## Incidente de API

1. Confirme `/health/live`. Se falhar, reinicie a instância e preserve os logs.
2. Confirme `/health/ready`. Se apenas banco falhar, interrompa deploys e valide conexões/pool. Se Redis falhar, pause publicações e renderizações antes de intervir.
3. Use o `X-Request-ID` para correlacionar logs e o registro em `operational_errors`.
4. Não grave stack trace, payload, token ou segredo na ação corretiva.
5. Depois da correção, execute smoke tests e marque o incidente como resolvido com uma ação concreta.

## Dead letter de publicação

1. Não reenvie manualmente sem conferir idempotency key e status do provedor.
2. Consulte o evento mais recente e o status oficial do TikTok.
3. Corrija credencial, permissão, mídia ou política.
4. Gere uma nova tentativa somente pelo fluxo autenticado e auditado.
5. Nunca altere um job mock para publicado.

## Backup diário

```bash
export DATABASE_URL='postgresql://...'
export BACKUP_DIR='/backup/darkttk'
./scripts/backup-postgres.sh
```

Copie `.dump` e `.sha256` para armazenamento externo versionado. Restrinja leitura, aplique retenção de 30 dias e monitore ausência de backup por mais de 26 horas.

## Restore testado

Use banco vazio e isolado:

```bash
export DATABASE_URL='postgresql://isolated-restore/...'
export BACKUP_FILE='/backup/darkttk/darkttk-YYYYMMDDTHHMMSSZ.dump'
export RESTORE_CONFIRMATION='RESTORE_ISOLATED_ENVIRONMENT'
./scripts/restore-postgres.sh
```

Após restaurar: aplicar somente migrações previstas, executar smoke tests, comparar contagens, verificar o checkpoint de auditoria e registrar RTO/RPO reais. Nunca aponte esse script diretamente para produção.

## Rollback

1. Interrompa a promoção e preserve a versão com falha.
2. Reative a imagem anterior imutável.
3. Não reverta migrações destrutivamente. Use correção compatível para frente.
4. Confirme readiness, filas e uma jornada autenticada.
5. Registre impacto, janela e decisão na auditoria.
