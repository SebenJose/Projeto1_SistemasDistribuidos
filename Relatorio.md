# Relatório do Projeto 1 - Sistemas Distribuídos
## Jogo de Adivinhação Multijogador

### 1. Introdução à Biblioteca RPC escolhida: Pyro5
O desenvolvimento da aplicação foi feito utilizando a linguagem Python, junto à biblioteca **Pyro5** (Python Remote Objects).

#### Justificativa da Escolha
A escolha pelo **Pyro5** se deu por diversos fatores:
1. **Curva de aprendizado e Facilidade de uso**: Ao contrário do gRPC, que exige a compilação de arquivos `.proto` e uma definição rígida de estubs, o Pyro5 permite exportar diretamente objetos e classes Python como serviços remotos usando decorators (ex: `@Pyro5.api.expose`).
2. **Abordagem Orientada a Eventos (Callbacks)**: Um dos diferenciais para obter uma melhor avaliação neste trabalho era utilizar atualizações baseadas em eventos em vez de *polling*. O Pyro5 suporta nativamente invocações de via única (`@Pyro5.api.oneway`) permitindo que o servidor invoque métodos nos clientes assincronamente (callbacks), sem travar a thread principal ou exigir que os clientes fiquem constantemente perguntando (polling) ao servidor por atualizações do jogo.
3. **Serialização Nativa**: A troca de dados complexos (listas, dicionários, arrays de bytes codificados em Base64 para as imagens) entre cliente e servidor foi bastante simplificada e transparente.

### 2. Descrição do Desenvolvimento e Arquitetura
A aplicação segue uma arquitetura **Cliente-Servidor**. 

**Servidor (`server.py`)**
- Armazena todo o estado do jogo (`GameServer`).
- Controla a divisão das fases (`LOBBY`, `WAITING_HINTS`, `ACTION_PHASE`, `END_GAME`).
- No início do jogo, distribui um objeto secreto (juntamente com sua imagem convertida em Base64) a cada cliente.
- Mantém um sistema de Chat integrado (via `receive_chat_message`) completamente separado da lógica do jogo.
- Controla os turnos (`turn_count`). Cada objeto tem um limite máximo de 3 turnos para a troca de dicas públicas e palpites. Após cada rodada, os clientes mandam `/pronto`, e as dicas públicas são reiniciadas.
- Contém o controle de pontuação distribuído e penaliza os jogadores que falham ao tentar espiar trocas de dicas.

**Cliente (`client.py`)**
- Implementa um Objeto Pyro (`ClientEvents`) para receber callbacks (eventos) disparados pelo servidor, evitando polling.
- Decodifica a imagem recebida em Base64, salva-a no disco local e a abre via visualizador do sistema (utilizando `webbrowser`).
- **Mecanismo de Arbitração**: O cliente possui um controle ativo nas respostas. Quando o Jogador A tenta adivinhar o objeto do Jogador B usando `/adivinhar`, o servidor roteia o palpite de A para B através do evento `request_judgment`. Então, B confere a resposta e responde ao servidor `/julgar A sim` ou `/julgar A nao`. Isso cria um modelo de arbitração distribuído onde "cada jogador é responsável por conferir as respostas para suas próprias dicas", em vez de uma checagem engessada com dicionário no servidor.

### 3. Instruções de Instalação e Uso

#### Pré-requisitos
- Python 3.8+
- Instalar as dependências do Python:
  ```bash
  pip install Pyro5 Pillow
  ```

#### Passo a passo para Execução
1. **Geração das Imagens (Opcional, pois são geradas no código se ausentes):**
   Execute o script fornecido na raiz para gerar localmente o banco de imagens dos objetos secretos:
   ```bash
   python generate_images.py
   ```
2. **Iniciando o Servidor:**
   Em um terminal, execute:
   ```bash
   python server.py
   ```
   *O servidor ficará rodando na porta 9090 esperando conexões.*

3. **Iniciando os Clientes:**
   Abra 2 ou mais novos terminais. Em cada um, inicie o cliente informando o nome do jogador:
   ```bash
   python client.py "Alice"
   python client.py "Bob"
   ```

4. **Regras e Comandos de Uso:**
   - No LOBBY, qualquer um pode digitar `/iniciar` para a partida começar.
   - Assim que o jogo começar, uma imagem será aberta em seu computador indicando seu objeto.
   - **`/chat <mensagem>`**: Fala no chat global, separado do jogo.
   - **`/dica <palavra>`**: Publica sua dica daquele turno para os demais. Todos precisam mandar uma antes da rodada de ações liberar.
   - **`/trocar <jogador> <dica_falsa_ou_real>`**: Propõe uma troca privada de dicas para outro jogador (apenas 1 troca por jogo).
   - **`/espiar <jogadorA> <jogadorB>`**: Tenta bisbilhotar a troca de dois jogadores. (30% de chance de perder 10 pontos).
   - **`/adivinhar <jogador_alvo> <palpite>`**: Envia um palpite para o dono de um objeto. O dono receberá a notificação.
   - **`/julgar <jogador_que_adivinhou> sim/nao`**: O dono do objeto usa esse comando para arbitrar se o palpite de alguém sobre seu objeto estava certo.
   - **`/pronto`**: Marca que você terminou as ações. Quando todos dão pronto, o jogo avança o turno (limpando as dicas) ou encerra após 3 turnos.
   - **`/votar`**: Ao final, vote para embaralhar os objetos e começar de novo.
