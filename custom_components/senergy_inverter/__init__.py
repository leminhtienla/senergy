"""Senergy Cloud Inverter integration cho Home Assistant."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SenergyCloudApi
from .const import (
    CONF_DATA_SIGN,
    CONF_GOODS_ID,
    CONF_LOGIN_SIGN,
    CONF_MEMBER_ID,
    CONF_PASSWORD,
    DOMAIN,
)
from .coordinator import SenergyDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Thiết lập config entry."""
    session = async_get_clientsession(hass)
    api = SenergyCloudApi(
        session,
        entry.data[CONF_MEMBER_ID],
        entry.data[CONF_PASSWORD],
        entry.data[CONF_LOGIN_SIGN],
    )
    await api.async_login()

    coordinator = SenergyDataUpdateCoordinator(
        hass, api, entry.data[CONF_GOODS_ID], entry.data[CONF_DATA_SIGN]
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Gỡ config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
