# PRD — Wakfu Damage Meter (v1.6.0.40)

## 1. Visão Geral do Produto
Overlay leve, transparente e em tempo real para o MMORPG **Wakfu**, focado na contabilização precisa de combate (**Dano Causado**, **Dano Recebido**, **Cura** e **Armadura**) e geração automática de relatórios analíticos em Excel (`.xlsx`), operando de forma **100% passiva** sobre os arquivos de texto (`.log`) do jogo.

* **Versão Base Estável:** `v1.6.0.40`
* **Idioma Suportado:** Exclusivamente **Português (PT-BR)** (tanto na interface quanto na leitura dos logs do cliente Wakfu).
* **Plataforma Alvo:** Windows (Python / Tkinter + API Win32 para transparência, *topmost* e *click-through*).

---

## 2. Princípios Inegociáveis (Regras de Ouro)
1. **Segurança Absoluta (Zero Injeção):** O aplicativo jamais lê memória RAM, não intercepta pacotes de rede e não envia comandos ao jogo (ver `[[ADR-001-Leitura-Passiva]]`).
2. **Motor de Cálculo Blindado (`FightState`):** A lógica de atribuição de dano, turnos, invocações e expressões regulares da `v1.6.0.40` é considerada fechada e estável. Nenhuma alteração estética ou periférica pode modificar o motor sem autorização expressa.
3. **Nomes de Personagens Intocados:** O nome de qualquer combatente é exibido e gravado exatamente como consta no log do jogo, sem traduções ou abreviações forçadas.

---

## 3. Funcionalidades Principais (Escopo Atual)

### 3.1. Interface Overlay (HUD Principal)
* **Abas de Métricas:** Alternância rápida entre `Causado`, `Recebido`, `Cura` e `Armadura`.
* **Modo Passado (`⏳ Passado`):** Permite alternar a visualização entre a luta atual e os dados consolidados da luta imediatamente anterior (`last_fight_data`).
* **Cards de Combatentes (Até 6 Aliados):**
  * Destaque visual dourado automático para o **MVP** (maior valor na aba ativa).
  * Carregamento automático do retrato da classe via `AvatarBreed` oficial (`1` a `19`, conforme `[[ADR-003-IDs-Raca-Ankama]]`).
  * Proibição de cache em avatares *fallback* (quadrado colorido com a inicial), garantindo atualização imediata quando a classe é identificada.
* **Painel de Detalhes (`📊 Detalhes`):** Janela expansível com rolagem mostrando o desempenho turno a turno (`T. 1`, `T. 2`...), barra de proporção, percentual por turno, total acumulado e média por turno do personagem selecionado.
* **Click-Through e Opacidade:** Atalho global configurável (padrão `ctrl+f12`) que torna a janela intangível aos cliques do mouse (`WS_EX_TRANSPARENT`), além de controle de opacidade do fundo (10% a 100%).

### 3.2. Reconhecimento de Entidades e Combate
* **Detecção Automática de Heróis/Jogadores:** Identificados via linhas `[_FL_]` (`isControlledByAI=false`), ganho de EXP ou ajuste de nível no log.
* **Lista Manual de Companheiros:** Inclusão/remoção rápida nas Configurações para companheiros controlados por IA que o jogador queira monitorar nos cards.
* **Roteamento de Invocações e Fogo Amigo:** Bombas do Ladino, Dublê do Sram e Clones do Zobal têm suas ações somadas ao dono real, ignorando fogo amigo entre aliados e protegendo o card do jogador contra desaparecimento (ver `[[ADR-002-Fogo-Amigo-Invocacoes]]`).

### 3.3. Histórico e Exportação Automática para Excel
* **Pop-up Pós-Combate com Foco Nativo:** Ao detectar o fim da luta, exibe caixa de diálogo com foco automático forçado via Win32 para informar a faixa de nível (ex: `140`).
* **Fila FIFO por Faixa de Nível:** Mantém no máximo as **últimas 30 lutas** por faixa de nível (`MAX_FIGHTS_PER_LEVEL = 30`), descartando as mais antigas para preservar performance e legibilidade (ver `[[ADR-005-Motor-FIFO-Threading]]`).
* **Planilha Simétrica e Gráficos OOXML (`Wakfu_Historico_De_Danos.xlsx`):**
  * Gerada automaticamente em segundo plano de forma atômica (`~temp_` + `os.replace`).
  * Contém tabela de lutas, destaque de MVP da luta (dourado) e Recorde Pessoal (verde), tabela de resumo individual e 2 gráficos nativos (Linha e Barras) com fontes forçadas via XML (ver `[[ADR-004-Injecoes-OOXML-Excel]]`).

### 3.4. Auto-Updater Integrado
* Consulta assíncrona ao repositório `wakfu-overlay-updater` no GitHub ao iniciar, baixando e aplicando novas versões via script `.bat` caso o usuário aceite.

---

## 4. Fora de Escopo (O que NÃO fazer)
* **Suporte Multi-Idioma (EN/FR/ES):** Rejeitado deliberadamente para evitar complexidade nas Regex de log e regressões não testáveis no motor.
* **Exportação Manual por Botão:** Removida das Configurações por ser redundante com o fluxo 100% automático pós-combate.
* **Leitura de Memória ou Overlay DirectX/OpenGL Injetado:** Proibido por diretriz de segurança da conta.

---

## 5. Mapa de Documentação Arquitetural (ADRs)
* `[[ADR-001-Leitura-Passiva]]` — Arquitetura de Leitura 100% Passiva (Anti-Ban)
* `[[ADR-002-Fogo-Amigo-Invocacoes]]` — Mapeamento de Fogo Amigo e Propriedade de Invocações
* `[[ADR-003-IDs-Raca-Ankama]]` — IDs de Raça baseados no Engine da Ankama
* `[[ADR-004-Injecoes-OOXML-Excel]]` — Injeção de Código OOXML (DrawingML) para Exportação
* `[[ADR-005-Motor-FIFO-Threading]]` — Motor FIFO e Threading Assíncrono