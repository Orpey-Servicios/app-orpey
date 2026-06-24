#!/bin/bash
# Script para ejecutar el servidor de desarrollo de Orpey Servicios
#
# Uso:
#   ./run.sh              → Inicia el servidor
#   ./run.sh --docs       → Abre el navegador con la documentación

cd "$(dirname "$0")"

echo "================================================"
echo "  Orpey Servicios - Backend API"
echo "================================================"
echo ""
echo "Servidor iniciando..."
echo "Documentación: http://127.0.0.1:8000/docs"
echo ""

python3 -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
