"""DataUpdateCoordinator cho Senergy Cloud Inverter."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SenergyApiError, SenergyCloudApi
from .const import DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class SenergyDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator poll dữ liệu InverterDetailInfoNewone định kỳ."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: SenergyCloudApi,
        goods_id: str,
        data_sign: str,
    ) -> None:
        self.api = api
        self.goods_id = goods_id
        self.data_sign = data_sign
        super().__init__(
            hass,
            _LOGGER,
            name=f"senergy_inverter_{goods_id}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.api.async_get_inverter_detail(
                self.goods_id, self.data_sign
            )
        except SenergyApiError as err:
            raise UpdateFailed(f"Lỗi lấy dữ liệu biến tần {self.goods_id}: {err}") from err
