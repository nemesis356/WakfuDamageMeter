# ADR-006: Exclusividade em Português (PT-BR) e Trava de Estabilidade na v1.6.0.40

## Contexto
Como o motor de leitura passiva (`LogTailer` e `FightState`) extrai dados diretamente das linhas de texto geradas pelo cliente no arquivo `wakfu.log`, todo o *parsing* de combate depende de expressões regulares (Regex) calibradas para a estrutura sintática das mensagens do jogo.

Na tentativa experimental da versão `v1.6.0.42`, buscou-se introduzir tradução na interface e suporte multi-idioma. Contudo, essa abordagem aumentou significativamente a complexidade da manutenção das Regex, introduziu riscos de regressão na contabilização de eventos e exigiria validação contínua em múltiplos clientes de idiomas diferentes, ameaçando a confiabilidade do núcleo de combate.

## Decisão
1. **Rollback e Baseline Oficial:** Descartar definitivamente as alterações de internacionalização da `v1.6.0.42` e fixar a versão **`v1.6.0.40`** como a *baseline* oficial, estável e definitiva do **Wakfu Damage Meter**.
2. **Exclusividade em PT-BR:** Estabelecer como diretriz arquitetural permanente que tanto a interface gráfica quanto a interpretação dos logs operam exclusivamente em **Português (PT-BR)**.
3. **Blindagem do Motor:** Manter a classe `FightState` e as expressões regulares da `v1.6.0.40` fechadas contra alterações motivadas por tradução ou mudanças estéticas, preservando sempre os nomes originais dos personagens sem qualquer modificação.

## Consequência
* **Positiva:** Garante estabilidade absoluta, precisão matemática nos cálculos de DPS/Cura/Armadura e manutenção enxuta do código, preservando intactas todas as calibrações críticas consolidadas na `v1.6.0.40` (mapeamento `AvatarBreed`, filtro de fogo amigo e imunidade de invocações).
* **Negativa (Trade-off):** O aplicativo permanece restrito a jogadores que utilizam o cliente do Wakfu configurado em Português (PT-BR), abrindo mão do suporte nativo para clientes em Inglês, Francês ou Espanhol.