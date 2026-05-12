# Plano de Atualização do Jogo para Nota Máxima

## 1. Imagens dos Objetos
Em vez de enviar apenas uma string, o servidor enviará uma imagem em Base64, e o cliente salvará e a abrirá (ou podemos usar ASCII art para facilitar no CLI, mas salvar/abrir imagem é mais bonito e cumpre o requisito). Vou baixar imagens para os 10 objetos e enviar.

## 2. Turnos Múltiplos
Implementar o controle de turnos. Atualmente só há 1 turno.
- Definir `MAX_TURNS = 3`.
- Adicionar `turn` à classe `GameServer`.
- Após todos darem `/pronto`, se `turn < MAX_TURNS`, iniciar o próximo turno (limpando as dicas e o status de `is_ready`).
- Impedir que o jogador adivinhe o mesmo objeto mais de uma vez? Ou permitir? (O requisito não fala, mas faz sentido não poder adivinhar se já acertou).

## 3. Limite de Trocas
"Uma vez para cada objeto, cada jogador terá a oportunidade de trocar"
- Adicionar `has_traded: False` no state de cada jogador.
- Ao concluir uma troca (aceita), ambos os jogadores ficam com `has_traded = True`.

## 4. Mecanismo de Arbitração (Jogador confere as respostas)
Em vez de checar com `self._check_guess`, quando o jogador dá `/adivinhar <alvo> <palavra>`:
- O servidor salva o palpite pendente.
- O servidor notifica o `<alvo>`: "O jogador X acha que seu objeto é Y. Isso está correto? Responda com /julgar <jogador> sim|nao".
- O `<alvo>` julga. Se sim, contabiliza o acerto. Se não, perde 5 pontos.

## 5. Escrita do Relatório
Criar o `Relatorio.pdf` ou `Relatorio.md`.
