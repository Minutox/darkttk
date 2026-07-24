# RC1 — Checkpoint 2: conta forte e ações persistentes

## Resultado

Este checkpoint fecha a base técnica de recuperação de conta, segundo fator TOTP e persistência das ações críticas de aprovação e agendamento.

## Recuperação de conta

- `POST /v1/auth/password-recovery/request` responde de forma uniforme para impedir enumeração de contas.
- Tokens possuem 256 bits de entropia, são armazenados somente por SHA-256 e expiram em 30 minutos por padrão.
- `POST /v1/auth/password-recovery/confirm` aceita o token uma única vez.
- A nova senha passa pela mesma política de força do cadastro.
- Tentativas e bloqueio da conta são limpos após a troca.
- Todos os refresh tokens ativos são revogados.
- A ação gera auditoria quando existe associação organizacional.
- O adaptador `mock` entrega o token somente fora de produção. Em produção ele é proibido no boot.
- Nenhum envio de e-mail é simulado como real: `ACCOUNT_DELIVERY_MODE=disabled` permanece o padrão.

## 2FA TOTP

- Segredo aleatório de 160 bits.
- Compatibilidade TOTP SHA-1, seis dígitos e janela de 30 segundos.
- Segredo criptografado em repouso pelo mesmo cofre lógico de tokens.
- Confirmação obrigatória antes da ativação.
- Prevenção de reutilização do mesmo passo TOTP.
- Oito códigos de recuperação de uso único; apenas hashes são persistidos.
- Login por senha exige TOTP ou código de recuperação quando habilitado.
- Ativação e desativação geram auditoria.
- O acesso pelo workspace continua usando a identidade autenticada da plataforma; o TOTP protege o fluxo próprio de e-mail e senha.

## Persistência das ações da interface

A interface hospedada nunca recebe o segredo de integração nem o token JWT da API.

- `POST /api/workflow` valida a identidade do workspace no servidor.
- Decisões são encaminhadas somente para IDs UUID e valores permitidos.
- Reprovação e solicitação de mudanças exigem justificativa.
- Agendamento valida projeto, data e fuso antes do encaminhamento.
- A API principal continua responsável por RBAC, conflito de horários, limite diário, auditoria e notificações.
- Em modo real, a interface carrega aprovações, calendário e notificações persistidos.
- Falhas de gravação não alteram otimisticamente o estado local.

## Área de segurança

`Configurações → Segurança` agora permite:

- consultar o estado do 2FA;
- gerar uma chave TOTP;
- confirmar o código do autenticador;
- exibir códigos de recuperação uma única vez;
- visualizar as garantias e a limitação atual do canal de recuperação.

## Migração

Aplicar `0008_account_security.sql` antes da promoção. A migração adiciona:

- `password_recovery_tokens`;
- `mfa_credentials`;
- índices de token, usuário e unicidade.

## Testes

Foram adicionados testes para:

- recuperação de senha de uso único;
- revogação de sessão após recuperação;
- exigência de segundo fator;
- consumo e bloqueio de replay de código de recuperação;
- build das rotas server-side;
- renderização do dashboard.

O download das dependências Python não concluiu dentro da janela disponível deste ambiente. A suíte Python permanece configurada no CI e não foi marcada falsamente como executada localmente.

## Próximo checkpoint

1. Conectar um provedor real de entrega de recuperação.
2. Adicionar regeneração autenticada de códigos de recuperação.
3. Executar a suíte Python e o E2E no CI.
4. Fechar tendências autorizadas, séries e editor visual.
