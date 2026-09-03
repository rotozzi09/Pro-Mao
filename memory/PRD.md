# ProMão — Product Requirements Document

## Original problem statement
Criar uma ferramenta para prestadores de serviços gerais e clientes, com cadastro por perfil, categorias, preços, contratação, avaliações, recomendações e portfólio com autorização de divulgação.

## Architecture decisions
- React 19 + CSS responsivo no frontend, com experiência inicial orientada à escolha de perfil.
- FastAPI + MongoDB no backend, usando `MONGO_URL` e `DB_NAME` existentes.
- Autenticação inicial por e-mail/senha, com sessão JWT em cookie httpOnly.
- Google fica preparado visualmente e no modelo de usuário, aguardando credenciais OAuth.

## User personas
- Cliente: quer encontrar profissionais confiáveis, publicar necessidades e avaliar atendimentos.
- Prestador: quer apresentar serviços, preços, portfólio e construir reputação.

## Core requirements (static)
- Escolha entre cliente e prestador no cadastro.
- Categorias de limpeza, elétrica, hidráulica, pintura, jardinagem, montagem e outras.
- Busca por categoria, prestadores recomendados e publicação de necessidade.
- Preço do serviço com possibilidade futura de incluir produto conforme exigências do cliente.
- Avaliações, depoimentos, indicações e fotos com autorização.

## What's been implemented (2026-09-03)
- Tela inicial ProMão com identidade visual, imagem de serviço, escolha de perfil e navegação.
- Cadastro/login por e-mail e senha, logout, sessão persistente e perfil do usuário.
- Catálogo de categorias, prestadores recomendados e filtros por categoria.
- Formulário autenticado para publicar necessidade de serviço.
- Estrutura backend para usuários, serviços, prestadores, pedidos e avaliações.
- Vínculo Google sinalizado como fluxo preparado, ainda sem OAuth real.

## What's been implemented (2026-09-03, phase 2)
- Catálogo real do prestador com categoria, preço, produto incluído e exigências do cliente.
- Painel do prestador com pedidos abertos e envio de propostas com preço, prazo e condições.
- Upload de foto com legenda e e-mail do cliente; fotos começam privadas e aguardam autorização.
- Área do cliente para autorizar a divulgação de fotos vinculadas ao seu e-mail.
- Login Google real via OAuth gerenciado, troca server-side do `session_id` e cookie de sessão.

## What's been implemented (2026-09-03, phase 3)
- Aceitação de propostas pelo cliente (POST /api/offers/{id}/accept), com propostas concorrentes marcadas como "não selecionadas" (visíveis).
- Confirmação de conclusão em duas etapas (cliente + prestador) com estado do pedido virando "Concluído" quando ambos confirmam.
- Novo endpoint GET /api/offers/mine para o prestador ver todas suas propostas com status.
- Sistema de avaliações vinculado ao atendimento concluído (nota 1-5, depoimento mínimo 10 chars, filtro de linguagem educada, uma avaliação por atendimento).
- Endpoint agregador GET /api/providers/{id}/reviews (média e total).
- Correções: validação de ObjectId (400 em vez de 500), authz em GET /requests/{id}/offers, remoção de projeções que estavam ocultando dados de catálogo/portfólio, toast auto-dismiss, link "Entrar" visível no mobile.

## What's been implemented (2026-09-03, phase 4)
- Perfil público aberto para prestadores em `/prestador/:id`, com catálogo, preços, portfólio autorizado, avaliações, indicações da comunidade e link compartilhável.
- Endpoints públicos e sociais: `GET /api/providers/public/{id}`, `POST /api/recommendations`, `GET /api/recommendations/mine` e `GET /api/notifications/mine`.
- Indicações da comunidade: clientes e prestadores podem indicar um prestador para outra pessoa por nome/e-mail; prestadores não podem autoindicar; mensagens passam pela mesma validação de linguagem educada.
- Notificações por e-mail integradas via Resend com envio real quando `RESEND_API_KEY` e `SENDER_EMAIL` existirem; sem credenciais, o sistema registra a notificação como `skipped` sem quebrar o fluxo.
- Propostas criadas/aceitas agora também registram notificações; duplicidade de proposta do mesmo prestador no mesmo pedido é bloqueada.
- UI do prestador mostra cartão de compartilhamento do perfil público e indicações recebidas; cards de prestadores reais abrem o perfil público.
- Correções adicionais: botão de avaliação passa para estado "Atendimento avaliado", contagem completa de recomendações, toast estabilizado em navegação e auto-dismiss validado.

## Prioritized backlog
### P0
- Ativar credenciais reais de e-mail (`RESEND_API_KEY`, `SENDER_EMAIL`) quando o domínio/remetente estiver pronto.
### P1
- Evoluir armazenamento de fotos para object storage dedicado em produção.
- Melhorar descoberta por localização/bairro e distância.
### P2
- Histórico avançado de notificações na interface e preferências de recebimento.
- Filtros de disponibilidade/agenda dos prestadores.

## Next tasks
1. Configurar remetente real de e-mail para envio efetivo das notificações.
2. Integrar object storage para fotos do portfólio.
3. Adicionar filtros por localização/disponibilidade para melhorar matching.