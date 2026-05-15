# Jogo de Adivinhação Multijogador - Sistemas Distribuídos

Este é um jogo de rede multiplayer com interface gráfica, desenvolvido para a disciplina de Sistemas Distribuídos. O jogo utiliza uma arquitetura cliente-servidor com comunicação totalmente baseada em eventos e callbacks RPC via **Pyro5**, garantindo a nota máxima nos requisitos técnicos do trabalho.

---

## 🚀 Guia Rápido: Como Rodar o Projeto

Siga o passo a passo abaixo após clonar este repositório para testar o projeto localmente.

### 1. Pré-requisitos
- **Python 3.8+** instalado.
- **Tkinter** instalado. *(Atenção usuários de Linux: dependendo da sua distribuição, o `tkinter` e o suporte a imagens dele não vêm instalados por padrão. Caso enfrente erros ao abrir a interface gráfica no Linux, rode: `sudo apt install python3-tk python3-pil.imagetk`)*.

### 2. Configurando o Ambiente
Abra o terminal na pasta raiz do projeto e crie um ambiente virtual para isolar as dependências:

```bash
# Criar o ambiente virtual
python3 -m venv venv

# Ativar o ambiente (Linux/macOS)
source venv/bin/activate
# Ativar o ambiente (Windows)
# venv\Scripts\activate
```

### 3. Instalando as Dependências
Com o ambiente ativado, instale o Pyro5 e o Pillow (usado para exibir e manipular imagens):

```bash
pip install -r requirements.txt
```



## 🎮 Passo a Passo para Testar (Simulação de Partida)

Para avaliar completamente o projeto, recomendamos simular uma partida com 3 jogadores. Você precisará abrir **4 abas/janelas de terminal** diferentes (lembre-se de ativar o `venv` em todas elas se estiver usando ambiente virtual).

> **Atenção Usuários de Windows:** Nos comandos abaixo, utilize `python` em vez de `python3`.

### Terminal 1: Iniciar o Servidor
```bash
python3 server.py
```
*Deixe esta janela minimizada. O servidor cuidará da orquestração RPC, sistema anti-polling e pontuação.*

### Terminais 2, 3 e 4: Iniciar os Jogadores (Interface Gráfica)
Abra mais 3 terminais e inicie um cliente em cada um:
```bash
python3 client.py "Alice"
```
```bash
python3 client.py "Bob"
```
```bash
python3 client.py "Charlie"
```
*Isso fará com que 3 janelas gráficas (GUI) independentes saltem na sua tela.*

---

## 🧪 Roteiro de Avaliação das Funcionalidades

Com as 3 janelas gráficas de jogadores posicionadas na sua tela, siga este roteiro infalível para testar e comprovar o funcionamento de todas as mecânicas distribuídas obrigatórias do trabalho:

1. **Iniciar a Partida:** 
   * Na janela da Alice, clique no botão verde **`▶ Iniciar Partida`**.
   * *O que observar:* As três telas vão atualizar sozinhas (sem polling do cliente) acionadas por um callback do servidor. A imagem secreta de cada jogador será injetada e exibida no canto esquerdo da interface correspondente.

2. **Rodada de Dicas Públicas:**
   * Na janela da Alice, digite uma palavra simples no campo de "Dica Pública" e clique em **`Enviar Dica`**.
   * Faça o mesmo para as janelas do Bob e do Charlie.
   * *O que observar:* As dicas aparecem no chat de todos. O turno de jogo avança automaticamente para a Fase de Ações no exato momento em que o servidor recebe a última dica.

3. **Teste de Arbitração (Julgamento Descentralizado do Cliente):**
   * Na janela da **Alice**, desça até a seção "Adivinhar (Jogador Alvo)". Digite **Bob**. Em "Palpite", tente adivinhar qual é o objeto do Bob. Clique no botão **`Enviar Palpite`**.
   * *O que observar:* Uma **Caixa de Pop-up (Alerta)** vai travar a tela exclusivamente do **Bob**. O próprio Bob é quem fará a arbitragem clicando em "Sim" ou "Não". Ao clicar, o resultado volta pro servidor que pontua a Alice e notifica a todos.

4. **Teste de Troca Secreta e Espionagem:**
   * No campo de Chat (inferior direito) na tela do **Charlie**, digite `/trocar Alice dica_falsa` e clique em enviar.
   * Na tela da **Alice**, ela receberá o pedido em seu histórico de logs e pode responder digitando no chat: `/aceitar Charlie dica_verdadeira`.
   * Na tela do **Bob**, ele verá um *[ALERTA]* avisando que Charlie e Alice efetuaram uma troca, mas a dica será secreta. Ele pode tentar interceptar digitando no seu chat: `/espiar Alice Charlie`. O servidor rodará a chance de 30% e aplicará punição ou recompensa.

5. **Avanço de Turno / Fim de Jogo:**
   * Todos os três jogadores devem clicar no botão laranja **`Pronto (Encerrar meu Turno)`**. 
   * *O que observar:* Assim que o terceiro clicar, as dicas da tela são limpas e a "Rodada 2" começará automaticamente, exigindo novas dicas. O jogo se encerra sozinho após 3 rodadas e imprime o Placar Final.
