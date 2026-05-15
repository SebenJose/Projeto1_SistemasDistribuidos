# Instruções para usar com o Codex — Projeto RPC/RMI: Jogo Multijogador de Adivinhação

Este arquivo deve ser usado como **guia de requisitos, regras de negócio, checklist de implementação e roteiro de auditoria** para pedir ao Codex que analise, complete e melhore o projeto. O objetivo é deixar o projeto o mais alinhado possível com o enunciado da avaliação prática de **Sistemas Distribuídos e Tecnologias — RPC/RMI**.

---

## 1. Objetivo do projeto

Desenvolver uma aplicação de **jogo multijogador de adivinhação** utilizando obrigatoriamente comunicação via **RPC ou RMI**.

A aplicação deve permitir que vários jogadores participem de uma partida em que cada jogador recebe um objeto/imagem secreta e, a cada turno, fornece dicas para que os outros tentem adivinhar seu objeto.

O projeto deve demonstrar domínio de:

- Comunicação remota via RPC/RMI.
- Separação clara entre cliente e servidor, ou entre clientes distribuídos.
- Controle de turnos.
- Troca de mensagens em tempo real.
- Regras de pontuação implementadas pela aplicação.
- Organização do código.
- Boa experiência de uso durante a demonstração.
- Qualidade de implementação, preferencialmente com atualização baseada em eventos, evitando polling sempre que possível.

---

## 2. Regra principal de arquitetura

Toda comunicação entre partes distribuídas deve ser feita usando **RPC ou RMI**.

Isso inclui, obrigatoriamente:

- Entrada de jogadores na partida.
- Distribuição de objetos/imagens.
- Envio de dicas públicas.
- Envio e aceite de troca de dicas privadas.
- Notificação de troca de dicas aos demais jogadores.
- Tentativas de adivinhação.
- Arbitração dos palpites.
- Cálculo e atualização de pontuação.
- Chat em tempo real.
- Finalização ou continuação da partida.

Não usar comunicação paralela fora de RPC/RMI para implementar funcionalidades do jogo.

---

## 3. Funcionalidades obrigatórias

### 3.1 Jogadores

A aplicação deve permitir múltiplos jogadores.

Cada jogador deve ter:

- Nome ou identificador único.
- Pontuação acumulada.
- Objeto/imagem secreta atual.
- Histórico de dicas dadas.
- Estado de acerto em relação aos objetos dos outros jogadores.
- Controle de uso da troca especial de dicas.

---

### 3.2 Distribuição de objetos/imagens

No início de cada rodada:

- Cada jogador recebe uma imagem de um objeto.
- O objeto deve ficar visível apenas para o dono.
- Os demais jogadores não devem ver a resposta diretamente.
- O sistema deve armazenar qual objeto pertence a cada jogador.

Recomendação para melhor avaliação:

- Criar uma pasta de imagens/objetos de entrada.
- Sortear objetos automaticamente.
- Evitar repetir objetos dentro da mesma rodada.
- Registrar no relatório como os objetos são carregados e distribuídos.

---

### 3.3 Turnos

A partida deve ser organizada em turnos.

A cada turno:

1. Cada jogador envia uma dica curta sobre seu objeto.
2. A dica pública deve conter preferencialmente **uma única palavra**.
3. Os outros jogadores podem:
   - tentar adivinhar o objeto;
   - ou esperar o próximo turno.
4. O sistema deve registrar as dicas enviadas.
5. O sistema deve atualizar o estado da rodada.

Recomendação:

- Implementar um limite máximo de turnos configurável.
- Exibir para todos o número do turno atual.
- Bloquear ações fora do momento correto.
- Evitar que um jogador envie várias dicas públicas no mesmo turno.

---

### 3.4 Dicas públicas

As dicas públicas devem ser enviadas para todos os jogadores.

Regras:

- Devem ser curtas.
- Idealmente devem conter apenas uma palavra.
- Devem ser separadas do chat.
- Não devem ser enviadas pelo chat comum.
- Devem ser registradas como ação específica do jogo.

Validações recomendadas:

- Não permitir dica vazia.
- Remover espaços extras.
- Alertar ou bloquear dicas com mais de uma palavra.
- Registrar jogador, turno e conteúdo da dica.

---

### 3.5 Tentativas de adivinhação

Os jogadores podem tentar adivinhar o objeto dos outros jogadores.

Regras:

- Um jogador não deve tentar adivinhar o próprio objeto.
- O palpite deve estar vinculado a um jogador-alvo.
- O sistema deve verificar se o palpite está correto usando um mecanismo de arbitração.
- O sistema deve registrar quem acertou, em qual turno e qual objeto foi adivinhado.
- O jogador que já acertou determinado objeto não deve pontuar novamente pelo mesmo objeto.

Recomendação:

- Mostrar na interface quais objetos/jogadores ainda podem ser adivinhados.
- Evitar palpites duplicados.
- Registrar no histórico da partida todos os palpites.

