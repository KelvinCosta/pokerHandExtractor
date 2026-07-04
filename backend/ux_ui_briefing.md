# Poker Analytics & Behavioral Audit SaaS - UX/UI Briefing

## 1. Visão Geral do Produto
O projeto é um **SaaS B2B voltado para o universo do Poker Profissional** (focado em times de poker, *stables* e jogadores profissionais). Ele resolve dois problemas principais do mercado:
1. **Business Intelligence (BI) e Telemetria:** Processamento de grandes volumes de históricos de mãos de poker para encontrar gargalos técnicos e vazamentos de dinheiro (*leaks*).
2. **Auditoria Comportamental (IA):** Um sistema multi-agentes que detecta desvios matemáticos no curto prazo (gatilhos de *Tilt*) e conduz uma entrevista psicológica com o jogador para avaliar seu nível de negação e vitimismo.

## 2. Estado Atual (Stack Tecnológica)
Atualmente, o frontend é prototipado inteiramente em **Streamlit** (Python). O backend utiliza **DuckDB** e **Polars** para agregação ultra-rápida de dados (Camada Silver em Parquet), **SQLAlchemy** para persistência de relatórios e chats, e **LangGraph/LangChain** para orquestração da IA. 

O objetivo do novo design UX/UI é migrar este protótipo engessado do Streamlit para uma aplicação web moderna (ex: React, Next.js, Tailwind, Shadcn/UI, Tremor).

## 3. Arquitetura da Interface (O que precisa ser desenhado)

O sistema é dividido em dois grandes módulos que precisam de coesão visual, mas possuem fluxos de usuário distintos:

### Módulo A: Telemetry Dashboard (Hard Data & BI)
Um painel denso de dados técnicos de poker. Atualmente é dividido em 11 visões detalhadas:
- **Saúde Geral:** KPIs globais (Lucro Total, bb/100, Mãos Jogadas, Gráficos de Tendência).
- **Motores Pré e Pós-Flop:** Métricas cruciais de agressividade (VPIP, PFR, Gap, C-Bet, W$SD, WWSF).
- **Mapeamento de Vilões & Rivalidade:** Listagem de oponentes, ranqueamento de quem mais "toma" dinheiro do herói, e sistema de anotações (Tags).
- **Auditoria de Potes Grandes & River:** Filtros de mãos específicas de alto valor monetário e análise de decisões na última rodada de apostas.
- **População (MDA - Mass Data Analysis):** Análise global do comportamento de todos os oponentes cruzados.

**Requisitos de UX para o Módulo A:** 
- Alta densidade de informação sem poluição visual.
- Uso intenso de tabelas ordenáveis (DataTables), gráficos de linha de tempo (Time-series) e gráficos de barra para distribuição de ações.

### Módulo B: Behavioral Auditor (Chat com IA)
Um fluxo de auditoria focado em interação humana vs. IA.
- **Sidebar / Setup Inicial:** Formulário para filtrar os dados que serão enviados à IA (Nome do Jogador, Tipo de Jogo, Nível de Aposta, e Janela em Dias). Ao extrair, um "Motor Analítico" (Agente 1) gera um laudo invisível.
- **Área Central (Chat Socrático):** Uma interface de chat (estilo ChatGPT) onde o usuário conversa com um "Psicólogo/Inquisidor" (Agente 2). O Agente usa os dados para fazer perguntas investigativas sobre quedas de lucro ou desvios de agressividade recentes, induzindo o jogador a se explicar.
- **Encerramento / Laudo Final:** Um botão para "Encerrar Auditoria". Quando clicado, um "Psiquiatra Implacável" (Agente 3) avalia a transcrição do chat, some com a tela de chat e exibe um **Dashboard Clínico**:
  - Nível de Negação (Escala de 1 a 5).
  - Admitiu o Erro? (Sim/Não).
  - Conclusão Clínica e Recomendação de Coaching em formato de texto.

## 4. Persona e Requisitos Estéticos
- **Público-Alvo:** Homens, 20-40 anos, perfil analítico, matemáticos, investidores, e treinadores de e-sports.
- **Estética Desejada:** Premium, B2B, Tecnológica e Implacável. 
- **Dark Mode:** OBRIGATÓRIO. Jogadores de poker operam *grinds* noturnos de 10 a 12 horas. Telas claras causam fadiga visual. Tons de cinza escuro, chumbo, com detalhes de destaque em cores neons institucionais (ex: verde para lucro, vermelho para *downswings*/tilt).
- **Inspirações Sugeridas:** Bloomberg Terminal, Vercel Dashboard, interfaces de exchanges de Criptomoedas (Binance, Bybit) devido ao foco em finanças e alta performance.

## 5. Pedido para a IA de UX/UI
Gere propostas de layout, organização de navegação (Sidebars vs. Topbars), paleta de cores (Dark Theme), e especifique quais bibliotecas de componentes modernos (ex: Tailwind, Shadcn/UI, Tremor, Recharts) seriam ideais para acomodar:
1. Um dashboard BI complexo.
2. Uma interface de Chat fluida e integrada à extração de dados.
3. A apresentação de "Laudos Clínicos" que pareçam documentos oficiais emitidos pela plataforma.
