"""Config flow cho Senergy Cloud Inverter."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SenergyApiError, SenergyAuthError, SenergyCloudApi
from .const import (
    CONF_DATA_SIGN,
    CONF_DEVICE_NAME,
    CONF_GOODS_ID,
    CONF_LOGIN_SIGN,
    CONF_MEMBER_ID,
    CONF_PASSWORD,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MEMBER_ID): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_LOGIN_SIGN): str,
        vol.Required(CONF_GOODS_ID): str,
        vol.Required(CONF_DATA_SIGN): str,
        vol.Optional(CONF_DEVICE_NAME, default="Senergy Inverter"): str,
    }
)


async def _validate(hass: HomeAssistant, data: dict[str, Any]) -> None:
    session = async_get_clientsession(hass)
    api = SenergyCloudApi(
        session,
        data[CONF_MEMBER_ID],
        data[CONF_PASSWORD],
        data[CONF_LOGIN_SIGN],
    )
    await api.async_login()
    result = await api.async_get_inverter_detail(data[CONF_GOODS_ID], data[CONF_DATA_SIGN])
    if not result or "GoodsID" not in result:
        raise CannotFetchData(f"Không nhận được dữ liệu hợp lệ từ GoodsID={data[CONF_GOODS_ID]}")


class CannotFetchData(HomeAssistantError):
    """Không lấy được dữ liệu biến tần với data_sign đã nhập."""


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow cho Senergy Cloud Inverter."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_MEMBER_ID]}_{user_input[CONF_GOODS_ID]}"
            )
            self._abort_if_unique_id_configured()
            try:
                await _validate(self.hass, user_input)
            except SenergyAuthError:
                errors["base"] = "invalid_auth"
            except CannotFetchData:
                errors["base"] = "cannot_fetch_data"
            except SenergyApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Lỗi không xác định khi thiết lập Senergy")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_DEVICE_NAME], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