---

### 3.6 Mecanismo de arbitração

Como um objeto pode ter mais de uma palavra ou variação de nome, deve existir um mecanismo de arbitração para definir se o palpite está correto.

Opções aceitas:

#### Opção A — Arbitração pelo dono do objeto

- O jogador dono do objeto recebe o palpite.
- Ele aceita ou rejeita o palpite.
- O resultado é enviado ao servidor/sistema.
- A pontuação é atualizada com base nessa decisão.

#### Opção B — Arbitração por jogador árbitro

- Um jogador ou administrador é responsável por validar respostas.
- O árbitro recebe os palpites e decide se estão corretos.

#### Opção C — Arbitração automática com aliases

- Cada objeto possui uma lista de respostas aceitas.
- Exemplo: `carro`, `automóvel`, `veículo`.
- O sistema normaliza a entrada e compara com os aliases.

Recomendação para maior avaliação:

- Usar arbitragem automática com lista de aliases e, se necessário, permitir confirmação manual.
- Documentar claramente no relatório qual mecanismo foi usado.

---

### 3.7 Troca especial de dicas privadas entre dois jogadores

Além das dicas públicas padrão enviadas em cada turno, deve existir um **sistema próprio de troca privada de dicas** entre dois jogadores. Essa funcionalidade é um dos pontos importantes do enunciado e não deve ser tratada como mensagem comum de chat.

Uma vez para cada objeto/rodada, cada jogador pode propor uma troca de dica privada com um jogador específico. A troca só acontece se o jogador convidado aceitar.

#### Fluxo obrigatório da troca privada

1. O jogador A escolhe o jogador B e solicita uma troca privada de dicas.
2. O servidor registra a solicitação como uma ação do jogo.
3. O jogador B recebe uma notificação privada perguntando se aceita ou recusa.
4. Se o jogador B recusar, a troca não acontece e o sistema registra a recusa.
5. Se o jogador B aceitar, os dois jogadores enviam uma dica privada, um para o outro.
6. Cada dica privada deve conter **uma única palavra**.
7. As dicas privadas podem ser verdadeiras ou falsas.
8. Os demais jogadores devem receber um alerta público informando que A e B realizaram uma troca privada.
9. Os demais jogadores **não devem receber automaticamente o conteúdo** das dicas privadas.
10. Após o alerta público, jogadores terceiros podem tentar espiar essa troca, conforme as regras de espionagem.

#### Regras obrigatórias

- A troca deve envolver exatamente dois jogadores específicos.
- A troca deve ser solicitada por um jogador e aceita pelo outro.
- A troca não pode ocorrer automaticamente sem aceite.
- Cada participante envia uma dica privada para o outro participante.
- Cada dica privada deve conter uma única palavra.
- As dicas privadas não precisam ser verdadeiras.
- Os demais jogadores devem ser avisados de que houve uma troca privada.
- O alerta público deve informar os nomes dos jogadores envolvidos, mas não o conteúdo das dicas.
- As dicas privadas devem ser separadas do chat e das dicas públicas.
- A aplicação deve registrar a troca no histórico de eventos da rodada.

#### Validações recomendadas

- Cada jogador só pode usar essa troca uma vez por objeto/rodada.
- Não permitir troca consigo mesmo.
- Não permitir troca com jogador inexistente, desconectado ou fora da partida.
- Não permitir nova solicitação se já houver uma solicitação pendente envolvendo o mesmo jogador.
- Não permitir dica privada vazia.
- Bloquear ou alertar dica privada com mais de uma palavra.
- Registrar solicitação, aceite/recusa, participantes, turno e horário/evento.
- Definir se a troca privada pode ocorrer em qualquer momento do turno ou apenas em uma fase específica.

#### Estados sugeridos para implementação

```text
SEM_TROCA
SOLICITACAO_PENDENTE
ACEITA_AGUARDANDO_DICAS
DICAS_ENVIADAS
TROCA_CONCLUIDA
TROCA_RECUSADA
```

#### Eventos recomendados

```text
private_hint_exchange_requested
private_hint_exchange_accepted
private_hint_exchange_rejected
private_hint_submitted
private_hint_exchange_completed
public_private_exchange_alert
```

Esses eventos ajudam a provar que a funcionalidade foi implementada de forma organizada e baseada em eventos.

---

### 3.8 Alerta público de troca privada

Quando uma troca privada for aceita e realizada, todos os jogadores que não participaram dela devem ser avisados. Esse alerta é obrigatório porque o enunciado diz que os outros jogadores devem saber que houve uma troca de dicas.

#### O alerta deve conter

- Quem trocou dicas com quem.
- Em qual turno a troca ocorreu.
- Uma indicação de que a troca foi privada.
- Uma opção ou ação disponível para tentar espionar, caso a troca ainda possa ser espionada.

