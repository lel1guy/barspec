# BarSpec — Guia do utilizador

Gestor de receitas e custos para **bares, pubs, cafés e restaurantes**: guarde
as suas receitas (bebidas *e* pratos) uma vez, ligue-as ao que compra
realmente — à garrafa, ao quilo ou à peça — e deixe o BarSpec fazer a
matemática do custo, do preço e da contagem de stock. Nada de folhas de
cálculo, nada de re-precificar à mão quando um fornecedor sobe um preço.

**Leia isto se gere um espaço.** Explica o que a app faz, como usar cada ecrã
e o que significam os números. Se for programador, o
[Guia do programador](DEV_GUIDE.md) explica como está construída e porquê.

---

## O que o BarSpec resolve

| Tarefa | Sem o BarSpec | Com o BarSpec |
|--------|---------------|---------------|
| Custo de uma bebida | Palpite, ou Excel por receita | Automático: preço da garrafa ÷ tamanho × quantidade servida |
| Re-precificar quando um preço muda | Recalcular cada receita à mão | Editar a garrafa uma vez — um relatório de impacto lista cada receita afetada |
| Quanto cobrar | Instinto | Cursor de margem alvo → preço sugerido |
| Encomendar stock | Contar garrafas em papel, adivinhar o que comprar | Contagem vs par → lista de encomendas + total de dinheiro parado |
| O que vende vs o que fica parado | Memória de balcão | Movimento entre contagens + lista de stock morto |
| Preparações de cozinha (maionese, sopa, molhos) | Palpite por tabuleiro | O lote diz "rende 20" → €/dose real |
| Desperdício e derrames | Um mistério no fim do mês | Registo de perdas: artigo, quantidade, motivo, quando |
| Encomendas a fornecedores | Telefonar às cegas | Lista de encomendas agrupada por fornecedor |

---

## Ideias-chave (5 minutos)

**Receita** — uma bebida: nome, copo, método, decoração + linhas de
ingredientes. Cada linha é uma quantidade de ingrediente (ex.: 30 ml de
Campari).

