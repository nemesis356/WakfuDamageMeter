# Wakfu Damage Meter

O **Wakfu Damage Meter** é uma ferramenta de sobreposição (overlay) leve e em tempo real desenvolvida para o MMORPG Wakfu. O aplicativo monitora e contabiliza métricas de combate — incluindo Dano Causado, Dano Recebido, Cura e Armadura — além de gerar relatórios analíticos automatizados em formato Excel.

A ferramenta opera de maneira 100% passiva através da leitura dos arquivos de registro de texto (`.log`) gerados localmente pelo próprio cliente do jogo. Não há qualquer tipo de injeção de memória, interceptação de pacotes de rede ou automação de comandos, garantindo total conformidade e segurança para a conta do jogador.


<div align="center">
  <a href="https://www.buymeacoffee.com/SEU_USUARIO" target="_blank">
    <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="60" width="217">
  </a>
</div>

---

## Funcionalidades Principais

* **Monitoramento em Tempo Real:** Acompanhamento instantâneo de Dano Causado, Dano Recebido, Cura realizada e Armadura concedida para até 6 aliados simultâneos.
* **Reconhecimento Automático de Classes:** Identificação nativa das classes dos personagens com carregamento automático dos respectivos retratos e destaque visual para o jogador de maior desempenho (MVP) na categoria ativa.
* **Tratamento Preciso de Invocações e Fogo Amigo:** Atribuição inteligente de ações provenientes de invocações e mecanismos de classe (como Bombas do Ladino, Dublê do Sram e Clones do Zobal) diretamente ao conjurador original, ignorando danos colaterais causados a aliados.
* **Análise Detalhada por Turno:** Painel expansível com o histórico turno a turno de cada combatente, apresentando média por turno, valor total acumulado e proporção percentual de desempenho.
* **Histórico do Combate Anterior:** Alternância rápida para consultar os dados consolidados da última luta encerrada sem interromper o monitoramento da sessão.
* **Exportação Automática para Excel:** Geração de planilhas formatadas (`.xlsx`) divididas por faixa de nível, contendo histórico das últimas 30 lutas, destaques de recordes pessoais e gráficos comparativos nativos.
* **Modo Click-Through e Opacidade Ajustável:** Atalho global configurável (padrão `Ctrl+F12`) que torna a interface intangível aos cliques do mouse durante a partida, além de controle de transparência do fundo.
* **Atualizador Integrado:** Verificação automática de novas versões diretamente pelo aplicativo ao iniciar.

---

## Requisitos de Uso

* **Sistema Operacional:** Windows.
* **Idioma do Jogo:** O cliente do Wakfu deve estar configurado em **Português (PT-BR)**, pois o motor de leitura interpreta os eventos de combate com base nos registros neste idioma.

---

## Instalação e Execução

### Para Usuários (Executável)
1. Baixe a versão mais recente na página oficial de distribuição ou na seção **Releases** deste repositório.
2. Extraia o conteúdo do arquivo `.zip` em uma pasta de sua preferência.
3. Execute o arquivo `Wakfu Damage Meter.exe`.
4. Caso o seu jogo não esteja instalado no diretório padrão do Ankama Launcher (`%APPDATA%\zaap\gamesLogs\wakfu\logs`), abra as Configurações do aplicativo e selecione a pasta onde se encontra o arquivo `wakfu.log`.

---

## Estrutura do Projeto

* `Wakfu Damage Meter.py` — Código-fonte principal contendo a interface gráfica e o motor de leitura de combate (`FightState`).
* `avatares/` — Diretório com os retratos das classes utilizados na interface.
* `docs/` — Documentação técnica do projeto, incluindo o Documento de Requisitos de Produto (`PRD.md`) e os Registros de Decisão de Arquitetura (`ADRs/`).
* `requirements.txt` — Lista de bibliotecas Python necessárias para execução e compilação (`Pillow`, `keyboard`, `openpyxl`).

---

## Créditos e Distribuição

* **Desenvolvedor:** Nemesis (`@NemesisRafa-26`)