Exemplo de alerta:

```text
[Turno 2] Ana e Pedro realizaram uma troca privada de dicas. Outros jogadores podem tentar espiar essa troca.
```

#### O alerta não deve conter

- A dica privada enviada por Ana.
- A dica privada enviada por Pedro.
- O objeto secreto de qualquer jogador.

#### Recomendação para maior nota

Implementar esse alerta como um **evento enviado pelo servidor aos clientes**, por callback/listener/stream/evento remoto, em vez de fazer os clientes perguntarem repetidamente ao servidor se houve alguma troca nova.

---

### 3.9 Espionagem de troca de dicas privadas

Qualquer jogador que não participou da troca pode tentar espiar a troca privada entre dois outros jogadores. Essa ação também deve ser uma funcionalidade própria do jogo, separada do chat.

#### Regras obrigatórias

- O jogador que tenta espiar deve ser diferente dos dois jogadores envolvidos na troca.
- Só deve ser possível espiar uma troca privada existente.
- Deve existir uma chance de o espião ser descoberto.
- Se for descoberto, o espião perde pontos.
- A aplicação deve contabilizar a penalidade automaticamente.
- A tentativa de espionagem deve ser registrada no histórico da partida.

#### Definição sugerida

- Chance de ser descoberto: 50%.
- Penalidade por ser descoberto: -2 pontos.
- Se não for descoberto, o espião vê uma ou ambas as dicas privadas.
- Se for descoberto, o espião não vê a dica e perde pontos.

#### Fluxo sugerido

1. Uma troca privada entre A e B é concluída.
2. O sistema envia alerta público aos jogadores C, D, etc.
3. O jogador C escolhe tentar espiar.
4. O servidor calcula aleatoriamente se C foi descoberto.
5. Se C for descoberto:
   - C perde pontos;
   - o placar é atualizado;
   - o evento é registrado;
   - opcionalmente A e B são notificados.
6. Se C não for descoberto:
   - C recebe o conteúdo da troca privada;
   - o evento é registrado sem revelar aos demais, se essa for a regra escolhida.

#### Recomendação para maior avaliação

- Tornar a chance de descoberta configurável.
- Tornar a penalidade configurável.
- Registrar no histórico quem tentou espionar, quem eram os envolvidos, se foi descoberto e quantos pontos foram perdidos.
- Notificar os jogadores envolvidos caso o espião seja descoberto.
- Garantir que participantes da própria troca não possam espiar a troca em que participaram.
- Garantir que a espionagem não dependa de texto enviado pelo chat.

---

### 3.10 Chat em tempo real

A aplicação deve ter um chat em tempo real integrado.

Regras obrigatórias:

- Todos os jogadores podem conversar no chat.
- O chat deve ser separado das funcionalidades do jogo.
- As ações abaixo não devem ser feitas pelo chat:
  - envio de dicas públicas;
  - troca especial de dicas;
  - espionagem;
  - tentativas de adivinhação;
  - aceite ou recusa de troca de dicas.

Recomendação para melhor avaliação:

- Implementar chat com atualização baseada em eventos/callbacks, se a tecnologia permitir.
- Exibir remetente, horário e conteúdo da mensagem.
- Separar visualmente o chat do painel de ações do jogo.

---

### 3.11 Finalização ou continuação da partida

Ao final dos turnos definidos:

- Os jogadores devem poder decidir se querem finalizar o jogo ou continuar.
- Se decidirem continuar:
  - cada jogador recebe um novo objeto;
  - uma nova rodada começa;
  - as regras se repetem.

Recomendação:

- Criar votação para continuar/finalizar.
- Definir maioria simples ou unanimidade.
- Registrar a decisão da rodada.
- Manter pontuação acumulada entre rodadas, se fizer sentido para o projeto.

---

## 4. Sistema de pontuação

A pontuação deve ser calculada automaticamente pela aplicação.

### 4.1 Pontos por adivinhar corretamente

Quem adivinhar corretamente um objeto recebe pontos.

Regras obrigatórias:

- O primeiro jogador a adivinhar corretamente recebe mais pontos.
- Jogadores que acertarem depois recebem menos pontos.
- Se apenas um jogador acertar determinado objeto, ele recebe bônus.

Sugestão de pontuação:

- Primeiro acerto de um objeto: +5 pontos.
- Acertos posteriores do mesmo objeto: +3 pontos.
- Bônus se apenas um jogador acertar o objeto até o fim da rodada: +2 pontos.

---

### 4.2 Pontos para o dono do objeto

Cada jogador também recebe pontos conforme a quantidade de outros jogadores que descobriram seu objeto.

Regras obrigatórias:

- O dono recebe mais pontos se apenas um outro jogador descobrir seu objeto.
- Se mais de um jogador acertar, a pontuação do dono é menor.
- Se ninguém acertar, o dono não ganha pontos nesse quesito.
- Se todos os outros jogadores acertarem, o dono perde pontos.

