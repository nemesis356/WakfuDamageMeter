Changelog — Wakfu Damage Meter

Todas as alterações notáveis, correções de bugs e evoluções arquiteturais do Wakfu Damage Meter estão documentadas neste arquivo.

[1.6.0.40] - 2026-11-14 (Versão Estável Atual)

Corrigido

Mapeamento Oficial de Classes (CLASS_MAP): Calibragem definitiva dos IDs internos (AvatarBreed) do motor do Wakfu para as classes Kilorf/Ouginak (15), Steamer (16), Eliotrope (17/18) e Huppermago (19). Corrige o problema em que o Eliotrope exibia o retrato do Huppermago e o Huppermago não tinha seu avatar carregado na interface.

Blindagem de Cache de Avatares (_get_avatar): Proibição do armazenamento em cache de avatares fallback (quadrados coloridos com a letra inicial). Garante que o retrato oficial da classe substitua imediatamente o ícone provisório assim que a classe do combatente for identificada no log.

Imunidade do Zobal ao Invocar Clones: Proteção completa na leitura de linhas [_FL_] e SUMMON_RE para impedir que jogadores reais cujo clone compartilha o mesmo nome do conjurador (ex: feitiço Carnaval do Zobal) sejam reclassificados como Inteligência Artificial (isControlledByAI=true) ou removidos da barra ativa durante o combate.

Alterado

Atualização de Schema de Configuração (CONFIG_SCHEMA_VERSION = 4): Limpeza automática de caches antigos de classes salvos no arquivo wakfu_damage_meter_config.json para evitar conflitos com IDs de versões anteriores.

[1.6.0.35 a 1.6.0.39] - Estabilidade, Foco Nativo e Gravação Atômica

Adicionado

Foco Nativo Automático no Pós-Combate: Integração com a API Win32 (AttachThreadInput e SetForegroundWindow) para contornar o bloqueio de foco do Windows. Ao encerrar uma luta, a janela de registro de nível ganha foco imediato na caixa de texto, permitindo digitar o nível e pressionar Enter diretamente.

Varredura Binária Rápida de Logs (_fast_binary_fl_scan): Leitura otimizada em blocos binários nos arquivos wakfu.log e backups rotacionados para identificar classes de personagens instantaneamente na abertura do aplicativo.

Alterado

Fluxo de Exportação 100% Automático: Remoção do botão de exportação manual nas Configurações, consolidando a gravação automática em segundo plano logo após o término de cada combate.

Salvamento Atômico de Planilhas Excel: A exportação para .xlsx passou a gravar primeiro em um arquivo temporário (~temp_Wakfu_Historico_De_Danos.xlsx) e realizar a substituição atômica via os.replace, prevenindo corrupção de arquivos.

Corrigido

Compatibilidade com OpenPyXL Recente: Remoção de chamadas obsoletas de largura de coluna que geravam AttributeError em versões novas da biblioteca openpyxl.

[1.6.0.30 a 1.6.0.34] - Motor FIFO e Padronização Gráfica OOXML

Adicionado

Fila FIFO de Histórico por Nível (MAX_FIGHTS_PER_LEVEL = 30): Limite automático que retém as 30 lutas mais recentes de cada faixa de nível, descartando registros antigos para manter a leitura dos gráficos limpa e evitar crescimento infinito de memória.

Injeção Direta de OOXML (DrawingML) nos Gráficos: Customização da árvore XML dos gráficos de Linha e de Barras no Excel (_inject_chart_font_xml), forçando tipografia Segoe UI Negrito em tamanhos legíveis (12pt a 15pt) e legendas centralizadas no topo, garantindo compatibilidade visual tanto no Microsoft Excel quanto no LibreOffice Calc.

Destaques Visuais na Planilha: Marcação automática em dourado para o maior dano de cada combate (MVP) e em verde para o recorde pessoal de cada personagem naquela faixa de nível.

[1.6.0.20 a 1.6.0.29] - Mecanismos de Classe, Isolamento de Fogo Amigo e Nova UI

Adicionado

Roteamento de Invocações (summon_owner): Vinculação automática do dano causado por Bombas do Ladino (ROUBLARD_BOMBS), Dublê do Sram (SRAM_DOUBLES), Clones do Zobal (ZOBAL_CLONES), glifos e efeitos próprios (Flamejante, Tetatoxina, Contra-Ataque) diretamente ao personagem conjurador.

Filtro de Fogo Amigo: Bloqueio matemático que impede que danos colaterais em área causados por aliados contra outros aliados ou invocações aliadas inflem o contador de Dano Causado.

Aba de Armadura, Modo Passado e Painel de Detalhes: Inclusão do rastreamento de Armadura concedida, botão Passado para consultar os dados consolidados da luta anterior e painel expansível com estatísticas turno a turno.

Sistema de Auto-Update: Verificação assíncrona de novas versões via GitHub com download e atualização automatizados.

Alterado

Interface Unificada em Cards: Redesenho da barra principal com cartões de personagens, retratos de classes e destaque dourado para o jogador de maior desempenho (MVP).

[1.3.0] - Motor Dinâmico de Autoria e Relatórios

Adicionado

Novo Motor Dinâmico de Autoria: Implementação de um sistema que lê o log em tempo real para atribuir corretamente o dano de Venenos, Glifos, Armadilhas e Estados ao personagem que os conjurou, corrigindo discrepâncias no cálculo de DPS.

Rastreador de Acertos Críticos: Adição de cartão estatístico na vista de Turnos para calcular a Taxa de Crítico exata por personagem durante o combate.

Exportação de Relatórios: Funcionalidade no menu superior para exportar resumos de combate em formato .txt, adaptando-se dinamicamente ao modo ativo (Dano, Cura ou Armadura) e detalhando Total, Média, Turno de Pico e Taxa de Crítico do grupo.