**Stock** — uma linha por *garrafa real que compra* (ex.: "Campari, 25% ABV,
€19 / 700 ml"). É a fonte única de verdade do preço. Cada linha de receita
*aponta para* a garrafa de stock em vez de copiar o preço — quando o preço do
Campari muda, edita num único sítio e todas as bebidas que o usam atualizam
sozinhas.

**Custo** — para cada receita, o BarSpec calcula:
- **custo / dose** — quanto lhe custa uma dose em ingredientes
- **ABV** — a força real da bebida, ponderada pelo volume dos ingredientes
- **volume** — líquido total por dose

**Margem bruta (GP %)** — a percentagem do *preço de venda* que é lucro:
`(preço − custo) ÷ preço`. Se uma bebida lhe custa €1,50 e vende por €6,00, a
margem é 75%.

**Nível de par** — quantas garrafas de um destilado quer na prateleira (o seu
objetivo). Garrafas sem par não entram na contagem.

**Contagem (stock-take)** — percorrer a prateleira, contar o que tem mesmo e
comparar com o par. O BarSpec transforma cada contagem numa **lista de
encomendas**: o que comprar e quanto dinheiro está *acima* do par ("dinheiro
parado").

---

## Os ecrãs (barra lateral no desktop / barra inferior no telemóvel)

### Receitas — o seu livro de receitas

Coluna esquerda: todas as receitas, pesquisáveis. Clique para abrir. Cada
receita mostra:

- **Custo / dose** e **custo de lote** (escreva N doses para dimensionar —
  útil para lotes de eventos)
- **ABV** e **volume**
- **Painel de preço** (ver "Precificar uma bebida" abaixo)
- **Tabela de ingredientes** — quantidade, ABV, custo de cada linha, mais uma
  **barra de partilha de custo** que mostra que % do custo da bebida cada
  ingrediente consome (saber que o vermute daquele Negroni é 21% do custo é o
  tipo de coisa que isto mostra)

Botões: **Editar** (nome/copo/método/decoração), **Ingredientes** (adicionar/
remover linhas), **Duplicar** (copia como "(cópia)"), **Apagar**.

**Adicionar ingredientes:** escreva o nome da garrafa. Se já existir no Stock
liga à garrafa existente (os campos ABV/preço/tamanho escondem-se — a
garrafa é que os possui). Se for um nome que o BarSpec não conhece, ele cria
a garrafa por si — preencha ABV/preço/tamanho agora ou depois no Stock.

### Stock — a lista partilhada (garrafas, sacos, peças)

Uma linha por artigo: nome, ABV, preço €, tamanho, par. Tudo se edita no
próprio sítio — clique no campo, altere, clique fora (ou Enter).

- **O tipo importa** (topo do formulário + Adicionar): **Garrafa/keg**
  (volume, ABV), **Peso** (café, açúcar — sem ABV, tamanho em g/kg) ou
  **À peça** (limas). O tamanho é guardado de forma canónica (ml / g / peças);
  escreve-o na unidade que lhe der jeito (700 ml ou 0,7 l; 1 kg ou 1000 g).
- **Usado em** mostra quantas receitas usam o artigo.
- Artigos que **nenhuma receita usa** ficam esbatidos e podem ser apagados.
  Artigos em uso não podem ser apagados (remova-os primeiro das receitas).
- **Coluna Par**: defina quantos quer ter à mão. Vazio = não entra nas
  contagens. Artigos de peso ficam fora do percurso de contagem — contam-se
  garrafas e peças, *pesa-se* o stock.
- **+ Adicionar** para um novo. Primeiro o nome — "o preço e o tamanho podem
  esperar até ter a fatura."

**O relatório de impacto:** altere o *preço* de um artigo e aparece um painel
a listar cada receita cujo custo mexeu, antigo → novo por dose — **incluindo
receitas que usam um xarope caseiro que contém esse artigo**. É a resposta
instantânea a "o Campari subiu €2 — o que é que isso faz à minha carta?",
através de todas as camadas.

### Xaropes — xaropes e infusões caseiros

Precificar um xarope caseiro com um palpite vago de "€1" é como as margens
mentem. Um **xarope** é uma mini-receita: o custo é **derivado dos
ingredientes, nunca escrito à mão**.

- **+ Novo xarope**: nome, tamanho final (1 litro é o normal), validade em
  dias, data de produção, nota de método.
- **Adicionar ingredientes** por nome: se estiver no Stock **liga ao vivo**
  (açúcar por kg, Campari por ml — uma alteração de preço entra no xarope
  sozinha). Se não for stock, escreva o **custo € para essa quantidade**
  (água = €0).
- O xarope mostra **total €**, **€ por litro** e um **chip de validade** —
  dias restantes, vermelho depois do prazo, "conserva-se" sem validade.
- Numa receita, despeje-o como qualquer ingrediente: escolha o xarope,
  escreva a quantidade. Custo = o seu despejo × (total do xarope ÷ tamanho).

Um primeiro lote clássico: **xarope simples 1:1** — 500 g de açúcar (ligado
ou €0,45) + 500 ml de água (€0) → €0,45 por litro em vez de €3+ de comprado.

### Contagens — contar, encomendar, tendências

Três separadores:

**Contar** — o percurso. Todas as garrafas *com par* aparecem, pré-preenchidas
com a sua **última** contagem para só corrigir o que mudou. Para cada garrafa:

- Garrafas cheias: escreva, ou use os passos − / +
- Garrafas abertas: seletor de fração **0 / ¼ / ½ / ¾ / 1** (estimativa visual
  da garrafa aberta — meia garrafa de gin que resta conta como 0,5)
- Par editável na própria linha (mude-o a meio da contagem se a realidade o
  pedir)
- Coluna FBE: **equivalentes de garrafa cheia** = cheias + fração (2 cheias +
  meia = 2,5)

Carregue em **Guardar contagem** e o BarSpec salta para a lista de encomendas.

**Lista de encomendas** — da sua última contagem vs par:
- **A encomendar**: garrafas abaixo do par, com quantas garrafas cheias
  comprar (uma falha de meia garrafa encomenda na mesma 1 — compram-se
  garrafas, não metades)
- **Acima do par — dinheiro parado**: o que está acima do objetivo e o **€
  parado** aí
- **No par**: garrafas exatamente no objetivo

**Tendências e stock morto** — aparece à medida que o histórico cresce:
- **Movimento** entre as suas duas últimas contagens: por garrafa, o que foi
  usado (antes → agora, em garrafas, ml e €). Precisa de 2+ instantâneos.
- **Stock morto**: garrafas da sua lista que nenhuma receita usa — dinheiro
  na prateleira. Crie uma receita para elas ou deixe de as comprar.

### Carta — precifique tudo e depois imprima

Cada receita com custo, preço de venda e chip de margem. Escreva um preço
direto na linha, ou defina-o por receita nas Receitas. A caixa **Só com
preço** filtra. Depois **Imprimir carta**:

- Imprime **nomes das bebidas + preços apenas**. Os custos nunca aparecem na
  folha.
- Os símbolos de moeda são omitidos de propósito — pistas de preço suprimem o
  consumo (psicologia de carta).
- A barra lateral, os botões e a pesquisa escondem-se automaticamente na
  impressão.

Sob a carta, a **P&L por secção** mostra a margem média de cada categoria
(verde ≥60, âmbar ≥40, vermelho abaixo) e o **stock morto** em € — dinheiro
sentado na prateleira que nenhuma receita toca.

---

### Resumo — a página de atenção

A homepage responde a uma pergunta: *o que precisa de mim hoje?*

- **Abaixo do par** — artigos abaixo do alvo desde a última contagem, com o
  fornecedor (para saber a quem ligar). Clique numa linha para abrir o Stock
  já filtrado nesse artigo.
- **A expirar** — lotes (xaropes, preparações) cuja validade acaba em menos
  de 7 dias; ≤2 dias aparece a vermelho.
- **Perdas este mês** — o € registado no registo de perdas.
- **Idade da contagem** — "contado há 3 dias", ou um aviso se passou mais de
  uma semana.
- **Gráficos** — receita diária dos últimos 30 dias e GP% por categoria
  (verde ≥60%, âmbar ≥40%, vermelho abaixo), com o total da janela no topo.

Se um cartão diz que está tudo bem: ótimo, vai servir.

### Vendas — o dinheiro

1. **Registar vendas** — escolha a receita, a quantidade, adicione linhas e
   *Guardar dia*. Guardar outra vez o mesmo dia **substitui** (nunca
   reescreve o histórico: preços e custos ficam congelados no momento).
2. **GP real** — por receita e no total: quantidade, receita, custo, GP €,
   GP%, com os chips de margem.
3. **Encolhimento** — compara o stock *usado* entre as duas últimas contagens
   com o que as vendas explicam. A diferença em € é a fuga.

## Precificar uma bebida (o momento da compra)

Abra uma receita → o painel de preço tem um **cursor de margem alvo**
(40–95%). O BarSpec mostra um **preço sugerido** para essa margem —
arredondado **para cima** aos €0,50 mais próximos para a margem real nunca
descer abaixo do alvo.

1. Arraste o cursor até ao seu alvo (os bares de cocktails costumam usar
   70–80% de GP).
2. Clique em **usar** ao lado do preço sugerido, ou escreva o seu.
3. **Guardar preço.** O chip de margem pinta o resultado:
   - 🟢 verde = no alvo/acima · 🟡 âmbar = até 10 pontos abaixo ·
   - 🔴 vermelho = bem abaixo · cinzento = sem preço

O servidor é a autoridade: os preços, custos e margens que vê são calculados
no servidor, não pelo seu browser.

---

## Unidades: apresentação e escrita

No topo à direita: **ml / cl / oz** — converte a apresentação *e* a escrita de
volumes (o material é sempre guardado de forma canónica, por isso mudar nunca
altera os seus dados). Além disso, cada linha de receita tem a **sua**
unidade: volumes usam ml/cl/oz, ingredientes de peso usam **g/kg** (9 g de
café são 9 g, não "0 ml"), peças usam **peça**. As quantidades convertem-se
no sítio quando muda a unidade de uma linha — 30 ml passa a 3 cl, mesma dose,
mesmo custo. Quantidades de peso e de peça mostram a sua unidade na própria
linha da tabela, porque um cabeçalho único não consegue cobrir com honestidade
uma bebida de unidades mistas.

---

## Começar: os primeiros 30 minutos

*Este guia é orientado a tarefas (how-to). O porquê das decisões — custos
derivados, snapshots congelados, porque as encomendas não mexem no stock —
está em [WHY.md](WHY.md); a referência técnica é o
[Guia do programador](DEV_GUIDE.pt-PT.md).*

**Atalho (5 minutos, sem escrever nada):** corra a demonstração de um mês e
acompanhe com dados reais — 48 artigos, 30 dias de contagens e vendas, e uma
fuga de €100 escondida no relatório de encolhimento:

```bash
BARSPEC_DB=/tmp/argo-demo.db .venv/bin/python ops/seed_argo.py --month
BARSPEC_DB=/tmp/argo-demo.db .venv/bin/python -m uvicorn main:app --port 8791
```

**Do zero a uma carta com preços (30 minutos):**

1. **Defina o PIN do dono** *(1 min).* A app fica aberta até o fazer, de
   propósito — não se tranca de fora. Depois, PIN errado = nada. 🔒 nas
   Definições termina a sessão.
2. **Dê nome ao espaço** *(1 min)* — Carta → ☰ Espaço; sai impresso na carta.
3. **Adicione stock real** *(10 min)* — Stock → **+ Adicionar artigo**, uma
   linha por coisa que compra: uma garrafa (nome, ABV, preço, tamanho — ex.
   gin €23 / 700 ml), café ao quilo (*Peso* + rendimento % se houver
   desperdício de corte), uma caixa de cerveja (*Por peça*, tamanho 1, e
   **Comprar em packs?** 24 @ €15,36 → o custo por lata sai sozinho), um keg
   de 30 L, vinho à garrafa. Vá preenchendo o **fornecedor** — a lista de
   encomendas agrupa por ele.
4. **Crie as primeiras receitas** *(8 min)* — Receitas → **+ Nova receita**:
   nome, copo, método, e as linhas de ingredientes (ml/cl/oz/g/dash/peça —
   tudo converte). Para coisas simples há o **+ Produto** (escolher o artigo,
   a dose, o preço — um refrigerante ou um copo de vinho em três campos).
5. **Precifique com honestidade** *(2 min)* — defina a **margem alvo** (ex.
   75%) e carregue em *sugerido*: o BarSpec arredonda **para cima** aos €0,50
   seguintes, para a margem real nunca ficar abaixo do alvo. O chip de margem
   lê verde ≥ alvo, âmbar perto, vermelho baixo.
6. **Defina pars e faça a primeira contagem** *(5 min)* — Contagem: par =
   o que quer ter na prateleira, conte em garrafas inteiras + frações de
   aberta, guarde. A **lista de encomendas** aparece logo, agrupada por
   fornecedor, com o € de stock morto.
7. **Encomendar e receber** *(2 min)* — 📥 **Compras**: crie um pedido (os
   preços congelam nesse momento) e, quando a entrega chegar, carregue em
   **Receber**. Se o preço da fatura mudou, o BarSpec pergunta "guardado €11,00
   → fatura €11,80?" — um clique aplica e propaga por todas as receitas.
8. **Registe um dia de vendas** *(1 min)* — Vendas: introduza o que vendeu por
   receita; reenviar um dia substitui-o (nunca reescreve o histórico). O seu
   **GP real** e o **encolhimento** aparecem — stock usado entre contagens vs
   o que as vendas explicam.
9. **Convide a equipa em segurança** *(1 min)* — Definições → PIN de equipa.
   A equipa vê receitas e carta; custos, preços e margens são removidos na
   API — nunca chegam ao browser deles.

Quando o mês enche, o Resumo torna-se a primeira coisa que vê: artigos abaixo
do par com fornecedores, lotes a expirar esta semana, perdas em €, aviso da
idade da contagem — mais os gráficos de receita a 30 dias e GP por categoria.

Opcional mas vale a pena: use o **+ Produto** para meter os 60% aborrecidos da
carta (latas, refrigerantes, água, café) — a app só se paga quando o bar
*inteiro* está lá dentro, não só os cocktails.

---

## Boas primeiras rotinas

**1. Precificar uma bebida nova** → Receitas → + Nova receita → nome →
Ingredientes → adicione cada garrafa (nomes conhecidos ligam, nomes
desconhecidos criam garrafas) → Guardar → leia o custo/dose, o ABV e as
barras de partilha de custo.

**2. Fazer um xarope caseiro e despejá-lo** → Xaropes → + Novo xarope
(1 litro, validade 14–30 dias) → adicione ingredientes (nomes de stock ligam;
água é €0) → depois Receitas → abra qualquer bebida → Ingredientes → escolha
o seu xarope → 20 ml → a receita custa o xarope real, não um palpite.

**3. Re-precificar a carta depois de uma subida** → Stock → edite o preço da
garrafa → leia o relatório de impacto → para cada receita afetada, arraste o
cursor de margem → use o sugerido → Guardar.

**4. Criar disciplina de encomenda** → Stock → defina um par em cada garrafa
que conta → Contagens → Contar (corrija o que mudou) → Guardar contagem → a
lista de encomendas dá-lhe as compras da semana e o valor de dinheiro parado.

**5. Encontrar stock morto** → Contagens → Tendências (ou leia as linhas
esbatidas no Stock) → decida: crie uma receita ou deixe de o comprar.

---

## Definições na navegação

A página **Definições (⚙)** vive na barra de navegação: idioma, tamanho do
texto, unidade de apresentação, PIN de equipa, auditoria, ajuda e trancar.

## Compras e receção (📥)

A lista de encomendas diz *o que* comprar; aqui é onde compra de facto.

1. **Criar um pedido** — 📥 Compras → *+ Novo pedido* → fornecedor, linhas
   (artigo + quantidade), *Criar pedido*. O preço unitário fica **congelado
   nesse momento**.
2. **Receber a entrega** — quando chegar, abra 📥 Compras → **Receber**. O
   BarSpec registra (com entrada na auditoria) e fecha o pedido. Entrega
   parcial: o botão recebe o resto todo — para parcial, crie um pedido
   menor.
3. **Desvio de preço** — se o preço da fatura diferir do guardado, o BarSpec
   pergunta *"guardado €11,00 → fatura €11,80?"*. Um clique aplica e propaga
   por todas as receitas. Se não aplicar, nada muda — o pedido fica na mesma
   com o que pagou.
4. **Histórico de preços** — cada linha recebida é memorizada por artigo
   (*"quanto paguei pelo gin em março?"*).

Receber **não** mexe nos níveis de stock: as contagens são donas do físico,
os pedidos são o rasto do dinheiro — é isso que mantém o encolhimento honesto.

## Impressão, exportações e cartões de formação

- **Carta** — *imprimir* para a parede/mesa, ou partilhar o **QR** para o
  telemóvel do cliente. Defina primeiro o nome do espaço e o IVA (Carta → ☰).
- **Exportações de Receitas / Stock** — .xlsx e .csv para o contabilista ou
  um gestor de folha de cálculo. Só para o dono (contêm custos).
- **Cartões de formação** — imprima um baralho a partir de Receitas:
  ingredientes, método, copo, guarnição — **nunca custos ou preços**, seguro
  para ficar no balcão.
- **Ajuda na app** — Definições → Ajuda: FAQ curta PT/EN para a equipa, sem
  dinheiro por desenho.

## Página de definições (⚙)

- **PIN do dono** — definido na primeira utilização. 🔒 termina a sessão.
  Não há "recuperar PIN": a recuperação é parar a app e limpar o PIN na base
  de dados (tarefa de ops) — escreva o PIN num sítio seguro.
- **PIN de equipa** — ative para a equipa consultar receitas e carta sem ver
  dinheiro. Custos, preços e margens são removidos **na API** (nunca chegam
  ao browser da equipa) e todas as escritas devolvem 403.
- **Nome do espaço + IVA %** — sai impresso na carta.
- **Idioma** — EN / PT-PT, por browser. Os preços formatam-se corretamente
  nos dois (€9.50 vs €9,50).
- **Tamanho do texto** — A− / A / A+ para o ecrã no balcão.
- **Auditoria** — as últimas edições de preço e eliminações, antigo → novo,
  com data e utilizador. Só acrescenta: nada é reescrito.
- **Ajuda** — a FAQ dentro da app.

## Cópias de segurança e restauro

Todas as noites a app faz um snapshot do seu único ficheiro SQLite
(`barspec.db`) para `backups/` (14 guardados) sem parar o serviço. Restaurar
é um comando, no Guia do programador (`ops/restore.sh`). Como o espaço inteiro
vive num ficheiro, "backup" também significa: copie esse ficheiro para uma
pen antes de algo assustador. (Corre no dono/ops, não na UI.)

## Resolução de problemas

- **"Está com aspeto antigo / um botão não faz nada depois de uma
  atualização"** — cache do browser. Faça hard-refresh (Ctrl+Shift+R).
- **"Um custo está a €0,00"** — o artigo não tem preço, ou a linha é texto
  livre. Abra Stock, meta o preço; todas as receitas atualizam logo.
- **"A lista de encomendas está vazia"** — precisa de uma contagem primeiro
  (ou pars definidos). Só aparecem artigos com par acima de 0.
- **"O encolhimento dá um número grande"** — verifique por ordem: as duas
  contagens foram feitas a horas semelhantes (antes/depois do serviço)?
  Registou as vendas da janela toda? Houve entrega não registada como
  pedido? Se as três estão limpas, a fuga é real — é esse o objetivo.
- **"A equipa não vê preços"** — correto, por desenho. O modo equipa não tem
  dinheiro.
- **"Idioma errado / preços estranhos"** — Definições → idioma; a formatação
  é por browser.
- **"Esqueci-me do PIN"** — ver Definições: é reset de ops, não há fluxo na UI.
- **"Os números parecem velhos"** — o Resumo atualiza a cada visita; as
  outras vistas atualizam quando as abre. Na dúvida, hard-refresh.

## Glossário

| Termo | Significado |
|---|---|
| **Par** | O nível de stock que quer manter. A lista de encomendas é o par menos o que tem. |
| **FBE** | *Full-bottle equivalent* — garrafas inteiras + fração da aberta (¾ = 0,75). |
| **Stock morto** | Artigos na lista que nenhuma receita usa — dinheiro a dormir. |
| **Encolhimento** | Stock usado entre duas contagens vs o que as vendas explicam. A diferença, em €, é a fuga. |
| **GP / margem** | Lucro bruto: (preço − custo) ÷ preço. Chips verde ≥ alvo, âmbar perto, vermelho abaixo. |
| **ABV** | Teor alcoólico; o BarSpec pondera por volume (com diluição) para mostrar o que serve mesmo. |
| **Diluição** | Água do gelo — sobe o volume, baixa o ABV, não muda o custo. |
| **Rendimento %** | Parte aproveitável ÷ comprada (aparas, perda ao cozinhar). 1 kg a 80% = 800 g úteis. |
| **Lote (batch)** | Preparação caseira (xarope, infusão, mistura) com receita própria; as receitas podem servir-se dela. |
| **PO** | Pedido de compra — o que compra ao fornecedor, com preços congelados na criação. |
| **Desvio de preço** | A fatura discordar do preço guardado ao receber um pedido. |

## Perguntas frequentes

**"Diluição por gelo não incluída"?** O ABV/custo assumem o despejo como está
na receita. O derretimento do gelo e o desperdício são reais mas variáveis —
o BarSpec não os adivinha, de propósito. Limitação conhecida, documentada,
não escondida.

**Consigo desfazer uma eliminação?** Não. As eliminações são imediatas.
Duplique antes de experimentar numa receita de que gosta.

**Porque é que não consigo apagar uma garrafa?** Porque as receitas a usam.
Removê-la partiria silenciosamente todas as bebidas onde entra. Remova-a
primeiro das receitas.

**Os meus dados estão seguros se atualizar?** Sim — as alterações de esquema
aplicam-se como migrações ordenadas no arranque. Uma instalação nova percorre
exatamente o mesmo caminho de atualização que uma base antiga
(auto-verificável). Os testes cobrem a repetição do esquema v0 original.

**Quem vê os meus preços e margens?** A app exige o PIN do dono desde a
primeira configuração — sem o PIN, tudo devolve 401. E o histórico de
alterações de preço e eliminações fica registado (Definições → Alterações
recentes), antigo → novo, com data/hora.

**Multi-utilizador? Cloud?** Não — hoje é uma app local, de um único
utilizador. Um espaço, um ficheiro. Isso é uma vantagem para o mercado-alvo
(offline, sem subscrição, dados seus), e o plano para multi-espaço vive no
plano de desenvolvimento.

**O que vem a seguir?** A cozinha está fechada (doses por lote, registo de
perdas, P&L por secção, alergénios, fornecedores) e a segurança enviou o PIN
e a auditoria. Cópias de segurança: locais, todas as noites (decisão de V —
sem destino offsite). Veja o plano de desenvolvimento para o roadmap.
