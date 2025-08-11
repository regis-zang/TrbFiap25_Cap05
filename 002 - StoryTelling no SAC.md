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

<center> <img src="img/Pasted image 20250810161727.png" width="600" height="300"> </center> <br>
    
- **Lateral (filtros)**: Tempo, Categoria, Canal, Geografia, Cliente.

    
- **Grade 3 col x 2 lin (gráficos)**:
    
    1. Série temporal: Itens × Pedidos (linhas) + Receita (eixo secundário).
	    ![[Pasted image 20250811114629.png]]
        
    2. Barras horizontais: Receita por Categoria (com % do total).
	    ![[Pasted image 20250811120344.png]]
        
    3. Mapa: Receita por Estado/Cidade.
        ![[Pasted image 20250811134800.png]]
    4. Linha: Ticket Médio por mês.
    5. ![[Pasted image 20250811135415.png]]
        
    6. Barras: Top 10 Clientes por Receita.
	    ![[Pasted image 20250811135738.png]]
        
    7. Donut: Receita por Canal.
        ![[Pasted image 20250811140344.png]]

## 4) Entrega Word (screenshots + explicações)

- Para cada visual: **título → insight → por que importa para Comercial → variação de filtro**.
    
- Inclua **visões filtradas** (ex.: Canal Online; Região Sul; Categoria “Rações”).
