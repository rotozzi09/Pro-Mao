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

## Prioritized backlog
### P0
- Implementar Google OAuth real com credenciais do projeto.
- Completar catálogo do prestador: serviços, preço, produto incluso e portfólio.
### P1
- Fluxo de propostas e aceite entre cliente e prestador.
- Avaliações e depoimentos vinculados a atendimentos concluídos.
- Autorização de uso de fotos por atendimento.
### P2
- Indicações entre usuários, notificações e filtros por localização.

## Next tasks
1. Implementar painel de catálogo do prestador.
2. Adicionar upload de fotos com autorização do cliente.
3. Criar propostas e acompanhamento do pedido.