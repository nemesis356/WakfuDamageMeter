# ADR-003: IDs de Raça baseados no Engine da Ankama

## Contexto
A partir de certas expansões, as classes não seguiram a ordem cronológica de lançamento no log. Por exemplo, Eliotrope, Steamer, Kilorf e Huppermago geram os IDs 15 a 19 de forma embaralhada, divergindo da numeração encontrada na enciclopédia pública do jogo. Isso causava a exibição de avatares trocados na UI.

## Decisão
O `CLASS_MAP` foi calibrado usando a tabela `AvatarBreed` interna do Java do próprio cliente do Wakfu, ignorando fontes externas. Um versionamento de schema JSON (`CONFIG_SCHEMA_VERSION`) foi adicionado às configurações para forçar a limpeza automática de caches corrompidos nos PCs dos usuários sempre que o mapa for atualizado.

## Consequência
Os avatares agora carregam de forma impecável no primeiro frame do combate. Erros graves de interface (como Huppermago assumindo a foto de Eliotrope) foram permanentemente extintos.