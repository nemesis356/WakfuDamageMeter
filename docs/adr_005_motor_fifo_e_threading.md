# ADR-005: Motor FIFO e Threading Assíncrono

## Contexto
O acúmulo infinito de dados na memória após o usuário realizar dezenas de lutas longas causava *memory leak* (vazamento de memória) e introduzia micro-travamentos na UI a cada ciclo de leitura de 250ms do overlay.

## Decisão
1. Implementação de um limite estrito de memória utilizando uma fila FIFO (First-In, First-Out) configurada para no máximo 30 lutas por faixa de nível (`MAX_FIGHTS_PER_LEVEL = 30`). 
2. Adição de uma trava de thread (`_history_lock`) para garantir o salvamento assíncrono em JSON e Excel de forma atômica (usando `os.replace` em arquivos temporários) por trás dos panos.

## Consequência
O aplicativo agora possui estabilidade extrema, podendo rodar ininterruptamente por meses sem travamentos ou degradação de performance. O loop visual principal foi otimizado, cortando drasticamente o uso de CPU durante o processamento de dicionários.