# Jogo de Adivinhação Multijogador - Sistemas Distribuídos

Este é um jogo de rede multiplayer desenvolvido para a disciplina de Sistemas Distribuídos. O jogo utiliza uma arquitetura cliente-servidor com comunicação baseada em eventos via **Pyro5**.

## 🚀 Como Rodar o Projeto

Siga os passos abaixo para configurar e executar o projeto em sua máquina local.

### 1. Pré-requisitos

Certifique-se de ter o **Python 3.8+** instalado.

### 2. Configuração do Ambiente

Recomendamos o uso de um ambiente virtual para instalar as dependências:

```bash
# Criar o ambiente virtual
python -m venv venv

# Ativar o ambiente (Linux/macOS)
source venv/bin/activate

# Ativar o ambiente (Windows)
# venv\Scripts\activate
```

### 3. Instalação de Dependências

Instale as bibliotecas necessárias:

```bash
pip install -r requirements.txt
```

### 4. Gerar Imagens dos Objetos

Antes de iniciar a primeira partida, gere as imagens que serão distribuídas aos jogadores:

```bash
python generate_images.py
```

---

## 🎮 Execução

Para jogar, você precisará de um servidor rodando e pelo menos **2 jogadores**.

### Passo 1: Iniciar o Servidor
Em um terminal dedicado, execute:
```bash
python server.py
```

### Passo 2: Iniciar os Clientes
Abra um novo terminal para cada jogador e execute informando o nome entre aspas:
```bash
python client.py "SeuNome"
```

---

## 🕹️ Comandos do Jogo

Os comandos devem ser digitados diretamente no terminal do cliente:

| Comando | Descrição |
| :--- | :--- |
| `/iniciar` | Inicia a partida (apenas no Lobby) |
| `/chat <msg>` | Envia uma mensagem no chat global |
| `/dica <palavra>` | Envia sua dica pública obrigatória da rodada |
| `/trocar <alvo> <dica>` | Propõe uma troca privada de dicas |
| `/espiar <jog1> <jog2>` | Tenta interceptar uma troca (risco de perder pontos) |
| `/adivinhar <alvo> <obj>`| Tenta descobrir o objeto de outro jogador |
| `/julgar <jog> sim/nao` | O dono do objeto confirma se o palpite de alguém está certo |
| `/pronto` | Encerra suas ações no turno atual |
| `/votar` | Vota para reiniciar o jogo ao final da partida |

---

## 🛠️ Tecnologias Utilizadas
- **Python 3**
- **Pyro5** (Python Remote Objects) para RPC e Callbacks
- **Pillow** para geração e manipulação de imagens
- **Base64** para transmissão de imagens via rede
