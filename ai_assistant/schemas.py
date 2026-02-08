from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    db_ip_address: str
    inference_model_name: str
    host: str
    port: int
