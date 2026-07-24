# RC1 — Checkpoint 4: fechamento e promoção controlada

## Resultado

O checkpoint final converte a RC1 em uma versão verificável e promovível sob
condições explícitas, sem confundir pipeline configurado com execução observada.

## Entregas

- Versão consolidada `1.0.0-rc.1`.
- Next.js atualizado e dependências transitivas corrigidas; auditoria de produção sem vulnerabilidades.
- Manifesto legível por máquina com gates, schema e integrações condicionais.
- Verificador local de consistência entre pacote, migrações, journal, ambiente e documentação.
- RC E2E usando PostgreSQL e Redis reais do CI.
- Aplicação das nove migrações antes do boot, com criação automática desativada.
- Jornada ampliada para identidade, 2FA, rotação de códigos, tendências, séries,
  operações, custos e refresh token.
- Diagnóstico da API preservado como artefato somente em falha.
- Plano detalhado de promoção e rollback.
- Matriz final de evidências e decisão de promoção condicionada.
- Tela de status da release na interface.

## Critério de aceite

A release só pode ser promovida quando todos os gates do
`release-manifest.json` estiverem verdes na mesma revisão. Credenciais externas
não configuradas permanecem bloqueadores explícitos, nunca simulações.

## Validação local

O fechamento executa:

- `npm run release:check`;
- lint;
- build e teste de renderização;
- compilação sintática da API e dos testes;
- validação do journal e do manifesto;
- inspeção do pacote final.

O `pytest` e a aplicação real das migrações PostgreSQL permanecem gates do CI
porque o ambiente local não concluiu a instalação das dependências Python.

## Publicação

A publicação hospedada só prossegue quando o conector Sites identificar a conta
e fornecer um projeto opaco válido.
