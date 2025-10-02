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


# https://backend.kerbl-iot.com/api/v0.1/auth/sign-in
API_URL_LOGIN = "https://backend.kerbl-iot.com/api/v0.1/auth/sign-in"   # <-- change to your API
API_URL_DATA = "https://backend.kerbl-iot.com/api/v0.1/device"   # <-- change to your API

JSON_KEY = "result"                   # <-- key to extract

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    session = aiohttp.ClientSession()

    email = config.get("email")
    password = config.get("password")

    async def async_update_data():
        """Fetch data from API."""
        try:
            # 1) Login
            with async_timeout.timeout(10):
                async with session.post(API_URL_LOGIN, json={"email": email, "password": password}) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"Login failed: {resp.status}")
                    login_data = await resp.json()

            access_token = login_data.get("accessToken")
            if not access_token:
                raise UpdateFailed("No access token in login response")

            headers = {"Authorization": f"Bearer {access_token}"}

            # 2) Fetch sensor data
            with async_timeout.timeout(10):
                async with session.get(API_URL_DATA, headers=headers) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"Data request failed: {resp.status}")
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

    devices = []
    if coordinator.data and "smartWeather" in coordinator.data:
        for dev in coordinator.data["smartWeather"]:
            devices.append(TempStationTemperature(coordinator, dev))
            devices.append(TempStationHumidity(coordinator, dev))

    async_add_entities(devices, True)


class TempStationBase(CoordinatorEntity, SensorEntity):
    """Base class for Temp Station sensors tied to one device."""

    def __init__(self, coordinator, device):
        super().__init__(coordinator)
        self.device = device
        self._attr_device_info = {
            "identifiers": {("temp_station_integration", device["id"])},
            "name": device.get("name", f"Station {device['id']}"),
            "manufacturer": "Kerbl IoT",
        }

    @property
    def device_id(self):
        return self.device["id"]

    def get_device(self):
        """Find latest device data by id in coordinator."""
        if not self.coordinator.data or "smartWeather" not in self.coordinator.data:
            return None
        for d in self.coordinator.data["smartWeather"]:
            if d["id"] == self.device["id"]:
                return d
        return None


class TempStationTemperature(TempStationBase):
    @property
    def name(self):
        return f"{self.device['name']} Temperature"

    @property
    def unique_id(self):
        return f"{self.device_id}_temperature"

    @property
    def native_unit_of_measurement(self):
        return "°C"

    @property
    def native_value(self):
        dev = self.get_device()
        return float(dev.get("tempf")) / 10.0 if dev else None


class TempStationHumidity(TempStationBase):
    @property
    def name(self):
        return f"{self.device['name']} Humidity"

    @property
    def unique_id(self):
        return f"{self.device_id}_humidity"

    @property
    def native_unit_of_measurement(self):
        return "%"

    @property
    def native_value(self):
        dev = self.get_device()
        return dev.get("humidity") if dev else None