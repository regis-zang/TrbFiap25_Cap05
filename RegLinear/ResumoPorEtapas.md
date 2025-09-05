📑 Resumo por Etapas
Etapa 001–003 – Importação e inspeção

Importa o arquivo CSV com os dados de gastos publicitários.

Cria o DataFrame df_raw e exibe a estrutura (linhas, colunas, primeiras observações).

Serve para checar se os dados foram carregados corretamente.

Etapa 004 – Normalização

Padroniza nomes de colunas (remove acentos, espaços, variações).

Seleciona e renomeia as variáveis principais: ano, mes, tipo_midia, gasto, aumento_vendas_mil.

Converte para tipos numéricos e prepara a base final (df).

Etapa 005 – Checagem de problemas

Identifica valores nulos, estatísticas descritivas e categorias únicas de mídia.

Detecta 3 valores faltantes em gasto.

Etapa 006 – Criação de features

Expande tipo_midia em colunas individuais (gasto_TV, gasto_Revista etc.).

Cria variáveis dummies de mês (mes_2 … mes_12) e tendência de ano (ano_trend).

Define três conjuntos de features (A: só gastos, B: gastos + meses, C: gastos + meses + ano).

Etapa 007 – Correlação

Monta a matriz de correlação e um heatmap.

Ajuda a identificar quais mídias têm relação mais forte com o aumento de vendas.

Etapa 008 – Gráficos de dispersão

Mostra a relação entre gasto por canal e aumento de vendas.

Permite ver linearidade, força da relação e outliers.

Etapa 009 – Treino inicial

Testa regressões lineares com validação cruzada (5-fold).

Compara os três modelos (A, B, C).

Modelo C se destaca (gastos + meses + ano).

Etapa 010 – Ajuste final

Treina o modelo vencedor em todos os dados.

Calcula métricas (R², RMSE) e lista coeficientes (impacto marginal de cada canal).

Etapa 011 – ROI por canal

Converte coeficientes em unidades adicionais por R$1.000 investidos.

Gera ranking de ROI: Google e Instagram lideram, canais tradicionais ficam atrás.

Etapa 012 – Validação

Cria gráficos Predito vs Observado e de resíduos.

Mostra que o modelo tem boa aderência.

Etapa 013 – Holdout

Divide a base em treino (80%) e teste (20%).

Confirma que o modelo generaliza bem (R² alto e erros aceitáveis).

Etapa 014 – Relatório para Marketing

Traduz os resultados estatísticos em texto executivo e acessível.

Entrega insights diretos: top 3 canais, confiabilidade do modelo e recomendações práticas.

Etapa 015 – Testes de normalidade

Aplica Shapiro, KS e Lilliefors nos resíduos.

Conclui que há desvios da normalidade, mas nada que invalide o modelo.

Etapa 016 – Diagnósticos estatísticos

Roda testes de heterocedasticidade (Breusch-Pagan), autocorrelação (Durbin-Watson), multicolinearidade (VIF).

Aponta colinearidade em canais tradicionais e necessidade de usar erros robustos.

Etapa 017 – Comparativo com dummies de mídia

Testa adicionar dummies de tipo_midia além dos gastos.

Ganho de R² foi pequeno (~0,3 p.p.), mostrando que não compensa a complexidade extra.

Etapa 018 – Simulador de orçamento

Cria uma função para prever vendas dado um orçamento por canal.

Exemplo: dividir R$100k entre Google, Instagram e Web.

Permite testar cenários práticos de alocação de verba.
