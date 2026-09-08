# BarSpec — Guia do programador (como está construído & porquê)

Uma visita guiada ao código do BarSpec: o que cada ficheiro faz, as decisões
de desenho e — o mais importante — **porquê** está construído assim. Escrito
para programadores e para quem está a aprender a criar uma aplicação web real
e útil a partir do zero.

Documentos complementares: [Guia do utilizador](USER_GUIDE.md) para *usar* a
app; o `README.md` como referência rápida de execução/testes/API.

> **Estado (2026-09-08):** migrações 001–012 enviadas — motor de unidades,
> UI de dimensões, lotes/xaropes (004), rendimento % (005), categorias (006),
> diluição (007), perfil do espaço (008), cozinha K1–K4 (009–011: doses +
> registo de perdas, P&L por secção, alergénios, fornecedores), auditoria
> (012), PT-PT, layout móvel, exportações/QR, fichas de treino,
> acessibilidade, cópias de segurança automáticas, **PIN do dono (S1)**.
> **158 testes verdes.** Cópias de segurança: locais apenas (decisão de V —
> sem destino offsite).

---

## 1. O que está a ver

```
barspec/
├── main.py            App FastAPI: rotas HTTP, validação, mapeamento de erros
├── db.py              Camada SQLite: cada query + corredor de migrações
├── pricing.py         Matemática PURA de €/ABV — sem I/O, sem estado
├── auth.py            PIN do dono (pbkdf2) + sessões por cookie assinado
├── exporters.py       .xlsx/.csv/QR — ficheiros do dono (custos incluídos)
├── migrations/        *.sql evolução de esquema, aplicada por ordem
├── static/            Frontend sem build: index.html, app.js, style.css
├── tests/             pytest: matemática, migrações, API, contagens, …
├── barspec.db         Ficheiro SQLite de dados (criado na 1ª execução)
├── Dockerfile / docker-compose.yml   execução portátil
└── docs/              Este guia + o guia do utilizador
```

**Stack:** Python + FastAPI + SQLite + JavaScript puro. Sem ORM, sem passo de
build, sem framework de frontend, sem servidor de base de dados. Poucos
ficheiros de Python, três de frontend. É esse o ponto.

---

## 2. A arquitetura, e porque é que é assim

O BarSpec é uma **app em camadas com um núcleo puro**:

```
Browser (static/index.html + app.js)
        │  fetch() JSON
        ▼
main.py  ─── rotas, validação Pydantic, mapeamento de estados HTTP
        │
        ▼
db.py    ─── SQLite: leituras/escritas, JOINs, migrações, impacto de preço
        │
        ▼
pricing.py ─── FUNÇÕES PURAS: custo, ABV, margem, preço sugerido, FBE
```

Duas regras comandam tudo:

### Regra 1 — a matemática do dinheiro é pura e vive num ficheiro

O `pricing.py` **não tem I/O, não importa db, não tem estado**. Cada função
recebe dicts/listas simples e devolve números. `line_cost()` não sabe o que é
uma base de dados; recebe um dict de linha com `amount_ml`,
`bottle_price_eur`, `bottle_volume_ml` e devolve €.

Porquê:
- **Testável.** Os testes de dinheiro (`tests/test_pricing.py`) chamam funções
  diretamente — sem DB, sem HTTP, sem preparação.
  `assert line_cost(...) == approx(...)`.
- **Uma fonte única de verdade.** O custo nunca é armazenado — é *derivado*
  de preço da garrafa ÷ tamanho × dose. Se guardasse o custo na receita, uma
  alteração de preço apodreceria todos os números guardados. Derivar faz do
  relatório de impacto um simples "recalcula com o preço novo", não uma caça
  a linhas desatualizadas.
- **Auditável.** Cada € é calculado por código que se lê e testa. É o
  requisito central de confiança do dono de um bar.

O frontend JS **espelha** algumas fórmulas (preço sugerido, margem, banda)
para pré-visualização ao vivo do cursor — mas o servidor é a autoridade; o
comentário no `pricing.py` diz exatamente isso. A duplicação é um trade
deliberado: feedback de UI instantâneo sem round-trip, com a resposta real
sempre recalculada no servidor ao guardar.

### Regra 2 — a verdade do preço vive na garrafa, não na receita

