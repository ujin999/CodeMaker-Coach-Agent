import logging
from typing import Generator
from neo4j import GraphDatabase, Driver
from config.settings import settings

logger = logging.getLogger(__name__)

_driver: Driver | None = None

def get_driver() -> Driver:
    """Returns the singleton Neo4j driver instance. Initializes connection if necessary."""
    global _driver
    if _driver is None:
        try:
            _driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
            # Verify connectivity
            _driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j database.")
        except Exception as e:
            logger.warning(f"Failed to connect to Neo4j database: {e}. Graph features will be offline.")
            # We don't raise here, so backend can still run if Neo4j is offline.
            raise e
    return _driver

def close_driver() -> None:
    """Closes the Neo4j driver instance."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
        logger.info("Neo4j driver connection closed.")
