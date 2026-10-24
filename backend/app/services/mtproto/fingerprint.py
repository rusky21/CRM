import random
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List


@dataclass
class DeviceFingerprint:
    """Represents a realistic device profile for Telegram MTProto client initialization."""
    device_model: str
    system_version: str
    app_version: str
    lang_code: str
    system_lang_code: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceFingerprint":
        return cls(
            device_model=data.get("device_model", "Desktop PC"),
            system_version=data.get("system_version", "Windows 11"),
            app_version=data.get("app_version", "5.1.7 x64"),
            lang_code=data.get("lang_code", "en"),
            system_lang_code=data.get("system_lang_code", "en-US"),
        )


# Curated realistic device pools to avoid Telegram default Telethon signatures
_REALISTIC_DEVICE_POOLS: List[Dict[str, str]] = [
    # iOS Devices (Official Telegram iOS)
    {
        "device_model": "iPhone 15 Pro",
        "system_version": "iOS 17.5.1",
        "app_version": "10.14.1 (29182)",
    },
    {
        "device_model": "iPhone 14 Pro Max",
        "system_version": "iOS 17.4.1",
        "app_version": "10.13.0 (28941)",
    },
    {
        "device_model": "iPhone 13",
        "system_version": "iOS 16.7.2",
        "app_version": "10.11.2 (28410)",
    },
    # Android Devices (Official Telegram Android)
    {
        "device_model": "Samsung Galaxy S24 Ultra (SM-S928B)",
        "system_version": "SDK 34 (Android 14)",
        "app_version": "10.14.0 (48219)",
    },
    {
        "device_model": "Google Pixel 8 Pro",
        "system_version": "SDK 34 (Android 14)",
        "app_version": "10.14.2 (48312)",
    },
    {
        "device_model": "Xiaomi 14 Pro (23116PN5BC)",
        "system_version": "SDK 34 (HyperOS 1.0)",
        "app_version": "10.13.1 (47901)",
    },
    # Desktop Devices (Official Telegram Desktop)
    {
        "device_model": "MacBook Pro (M3 Max)",
        "system_version": "macOS Sonoma 14.5",
        "app_version": "10.14.1.258913 Stable",
    },
    {
        "device_model": "PC 64bit",
        "system_version": "Windows 11 Pro 23H2",
        "app_version": "5.1.7 x64",
    },
]


def generate_random_fingerprint(
    lang_code: str = "en",
    system_lang_code: Optional[str] = None,
) -> DeviceFingerprint:
    """
    Generates a realistic, randomized device fingerprint for a new account.
    Prevents Telegram heuristic bans targeting default library fingerprints.
    """
    profile = random.choice(_REALISTIC_DEVICE_POOLS)
    
    if not system_lang_code:
        lang_mapping = {
            "en": "en-US",
            "ru": "ru-RU",
            "es": "es-ES",
            "de": "de-DE",
            "fr": "fr-FR",
        }
        system_lang_code = lang_mapping.get(lang_code, "en-US")

    return DeviceFingerprint(
        device_model=profile["device_model"],
        system_version=profile["system_version"],
        app_version=profile["app_version"],
        lang_code=lang_code,
        system_lang_code=system_lang_code,
    )