O esquema v0 original guardava cada ingrediente *na receita* com o seu preço
(tabela `ingredients`). Duas receitas que usassem Campari carregavam cada uma
um preço do Campari. Mudança de preço? Atualizar todas as linhas que diziam
"Campari". Renomear? Todas as linhas. É a armadilha da desnormalização, e a
migração 001 existe para sair dela.

Agora: **`stock_items` = uma linha por garrafa real que compra. `spec_lines`
apenas aponta para ela.** O JOIN em `_spec_lines_joined()` volta a ligar
nome/ABV/preço/tamanho na leitura. Consequências:

- Preço editado **uma vez** na garrafa → todas as receitas que a usam
  atualizam (JOIN).
- O **relatório de impacto** (PUT `/api/stock/{id}` → `impact[]`) calcula-se
  repetindo o custo de cada receita afetada com o preço antigo vs novo — zero
  mutação, pura recomputação.
- Apagar uma garrafa em uso é recusado (409) — esse JOIN partir-se-ia
  silenciosamente.

### Porquê SQLite e sem ORM

- **Sem servidor para correr.** A app inteira é um ficheiro. Os donos fazem
  cópias de segurança copiando um ficheiro; uma instalação num espaço é uma
  pasta + um processo.
- **Sem ORM significa que cada query é visível.** O `db.py` é SQL explícito.
  Para um código de ensino isto é ouro — lê-se exatamente o que toca no
  disco.
- **SQLite chega.** Um utilizador, um espaço, centenas de linhas. PostgreSQL
  aqui seria teatro de arquitetura. (Anti-objetivo: ver §9.)

### Porquê migrações em vez de "recriar a base"

O `PRAGMA user_version` controla a versão do esquema. No arranque o
`db.migrate()` percorre `migrations/*.sql`, aplica cada ficheiro numerado
acima da versão atual, cada um dentro de uma transação, e depois sobe a
versão.

O movimento subtil: **uma instalação nova percorre exatamente o mesmo caminho
que uma atualização.** O `SCHEMA` no `db.py` é deliberadamente a forma *antiga*
v0 (com a tabela `ingredients` legada) — assim a migração 001 (que normaliza e
remove `ingredients`) é exercitada em todas as instalações, novas ou antigas.
Não há um caminho "setup" e outro "migrate" que possam divergir.
Auto-verificável.

Os dados de semente só correm quando `specs` está vazia e escrevem pelo
esquema *novo* — uma base antiga com dados reais nunca é re-semeada, e uma
base nova recebe 5 receitas de demonstração que fazem o custo e o preço
demonstrarem logo.

### Porquê frontend sem passo de build

`index.html` + `app.js` (JavaScript puro) + `style.css`. Sem React, sem
bundler, sem npm install. Porquê:

- **O servidor não renderiza nada** — é uma API JSON; o frontend é um cliente
  fino sobre `fetch()`. Um framework acrescentaria peso de ferramentas, não
  valor.
- **Zero build = zero supply chain, zero upgrades que partem**, trivial de
  depurar, e qualquer programador o lê.
- **Uma página HTML, cinco vistas** alternadas por JS (`showView()`) — simples
  o suficiente para a UI inteira caber num ficheiro legível. Quando isto se
  tornar pequeno, o plano diz *então* rever — não antes.

O JS espelha alguma matemática de preços (§ Regra 1) e guarda a conversão de
unidade de apresentação (ml ↔ cl ↔ oz) só no cliente — a API só vê ml.

---

## 3. O modelo de dados, evoluído

**v0 (esquema base, mantido como `SCHEMA` para testar migrações):** `specs` +
`ingredients` (preços desnormalizados — a armadilha).

**Migração 001 — normalizar stock.** Cria `stock_items` (uma linha por
garrafa, `name UNIQUE COLLATE NOCASE`) e `spec_lines` (spec → stock_item +
`amount_ml`). Deduplica ingredientes em garrafas sem diferenciar maiúsculas,
preferindo linhas com preço real; reconstrói linhas 1:1 contra o JOIN; adiciona
`price_eur` + `target_gp` às specs; remove `ingredients`. Idempotente,
preserva dados.

**Migração 002 — contagens.** Adiciona `par_level REAL NULL` nos stock_items
(NULL = "não contado") e **instantâneos datados**: `stock_takes(id,
taken_at)` e `stock_take_lines(take_id, stock_item_id, full_bottles,
open_fraction)`. `open_fraction` está limitada a `(0, .25, .5, .75, 1)` — um
CHECK, seguro porque esses valores são exatos em vírgula flutuante binária.