Sugestão de pontuação:

- Ninguém acertou: 0 pontos para o dono.
- Apenas 1 jogador acertou: +4 pontos para o dono.
- Mais de 1 jogador acertou, mas não todos: +2 pontos para o dono.
- Todos os outros acertaram: -2 pontos para o dono.

---

### 4.3 Penalidade por espionagem descoberta

Se um jogador for descoberto espiando:

- Ele deve perder pontos automaticamente.

Sugestão:

- Espião descoberto: -2 pontos.

---

### 4.4 Requisitos de implementação da pontuação

O sistema deve:

- Calcular pontos sem depender de cálculo manual.
- Atualizar placar após eventos importantes.
- Exibir placar atual para os jogadores.
- Manter histórico de pontuação.
- Evitar pontuação duplicada.
- Ter funções ou métodos claros para aplicar cada regra.

---

## 5. Requisitos técnicos de RPC/RMI

O projeto deve deixar evidente que usa RPC ou RMI para comunicação distribuída.

### 5.1 Requisitos mínimos

- Definir interface remota ou serviços RPC.
- Separar chamadas remotas das regras de interface.
- Ter cliente e servidor, ou clientes comunicando-se por chamadas remotas.
- Documentar como iniciar o servidor.
- Documentar como iniciar os clientes.
- Tratar erros de conexão.
- Permitir mais de um cliente conectado.

---

### 5.2 Métodos remotos recomendados

O Codex deve verificar se existem métodos equivalentes aos seguintes:

```text
registrar_jogador(nome)
iniciar_partida()
distribuir_objetos()
enviar_dica_publica(jogador, dica)
tentar_adivinhar(jogador, jogador_alvo, palpite)
arbitrar_palpite(jogador_alvo, jogador_palpiteiro, palpite, resultado)
solicitar_troca_dica(jogador_origem, jogador_destino)
responder_troca_dica(jogador_destino, aceitar_ou_recusar)
enviar_dica_privada(jogador_origem, jogador_destino, dica)
tentar_espiar(jogador_espiao, jogador_a, jogador_b)
enviar_mensagem_chat(jogador, mensagem)
obter_estado_jogo()
obter_placar()
finalizar_turno()
votar_continuar(jogador, decisao)
iniciar_nova_rodada()
```

Os nomes podem variar, mas as responsabilidades devem existir.

---

### 5.3 Atualização baseada em eventos — requisito de qualidade para maior nota

O enunciado deixa claro que a **qualidade da implementação será avaliada** e cita explicitamente que uma aplicação com estratégia de atualização baseada em eventos será melhor avaliada do que uma aplicação baseada em polling.

Portanto, para buscar a maior nota, o projeto deve preferir uma arquitetura em que o servidor avisa os clientes quando algo acontece, em vez de cada cliente ficar perguntando repetidamente se houve mudança.

#### Prioridade técnica

O Codex deve priorizar, conforme a tecnologia permitir:

- Callbacks remotos.
- Objetos remotos de cliente para receber notificações.
- Streams de eventos.
- Observers/listeners.
- Fila de eventos mantida pelo servidor.
- Publicação de eventos pelo servidor para todos os clientes interessados.
- WebSocket apenas se estiver integrado de forma coerente com RPC/RMI e sem substituir indevidamente as chamadas RPC/RMI obrigatórias.

#### Eventos que devem atualizar os clientes

A aplicação deve tentar notificar automaticamente os clientes quando ocorrer:

- Entrada ou saída de jogador.
- Início da partida.
- Distribuição de objeto.
- Mudança de turno.
- Envio de dica pública.
- Solicitação de troca privada.
- Aceite ou recusa de troca privada.
- Conclusão de troca privada.
- Alerta público de que houve troca privada.
- Tentativa de espionagem.
- Resultado da espionagem quando o jogador for descoberto.
- Tentativa de adivinhação.
- Resultado da arbitragem.
- Atualização de pontuação.
- Mensagem de chat.
- Fim de rodada.
- Votação para continuar ou finalizar.

#### Evitar

- Cliente chamando `obter_estado_jogo()` em loop a cada poucos segundos.
- Cliente verificando repetidamente se há novas mensagens no chat.
- Cliente perguntando repetidamente se houve troca privada.
- Cliente perguntando repetidamente se o placar mudou.
- Laços infinitos de atualização sem necessidade.

#### Se polling já existir no projeto

O Codex deve:

1. Identificar exatamente onde ocorre polling.
2. Explicar por que isso pode reduzir a avaliação.
3. Classificar se o polling é aceitável temporariamente ou se deve ser removido.
4. Sugerir alternativa baseada em eventos/callbacks/listeners.
5. Refatorar primeiro os fluxos mais importantes: chat, dicas públicas, troca privada, espionagem e placar.

