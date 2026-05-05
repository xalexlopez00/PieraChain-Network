#!/bin/bash
# Inicia la API y la deja en segundo plano
uvicorn main:app --host 0.0.0.0 --port 10000 &

# Espera 5 segundos para que la API esté lista antes de lanzar el bot
sleep 5

# Inicia el Bot de Discord
python bot.py