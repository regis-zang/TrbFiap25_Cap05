# A) SAC — execução imediata

## 1) Modelo (a partir do CSV já limpo)

- **Fonte**: `vendas_linha_petshop_2020_2024.csv`
    
- **Dimensões (com hierarquias)**
    
    - Tempo: Ano ▸ Trimestre ▸ Mês (usar coluna `data_pedido` para gerar hierarquia)
        
    - Produto: Categoria ▸ Subcategoria ▸ SKU/Produto
        
    - Cliente: Cliente (ou Segmento, se houver)
        
    - Geografia: Região País ▸ Estado ▸ Cidade
        
    - Canal de Venda
        
    - Centro de Distribuição / Responsável do Pedido (se relevantes ao negócio)
        
- **Medidas**
    
    - `Receita` = `valor_total_bruto`
        
    - `Itens` = `quantidade`
        
    - `Pedidos` = `count distinct cod_pedido` (no SAC, crie uma **Medida Calculada** ou **Contagem Distinta** em nível de visual)
        

## 2) Medidas calculadas (exemplos)

- **Ticket Médio** = `Receita / Pedidos`
    
- **Crescimento % (YoY)** = `(Receita - Receita(Período Anterior)) / Receita(Período Anterior)`  
    _(no gráfico de série temporal, ative comparação com período anterior ou crie medida com função de desvio de tempo)_
    
- **Participação por Categoria** = `Receita (Categoria) / Receita (Total)`  
    _(como “% of Grand Total” na visualização ou medida calculada com restrição de contexto)_
    

## 3) Storytelling (layout do Story)

- **Linha 1 (cards métricos)**: Receita (LTM/Total), Pedidos, Itens, Ticket Médio.

<center> <img src="img/Pasted image 20250810161727.png" width="800" height="500"> </center> <br>
    
- **Lateral (filtros)**: Tempo, Categoria, Canal, Geografia, Cliente.

    
- **Grade 3 col x 2 lin (gráficos)**:
    
    1. Série temporal: Itens × Pedidos (linhas) + Receita (eixo secundário).
       <center> <img src="img/Pasted image 20250811114629.png" width="800" height="500"> </center> <br>
	   
        
    3. Barras horizontais: Receita por Categoria.
        <center> <img src="img/Pasted image 20250811120344.png" width="800" height="500"> </center> <br>

        
    5. Mapa de calor: Receita por Estado/Cidade.
       <center> <img src="img/Pasted image 20250811134800.png" width="800" height="500"> </center> <br>
       
    7. Linha: Ticket Médio por mês.
   <center> <img src="img/Pasted image 20250811135415.png" width="800" height="500"> </center> <br>
  
        
    10. Barras: Top 10 Clientes por Receita.
          <center> <img src="img/Pasted image 20250811135738.png" width="800" height="500"> </center> <br>
	    
        
    12. Donut: Receita por Canal.
    13.  <center> <img src="img/Pasted image 20250811140344.png" width="200" height="200"> </center> <br>
      

## 4) Entrega Word (screenshots + explicações)

- Para cada visual: **título → insight → por que importa para Comercial → variação de filtro**.

- # Justificativas do Painel — _Mapa de Oportunidades (Pet)_ Analise Trab Fiap Fase0…
<center> <img src="img/Pasted image 20250811201527.png" width="1200" height="800"> </center> <br>


## Filtros (lado esquerdo)

- **Por que**: permitir leituras executivas com recortes por **Tempo, Forma de Pagamento, Região Brasil e Centro de Distribuição** — pilares que mudam o comportamento de consumo. Analise Trab Fiap Fase0…
    
- **Como usar**: destacar no topo os filtros aplicados para contextualizar cada insight (evita leitura fora de contexto). Analise Trab Fiap Fase0…
    

---

## Cards de KPI (linha 1)

- **Faturamento Bruto (R$)** — métrica de receita padrão para visão comercial; âncora para todas as comparações. _(R$ 76,56 mi no snapshot atual)._ Analise Trab Fiap Fase0… Analise Trab Fiap Fase0…
    
- **Pedidos (Distintos)** — volume de ordens, mede frequência de compra e base transacional. _(224.918 no snapshot)._ Analise Trab Fiap Fase0…
    
- **Itens Vendidos** — intensidade de consumo; suporte a mix e logística. _(893.494 no snapshot)._ Analise Trab Fiap Fase0…
    
- **Ticket Médio (R$)** — gasto por pedido; sinaliza upsell/cross-sell e política de preço. _(R$ 340,40 no snapshot)._ Analise Trab Fiap Fase0…  
    **Decisão habilitada**: metas por canal/categoria e planejamento de estoque sazonal.
    

---

## Gráfico 001 — Série temporal: Faturamento × Pedidos

- **Por que**: evidencia **sazonalidade** e **tendência**; identifica picos/vales para ações táticas (promoções, capacidade logística). Analise Trab Fiap Fase0…
    
- **Como ler**: correlação entre receita e pedidos mês a mês; atenção a meses com **descolamento** (ex.: receita sobe sem subir pedidos → preço/mix). Analise Trab Fiap Fase0…
    
- **Ação**: alinhar calendário comercial e abastecimento com meses de maior conversão.
    

---

## Gráfico 002 — Receita por **Categoria**

- **Por que**: mostra **mix** e oportunidades de **share**; base para sortimento e campanhas por linha. Analise Trab Fiap Fase0…
    
- **Como ler**: ranking por faturamento; observar **caudas longas** para bundle/kit. Analise Trab Fiap Fase0…
    
- **Ação**: reforçar top categorias e testar combos nas categorias intermediárias.
    

---

## Gráfico 003 — Receita por **Sub-Região**

- **Por que**: leitura **geográfica** para priorizar praça, frete e cobertura comercial. Analise Trab Fiap Fase0…
    
- **Como ler**: comparar barras por sub-região; metas podem seguir a **parcela de contribuição** de cada região. Analise Trab Fiap Fase0…
    
- **Ação**: calibrar mídia local e estoques regionais.
    

---

## Gráfico 004 — **Ticket Médio** (série)

- **Por que**: mede **valor por pedido** ao longo do tempo — proxy de pricing, mix e upsell. Analise Trab Fiap Fase0…
    
- **Como ler**: quedas persistentes sugerem ajuste de preço/kit; picos sazonais indicam campanhas eficazes.
    
- **Ação**: criar bundles por época e revisar descontos por canal.
    

---

## Gráfico 005 — **Top 10 Responsável do Pedido**

- **Por que**: foco em **performance comercial**; identifica quem puxa a receita e quem precisa de coaching. Analise Trab Fiap Fase0…
    
- **Ação**: replicar práticas do top-performer e metas específicas para a cauda.
    

---

## Gráfico 006 — **Forma de Pagamento**

- **Por que**: revela **preferência de pagamento** e impacto no custo/risco (taxas, chargeback, prazo). Analise Trab Fiap Fase0…
    
- **Ação**: incentivar meios com menor custo (ex.: Pix) onde há aderência; negociar taxas de cartão.
    

---

## Tabela de Calor — Detalhe por Sub-Região

- **Por que**: visão densa para **achados finos** (anomalias, outliers). Analise Trab Fiap Fase0…
    
- **Ação**: abrir os “blocos quentes” e criar planos táticos por praça/categoria.
    

---

### Nota de metodologia

Todos os insights devem sempre mencionar os **filtros ativos** exibidos no topo, para manter a rastreabilidade analítica do contexto de leitura.
    
- Inclua **visões filtradas** (ex.: Canal Online; Região Sul; Categoria “Rações”).