#### Exemplo de arquitetura recomendada

```text
Cliente chama método RPC/RMI para executar uma ação
        ↓
Servidor valida a regra do jogo
        ↓
Servidor atualiza o estado central
        ↓
Servidor cria um evento de domínio
        ↓
Servidor notifica os clientes inscritos por callback/listener/stream
        ↓
Clientes atualizam a interface sem polling constante
```

Essa abordagem deve ser mencionada no relatório e demonstrada na apresentação, porque mostra preocupação com qualidade de implementação.

---

## 6. Separação entre chat e ações do jogo

O Codex deve verificar se o projeto separa claramente:

### Chat

- Mensagens livres entre jogadores.
- Discussão geral.
- Conversa em tempo real.

### Ações do jogo

- Dicas públicas.
- Dicas privadas.
- Trocas de dicas.
- Espionagem.
- Palpites.
- Arbitração.
- Pontuação.
- Votos para continuar/finalizar.

Essas ações devem ser chamadas específicas da aplicação, não mensagens interpretadas a partir do chat.

---

## 7. Checklist de implementação para o Codex analisar

Peça ao Codex para verificar o projeto usando este checklist.

### 7.1 Estrutura geral

- [ ] Existe servidor ou componente central de coordenação.
- [ ] Existem clientes para os jogadores.
- [ ] A comunicação distribuída usa RPC/RMI.
- [ ] O projeto permite múltiplos jogadores.
- [ ] O estado do jogo é mantido de forma consistente.
- [ ] Existem instruções claras de execução.

### 7.2 Jogo

- [ ] Cada jogador recebe um objeto/imagem.
- [ ] O objeto é secreto para os outros jogadores.
- [ ] Há controle de turnos.
- [ ] Cada jogador envia uma dica curta por turno.
- [ ] Os jogadores podem tentar adivinhar objetos.
- [ ] Existe mecanismo de arbitração.
- [ ] Existe limite de turnos ou opção configurável.
- [ ] Ao fim da rodada, é possível continuar ou finalizar.

### 7.3 Troca de dicas

- [ ] Um jogador pode solicitar troca com outro jogador.
- [ ] O outro jogador pode aceitar ou recusar.
- [ ] Os dois jogadores enviam dicas privadas.
- [ ] A troca só pode ocorrer uma vez por objeto/rodada.
- [ ] Os demais jogadores são avisados de que a troca ocorreu.
- [ ] O alerta público informa quem trocou dicas, mas não revela o conteúdo.
- [ ] Após o alerta, jogadores terceiros conseguem tentar espiar a troca.
- [ ] As dicas privadas não são enviadas automaticamente a todos.
- [ ] A troca privada é implementada como ação RPC/RMI própria, não como mensagem de chat.

### 7.4 Espionagem

- [ ] Um terceiro jogador pode tentar espionar uma troca.
- [ ] Existe chance de ser descoberto.
- [ ] Se descoberto, perde pontos.
- [ ] A penalidade é aplicada automaticamente.
- [ ] O evento é registrado no histórico.

### 7.5 Pontuação

- [ ] O primeiro a acertar recebe mais pontos.
- [ ] Quem acerta depois recebe menos pontos.
- [ ] Se apenas um acertar, recebe bônus.
- [ ] O dono do objeto pontua conforme quantos acertaram.
- [ ] O dono perde pontos se todos acertarem.
- [ ] Pontuação é calculada automaticamente.
- [ ] Placar é exibido e atualizado.

### 7.6 Chat

- [ ] Existe chat em tempo real.
- [ ] Todos os jogadores podem enviar mensagens.
- [ ] Chat é separado das ações do jogo.
- [ ] Dicas, palpites, espionagem e trocas não usam o chat.

### 7.7 Qualidade técnica

- [ ] Código organizado em módulos/camadas.
- [ ] Regras de negócio separadas da interface.
- [ ] Tratamento de erros de conexão.
- [ ] Validação de entradas.
- [ ] Estado sincronizado entre clientes.
- [ ] Pouco ou nenhum polling.
- [ ] Uso de eventos/callbacks/listeners/streams quando possível.
- [ ] Chat, dicas, troca privada, espionagem e placar são atualizados por eventos sempre que possível.
- [ ] Logs ou histórico de ações importantes.

### 7.8 Entrega

- [ ] Todos os arquivos do projeto estão incluídos.
- [ ] Arquivos de entrada/imagens estão incluídos.
- [ ] Relatório em PDF está pronto.
- [ ] Instruções de instalação e uso estão no relatório.
- [ ] ZIP final está organizado.
- [ ] O ZIP será enviado no Moodle.

---

## 8. Prompts prontos para usar com o Codex

### 8.1 Auditoria inicial do projeto

Use este prompt no Codex:

