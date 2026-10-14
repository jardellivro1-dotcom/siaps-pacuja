# Metodologia aplicada

**Norma:** Nota Técnica nº 8/2026-DEAPS/SAPS/MS (assinada em 29/05–01/06/2026), que revoga a NT nº 6/2025.
Base legal: Portaria GM/MS nº 3.493/2024 (alterada pelas Portarias GM/MS nº 6.907/2025 e 7.799/2025).
**Versão da regra no código:** `config.METODOLOGIA["id"] = "NT8-2026"`, gravada no manifesto e exibida no painel.
Quando uma nova NT passar a valer, crie nova versão (ex.: `NT9-2027`), mantenha a anterior documentada e
**não reprocesse resultados históricos oficiais** — eles ficam em `data/raw/`.

## 1. Mensal × quadrimestral
- Resultados **mensais** servem a monitoramento (NT 2.3). Este painel não usa valores mensais (não são públicos).
- Resultado **quadrimestral** = **média dos meses** monitorados (NT 2.4, 3.1, 4.1), já calculado pelo Ministério e
  publicado no Siaps. O painel **não recalcula** essa média.
- **Janela de monitoramento** (Figura 2 da NT) é o período olhado em cada mês para cada boa prática — C1: 30 dias;
  C2: 24 meses; C3–C6: 12 meses; C7: 60 meses; B1–B6: 30 dias; M1–M2: 4 meses. **Não é** o período da média.
- Exceções: C2 e C3 consideram só meses com crianças que completaram 2 anos / gestações que atingiram o 42º dia de
  puerpério (NT 4.1, “Atenção”); em suspensão de pagamento, média só dos meses válidos (NT 4.1.1).

## 2. Componente III – Qualidade
Pontos por conceito (NT 4.3.2): **Ótimo 1,00 · Bom 0,75 · Suficiente 0,50 · Regular 0,25**.
Nota final da equipe = Σ (pontos do conceito × peso do indicador) (NT 4.3.1), peso total 10:

| Equipe | Pesos |
|---|---|
| eSF/eAP | C1 1 · C2 2 · C3 2 · C4 1 · C5 1 · C6 1 · C7 2 |
| eSB | B1 2 · B2 2 · B3 2 · B4 1 · B5 2 · B6 1 |
| eMulti | M1 6 · M2 4 |

Classificação da nota final (NT Quadro 6): **Ótimo > 7,5 · Bom ≥ 5 e ≤ 7,5 · Suficiente > 2,5 e < 5 · Regular ≤ 2,5**.
Os exemplos numéricos da NT (8,5; 7,5; 9,0) são testes automatizados (`test_metrics.py`).

## 3. Componente II – Vínculo e Acompanhamento
Avaliado pela média mensal das dimensões Cadastro e Acompanhamento, com bônus de Satisfação do Usuário (maior nota
entre os meses). Faixas (Quadro 5): Ótimo > 8,5 · Bom 7–8,5 · Suficiente 5–<7 · Regular < 5. **Os pesos das
dimensões não constam na NT 8/2026 e a nota por equipe não é pública**; por isso o painel mostra apenas o
**conceito final oficial** e a distribuição por dimensão.

## 4. O que o painel calcula (e seus limites)
O dado público é, por indicador e quadrimestre, **quantas equipes ficaram em cada conceito**.
- **Pontuação média do indicador** = Σ(equipes × pontos) ÷ equipes.
- **Nota média estimada do Componente III** = Σ(peso × pontuação média). Como a nota é linear, isto é **exatamente**
  a média das notas das equipes — *se todas as equipes foram avaliadas em todos os indicadores* (verificado por
  `test_media_das_notas_individuais…`). Quando o nº de equipes varia entre indicadores (ex.: C2/C3), o valor é
  marcado **“≈ aproximada”**.
- **Não** se reconstrói a nota de nenhuma equipe individual (as contagens não dizem quem teve qual conceito).
- **Não** se somam grupos sobrepostos: Componentes II e III avaliam as mesmas equipes eSF; o gráfico agregado usa
  só o Componente III (eSF, eSB, eMulti são equipes distintas).
- **Ausência de dado ≠ zero:** indicador sem equipes avaliadas é “—” e fica fora da média.
- **Percentual de equipes por conceito** (o que o painel mostra) **≠ percentual de execução da prática** (valor
  mensal por equipe, não público).
- **Prioridades** = peso × (1 − pontuação média): ganho máximo de nota se todas as equipes chegassem a “Ótimo”.
  É uma heurística de apoio à decisão, não uma norma.
- **Faixa visual** do mapa de calor (≥1 Ótimo; ≥0,75 Bom; ≥0,5 Suficiente) é só para colorir; não é classificação oficial.

## 5. Limitações conhecidas
- Os quadrimestres de 2025 foram avaliados sob a NT nº 6/2025. O painel aplica a eles os pesos e faixas da NT 8/2026.
  A NT 8/2026 declara que a correção das descrições de B4/B5 não alterou a metodologia, mas **não foi verificada**
  diferença de pesos entre as duas NT: confirme antes de usar a nota estimada de 2025 como referência formal.
- O 1º quadrimestre de 2025 existe na API mas não é exibido pelo portal; fica fora (`PRIMEIRO_QUADRIMESTRE`).
