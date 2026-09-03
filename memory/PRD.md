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

## Prioritized backlog
### P0
- Associar propostas a estados de atendimento e aceite do cliente.
- Evoluir armazenamento de fotos para object storage dedicado em produção.
### P1
- Avaliações e depoimentos vinculados a atendimentos concluídos.
- Indicações entre clientes e prestadores.
### P2
- Indicações entre usuários, notificações e filtros por localização.

## Next tasks
1. Implementar painel de catálogo do prestador.
2. Adicionar upload de fotos com autorização do cliente.
3. Criar propostas e acompanhamento do pedido.