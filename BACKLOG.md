# Poker Telemetry Dashboard - Backlog & Tarefas Futuras

Este documento serve como radar para as próximas iterações e desenvolvimento do sistema.

## UI / UX (Frontend)
- [ ] **Ajustar Topbar**: O botão localizado entre a lupa de busca e o sino de notificações está sem atribuição clara. Definir sua função ou removê-lo.
- [ ] **Menu de Perfil**: O botão de perfil (Avatar) não tem função e mostra sempre as iniciais estáticas "HR". Deve ser dinâmico (puxar iniciais do usuário logado) e exibir o menu de usuário (Logout, Settings, Perfil, etc).
- [ ] **Sistema de Notificações**: Definir o que aparecerá no dropdown do sino (ex: laudos de IA prontos, solicitações de olheiros de times, alertas de tilt).

## Filtros e Classificação (Dashboard)
- [ ] **Filtro por Plataforma**: Adicionar suporte na UI e no Backend para filtrar mãos por plataforma específica (ex: GGPoker, PokerStars, WPT, etc).
- [ ] **Indexação de Torneios**: Ajustar a forma como os torneios (Buy-ins, Fichas, Bounty) são extraídos no ETL e mostrados no Dashboard (separar BBs de Fichas, ajustar gráficos financeiros).
- [ ] **Novos Tipos de Jogos**: Adicionar suporte/reconhecimento no parser para os outros tipos de jogos existentes nas plataformas.

## Milestone 5 (Visão de Longo Prazo)
- [ ] **Scouting & Stables (Times)**: Implementar a arquitetura B2B onde jogadores podem deixar seus perfis abertos para times (Opt-in Scouting).
- [ ] **Report Requests (Caça Talentos)**: Permitir que recrutadores de equipes solicitem laudos comportamentais profundos (via LangGraph AI) diretamente aos jogadores na plataforma.

## Pipeline ETL & Background Tasks
- [ ] **Extração Assíncrona (Parciais em Tempo Real)**: Mover o script `extractor.py` para um worker assíncrono (ex: Celery ou background task do FastAPI). Isso permitirá que o usuário continue navegando no Dashboard enquanto vê o progresso parcial das mãos sendo extraídas via WebSocket ou Polling (Baixa Prioridade).
