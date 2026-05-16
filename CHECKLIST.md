# Checklist de Atendimento ao PDF do Professor

Este checklist compara as regras do arquivo `trabalho-1-cc5sdt-2026-1.pdf` com a implementação atual do projeto.

## Requisitos do Jogo

| Regra do PDF | Como atendemos no projeto | Status |
| --- | --- | --- |
| Desenvolver uma aplicação usando RPC ou RMI. | A comunicação usa Pyro5, expondo o `GameServer` como objeto remoto em `server.py` e callbacks remotos no cliente em `events.py`. | Atendido |
| A aplicação deve ser um jogo multijogador de adivinhação. | O servidor gerencia múltiplos jogadores, distribui objetos secretos e processa dicas, palpites, trocas e pontuação. | Atendido |
| Cada jogador receberá uma imagem de um objeto. | `_start_round()` sorteia objetos de `POSSIBLE_OBJECTS`, lê a imagem em `objects_images/` e envia em Base64 ao cliente pelo callback `game_started`. | Atendido |
| A cada turno, cada jogador envia aos outros uma dica curta sobre seu objeto. | `send_public_hint()` aceita uma dica pública de uma palavra na fase `WAITING_HINTS` e envia para todos via `receive_public_hint`. | Atendido |
| A dica pública deve ser curta, por exemplo uma única palavra. | O servidor bloqueia dicas públicas com mais de uma palavra. A interface também valida antes de enviar. | Atendido |
| Os outros jogadores podem tentar adivinhar ou esperar até o próximo turno. | Na fase `ACTION_PHASE`, cada jogador pode enviar palpite com `guess_object()` ou clicar em `Pronto` para encerrar suas ações no turno. | Atendido |
| Uma vez para cada objeto, cada jogador pode trocar uma dica com outro jogador específico. | `has_traded` limita a troca privada. Ele não é resetado entre turnos, apenas quando uma nova rodada/novo objeto começa. | Atendido |
| A troca de dicas deve ser aceita pelo outro jogador. | `request_trade()` cria uma solicitação pendente e `respond_trade()` exige aceite ou recusa do alvo. | Atendido |
| A dica trocada também deve conter uma única palavra. | `request_trade()` e `respond_trade()` rejeitam dicas privadas com mais de uma palavra. | Atendido |
| Não é obrigatório que as dicas trocadas sejam verdadeiras. | O sistema não valida se a dica privada é verdadeira; apenas valida formato e filtro de palavra proibida. | Atendido |
| Os outros jogadores devem ser avisados que dois jogadores trocaram dicas. | Após uma troca aceita, `trade_occurred_public()` é enviado a todos, informando os nomes dos envolvidos. | Atendido |
| Qualquer jogador poderá tentar espiar a troca de dicas entre dois outros jogadores. | Terceiros recebem alerta de troca e podem chamar `spy_on_trade()`. Jogadores envolvidos não podem espiar a própria troca. | Atendido |
| Espionagem deve ter chance de ser descoberta. | `spy_on_trade()` usa chance aleatória de 30% para falha. | Atendido |
| Se descoberto espiando, o jogador perde pontos. | Em caso de falha na espionagem, o servidor desconta 10 pontos e notifica os clientes. | Atendido |
| Pode ser definido um limite máximo de turnos. | `MAX_TURNS = 3` em `constants.py`. Ao completar o último turno, o servidor vai para votação. | Atendido |
| Deve haver mecanismo de arbitragem para definir se palpites estão corretos. | O dono do objeto recebe um pop-up de julgamento pelo callback `request_judgment` e responde com `judge_guess()`. | Atendido |
| Ao final dos turnos, jogadores podem decidir finalizar ou continuar. | Após o último turno, a fase vira `VOTE_CONTINUE`, com botões para continuar ou encerrar. | Atendido |
| Caso decidam continuar, cada jogador recebe novo objeto e o jogo repete. | Se a maioria votar por continuar, `_start_round()` inicia nova rodada com novos objetos e mantém a pontuação acumulada. | Atendido |

## Requisitos de Pontuação

