from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuración de la aplicación.
    Lee las variables de entorno del archivo .env
    """
    database_url: str = "postgresql+asyncpg:///orpey_db?host=/var/run/postgresql"
    app_name: str = "Orpey Servicios"
    debug: bool = True

    model_config = {"env_file": ".env"}


settings = Settings()

# Engine: es la conexión principal a la base de datos
# asyncpg es el driver que usa FastAPI para conectar de forma asíncrona
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # Si debug=True, muestra las consultas SQL en la consola
)

# SessionFactory: crea sesiones para interactuar con la BD
# Cada request HTTP tendrá su propia sesión
async_session = async_sessionmaker(
    engine,
    expire_on_commit=False,  # Evita que los objetos se "desconecten" después de commit
)


async def get_db():
    """
    Dependency que provee una sesión de base de datos.
    Se usa en cada endpoint para obtener acceso a la BD.
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()  # Guarda los cambios si todo salió bien
        except Exception:
            await session.rollback()  # Deshace los cambios si hubo error
            raise
