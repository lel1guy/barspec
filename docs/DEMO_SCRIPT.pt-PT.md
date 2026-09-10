# BarSpec — guião de demonstração (10 minutos)

Configura-se uma vez; depois é sempre a mesma visita. O espaço de
demonstração é **The Prancing Pony** — um bar ficcional com cozinha — com um
mês inteiro de uso já lá dentro.

- URL: **http://192.168.1.77:8791** · PIN do dono **1234**, PIN de equipa **2468**
- Reiniciar quando quiser: `ops/demo_reset.sh` (mês novo, determinístico)
- Antes de uma reunião: `GET /api/demo/status` → 7/7 verificações

---

## Os três momentos (por esta ordem — acumulam)

### 1. A vista do dinheiro — "isto é o que o mês fez" (~2 min)
**Homepage** (primeiro item da navegação).

> "Isto é a homepage: o que precisa de ti hoje. Artigos abaixo do par com o
> fornecedor a ligar, lotes a expirar esta semana, o € que fugiu este mês e
> a idade da última contagem. E aqui em baixo — 30 dias de receita e o lucro
> bruto por categoria."

Aponta os dois gráficos: **receita diária** e **GP por categoria** (vinho
~60%, cerveja ~75%, café ~90%).

### 2. Onde foge — "e aqui está o dinheiro que saiu a pé" (~2 min)
**Vendas** → a janela de encolhimento.

> "Duas contagens e as vendas pelo meio. Tudo o que a prateleira gastou e a
> caixa não explica aparece aqui — em euros. É a fuga. Todos os bares têm
> uma; a maioria dos donos só descobre no fim do ano."

Depois **Carta** → a linha de stock morto ("€45 parados que nenhuma receita
usa").

### 3. O ciclo de compra — "e apanha o fornecedor, não a ti" (~3 min)
**📥 Compras** (botão no topo).

> "Estes são pedidos de compra. O preço fica congelado quando encomendas.
> Quando a entrega chega, recebes linha a linha — porque as entregas são
> sempre parciais."

Escreve um número menor numa linha → **Receber**.
> "O pedido fica aberto com o resto por receber."

Recebe o resto. Se o preço da fatura diferir:
> "Pergunta: guardado €11, fatura €11,80 — aplicar? Um clique atualiza todas
> as receitas que o usam e a auditoria guarda antigo → novo."

### Fecho (~1 min)
**⚙ Definições** → PIN de equipa:
> "A tua equipa abre o mesmo URL, entra com este PIN e vê receitas e carta —
> com preços, custos e margens removidos no servidor, não escondidos no
> browser. As vendas são lançadas pelo dono ou gerente."

E depois: *"Trinta dias, um espaço, grátis. Continuas a contar tu; eu
configuro e ligo-te uma vez por semana. No fim dizes-me com honestidade se
pagarias por isto — e quanto vale para ti."*

---

## Perguntas que fazem sempre

| Pergunta | Resposta curta |
|---|---|
| "Fala com o meu POS?" | Hoje não é preciso: contagens + lançamento de vendas dão a fuga sem integração. A integração é fase seguinte. |
| "Onde ficam os dados?" | Num único ficheiro SQLite na tua máquina, com backup noturno. Sem nuvem. |
| "Quem vê os preços?" | Só o PIN do dono. O modo equipa é limpo no servidor (nunca chega ao telemóvel). |
| "E se a carta mudar?" | Adicionas o artigo em Receitas, preço, imprimes — minutos. |
| "Serve para a cozinha?" | Sim — rendimentos, itens a peso e custo de prato, no mesmo motor (secção Cozinha). |
| "Preço?" | (Resposta de piloto) "A configuração é feita por mim no piloto; depois, planos de €X/mês ou valor único + suporte." — decide o X antes da reunião. |
