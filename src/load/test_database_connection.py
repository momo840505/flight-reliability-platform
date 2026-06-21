import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENT_FILE = PROJECT_ROOT / ".env"


def main() -> None:
    """Test the PostgreSQL connection using environment variables."""

    if not ENVIRONMENT_FILE.exists():
        raise FileNotFoundError(
            f"Environment file was not found:\n{ENVIRONMENT_FILE}"
        )

    load_dotenv(ENVIRONMENT_FILE)

    database_settings = {
        "host": os.getenv("POSTGRES_HOST"),
        "port": os.getenv("POSTGRES_PORT"),
        "dbname": os.getenv("POSTGRES_DATABASE"),
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "connect_timeout": 10,
    }

    missing_settings = [
        setting_name
        for setting_name, setting_value in database_settings.items()
        if setting_name != "connect_timeout" and not setting_value
    ]

    if missing_settings:
        raise ValueError(
            f"Missing database settings: {missing_settings}"
        )

    print("=" * 60)
    print("POSTGRESQL CONNECTION TEST")
    print("=" * 60)

    try:
        with psycopg.connect(**database_settings) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        current_database(),
                        current_user,
                        current_setting('port'),
                        version();
                    """
                )

                (
                    database_name,
                    user_name,
                    database_port,
                    database_version,
                ) = cursor.fetchone()

        print("Connection status: SUCCESS")
        print(f"Database: {database_name}")
        print(f"User: {user_name}")
        print(f"Port: {database_port}")
        print(f"Version: {database_version}")
        print("=" * 60)

    except psycopg.Error as database_error:
        print("Connection status: FAILED")

        raise RuntimeError(
            "Could not connect to PostgreSQL. "
            "Check the .env password, port and PostgreSQL service."
        ) from database_error


if __name__ == "__main__":
    main()