#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"
echo "=================================================="
echo " CelebMaker AI - Galeria de Mídias Local"
echo "=================================================="
echo "Abrindo galeria em http://localhost:8080..."
python3 -m http.server 8080 &
SERVER_PID=$!
sleep 1
open "http://localhost:8080"
echo "Servidor ativo! Para fechar, pressione Ctrl + C nesta janela."
wait $SERVER_PID
