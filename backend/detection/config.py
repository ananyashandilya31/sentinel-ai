from pydantic_settings import BaseSettings, SettingsConfigDict


class DetectionConfig(BaseSettings):
    """
    Configurable parameters and sliding window thresholds for detection rules.
    Values can be overridden via environment variables without code modification.
    """
    # 1. Brute Force Rule
    BRUTE_FORCE_FAILED_THRESHOLD: int = 8
    BRUTE_FORCE_WINDOW_SECONDS: int = 120

    # 2. Port Scan Rule
    PORT_SCAN_PORTS_THRESHOLD: int = 20
    PORT_SCAN_WINDOW_SECONDS: int = 30

    # 3. Data Exfiltration Rule (500 MB baseline outlier)
    DATA_EXFILTRATION_BYTES_THRESHOLD: int = 500_000_000

    # 4. Account Compromise Rule
    ACCOUNT_COMPROMISE_FAILED_THRESHOLD: int = 3
    ACCOUNT_COMPROMISE_WINDOW_SECONDS: int = 300
    ACCOUNT_COMPROMISE_BYTES_THRESHOLD: int = 200_000_000

    # 5. Privilege Escalation
    PRIVILEGE_CHANGE_EVENT_TYPE: str = "PRIVILEGE_CHANGE"
    AUTHORIZED_ADMINS: list[str] = ["admin", "root", "system"]

    model_config = SettingsConfigDict(
        env_prefix="DETECTION_",
        env_file=(".env", "../.env"),
        extra="ignore",
    )


detection_config = DetectionConfig()