| Regra do PDF | Como atendemos no projeto | Status |
| --- | --- | --- |
| Quem adivinhar corretamente um objeto ganha pontos. | `ScoreCalculator.apply_correct_guess()` soma pontos ao jogador que acertou. | Atendido |
| O primeiro a adivinhar recebe pontuação maior. | Primeiro acerto vale `20` pontos. | Atendido |
| Jogadores que acertarem depois recebem menos pontos. | Acertos posteriores do mesmo objeto valem `10` pontos. | Atendido |
| Se apenas um jogador adivinhar corretamente, ele recebe bônus. | Ao fim da rodada, se apenas um jogador acertou determinado objeto, esse acertador recebe bônus de `10` pontos. | Atendido |
| Cada jogador recebe pontos baseado em quantos jogadores acertaram seu objeto. | Ao fim da rodada, o dono recebe pontos conforme a quantidade de acertos no seu objeto. | Atendido |
| O dono recebe maior pontuação se apenas um outro jogador descobrir seu objeto. | Se exatamente um jogador acerta o objeto, o dono recebe `15` pontos. | Atendido |
| Se mais de um jogador acertar, a pontuação do dono será menor. | Se mais de um acerta, mas não todos, o dono recebe `8` pontos. | Atendido |
| Se ninguém acertar, o dono não ganha pontos nesse quesito. | Se `guessers` está vazio, nenhuma pontuação é adicionada ao dono. | Atendido |
| Se todos os outros jogadores acertarem, o dono perde pontos. | Com mais de 2 jogadores, se todos os outros acertam, o dono perde `10` pontos. | Atendido |
| A contabilização dos pontos deve ser feita pela aplicação. | A pontuação é calculada automaticamente no servidor, principalmente em `score.py`. | Atendido |
| Evitar problema de pontuação com apenas 2 jogadores. | Com 2 jogadores, a pontuação especial do dono é ignorada para evitar conflito entre "apenas um acertou" e "todos acertaram". | Atendido |

## Requisitos de Chat e Separação de Funcionalidades

| Regra do PDF | Como atendemos no projeto | Status |
| --- | --- | --- |
| Deve haver chat em tempo real integrado. | `send_chat_message()` envia mensagens para todos via callback `receive_chat_message`. | Atendido |
| Todos os jogadores podem conversar e discutir o jogo. | O chat global fica disponível na interface de todos os clientes. | Atendido |
| Chat deve ser separado das outras funcionalidades. | Chat, dica pública, palpite, troca privada e espionagem usam métodos RPC diferentes. | Atendido |
| Dicas para o grupo não devem ser realizadas via chat. | Dicas públicas usam `send_public_hint()`, não o chat. | Atendido |
| Trocas de dicas não devem ser realizadas via chat. | Trocas usam `request_trade()` e `respond_trade()`. | Atendido |
| Espionagem não deve ser realizada via chat. | Espionagem usa `spy_on_trade()`. | Atendido |
| Tentativas de adivinhar não devem ser realizadas via chat. | Palpites usam `guess_object()` e julgamento usa `judge_guess()`. | Atendido |
| Evitar que o jogador entregue o próprio objeto no chat ou dicas. | O servidor bloqueia nome do próprio objeto e sinônimos definidos em `OBJECT_SYNONYMS` no chat, dica pública e troca privada. | Melhoria extra |

## Requisitos de Comunicação e Arquitetura

| Regra do PDF | Como atendemos no projeto | Status |
| --- | --- | --- |
| Toda comunicação deve ser realizada via RPC ou RMI. | Clientes chamam métodos remotos do servidor via Pyro5; servidor chama callbacks remotos dos clientes via Pyro5. | Atendido |
| É livre escolher se os clientes conectam entre si ou via servidor. | A arquitetura usa servidor central. Clientes não precisam se conectar diretamente entre si. | Atendido |
| Aplicação baseada em eventos é melhor avaliada que polling. | O servidor notifica clientes por callbacks (`@Pyro5.api.oneway`). A interface usa apenas uma fila local do Tkinter para processar eventos recebidos. | Atendido |

## Requisitos de Relatório e Entrega

| Regra do PDF | Como atendemos no projeto | Status |
| --- | --- | --- |
| Relatório deve apresentar introdução à biblioteca RPC/RMI escolhida. | `Relatorio.md` contém introdução ao Pyro5. | Parcial |
| Relatório deve justificar a escolha da biblioteca. | `Relatorio.md` contém justificativa da escolha do Pyro5. | Parcial |
| Relatório deve descrever como a aplicação foi desenvolvida. | `Relatorio.md` descreve arquitetura e funcionalidades principais. | Parcial |
| Relatório deve conter capturas de tela. | Ainda é necessário inserir capturas de tela reais da aplicação. | Pendente |
| Relatório deve conter trechos de código. | Ainda é recomendado inserir trechos de código relevantes no relatório final. | Pendente |
| Relatório deve conter instruções de instalação e uso. | `README.md` e `Relatorio.md` contêm instruções de execução. | Parcial |
| Relatório deve ser entregue em PDF. | Atualmente existe `Relatorio.md`; ainda precisa ser convertido para PDF. | Pendente |
| Entrega deve conter todos os arquivos do projeto e arquivos de entrada. | O projeto contém código e imagens em `objects_images/`. | Atendido |
| Todos os arquivos devem estar em um ZIP enviado ao Moodle. | Ainda é necessário gerar o arquivo `.zip` final com código, imagens e relatório PDF. | Pendente |

## Validação Técnica Atual

Comandos executados durante a revisão:

```bash
python3 -m unittest discover -s tests
python3 -m py_compile server.py client.py interface.py events.py score.py constants.py
```

Resultado atual:

- Testes automatizados passando.
- Arquivos Python compilando sem erro de sintaxe.
