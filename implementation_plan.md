# Master Roadmap: SaaS B2B de Poker

Para garantir a estabilidade do sistema e evitar o "efeito dominó" (quebrar o código todo de uma vez), nossa engenharia será baseada em **Marcos de Entrega (Milestones)** incrementais e totalmente testáveis.

## User Review Required

> [!IMPORTANT]
> Este documento servirá como a "Bússola" do projeto. Ao aprovar este plano, o **Milestone 1** se tornará a nossa tarefa imediata e ativa. Os demais marcos serão executados em sequência assim que validarmos que a fase anterior funciona perfeitamente com o Frontend no React. 
> 
> Você concorda com essa divisão cronológica das prioridades?

## Proposed Changes (Passo a Passo)

### 🚩 Milestone 1: A Fundação API (Foco Imediato)
Neste momento ignoramos usuários e equipes. O foco é apenas fazer o backend e o React conversarem.
- [ ] Criar a estrutura base do `FastAPI` (CORS e inicialização).
- [ ] Criar modelos `Pydantic` para receber os filtros do React (ex: datas, stakes).
- [ ] Refatorar os painéis do Streamlit (`render_health`, `render_preflop`) para retornarem JSON em rotas **POST**.
- [ ] Refatorar o Chat Socrático para rotas API (`/start`, `/chat`, `/complete`).
- **Validação:** O React consegue mostrar os gráficos e conversar com a IA acessando os dados brutos.

---

### 🚩 Milestone 1.5: Extrator Agnóstico e Tratamento de Identidade
Antes de criarmos o Banco de Dados com usuários, precisamos preparar a fundação dos dados para aceitar múltiplas plataformas e associar as mãos processadas ao nome real do dono do arquivo, garantindo a integridade e segurança analítica.

#### User Review Required
> [!IMPORTANT]
> **Identidade do Hero:** Como a conversão de "Hero" para o `nickname` real será no momento da extração dos TXT para JSON/Parquet, e o `extractor.py` atualmente varre a pasta global `bronze`, precisaremos passar o "Nickname do Usuário Dono da Pasta" para o Extrator. Como não temos o banco de dados ainda, testaremos via terminal passando um parâmetro no Python (ex: `python extractor.py --user_id KelvinCosta --platform ggpoker`). Tudo bem testarmos assim por enquanto?

## Proposed Changes

### `backend/extractor.py` e `backend/src/parser/`
- Refatorar `extractor.py` para receber argumentos: `player_nickname` e `platform`.
- Criar a camada agnóstica de `Tokenizer`: Utilizar o padrão Factory para selecionar o Tokenizer com base na `platform` (atualmente com a classe `GGPokerTokenizer`).
- Modificar o fluxo de conversão e parseamento para injetar o `player_nickname` em todas as ações listadas como "Hero", garantindo a despoluição dos dados.
- Adicionar o campo `platform` e `player_nickname` em todas as entidades persistidas no JSON.

### `backend/bridge_duckdb.py`
- Adicionar a nova dimensão de análise `platform` na tabela e salvar no arquivo Parquet.

### `backend/src/api/`
#### [MODIFY] [filters.py](file:///c:/Desenvolvimento/DataScience/pokerHandExtractor/backend/src/api/schemas/filters.py)
- Adicionar `platforms: Optional[List[str]] = None` no modelo Pydantic.

#### [MODIFY] [dependencies.py](file:///c:/Desenvolvimento/DataScience/pokerHandExtractor/backend/src/api/dependencies.py)
- Ler a propriedade `platforms` e aplicar um filtro adicional no Polars, garantindo o agrupamento por plataforma solicitado.

## Verification Plan

### Testes Manuais
- Rodar o extrator no terminal com o parâmetro `--player_nickname "Kelvin"` e validar se os JSON/Parquet gerados substituíram "Hero" e incluíram a coluna `platform`.
- Bater na rota `/api/dashboard/health` enviando `{"hero_name": "Kelvin", "platforms": ["ggpoker"]}` e verificar o retorno dos dados reais.

---

### 🚩 Milestone 2: Infraestrutura Multilocatário (Banco de Dados e Datalake Dinâmico)
Nesta fase, prepararemos o terreno (ainda invisível para o usuário final no React) para suportar múltiplas pessoas e equipes no mesmo sistema.

#### User Review Required
> [!IMPORTANT]
> **Simulação de Autenticação:** Como ainda não implementamos JWT (Milestone 3), precisaremos simular a identidade do usuário na API. Propomos adicionar um campo `user_id: str = "default_user"` nas requisições da API para que o backend saiba de qual pasta `/silver/{user_id}` deve puxar o Datalake. Você concorda com esse mock temporário?

