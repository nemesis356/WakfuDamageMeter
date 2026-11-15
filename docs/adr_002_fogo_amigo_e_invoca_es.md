# ADR-002: Mapeamento de Fogo Amigo e Propriedade de Invocações

## Contexto
Ataques em área (ex: Bombas do Ladino) inflavam o dano ao atingir aliados. Além disso, clones (como o Dublê do Sram e o Clone do Zobal) poluíam a lista de combatentes ou faziam com que o jogador real desaparecesse da interface devido a reclassificações indevidas geradas pelo log.

## Decisão
Criação dos dicionários de barreira (`ROUBLARD_BOMBS`, `SRAM_DOUBLES`, `ZOBAL_CLONES`) e do roteador lógico `summon_owner`. 
* Qualquer entidade listada é imediatamente vinculada ao seu conjurador.
* Danos causados a alvos válidos como aliados recebem trava de bloqueio matemática (`if not (is_ally_caster and is_ally_target)`). 
* Jogadores reais ganharam imunidade rigorosa no código contra a reclassificação de IA.

## Consequência
A contabilidade de DPS tornou-se cirúrgica e limpa. Personagens complexos como o Zobal agora mantêm seu card ativo e intacto na interface, mesmo quando o motor do jogo gera entidades controladas por IA com o mesmo nick do jogador.