```text
Analise todo este projeto como se fosse uma avaliação prática de Sistemas Distribuídos sobre RPC/RMI. Verifique o que já está implementado e compare com os requisitos do arquivo INSTRUCOES_CODEX_RPC_RMI_ADIVINHACAO.md.

Quero que você me entregue:
1. Lista do que já está pronto.
2. Lista do que está parcialmente implementado.
3. Lista do que ainda falta.
4. Problemas que podem reduzir a nota.
5. Sugestões de melhoria priorizadas.
6. Arquivos que precisam ser alterados.
7. Plano de implementação em etapas, começando pelo que vale mais nota.

Não altere o código ainda. Apenas analise e gere um diagnóstico.
```

---

### 8.2 Implementar funcionalidades faltantes

```text
Com base na auditoria anterior e no arquivo de requisitos INSTRUCOES_CODEX_RPC_RMI_ADIVINHACAO.md, implemente as funcionalidades que faltam priorizando os critérios que mais impactam a avaliação.

Prioridade:
1. Garantir que toda comunicação entre jogadores/servidor use RPC ou RMI.
2. Implementar corretamente regras de turno, dicas e palpites.
3. Implementar troca especial de dicas com aceite/recusa.
4. Implementar espionagem com chance de descoberta e penalidade.
5. Implementar pontuação automática completa.
6. Garantir chat em tempo real separado das ações do jogo.
7. Melhorar arquitetura para evitar polling e usar eventos/callbacks quando possível.
8. Corrigir bugs e melhorar validações.

Antes de modificar cada parte, explique brevemente o que será alterado e por quê.
```

---
### 8.3 Implementar troca privada, alerta público e espionagem

```text
Analise e implemente com prioridade alta o sistema de troca privada de dicas descrito no PDF da avaliação e no arquivo INSTRUCOES_CODEX_RPC_RMI_ADIVINHACAO.md.

Requisitos obrigatórios:
1. Além das dicas públicas padrão, deve existir uma ação própria para solicitar troca privada de dicas com outro jogador específico.
2. O jogador convidado precisa aceitar ou recusar a troca.
3. Se aceitar, os dois jogadores enviam uma dica privada um para o outro.
4. Cada dica privada deve conter uma única palavra.
5. A dica privada pode ser verdadeira ou falsa.
6. Os demais jogadores devem receber um alerta dizendo que houve uma troca privada entre aqueles dois jogadores.
7. O alerta público não pode revelar o conteúdo das dicas privadas.
8. Após o alerta, jogadores terceiros devem poder tentar espiar a troca.
9. A espionagem deve ter chance de descoberta.
10. Se o espião for descoberto, ele deve perder pontos automaticamente.
11. Participantes da troca não podem espiar a própria troca.
12. Tudo isso deve ser separado do chat.
13. Tudo isso deve usar RPC/RMI, não comunicação paralela fora da arquitetura principal.

Também quero que você melhore essa parte usando eventos/callbacks/listeners, evitando polling. O servidor deve notificar os clientes quando houver solicitação, aceite, alerta público, tentativa de espionagem, resultado de descoberta e atualização de pontuação.

Antes de alterar o código, mostre quais arquivos serão modificados e qual fluxo de eventos será implementado.
```

---

### 8.4 Melhorar qualidade para maior nota

```text
Revise o projeto buscando melhorar a qualidade da implementação para a avaliação.

Foque em:
- Remover ou reduzir polling.
- Usar eventos, callbacks, listeners ou mecanismo equivalente.
- Separar regras de negócio, comunicação RPC/RMI e interface.
- Melhorar tratamento de erros.
- Melhorar validação de entradas.
- Melhorar logs e histórico de ações.
- Garantir que o estado do jogo fique consistente entre todos os clientes.
- Deixar o fluxo fácil de demonstrar ao professor.

Mostre primeiro os problemas encontrados e depois aplique as correções necessárias.
```

---

### 8.5 Gerar ou revisar o relatório

```text
Crie ou revise o relatório do projeto conforme o enunciado da avaliação.

O relatório deve conter:
1. Introdução à biblioteca ou módulo RPC/RMI usado no projeto.
2. Justificativa da escolha dessa tecnologia.
3. Descrição de como a aplicação foi desenvolvida.
4. Explicação da arquitetura do sistema.
5. Explicação das principais funcionalidades do jogo.
6. Capturas de tela ou indicação dos pontos onde devo inserir as capturas.
7. Trechos de código importantes explicados.
8. Instruções de instalação.
9. Instruções de uso.
10. Explicação de como executar a demonstração.

Use linguagem acadêmica simples, clara e objetiva.
```

---

### 8.6 Preparar a demonstração

