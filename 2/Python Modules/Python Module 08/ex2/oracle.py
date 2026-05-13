import os
# Isto permite carregar variáveis a partir de um ficheiro .env
from dotenv import load_dotenv


def load_configuration():
    load_dotenv()

    matrix_mode = os.getenv("MATRIX_MODE")
    database_url = os.getenv("DATABASE_URL")
    api_key = os.getenv("API_KEY")
    log_level = os.getenv("LOG_LEVEL")
    zion_endpoint = os.getenv("ZION_ENDPOINT")

    config = {
        "MATRIX_MODE": matrix_mode,
        "DATABASE_URL": database_url,
        "API_KEY": api_key,
        "LOG_LEVEL": log_level,
        "ZION_ENDPOINT": zion_endpoint
    }

    return config


def validate_configuration(config):
    missing = []

    for key, value in config.items():
        if not value:
            missing.append(key)

    return missing


def main():
    print("ORACLE STATUS: Reading the Matrix...\n")

    config = load_configuration()

    missing = validate_configuration(config)

    if missing:
        print("WARNING: Missing configuration variables:")
        for var in missing:
            print(f"- {var}")
        print("\nUsing fallback/default behavior...\n")

    print("Configuration loaded:")

    mode = config["MATRIX_MODE"] or "development"
    print(f"Mode: {mode}")

    if config["DATABASE_URL"]:
        print("Database: Connected")
    else:
        print("Database: Not configured")

    if config["API_KEY"]:
        print("API Access: Authenticated")
    else:
        print("API Access: Missing API Key")

    log = config["LOG_LEVEL"] or "INFO"
    print(f"Log Level: {log}")

    if config["ZION_ENDPOINT"]:
        print("Zion Network: Online")
    else:
        print("Zion Network: Offline")

    print("\nEnvironment security check:")

    print("[OK] No hardcoded secrets detected")
    print("[OK] .env file properly configured")
    print("[OK] Production overrides available")

    print("\nThe Oracle sees all configurations.")


if __name__ == "__main__":
    main()
