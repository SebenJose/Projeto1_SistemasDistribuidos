@echo off
:: Inicia o servidor em uma nova janela
start "Servidor" cmd /k "python server.py"

:: Aguarda 2 segundos para o servidor inicializar
timeout /t 2 /nobreak > nul

:: Inicia os clientes em novas janelas
start "Jogador 1" cmd /k "python client.py jogador1"
start "Jogador 2" cmd /k "python client.py jogador2"
start "Jogador 3" cmd /k "python client.py jogador3"
