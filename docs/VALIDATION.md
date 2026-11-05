# Validação — 0.1.0 (2026-11-04)

## Verificado

- 12 testes automatizados: tempo de aquisição/troca, alvo único, continuidade, oclusão, perda, fixação, cone de foco, sinais dos ângulos, OSC real em socket UDP local, rejeição de NaN e rótulos de exemplos.
- YOLOX-Nano real, CPU com duas threads: três pessoas na imagem fotográfica de controle; mediana 10,02 ms e p95 amostral 10,46 ms em 20 execuções. Isso não mede detecção de avatares nem FPS do jogo.
- Captura real pelo Windows Graphics Capture de uma janela de controle: detecção com tamanho normal e janela reduzida; rejeição quando minimizada e retomada após restaurar. A imagem de controle não está no repositório.
- DLL OpenVR/D3D11 compilada com MSVC x64. No teste inicial, a API retornou falta de headset/sessão ativa; o aplicativo permaneceu responsivo aguardando.
- Executável Windows empacotado aberto: botões Pausar/Retomar acionados na interface, estado conferido no diagnóstico, worker permaneceu ativo com o aplicativo minimizado. Em espera: cerca de 99 MB de RAM e 0,1% de CPU da máquina.
- Captura Windows com quadro novo/sem quadro: janela de controle 480 × 640 e 320 × 360, detecção real nos dois tamanhos, pausa ao minimizar a fonte e retomada ao restaurar.

## Ainda precisa de teste com o usuário

- Reconhecimento confiável dos seus avatares reais, inclusive próximos, pequenos e estilizados.
- Movimento visível dos olhos do avatar por OSC em uma sessão de VRChat.
- Captura real do compositor com Quest conectado, com a janela espelhada pequena/minimizada, e comparação do FPS do jogo com/sem o app.

O usuário informou que está sem o Quest durante o upload de um avatar. Essa indisponibilidade não foi substituída por uma afirmação de teste em VR concluído. A versão foi preparada também para testes em PC/Desktop.

## Roteiro curto

1. Entre no VRChat Desktop, ative OSC, use avatar com eye-look e abra um espelho.
2. Coloque outra pessoa perto do centro; confira único retângulo verde e mudança do olhar no avatar.
3. Mova a câmera; mantenha outra pessoa centralizada e confira que a troca exige um pequeno intervalo.
4. Minimize o GatoFocus: os envios devem continuar. Minimize o jogo em modo PC: o envio deve parar; restaurar deve retomar.
5. Salve e corrija exemplos dos erros. Eles ficam locais; não alteram pesos automaticamente.
6. Quando o Quest estiver disponível, escolha Quest/SteamVR e repita usando a imagem do headset.

O timeout de retorno ao olhar automático é controlado pelo VRChat (cerca de 10 segundos sem pacotes). O aplicativo não envia piscadas nem parâmetros de corpo.
