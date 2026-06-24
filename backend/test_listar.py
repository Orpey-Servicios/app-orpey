import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.database import async_session
from src.routers.ordenes import listar_ordenes

async def run():
    try:
        async with async_session() as session:
            ordenes = await listar_ordenes(estado=None, cliente_id=None, tipo_equipo=None, db=session)
            print("OK, fetched:", len(ordenes))
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