Alterado

Otimização do Executável: Isolamento da compilação do pacote em ambiente virtual, reduzindo drasticamente o tamanho final do arquivo para download.

Corrigido

Reset de Combate: O botão de Reiniciar Histórico passou a atuar como uma limpeza instantânea da interface e da memória, eliminando a necessidade de recarregar todo o arquivo de log anterior.

[1.2.9b] - Hotfix: Botão de Reset

Corrigido

Comportamento do Reset de Combate: Ajustado o botão "Reiniciar o Histórico do Combate". Anteriormente, acioná-lo forçava o aplicativo a reabrir o arquivo .log e reler todo o histórico de batalhas passadas desde a primeira linha. Passou a zerar os dados da interface e a memória da luta atual instantaneamente, aguardando apenas novos eventos.

[1.2.7b] - Hotfix: Botão de Salvar e Seleção Temporária

Adicionado

Botão de Salvar Permanente: Adicionado botão ao lado dos nomes na "Luta Atual" para promover um personagem permanentemente para a Biblioteca caso o jogador deseje.

Alterado

Comportamento de Seleção na Luta Atual: Marcar a caixa de seleção de um monstro ou NPC na "Luta Atual" deixou de movê-lo permanentemente para a Biblioteca, mantendo o rastreamento apenas até o início do próximo combate.

[1.2.7] - Biblioteca de Personagens (Party Roster)

Adicionado

Biblioteca de Personagens (Party Roster): Recurso voltado para jogadores com múltiplas contas ou composição variável, permitindo predefinir e salvar uma lista de nomes nas Configurações antes do combate começar.

Permanência de Nomes: Personagens desmarcados permanecem salvos na Biblioteca para facilitar a alternância entre lutas sem precisar aguardar uma nova ação no log.

Exclusão Manual: Adicionado botão para remover nomes indesejados definitivamente da Biblioteca, com destaque dourado para personagens cadastrados.

[1.2.6a] - Hotfix: Ordenação e Limpeza da Lista

Alterado

Ordenação Inteligente: A lista de seleção de personagens nas Configurações passou a se reorganizar dinamicamente, fixando os personagens salvos no topo em ordem alfabética e agrupando NPCs e monstros temporários na parte inferior.

Corrigido

Limpeza de Entidades Antigas: Resolvido o problema em que monstros de lutas anteriores não desapareciam da lista caso o executável antigo estivesse retido em cache.

[1.2.6] - Performance e Qualidade de Vida

Adicionado

Filtro Inteligente de Fim de Luta: Implementado o gatilho inicial para limpeza automática de NPCs e monstros desmarcados da luta anterior ao iniciar um novo combate.

Alterado

Otimização de Renderização (State Hash): O motor de interface recebeu uma assinatura de estado (_last_state_hash), garantindo que elementos gráficos e o ranking só sejam recalculados e redesenhados quando os dados do log ou da interface sofrerem alteração real, reduzindo drasticamente o consumo de CPU e GPU em momentos ociosos.

[1.2.4] - Hotfix: Caminho Dinâmico de Logs

Adicionado

Persistência de Caminho Customizado: Adicionada função para salvar no arquivo de configuração qualquer diretório de log personalizado escolhido pelo usuário.

Corrigido

Resolução Dinâmica do Diretório Padrão: O caminho padrão dos logs passou a ser resolvido via variável de ambiente (%APPDATA%), localizando a pasta correta independentemente do nome de usuário do Windows.

[1.2.3] - Release Candidate Final

Alterado

Automação de Build (build.py): Script de compilação aprimorado com limpeza automática de cache, empacotamento em modo --onedir para evitar falsos-positivos de antivírus e geração automatizada do arquivo .zip final.

Corrigido

Proteção na Classe ToolTip: Adicionada verificação de existência do widget antes da renderização para evitar falhas silenciosas ao fechar janelas.

[1.2.0 a 1.2.2] - Modo Mini-Overlay e Transparência Chroma Key

Adicionado

Modo Mini-Overlay (v1.2.0): Implementação de janela secundária (tk.Toplevel) dedicada ao modo compacto, com sincronização automática de atalhos (Click-through) e opacidade.

Alterado

Transparência Total via Chroma Key (v1.2.1 e v1.2.2): Aplicação de máscara de transparência (CHROMA_KEY) ao fundo e ao rodapé do Mini-Overlay, mantendo apenas os textos e as barras dinâmicas horizontais visíveis sobre o jogo.

[1.1.0 a 1.1.2] - Instância Única, Ícones e Ajustes de Z-Index

Adicionado

Controle de Instância Única (v1.1.0): Implementação de trava via Mutex da API do Windows (CreateMutexW) para impedir a abertura acidental de múltiplas instâncias do aplicativo.

Unificação de Ícones (v1.1.0): Renderização unificada do ícone na janela do Tkinter e na barra de tarefas do Windows.

Alterado

Atraso de Exibição em Tooltips (v1.1.2): Ajuste do tempo de exibição das dicas de botões para 1 segundo (1000ms), evitando poluição visual ao mover o cursor.

Corrigido

Sobreposição (Z-Index) de Tooltips (v1.1.1): Correção no motor de atualização para elevar a janela flutuante em sincronia com a interface principal.

[1.0.0] - Versão Base Consolidada

Adicionado

Motor de Leitura Passiva (LogTailer e FightState): Estabilização do parser de expressões regulares sobre o arquivo wakfu.log com identificação de turnos em tempo real e zero injeção de memória.

Interface e Controles de Overlay: Controle de opacidade, modo Click-through, seleção de diretório de logs e salvamento persistente de configurações em arquivo .json.