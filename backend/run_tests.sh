#!/bin/bash
echo "Instalando dependencias de testing..."
source .venv/bin/activate
pip install pytest pytest-asyncio httpx aiosqlite

echo ""
echo "=============================="
echo " Ejecutando Pruebas (Pytest)  "
echo "=============================="
python -m pytest tests/

echo ""
echo "¡Pruebas finalizadas!"