Decisão de desenho que vale a pena sublinhar: **instantâneos, não estado.**
Uma contagem é uma linha datada no histórico — "o que tínhamos na segunda" —
não uma sobrescrita de "o que temos agora". Dois instantâneos = tendências,
movimento, sinal de stock morto. Estado de UI descartável nunca responderia a
"o que mexeu esta semana". (O endpoint de tendências diz: *a perceção aparece
à medida que o histórico cresce.*)

**Migração 003 — motor de unidades (enviado 2026-09-06).** Adiciona
`dimension` (volume|weight|count) aos stock_items e `unit` às spec_lines, com
tabelas de conversão canónica no `pricing.py` (cl→10 ml, oz→29,5735 ml,
dash=1 ml fixo, barspoon=5 ml fixo, kg→1000 g, piece=1). Uma regra de custo
para todas as dimensões — um espresso de café é 9 g de grão + 60 ml de leite +
1 peça de chávena. Linhas legadas fazem backfill como volume/ml — o teste de
migrações prova que 0 cêntimos mexem para dados pré-motor. A API agora aceita
`LineIn.unit` e `StockIn.dimension` e rejeita desencontros de dimensão (400).

**Migração 004 — lotes caseiros (enviado 2026-09-06).** `batches` (nome,
método, tamanho_ml, data, validade_dias) + `batch_lines`; `spec_lines` ganha
`batch_id` anulável e um CHECK de tabela que **exatamente um** de
stock_item_id/batch_id está definido (a reconstrução renomeia e recria a
tabela, copiando linhas 1:1). Uma linha de lote é ou **ligada a stock**
(stock_item_id → o custo deriva pelo motor, por isso açúcar por kg e Campari
por ml funcionam) ou **texto livre** com `cost_eur` digitado para essa
quantidade exata (água é €0 — o CHECK obriga a uma fonte de preço: ligada XOR
com custo). Custo de dose = `quantidade × (total do lote ÷ tamanho_ml)`;
lotes nunca aninham. `shelf_life_days` + `made_date` geram `days_left`
(negativo = passado do prazo; NULL = conserva-se). As linhas de dose das
receitas levam um marcador `serve_batch` explícito porque uma linha de
ingrediente de lote partilha legitimamente o `batch_id` do pai — o pricing não
pode confundir os dois (um bug de colisão de chaves apanhado em QA,
regressão-testeado).

**Migrações 005–007 (precisão do custo, enviadas 2026-09-06/07):**
`yield_frac` (aproveitamento do comprado: €6 ÷ (1000 g × 0,80) precifica carne
limpa), `category` nas specs (secções de carta, PUTs parciais não a apagam —
`exclude_unset`), `dilution_pct` (gelo: volume servido = receita ×
(1 + pct/100), ABV servido = ABV ÷ (1 + pct/100); custo inalterado).

**Migrações 008–012 (espaço + cozinha + segurança, enviadas 2026-09-07/08):**
perfil do espaço (nome, IVA % — título e rodapé da carta impressa); `servings`
nos lotes (custo por dose na folha de preparação) + `stock_adjustments`
(registo de perdas: delta canónico assinado + motivo); listas `allergens` +
`dietary` (14 UE, V/VE/GF — códigos neutros, nomes por idioma);
`supplier` nos artigos (lista de encomendas agrupada por fornecedor); e o
rasto de auditoria `audit_log` (só-adição: cada preço antigo → novo com
data/hora).

---

## 4. A matemática de € e ABV (o núcleo puro)

Tudo no `pricing.py`. As convenções no topo do ficheiro importam — leia-as:

- Dinheiro entra e sai como float, **arredondado só na saída**
  (`round(x, 2)`). A precisão intermédia nunca é destruída cedo.
- Volume ≤ 0 ou preço ≤ 0 ⇒ custo 0. Uma garrafa sem preço custa zero e
  *nunca parte a matemática* — a UI mostra então "defina o preço da garrafa".
- **Preço sugerido** = `custo ÷ (1 − target_gp)` arredondado **para cima** aos
  €0,50 mais próximos (`math.ceil(raw * 2) / 2`). Porquê ceil, não round? Um
  preço arredondado para baixo podia descer abaixo da margem alvo. Ceil
  garante: **se vender ao preço sugerido, a sua margem real ≥ alvo.** Esse
  invariante tem teste (`test_never_dips_below_target`).
