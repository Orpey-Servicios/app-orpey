import pytest
from src.services.consulta_ruc_sri import (
    validar_identificacion_ecuador,
    separar_nombres_apellidos,
    consultar_sri
)


def test_validar_cedula_valida():
    # Cédulas reales válidas
    cedulas = ["0941190118", "0956266506", "0927295410"]
    for c in cedulas:
        res = validar_identificacion_ecuador(c)
        assert res["valido"] is True
        assert res["tipo"] == "CEDULA"


def test_validar_cedula_invalida():
    # Longitud incorrecta
    assert validar_identificacion_ecuador("123")["valido"] is False
    # Provincia inválida (99)
    assert validar_identificacion_ecuador("9912345678")["valido"] is False
    # Tercer dígito >= 6 en cédula
    assert validar_identificacion_ecuador("0981234567")["valido"] is False
    # Dígito verificador incorrecto
    assert validar_identificacion_ecuador("0941190119")["valido"] is False


def test_validar_ruc_natural():
    res = validar_identificacion_ecuador("0941190118001")
    assert res["valido"] is True
    assert res["tipo"] == "RUC_NATURAL"

    # Establecimiento 000 es inválido
    res_000 = validar_identificacion_ecuador("0941190118000")
    assert res_000["valido"] is False


def test_validar_ruc_sociedad():
    # RUCs reales de sociedades
    rucs = ["1790016919001", "1790166406001"]
    for r in rucs:
        res = validar_identificacion_ecuador(r)
        assert res["valido"] is True
        assert res["tipo"] == "RUC_SOCIEDAD"


def test_separar_nombres_apellidos():
    # 4 palabras (Caso típico SRI: APELLIDO1 APELLIDO2 NOMBRE1 NOMBRE2)
    p4 = separar_nombres_apellidos("ORTIZ CAYETANO ARELYS DAYANNA", "PERSONA NATURAL")
    assert p4["apellido"] == "Ortiz Cayetano"
    assert p4["nombre"] == "Arelys Dayanna"

    # 3 palabras
    p3 = separar_nombres_apellidos("PEREZ GOMEZ JUAN", "PERSONA NATURAL")
    assert p3["apellido"] == "Perez Gomez"
    assert p3["nombre"] == "Juan"

    # 2 palabras
    p2 = separar_nombres_apellidos("PEREZ JUAN", "PERSONA NATURAL")
    assert p2["apellido"] == "Perez"
    assert p2["nombre"] == "Juan"

    # Sociedad
    soc = separar_nombres_apellidos("CORPORACION FAVORITA C.A.", "SOCIEDAD")
    assert "Corporacion" in soc["nombre"]
    assert "Favorita C.A." in soc["apellido"]


@pytest.mark.asyncio
async def test_consultar_sri_cedula_real():
    # Cédula que tiene RUC en SRI
    res = await consultar_sri("0941190118")
    assert res["valido"] is True
    assert res["encontrado"] is True
    assert "ORTIZ CAYETANO ARELYS DAYANNA" in res["razon_social"]
    assert res["nombre"] == "Arelys Dayanna"
    assert res["apellido"] == "Ortiz Cayetano"
    assert res["tipo_persona"] == "natural"
    assert "GUAYAS" in res["direccion"]


@pytest.mark.asyncio
async def test_consultar_sri_ruc_sociedad():
    # RUC Corporación Favorita
    res = await consultar_sri("1790016919001")
    assert res["valido"] is True
    assert res["encontrado"] is True
    assert "CORPORACION FAVORITA" in res["razon_social"]
    assert res["tipo_persona"] == "juridica"
    assert res["estado"] == "ACTIVO"

from httpx import AsyncClient, ASGITransport
from src.main import app

@pytest.mark.asyncio
async def test_endpoint_consultar_sri():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/clientes/consultar-sri/0941190118")
    assert response.status_code == 200
    data = response.json()
    assert data["encontrado"] is True
    assert data["identificacion"] == "0941190118"
    assert "ORTIZ CAYETANO ARELYS DAYANNA" in data["razon_social"]