```text
Crie um roteiro de demonstração para apresentar este projeto ao professor.

O roteiro deve mostrar:
1. Como iniciar o servidor.
2. Como iniciar múltiplos clientes.
3. Como os jogadores entram na partida.
4. Como cada jogador recebe seu objeto.
5. Como funcionam os turnos.
6. Como enviar dicas públicas.
7. Como tentar adivinhar um objeto.
8. Como funciona a arbitragem.
9. Como funciona a troca privada de dicas.
10. Como funciona a espionagem e a perda de pontos.
11. Como funciona o chat em tempo real separado das ações do jogo.
12. Como o placar é calculado.
13. Como finalizar ou continuar a rodada.

Inclua também uma lista de testes rápidos para garantir que nada quebre durante a apresentação.
```

---

## 9. Critérios que mais podem aumentar a nota

Para buscar a maior avaliação possível, priorize estes pontos:

1. **Comunicação RPC/RMI real e clara**  
   O professor precisa perceber facilmente que o projeto usa RPC/RMI, não apenas chamadas locais.

2. **Funcionalidades obrigatórias completas**  
   Todas as regras do jogo precisam estar implementadas: dicas, palpites, troca privada, espionagem, pontuação e chat.

3. **Chat separado das ações do jogo**  
   Esse ponto é explícito no enunciado e deve estar evidente.

4. **Pontuação automática**  
   Não deixar pontuação para cálculo manual.

5. **Troca privada com alerta e espionagem bem implementados**  
   Deve haver solicitação, aceite/recusa, dicas privadas de uma palavra, alerta público aos demais e possibilidade de espionagem com chance de descoberta e penalidade.

6. **Atualização baseada em eventos**  
   O enunciado indica que isso é melhor avaliado do que polling. Essa melhoria deve aparecer no código, no relatório e na demonstração.

7. **Boa demonstração**  
   A apresentação precisa mostrar o jogo funcionando com múltiplos jogadores.

8. **Relatório completo**  
   O relatório deve explicar tecnologia escolhida, desenvolvimento, capturas, código, instalação e uso.

9. **Entrega organizada em ZIP**  
   Incluir código, arquivos de entrada/imagens e relatório PDF.

---

## 10. Estrutura recomendada do projeto

A estrutura pode variar conforme a linguagem, mas uma organização adequada seria:

```text
projeto-rpc-rmi-adivinhacao/
├── README.md
├── INSTRUCOES_CODEX_RPC_RMI_ADIVINHACAO.md
├── relatorio/
│   └── relatorio.pdf
├── assets/
│   └── objetos/
│       ├── objeto1.png
│       ├── objeto2.png
│       └── ...
├── src/
│   ├── server/
│   │   ├── servidor
│   │   ├── servicos_rpc_ou_rmi
│   │   └── estado_jogo
│   ├── client/
│   │   ├── cliente
│   │   ├── interface
│   │   └── callbacks_ou_eventos
│   ├── game/
│   │   ├── jogador
│   │   ├── partida
│   │   ├── rodada
│   │   ├── pontuacao
│   │   ├── arbitragem
│   │   └── regras
│   └── chat/
│       └── chat_service
├── tests/
│   └── testes_basicos
└── docs/
    └── roteiro_demo.md
```

---

## 11. Regras de validação importantes

O Codex deve garantir que o sistema valide:

- Nome de jogador vazio.
- Jogador duplicado.
- Jogador tentando adivinhar o próprio objeto.
- Dica vazia.
- Dica pública com mais de uma palavra.
- Dica privada com mais de uma palavra.
- Palpite vazio.
- Troca de dica consigo mesmo.
- Troca repetida na mesma rodada.
- Espionagem feita por participante da própria troca.
- Pontuação duplicada pelo mesmo acerto.
- Ações fora do turno.
- Cliente desconectado.
- Servidor indisponível.

---

## 12. Histórico de eventos recomendado

Para facilitar depuração, relatório e demonstração, implementar um histórico de eventos como:

```text
[Turno 1] João enviou dica pública: "metal"
[Turno 1] Maria tentou adivinhar o objeto de João: "chave"
[Turno 1] Palpite de Maria foi aceito
[Turno 2] Ana solicitou troca de dica com Pedro
[Turno 2] Pedro aceitou a troca
[Turno 2] Carlos tentou espionar a troca entre Ana e Pedro
[Turno 2] Carlos foi descoberto e perdeu 2 pontos
[Final] Pontuação calculada
```

Esse histórico ajuda a provar que as regras foram executadas corretamente.

---

## 13. Testes mínimos antes da entrega

Executar testes manuais ou automatizados para verificar:

- [ ] Dois jogadores conseguem conectar.
- [ ] Três ou mais jogadores conseguem conectar.
- [ ] Cada jogador recebe objeto diferente.
- [ ] Jogador envia dica pública.
- [ ] Todos recebem a dica pública.
- [ ] Jogador consegue tentar adivinhar objeto de outro.
- [ ] Palpite correto gera pontuação.
- [ ] Palpite errado não gera pontuação indevida.
- [ ] Troca privada exige aceite.
- [ ] Troca privada avisa os demais jogadores.
- [ ] Espionagem pode ser descoberta.
- [ ] Espionagem descoberta remove pontos.
- [ ] Chat funciona separado das ações.
- [ ] Fim dos turnos permite continuar ou encerrar.
- [ ] Nova rodada distribui novos objetos.
- [ ] Placar final está correto.