- **ABV** é ponderado pelo volume: Σ(volume × abv) ÷ Σ(volume). Linhas de
  água/sumo diluem corretamente. A diluição por gelo é excluída de propósito —
  documentada, não fingida.
- **Banda de margem** (`good|ok|low|unpriced`) conduz os chips
  verde/âmbar/vermelho: ≥ alvo = good; até 10 pontos abaixo = ok; senão low.

**Matemática das contagens** (mesmo ficheiro, segunda metade):
- **FBE** (equivalentes de garrafa cheia) = `full_bottles + open_fraction`.
  Uma contagem "2 cheias + meia" = 2,5 FBE.
- **Falha de encomenda** = `ceil(par − FBE)`, mín. 0. Par 3, tem 2,5 ⇒
  encomendar 1. A guarda epsilon `1e-9` mata o ruído de floats para que
  *exatamente no par* encomende 0, nunca 1 (testado: `2.9999999999` ⇒ 0).
- **Dinheiro parado** = FBE em excesso × preço da garrafa — stock acima do par
  é dinheiro amarrado em garrafas em vez de no banco. Este número é o
  "e então?" da contagem.

---

## 5. A API (`main.py`)

Fina por desenho: os modelos Pydantic validam o pedido, uma chamada `db.*`
faz o trabalho, exceções tornam-se estados HTTP. Mapeamentos notáveis:

| Situação | Estado |
|---|---|
| Receita/garrafa/linha não encontrada | 404 |
| Nome de garrafa duplicado | 409 |
| Apagar garrafa ainda usada por receitas | 409 |
| Unidade desconhecida / desencontro de dimensão / par em artigo de peso | 400 |
| Contagem má (sem par, fração má, cheias negativas) | 400 |
| PIN em falta (gate S1) | 401 |
| Código de alergénio/dieta desconhecido | 422 |

As mensagens de erro são frases humanas (o FastAPI coloca-as em `detail`) e o
frontend mostra-as num toast — o browser nunca tem de adivinhar.

As rotas agrupam-se por recurso e leem-se como o domínio: `/api/specs`,
`/api/specs/{id}/lines`, `/api/stock`, `/api/stock/{id}/par`, `/api/batches`,
`/api/batches/{id}/lines`, `/api/stock-takes/{sheet|last|trends}`,
`/api/menu`, mais exportações, relatórios, auditoria e o gate `/api/auth/*`.
`GET /api/menu` é a vista **imprimível** (nomes + preços apenas — custos e
chips excluídos, símbolos de moeda omitidos por psicologia de carta).

**Gate S1 (middleware):** uma vez definido o PIN (hash pbkdf2 com sal por PIN,
260 mil iterações), *todas* as rotas `/api` devolvem 401 sem cookie de sessão
válido (HMAC, 14 dias); `/api/auth/*`, `/static` e `/` ficam abertos. O
segredo de assinatura é aleatório, gerado na primeira configuração e guardado
nas definições. A auditoria S2 escreve de dentro dos próprios mutadores do
`db.py` (preço antigo → novo comparado contra a linha pré-edição; no-ops
silenciosos).

---

## 6. Como flui um pedido (leia isto duas vezes)

`PUT /api/stock/{id}` — "o Campari passou de €19 para €25":

1. O `main.py` valida `StockIn` (Pydantic; `dimension` é um `Literal`, por
   isso uma dimensão absurda dá 422 antes da camada db — o QA apanhou-o uma
   vez a reportar um 409 enganador).
2. O `db.update_stock_item()` carrega a linha atual e regista `old_price`.
3. Preço mexeu → para cada receita tocada — **diretamente por linha de
   garrafa OU através de um lote que lista a garrafa** (dois níveis, um
   relatório de impacto) — repete `drink_cost()` com o preço antigo e o novo
   **em memória** (`_spec_lines_all(..., override=(stock_id, price))` →
   `impact[]`). Os custos dos lotes recalculam dos seus links de stock, por
   isso uma receita que despeje 30 ml de um lote à base de Campari também
   mexe.
4. O UPDATE executa, commit, fecha. Devolve `{"ok": True, "impact": [...]}`.
5. O frontend vê `impact.length > 0` → `showRipple()` renderiza "A alteração
   de preço afeta N receitas: Negroni €2,20 → €2,45 por dose" (matemática
   real da semente: gin 30 ml @ €22/700 + Campari 30 ml @ €19/700→€25/700 +
   vermute 30 ml @ €11/750 = €2,197 → €2,454, arredondado a 3 casas pela
   API).

