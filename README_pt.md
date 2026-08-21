# Poker Analytics & Behavioral Audit SaaS 🃏 

Um sistema avançado de **Business Intelligence (BI)** e **Auditoria Comportamental via Inteligência Artificial** focado no ecossistema do Poker Profissional (jogadores, times e *stables*). 

Este software foi projetado para processar grandes volumes de históricos de mãos, encontrar vazamentos técnicos (*leaks*) de dinheiro, e utilizar agentes de IA para conduzir entrevistas psicológicas focadas em avaliar o nível de negação e vitimismo (*Tilt*) do jogador após períodos de perda (*downswings*).

---

## 🎯 Principais Funcionalidades

### 📊 Telemetry Dashboard (BI)
Painel denso focado em performance técnica com 11 visões, incluindo:
- **Saúde Geral:** KPIs globais como Lucro Total, bb/100, Mãos Jogadas e Tendências.
- **Motores Pré e Pós-Flop:** Métricas de agressividade e efetividade (VPIP, PFR, C-Bet, W$SD, WWSF).
- **Mapeamento de Rivalidade:** Ranqueamento de oponentes que mais extraem valor do herói e sistema de anotações (Tags).
- **Auditoria de Potes Grandes:** Filtros avançados para análise de decisões críticas no River.
- **MDA (Mass Data Analysis):** Análise do comportamento e tendências gerais da população de jogadores (Field).

---

## 🚀 Como Executar o Projeto

Existem duas formas de rodar o projeto: usando o Executável ou rodando a partir do código-fonte (Modo Desenvolvedor).

### 🟢 Opção 1: Usando os Executáveis (Recomendado para Usuários)
Você não precisa configurar bancos de dados ou instalar Python/Node.js. Tudo já vem empacotado e pronto para rodar.

1. Acesse a aba de **[Releases](../../releases/latest)** no GitHub.
2. Baixe o executável para o seu sistema operacional:
   - **Windows:** Baixe e execute o `PokerApp.exe`
   - **Ubuntu/Linux:** Baixe e execute o arquivo `PokerApp`
3. O servidor backend será inicializado e uma janela nativa do aplicativo se abrirá automaticamente!

---

### 🛠️ Opção 2: A partir do Código-Fonte (Para Desenvolvedores)

O projeto é dividido em um frontend (Next.js) e um backend (Python/FastAPI).

**1. Preparando o Backend (Python):**
Abra o terminal na pasta raiz e execute:
```bash
cd backend
python -m venv .venv
```
Ative a máquina virtual (no Windows PowerShell):
```bash
.\.venv\Scripts\Activate.ps1
```
*(No Linux use: `source .venv/bin/activate`)*

Instale as dependências e rode o servidor:
```bash
pip install -r requirements.txt
uvicorn src.api.main:app --reload
```

**2. Preparando o Frontend (Next.js):**
Abra um **novo terminal** na pasta raiz e execute:
```bash
cd frontend
pnpm install
pnpm run dev
```
*(O frontend será servido localmente e conectará automaticamente ao backend).*

---

## 🏗️ Stack Tecnológica

- **Frontend:** Next.js (React), Tailwind CSS, Shadcn/UI (Estética Premium Dark Mode B2B).
- **Backend:** Python, FastAPI.
- **Processamento de Dados:** DuckDB e Polars (Agregação ultra-rápida em Parquet).
- **Banco de Dados / Persistência:** SQLAlchemy.
- **Orquestração de Inteligência Artificial:** LangGraph & LangChain.
- **Empacotamento:** PyInstaller & PyWebView.

## 📄 Licença

Este projeto é de código aberto e está licenciado sob a **GNU Affero General Public License v3.0 (AGPLv3)**.
O uso, modificação e distribuição são permitidos, desde que todas as modificações ou serviços de rede derivados também sejam de código aberto sob a mesma licença. Esta licença garante a proteção do código enquanto o software é monetizado no modelo SaaS.