---

## 14. Conteúdo obrigatório do relatório PDF

O relatório final deve conter:

### 14.1 Introdução

- Explicar o objetivo do projeto.
- Explicar brevemente o conceito de RPC/RMI.
- Apresentar a tecnologia escolhida.

### 14.2 Biblioteca ou módulo RPC/RMI escolhido

Incluir:

- Nome da biblioteca.
- Como ela funciona.
- Por que foi escolhida.
- Vantagens para o projeto.
- Limitações encontradas.

### 14.3 Desenvolvimento da aplicação

Explicar:

- Arquitetura geral.
- Comunicação entre cliente e servidor.
- Controle de jogadores.
- Controle de turnos.
- Distribuição de objetos.
- Envio de dicas.
- Palpites e arbitração.
- Troca privada de dicas.
- Espionagem.
- Chat.
- Pontuação.

### 14.4 Capturas de tela

Inserir imagens mostrando:

- Servidor iniciado.
- Clientes conectados.
- Objeto recebido por jogador.
- Dicas públicas.
- Chat em funcionamento.
- Tentativa de palpite.
- Troca de dicas.
- Espionagem.
- Placar.

### 14.5 Trechos de código

Inserir trechos relevantes:

- Interface RPC/RMI.
- Registro de jogador.
- Envio de dica.
- Chat.
- Pontuação.
- Espionagem.
- Callback/evento, se existir.

### 14.6 Instalação

Explicar:

- Dependências.
- Versão da linguagem.
- Como instalar bibliotecas.
- Como configurar arquivos de entrada.

### 14.7 Uso

Explicar:

- Como iniciar servidor.
- Como iniciar cliente.
- Como entrar na partida.
- Como jogar.
- Como encerrar.

---

## 15. Roteiro resumido para apresentação

Durante a apresentação, demonstrar nesta ordem:

1. Abrir o projeto e explicar a arquitetura.
2. Mostrar rapidamente onde está a parte RPC/RMI.
3. Iniciar servidor.
4. Iniciar dois ou três clientes.
5. Registrar jogadores.
6. Iniciar partida.
7. Mostrar objetos diferentes para cada jogador.
8. Enviar dicas públicas.
9. Fazer uma tentativa de adivinhação.
10. Mostrar arbitração ou validação automática.
11. Mostrar pontuação sendo atualizada.
12. Solicitar troca privada de dica.
13. Aceitar troca.
14. Mostrar aviso aos demais jogadores.
15. Tentar espionagem.
16. Mostrar chance de descoberta e penalidade.
17. Enviar mensagens no chat.
18. Reforçar que chat não é usado para ações do jogo.
19. Encerrar turnos.
20. Mostrar opção de continuar ou finalizar.
21. Exibir placar final.

---

## 16. Ordem recomendada de desenvolvimento restante

Caso ainda faltem partes no projeto, implementar nesta ordem:

1. Garantir conexão RPC/RMI entre servidor e múltiplos clientes.
2. Implementar estado central da partida.
3. Implementar cadastro de jogadores.
4. Implementar distribuição de objetos/imagens.
5. Implementar turnos.
6. Implementar dicas públicas.
7. Implementar palpites e arbitração.
8. Implementar pontuação básica.
9. Implementar troca privada de dicas.
10. Implementar espionagem.
11. Implementar chat em tempo real separado.
12. Implementar continuação/finalização de rodada.
13. Melhorar eventos/callbacks.
14. Melhorar interface e experiência de demonstração.
15. Finalizar relatório e ZIP.

---

## 17. Definição de pronto

Considere o projeto pronto quando:

- Vários jogadores conseguem jogar ao mesmo tempo.
- O professor consegue ver claramente o uso de RPC/RMI.
- Todas as ações do jogo funcionam separadas do chat.
- O sistema calcula pontuação automaticamente.
- Existe troca privada de dicas com aceite.
- Existe espionagem com chance de descoberta.
- O chat funciona em tempo real.
- O projeto possui relatório PDF completo.
- O ZIP contém código, imagens/arquivos de entrada e relatório.
- A demonstração pode ser feita sem passos improvisados.

---

## 18. Observação final para o Codex

Ao modificar o projeto, preserve o que já funciona. Não reescreva tudo sem necessidade.

Sempre que possível:

- Faça alterações pequenas e verificáveis.
- Explique o motivo das mudanças.
- Rode testes ou indique como testar.
- Atualize o README se comandos de execução mudarem.
- Priorize os requisitos explícitos do enunciado.
- Evite adicionar dependências desnecessárias.
- Garanta que o projeto final seja simples de demonstrar.