Nenhum custo guardado foi atualizado em lado nenhum. É a Regra 1 a pagar a
renda.

---

## 7. Estratégia de testes (porque tem esta forma)

O `conftest.py` faz duas coisas inteligentes:

1. Define `BARSPEC_DB` para um caminho temporário **antes de qualquer import
   de db/main** — um import de teste nunca pode tocar no `barspec.db` real.
2. Expõe duas fixtures:
   - `fresh_db` — uma base nova construída pelo **caminho de init completo**
     (esquema base → todas as migrações → semente), por teste. Exercita o
     maquinismo real de atualização em cada execução.
   - `legacy_db` — constrói uma **base v0 real** (com `ingredients`, com um
     duplicado "Campari/campari" onde só uma linha tem preço) e depois corre
     `init_db()`. É o teste do dinheiro: se a repetição de migrações passar
     aqui, todos os ficheiros de espaço futuros atualizam em segurança.

Mapa da suíte (158 testes verdes em HEAD):

| Ficheiro | Protege |
|---|---|
| `test_pricing.py` | Matemática pura: custo, ponderação ABV, ceil-0,50 nunca abaixo do alvo, bandas de margem, FBE/encomenda/dinheiro parado |
| `test_migrations.py` | Repetição v0→última (001→012) byte-idêntica, dedupe, preservação 1:1, idempotência, sem re-semente |
| `test_api.py` | Smoke: estado da semente, CRUD, resolve-vs-cria em linhas, impacto, regras de cascata |
| `test_stocktake.py` | Portão do par, pré-preenchimento, matemática da encomenda, validação de frações, tendências/stock morto |
| `test_units.py` | Conversão canónica, guardas de dimensão (em uso 400, lixo 422), prova do café |
| `test_batches.py` | Custo derivado do lote, impacto de dois níveis, validade, guardas |
| `test_yield.py` | Matemática do rendimento + round-trip API |
| `test_categories.py` | Preservação em PUT parcial, duplicados, agrupamento da carta |
| `test_dilution.py` | Matemática da diluição + valores servidos no resumo |
| `test_exports.py` | Paridade .xlsx/.csv, QR SVG |
| `test_settings.py` | Round-trip do perfil do espaço + limites do IVA |
| `test_kitchen.py` | Doses → €/dose, guardas do registo de perdas |
| `test_report.py` | Margens da P&L por secção + stock morto |
| `test_allergens.py` | Códigos UE-14/dieta: 422s, preservação, duplicado, exportação |
| `test_supplier.py` | CRUD do fornecedor, linhas de encomenda levam-no, coluna na exportação |
| `test_audit.py` | Pista só-adição: detalhe antigo→novo, no-ops silenciosos, eliminações |
| `test_auth.py` | Gate S1: aberto sem PIN, 401 com PIN, fluxo login/logout, cabeçalhos |

A separação em três camadas (matemática pura / migrações / API) faz com que
uma falha diga *qual* camada está errada antes de começar a ler.

---

## 8. Coisas que parecem simples mas foram decisões

- **Faltar o mount estático foi um bug real** (histórico de commits): os
  assets davam 404 e a app servia sem estilo até o
  `app.mount("/static", ...)` chegar. A lição: cada camada de uma stack
  "simples" tem de ser ligada na mesma.
- **As frações ¼/½/¾ de garrafa aberta são exatas em vírgula flutuante
  binária** — é por isso que o CHECK é seguro (0,1 não seria). Escolher
  valores amigáveis tornou possível validar ao nível do esquema.
- **Par ≤ 0 ou vazio = não contado** (guardado NULL). Um alvo de zero não tem
  sentido num balcão de bar, por isso o modelo recusa representá-lo.
- **Artigos de peso ficam fora do percurso de contagem** (contam-se garrafas,
  *pesa-se* o stock — trabalho diferente). O código torna o limite explícito:
  par num artigo de peso dá 400 em vez de contar silenciosamente algo que
  devia ser pesado.
- **A carta impressa esconde os símbolos de moeda** — decisão de domínio
  (pistas de preço suprimem o consumo) implementada como sistema de classes
  CSS `no-print`.
- **Receita duplicada = sufixo " (cópia)"**, linhas re-apontadas para as
  mesmas garrafas de stock. Barato, e os testadores adoram.
