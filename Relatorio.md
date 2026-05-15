# Relatório do Projeto 1 - Sistemas Distribuídos
## Jogo de Adivinhação Multijogador

### 1. Introdução à Biblioteca RPC escolhida: Pyro5
O desenvolvimento da aplicação foi feito utilizando a linguagem Python, junto à biblioteca **Pyro5** (Python Remote Objects).

#### Justificativa da Escolha
A escolha pelo **Pyro5** se deu por diversos fatores:
1. **Curva de aprendizado e Facilidade de uso**: O Pyro5 permite exportar diretamente classes Python como serviços remotos usando decorators (ex: `@Pyro5.api.expose`).
2. **Abordagem Orientada a Eventos (Callbacks)**: O projeto utiliza atualizações baseadas em eventos em vez de *polling*. O Pyro5 suporta invocações de via única (`@Pyro5.api.oneway`) permitindo que o servidor invoque métodos nos clientes assincronamente (callbacks), sem travar a thread principal.
3. **Serialização Nativa**: A troca de dados (listas, dicionários, imagens em Base64) entre cliente e servidor foi simplificada e transparente.

### 2. Descrição do Desenvolvimento e Arquitetura Modular
A aplicação segue uma arquitetura **Cliente-Servidor modularizada**, visando alta manutenibilidade e separação de preocupações:

**Arquitetura de Arquivos:**
- **`server.py`**: Orquestrador central de rede e estado.
- **`client.py`**: Ponto de entrada leve do jogador.
- **`interface.py`**: Gerenciamento completo da interface gráfica (Tkinter).
- **`score.py`**: Módulo dedicado ao cálculo complexo de pontuação.
- **`events.py`**: Tratamento de callbacks recebidos do servidor.
- **`constants.py`**: Configurações globais e dados estáticos (objetos, sinônimos).

**Funcionalidades de Destaque:**
- **Placar Dinâmico em Tempo Real**: A interface exibe quem já acertou e quem está pronto imediatamente após a ação, garantindo feedback visual constante.
- **Interface Inteligente (Dropdowns)**: Campos de seleção de jogadores foram substituídos por menus suspensos dinâmicos, eliminando erros de digitação e tentativas de ações inválidas contra si mesmo.
- **Sistema de Pontuação Avançado**: Implementa as regras de **Rapidez** (bônus para o primeiro acerto) e **Exclusividade** (recompensa ao dono por dicas equilibradas e penalidade por dicas óbvias).
- **Mecanismo Anti-Spam**: Jogadores que erram um palpite ficam bloqueados de tentar adivinhar o mesmo alvo novamente até o próximo turno.
- **Arbitração Distribuída**: O dono do objeto é o juiz dos palpites recebidos, permitindo uma validação flexível e descentralizada.

### 3. Instruções de Instalação e Uso

#### Pré-requisitos
- Python 3.8+
- Instalar as dependências: `pip install Pyro5 Pillow`

#### Passo a passo para Execução
1. **Iniciando o Servidor:** `python server.py`
2. **Iniciando os Clientes:** `python client.py "Nome_do_Jogador"`

#### Comandos e Uso:
- **Interface**: Utilize os botões e menus suspensos para realizar ações (Dicas, Palpites, Trocas e Espionagem).
- **`/chat <mensagem>`**: Comunicação global através do campo de texto inferior.
- **`/espiar <J1> <J2>`**: Comando via chat para tentar ver as dicas trocadas entre dois jogadores.
- **Pronto**: Finaliza suas ações no turno. O jogo avança quando todos estiverem prontos.
