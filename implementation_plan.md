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

### 🚩 Milestone 2: Infraestrutura Multilocatário (Banco de Dados)
Começaremos a preparar o terreno (ainda invisível pro usuário final) para suportar múltiplas pessoas.
- [ ] Criar no SQLAlchemy as tabelas centrais: `User`, `Team`, `TeamMember` e `Invitation`.
- [ ] Refatorar a lógica do Datalake para deixar de ser uma pasta global (`/silver/*.parquet`) e suportar injeção dinâmica de caminhos (`/silver/{user_id}/*.parquet`).
- **Validação:** O banco de dados consegue salvar relações entre times e o DuckDB não quebra ao ler pastas dinâmicas.

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
