# ADR-001: Arquitetura de Leitura 100% Passiva (Anti-Ban)

## Contexto
Ferramentas de terceiros em MMORPGs correm o risco de banimento se injetarem código na memória do jogo (RAM) ou interceptarem pacotes de rede. O objetivo principal do projeto é garantir total segurança para as contas dos usuários.

## Decisão
O motor do aplicativo foi construído para ser puramente passivo. Utilizamos a biblioteca `re` (Regex) para ler o arquivo `wakfu.log` do disco de trás para frente. O aplicativo reage estritamente a eventos de texto gerados pelo próprio cliente do jogo para atualizar a interface gráfica.

## Consequência
* **Positiva:** Risco zero de banimento pela Ankama, garantindo tranquilidade aos jogadores.
* **Negativa (Trade-off):** Como contrapartida técnica, exigiu a criação de uma classe `FightState` complexa na memória local do Python para reconstruir a matemática e o estado do combate linha a linha.