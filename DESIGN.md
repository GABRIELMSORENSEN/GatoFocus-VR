---
version: alpha
name: GatoFocus VR
description: Painel local e discreto para foco visual em um avatar por vez.
colors:
  background: "#101722"
  surface: "#192332"
  raised: "#223147"
  primary: "#9BC4FF"
  text: "#F1F5FC"
  muted: "#A9B8CC"
  success: "#86D9B0"
  warning: "#F5CB80"
  border: "#33445D"
typography:
  sans:
    fontFamily: "Segoe UI"
  mono:
    fontFamily: "Consolas"
rounded:
  DEFAULT: "16px"
  lg: "18px"
spacing:
  section-gap: "18px"
  page-padding: "28px"
components:
  button: {}
  preview: {}
  status: {}
  annotation: {}
---

# GatoFocus VR Design System

## North Star

- **Intent:** saber em um olhar se a captura está pronta, se há um único alvo e se o envio está ativo.
- **Audience:** usuário brasileiro de VRChat, PC primeiro e Quest PCVR depois; não pressupõe familiaridade com visão computacional.
- **Locale:** português brasileiro; textos técnicos restritos ao diagnóstico e documentação.
- **Usage scene:** utilitário Windows usado junto a jogo/Unity; minimizar mantém o motor funcionando.
- **Register:** produto, uma única tela principal e editor opcional de exemplos.
- **Signature:** círculo de foco na prévia e somente um retângulo verde para o alvo escolhido.
- **Restraint:** controles nativos previsíveis, sem animação decorativa, publicidade, cadastro ou navegação extra.
- **Anti-references:** painel gamer cheio de métricas e assistente que aparenta estar conectado sem evidência.
- **Token ownership:** `gatofocus/theme.py` é a fonte canônica. `COLORS` mapeia diretamente os tokens acima, `FONT`/`MONO` alimentam CustomTkinter. `ui.py` e `annotation_ui.py` consomem o mesmo módulo.

## Colors

Fundo azul escuro reduz brilho próximo ao headset. Superfícies se distinguem por tom; azul claro indica ação/foco, verde indica alvo e endpoint disponível, âmbar indica preparação necessária. Cor sempre acompanha texto. A imagem capturada mantém suas cores originais.

## Typography

Segoe UI para ações e instruções, Consolas apenas para medidas. Título 28 px, estado 23 px, controles 13–15 px, apoio 11–12 px. Sem fontes baixadas em tempo de execução.

## Layout

Janela inicial de 850 × 850, mínimo 800 × 810. Cabeçalho e estado precedem prévia à esquerda e controles à direita. Três ajustes ficam abaixo. Editor de exemplos separado de 720 × 720. A prévia mantém proporção; coordenadas de marcação são normalizadas.

## Elevation & Depth

Sem sombras caras ou transparência. Cards por cor de fundo e espaçamento. O editor pertence à janela principal e não bloqueia a captura do motor.

## Shapes

Cards 16–18 px, ícone geométrico de olho/alvo, foco circular e marcações retangulares. Botões usam o mesmo componente CustomTkinter.

## Components

### Foundational visual states

Pronto, iniciando, aguardando jogo/headset, sem imagem, procurando, acompanhando e pausado têm textos próprios. Ausência de quadro remove a prévia antiga. OSC escutando significa porta local pertencente ao VRChat; não significa que o avatar comprovadamente moveu os olhos.

### Buttons and actions

Iniciar/Pausar é a ação primária. Escolher novamente e salvar exemplo são secundárias. Salvar exemplo fica desabilitado sem quadro. Fechar encerra; minimizar continua. Sem ação destrutiva global.

### Navigation and data display

Fonte PC/Quest explícita, um alvo máximo. Métricas são medidas locais e não alegam FPS do jogo. Prévia pode ser desativada. Cada candidato é cinza; alvo único é verde.

### Forms and overlays

Perfis 6/10/15 Hz, foco limitado entre 12° e 40°, três níveis de confiança. Editor permite desenho, remoção por botão direito e limpeza de marcações antes de salvar. Validação inline recusa caixas vazias/invertidas/fora da imagem. Imagens só são salvas por ação explícita.

### Iconography

Logo vetorial próprio de olho concêntrico. Ações sempre têm texto; o círculo de foco não substitui status textual.

### Motion

Não há animações decorativas. Atualização da interface a cada 250 ms; redesenho de imagem suspenso quando minimizada. Suavização do olhar é comportamento funcional, não animação da interface.

### Content and data visualization

Falar em estimativa, candidato e exemplo. Coletar exemplos não é anunciado como treinamento realizado. Orientações de PC/Quest e limitações ficam explícitas. Nenhuma identidade de jogador é inferida ou exibida.

## Do's and Don'ts

- **Do:** mostrar por que a captura aguarda e qual fonte está selecionada.
- **Do:** manter desenho e alvo consistentes ao redimensionar.
- **Don't:** chamar UDP enviado de confirmação visual no avatar.
- **Don't:** salvar capturas, iniciar treino ou publicar exemplos automaticamente.
