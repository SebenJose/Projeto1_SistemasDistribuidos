# Trabalho 1: Jogo de Adivinhação Distribuído (RPC/RMI)

## 🎯 Objetivo Central
O objetivo deste projeto é desenvolver um **jogo multijogador de adivinhação** utilizando tecnologias de comunicação remota, especificamente **Remote Procedure Call (RPC)** ou **Remote Method Invocation (RMI)**. A aplicação deve gerenciar múltiplos jogadores, distribuição de objetos (imagens), troca de dicas e um sistema de pontuação automatizado, garantindo que toda a lógica de rede siga os paradigmas de sistemas distribuídos.

---

## 📋 Requisitos de Funcionalidade
Para cumprir as exigências do trabalho, a aplicação deve implementar:

* **Distribuição de Objetos:** Cada jogador deve receber a imagem de um objeto no início da rodada.
* **Rodadas de Dicas:** A cada turno, o jogador envia uma dica curta (uma palavra) sobre seu objeto para todos os outros.
* **Adivinhação:** Os jogadores podem tentar adivinhar o objeto alheio ou esperar pelo próximo turno.
* **Mecânica de Troca Secreta:** Uma vez por objeto, um jogador pode solicitar a troca de uma dica com outro jogador específico. Ambas as partes devem aceitar, a dica pode ser mentirosa e os demais jogadores devem ser notificados de que a troca ocorreu.
* **Espionagem:** Jogadores podem tentar "espiar" a troca de dicas alheia, correndo o risco de serem descobertos e perderem pontos.
* **Arbitração:** Deve haver um mecanismo (seja um jogador juiz ou o próprio dono do objeto) para validar se o palpite está correto, considerando sinônimos.
* **Sistema de Pontuação:** A contabilização deve ser automática baseada na rapidez do acerto e na exclusividade (pontuações maiores para quem acerta primeiro ou sozinho).
* **Chat em Tempo Real:** Um chat integrado para comunicação geral, que deve ser tecnicamente separado das ações de jogo (dicas e palpites não devem ser enviados via chat).

---

## 🛠️ Regras de Implementação
As diretrizes técnicas obrigatórias são:

* **Comunicação:** É obrigatório que **toda a comunicação** (exceto talvez o transporte inicial da imagem, se necessário) seja realizada via **RPC ou RMI**.
* **Linguagem:** Livre escolha (implementado em **Python**).
    * *Sugestões de bibliotecas Python:* gRPC, Pyro5, ou XML-RPC.
* **Arquitetura:** Pode ser Cliente-Servidor centralizado ou P2P (conexão direta entre clientes).
* **Separação de Fluxos:** O chat deve ser independente das funcionalidades mecânicas do jogo.

---

## 🔝 Regras para a Nota Máxima
De acordo com os critérios de avaliação do professor, os pontos chave para a melhor nota são:

1.  **Arquitetura Baseada em Eventos:** Aplicações que utilizam **atualização por eventos** (o servidor "avisa" o cliente) serão melhor avaliadas do que aquelas que usam *polling* (o cliente pergunta ao servidor repetidamente se há novidades).