- **Guardas de contagem por guardar** (`beforeunload` + confirmação na troca
  de vista) existem porque meia contagem de prateleira perdida é exatamente
  o que um gerente de bar odiaria perder. Pequena UX, empatia de domínio
  real.
- **UI PT-PT por dicionários de chaves** (toasts incluídos — um mapa central
  traduz os literais de feedback sem tocar nos pontos de chamada); o README e
  os guias são também PT-PT.

---

## 9. Anti-objetivos (contenção como arquitetura)

Do plano de desenvolvimento, e honrados no código: **Postgres · ORM ·
Alembic · React/Vue + passo de build · Redis · inventário/POS · funções
multi-utilizador · Stripe**. Cada um foi considerado e rejeitado para um
produto de espaço único, amigo do offline, com dados num ficheiro. A
disciplina não é "não podemos" — é "ainda não, e só quando um espaço pagante o
exigir" (portões das Fases B/C no plano).

---

## 10. Execução (deploy)

- **Dev:** uvicorn com `--reload`; ficheiro DB ao lado da app.
- **Docker:** `docker compose up -d --build` — a imagem copia os ficheiros de
  Python + migrações + static; os dados ficam montados como ficheiro SQLite
  simples em `./data/` (healthcheck bate em `/api/specs`). Porta 8780 do host
  para não chocar com a unit systemd do homelab em 8777.
- **Produção (homelab):** unit systemd a correr **/usr/bin/python3** (o
  SELinux bloqueia o sistema de executar o venv — 203/EXEC); dependências
  novas de Python instalam-se por dnf, nunca pelo venv (o venv é só para
  testes). PIN do dono: na primeira visita após um deploy de S1 a app pede
  para o definir; até lá fica aberta de propósito.
- **Cópias de segurança:** todas as noites às 03:17 (`barspec-backup.timer`)
  — instantâneo sqlite online para `backups/`, 14 mantidas, registo em
  `backups/backup.log`. Restauro: `sudo ops/restore.sh backups/barspec-*.db`.
- **Dados:** um ficheiro, override `BARSPEC_DB` para o caminho. Cópia de
  segurança = instantâneo online desse ficheiro; restauro = repor o ficheiro.

---

## 11. O que aprender com este código

Se está a aprender a construir apps assim, estude por esta ordem:

1. **`pricing.py` primeiro.** São funções puras sobre dados simples — a
   superfície mais fácil de entender, e guarda a matemática do domínio
   inteiro. Aprenda: *derive, não guarde*; arredonde só na saída; puro =
   testável.
2. **`tests/test_pricing.py`** — veja como a matemática é travada, incluindo
   os testes de invariante (nunca abaixo da margem alvo, ruído de floats no
   par).
3. **Esquema do `db.py` + `migrations/001`** — a história da normalização é a
   lição mais transferível: *uma verdade por conceito, referências não
   cópias*.
4. **`main.py`** — camada HTTP fina: validação à entrada, chamada de domínio,
   estado à saída.
5. **`auth.py`** — o gate do dono: hash pbkdf2 na definição, cookie HMAC na
   sessão, middleware que protege tudo menos as rotas públicas.
6. **`app.js`** — cliente fetch, troca de vistas, os espelhos JS
   deliberados.
7. **`conftest.py`** — isolamento de ambiente + repetição da base legada. É
   assim que se mudam esquemas sem medo.

A stack é deliberadamente aprendível: lógica Python → SQL/SQLite → FastAPI →
HTML/CSS/JS puro. Quatro camadas, cada uma com um trabalho claro. Crie o
hábito de perguntar "**que camada é dona disto?**" — se a resposta for difusa,
o desenho é difuso.

---

## 12. Apontadores do roadmap

A direção do produto, o raciocínio de mercado e o plano faseado vivem no
plano de desenvolvimento do vault
(`Projects/Bar-Tech-Venture/BarSpec-Vision-and-Dev-Plan.md`): a Fase A está
fechada (contagens, motor de unidades, lotes, precisão de custo, PT-PT,
cozinha K1–K4) e a segurança enviou o PIN (S1) e a auditoria (S2) — cópias de
segurança ficam locais (decisão de V). As Fases B/C (multi-espaço, VPS+Caddy,
autenticação por funções, PWA) estão deliberadamente condicionadas a um espaço
pagante real. Atualize este documento quando isso acontecer — o código terá
mudado de forma.
