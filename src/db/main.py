"""
Database seeding entry point.
Initializes InfluxDB with device registry and sensor data.
"""

import logging
import sys

from seed import initialize_database
from database import close_db_client


def setup_logging() -> None:
    """Configure logging for database operations."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def main() -> int:
    """
    Main entry point for database seeding.
    
    Returns:
        Exit code (0 = success, 1 = failure)
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        
        # Initialize database (creates devices and seeds data)
        devices = initialize_database()
        
        # Display results
        logger.info("Database initialization complete. Seeded %d devices.", len(devices))
        
        return 0
        
    except Exception as e:
        logger.error("Database initialization failed: %s", e)
        return 1
        
    finally:
        # Cleanup
        close_db_client()
        logger.info("Database client closed")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
