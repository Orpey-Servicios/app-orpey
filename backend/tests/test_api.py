import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app

@pytest.mark.asyncio
async def test_health_check():
    """Prueba que la API responde correctamente"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.2.0"}

@pytest.mark.asyncio
async def test_raiz():
    """Prueba el endpoint raíz"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "mensaje" in data
    assert data["mensaje"] == "Bienvenido a Orpey Servicios API"