## Proposed Changes

### 1. `backend/src/database/` (Camada Relacional - SQLite)
- **`models.py`**: Criar as tabelas `User`, `Team`, `TeamMember`, e `Invitation`. Manteremos a tabela `Player` anterior mas ela será refatorada para integrar ao `User` ou atuará como alias.
- **`session.py` (Novo)**: Criar a configuração do SQLAlchemy (`create_engine`, `sessionmaker`, `get_db()`) apontando para um SQLite local (`app.db`).

### 2. Datalake e ETL Multilocatário
#### [MODIFY] [extractor.py](file:///c:/Desenvolvimento/DataScience/pokerHandExtractor/backend/extractor.py) e [loader.py](file:///c:/Desenvolvimento/DataScience/pokerHandExtractor/backend/src/etl/loader.py)
- Alterar a lógica de salvamento. Em vez de salvar em `/silver/hands_*.parquet`, salvaremos em `/silver/{user_id}/hands_*.parquet`. O extrator passará a receber `--user_id` via linha de comando.

### 3. FastAPI (Leitura Dinâmica)
#### [MODIFY] [dependencies.py](file:///c:/Desenvolvimento/DataScience/pokerHandExtractor/backend/src/api/dependencies.py) e [data_loader.py](file:///c:/Desenvolvimento/DataScience/pokerHandExtractor/backend/src/dashboard/data_loader.py)
- Remover o carregamento estático e global do `AppState.df_hands` no startup (`main.py`).
- Refatorar `get_filtered_df` para usar `pl.scan_parquet(f"{DATALAKE_SILVER}/{user_id}/*.parquet")`. Isso garante que a API só carregue para a memória os dados do usuário que fez a requisição.

#### [MODIFY] [filters.py](file:///c:/Desenvolvimento/DataScience/pokerHandExtractor/backend/src/api/schemas/filters.py)
- Adicionar `user_id: str = "default_user"` no payload.

## Verification Plan
1. Rodar `extractor.py --platform ggpoker --hero_name Kelvin --user_id 123` e verificar se a pasta `/silver/123/` foi criada.
2. Fazer um request POST para `/api/dashboard/health` passando `{"user_id": "123", "hero_name": "Kelvin", "platforms": ["ggpoker"]}` e garantir que os dados de Kelvin retornaram com sucesso e que a performance via `scan_parquet` se manteve instantânea.
3. Inspecionar o arquivo `app.db` com DBeaver/SQLiteViewer para garantir que as tabelas do SQLAlchemy foram geradas corretamente.

---

### 🚩 Milestone 3: Autenticação e Blindagem de Dados (Segurança)
Aqui o sistema ganha "fechaduras".
- [ ] Implementar sistema de login JWT (Tokens de Segurança) no FastAPI.
- [ ] Proteger **todos** os endpoints do Milestone 1: a API passará a exigir o Token do React.
- [ ] Ligar a extração do DuckDB ao Token: o jogador logado só conseguirá gerar gráficos se o arquivo existir na pasta `silver/{seu_user_id}`.
- **Validação:** Tentativas de acesso sem login darão Erro 401. Um usuário não conseguirá ver os dados de outro.

---

### 🚩 Milestone 4: Motor de Equipes (O Modelo de Negócios)
A regra de negócios complexa entra aqui, com o terreno de segurança já preparado.
- [ ] Criar as rotas de Gestão de Equipe (Criar Time, Listar Membros).
- [ ] Implementar a rota de Convite com a trava de exclusividade (Bloqueio se o jogador estiver em outro time).
- [ ] Implementar a rota do Jogador (Aceitar Convite -> Double Opt-In).
- [ ] Implementar a rota de Saída/Demissão: gera o snapshot financeiro final de lucro e prejuízo com base nas datas de entrada e saída.
- **Validação:** Testes de ponta-a-ponta garantindo que jogadores blindados não recebem convites duplicados e que o relatório financeiro de rompimento de contrato calcula os lucros corretamente.

---

### 🚩 Milestone 5: Permissões de IA e Relatórios
Ligando a Gestão aos Laudos da Inteligência Artificial.
- [ ] Garantir que o "Gestor" do time consiga chamar a API para baixar e ler os Laudos Clínicos gerados pelos jogadores de sua equipe.
- [ ] Ocultar dados pessoais se necessário e refinar o painel analítico do Gestor (que verá o lucro agregado da equipe).
- **Validação:** Teste de permissão cruzada entre cargos diferentes no frontend.
