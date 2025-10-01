import logging
import aiohttp
import async_timeout
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=1)  # refresh every 1 min

API_URL = "https://example.com/api"   # <-- change to your API
POST_PAYLOAD = {"key": "value"}       # <-- change payload
JSON_KEY = "result"                   # <-- key to extract

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    session = aiohttp.ClientSession()

    async def async_update_data():
        try:
            with async_timeout.timeout(10):
                async with session.post(API_URL, json=POST_PAYLOAD) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"Error {resp.status}")
                    data = await resp.json()
                    return data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="my_api_integration",
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )

    await coordinator.async_config_entry_first_refresh()
    async_add_entities([MyAPISensor(coordinator)], True)


class MyAPISensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "My API Sensor"
        self._attr_unique_id = "my_api_sensor"

    @property
    def native_value(self):
        data = self.coordinator.data
        if data is None:
            return None
        return data.get(JSON_KEY)