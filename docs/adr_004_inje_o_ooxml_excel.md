# ADR-004: Injeção de Código OOXML (DrawingML) para Exportação

## Contexto
O salvamento de dados gerado de forma padrão via biblioteca `openpyxl` perdia a formatação de fontes em softwares de código aberto (como o LibreOffice Calc). Isso quebrava o layout dos textos e dos eixos fora das caixas de gráficos, resultando em planilhas mal formatadas para parte dos usuários.

## Decisão
Substituição dos métodos padrão e automáticos do Python por injeção manual e de baixo nível de nós XML (`<c:txPr>`, `<c:title>`, `<a:p>`) na árvore do arquivo gerado (OOXML/DrawingML). Foi forçado o uso de fontes entre 13pt e 15pt, estritamente na tipografia *Segoe UI Negrito*.

## Consequência
O arquivo `.xlsx` gerado passou a possuir simetria perfeita e alta legibilidade em qualquer programa de planilhas de mercado, operando de forma nativa e nítida a 100% de zoom, independente da plataforma do usuário.