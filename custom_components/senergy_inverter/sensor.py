"""Sensor entities cho Senergy Cloud Inverter.

Danh sách sensor map từ field của endpoint InverterDetailInfoNewone.
Sensor nào không cần, tắt trong HA: Settings > Devices & Services >
thiết bị Senergy > entity > bánh răng > tắt "Enabled", không cần sửa code.

Lưu ý đơn vị (đã đối chiếu với dữ liệu thật có pin PYLON):
- batChrg / batDischrg  : điện năng sạc / xả pin HÔM NAY, đơn vị kWh.
- toPbat / fromPbat     : công suất đang sạc vào / xả ra khỏi pin, đơn vị W.
- Pdc                   : công suất từng chuỗi PV, đơn vị kW.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_GOODS_ID, DOMAIN
from .coordinator import SenergyDataUpdateCoordinator


def _list_get(value: Any, index: int = 0) -> Any:
    """Nhiều field trả về dạng list (nhiều pha/nhiều string MPPT)."""
    if isinstance(value, list):
        return value[index] if len(value) > index else None
    return value if index == 0 else None


def _to_float(value: Any, index: int = 0) -> float | None:
    value = _list_get(value, index)
    if value in (None, "", "-"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _get(d: dict, *keys: str) -> Any:
    """Lấy giá trị lồng nhau an toàn, vd _get(d, 'ESP32Version', 'Version')."""
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


@dataclass(frozen=True, kw_only=True)
class SenergySensorDescription(SensorEntityDescription):
    """Mô tả 1 sensor, kèm hàm lấy giá trị từ dict JSON trả về."""

    value_fn: Callable[[dict[str, Any]], Any] = lambda data: None


_W = UnitOfPower.WATT
_KW = UnitOfPower.KILO_WATT
_KWH = UnitOfEnergy.KILO_WATT_HOUR
_V = UnitOfElectricPotential.VOLT
_A = UnitOfElectricCurrent.AMPERE
_HZ = UnitOfFrequency.HERTZ
_C = UnitOfTemperature.CELSIUS

_POWER = SensorDeviceClass.POWER
_ENERGY = SensorDeviceClass.ENERGY
_VOLTAGE = SensorDeviceClass.VOLTAGE
_CURRENT = SensorDeviceClass.CURRENT
_FREQ = SensorDeviceClass.FREQUENCY
_TEMP = SensorDeviceClass.TEMPERATURE

_MEAS = SensorStateClass.MEASUREMENT
_TOTAL = SensorStateClass.TOTAL_INCREASING

_DIAG = EntityCategory.DIAGNOSTIC


def _num(key: str, name: str, field: str, unit: Any, dev: Any, state: Any, **kw: Any):
    """Sensor số lấy từ field cấp 1 của JSON."""
    return SenergySensorDescription(
        key=key,
        name=name,
        native_unit_of_measurement=unit,
        device_class=dev,
        state_class=state,
        value_fn=lambda d, f=field: _to_float(d.get(f)),
        **kw,
    )


def _nested(
    key: str, name: str, field: str, idx: int, unit: Any, dev: Any, state: Any, **kw: Any
):
    """Sensor số lấy từ d['data'][field][idx] (AC / chuỗi PV)."""
    return SenergySensorDescription(
        key=key,
        name=name,
        native_unit_of_measurement=unit,
        device_class=dev,
        state_class=state,
        value_fn=lambda d, f=field, i=idx: _to_float(_get(d, "data", f), i),
        **kw,
    )


def _text(key: str, name: str, fn: Callable[[dict[str, Any]], Any], **kw: Any):
    """Sensor văn bản / chẩn đoán."""
    return SenergySensorDescription(key=key, name=name, value_fn=fn, **kw)


_OFF = {"entity_registry_enabled_default": False}

SENSOR_TYPES: tuple[SenergySensorDescription, ...] = (
    # ---------- Tổng quan AC / sản lượng ----------
    _nested("pac", "Công suất AC", "Pac", 0, _W, _POWER, _MEAS),
    _nested("ac_voltage", "Điện áp AC đầu ra", "Vac", 0, _V, _VOLTAGE, _MEAS, **_OFF),
    _nested("ac_current", "Dòng điện AC đầu ra", "Iac", 0, _A, _CURRENT, _MEAS, **_OFF),
    _nested("ac_frequency", "Tần số AC đầu ra", "Fac", 0, _HZ, _FREQ, _MEAS, **_OFF),
    _num("e_today", "Sản lượng hôm nay", "EToday", _KWH, _ENERGY, _TOTAL),
    _num("e_total", "Tổng sản lượng", "ETotal", _KWH, _ENERGY, _TOTAL),
    _num("peak_power", "Công suất đỉnh", "Peackpower", _W, _POWER, None,
         entity_category=_DIAG),
    _num("total_dc_power", "Tổng công suất DC (PV)", "TotalDCpower", _W, _POWER, _MEAS),
    _num("temperature", "Nhiệt độ biến tần", "Tntc", _C, _TEMP, _MEAS),
    _num("self_use_rate", "Tỷ lệ tự dùng", "Dailyself_userate", PERCENTAGE, None, _MEAS,
         icon="mdi:home-lightning-bolt"),
    _num("self_sufficiency_rate", "Tỷ lệ tự cung tự cấp", "Dailyself_sufficiencyrate",
         PERCENTAGE, None, _MEAS, icon="mdi:solar-power"),

    # ---------- DC / chuỗi PV (Pdc đơn vị kW) ----------
    _nested("dc_voltage_string1", "Điện áp PV chuỗi 1", "Vdc", 0, _V, _VOLTAGE, _MEAS),
    _nested("dc_current_string1", "Dòng điện PV chuỗi 1", "Idc", 0, _A, _CURRENT, _MEAS),
    _nested("dc_power_string1", "Công suất PV chuỗi 1", "Pdc", 0, _KW, _POWER, _MEAS),
    _nested("dc_voltage_string2", "Điện áp PV chuỗi 2", "Vdc", 1, _V, _VOLTAGE, _MEAS),
    _nested("dc_current_string2", "Dòng điện PV chuỗi 2", "Idc", 1, _A, _CURRENT, _MEAS),
    _nested("dc_power_string2", "Công suất PV chuỗi 2", "Pdc", 1, _KW, _POWER, _MEAS),

    # ---------- Lưới điện ----------
    _num("grid_voltage", "Điện áp lưới", "gridVac", _V, _VOLTAGE, _MEAS),
    _num("grid_current", "Dòng điện lưới", "gridIac", _A, _CURRENT, _MEAS, **_OFF),
    _num("grid_frequency", "Tần số lưới", "gridFac", _HZ, _FREQ, _MEAS),
    _num("grid_power", "Công suất lưới", "gridCurrpac", _W, _POWER, _MEAS),
    _num("e_to_grid_today", "Điện bán lưới hôm nay", "ETDay", _KWH, _ENERGY, _TOTAL),
    _num("e_from_grid_today", "Điện mua lưới hôm nay", "EFDay", _KWH, _ENERGY, _TOTAL),
    _num("e_to_grid_total", "Tổng điện bán lưới", "ETTotal", _KWH, _ENERGY, _TOTAL),
    _num("e_from_grid_total", "Tổng điện mua lưới", "EFTotal", _KWH, _ENERGY, _TOTAL),

    # ---------- Tải tiêu thụ ----------
    _num("load_voltage", "Điện áp tải", "loadVac", _V, _VOLTAGE, _MEAS, **_OFF),
    _num("load_current", "Dòng điện tải", "loadIac", _A, _CURRENT, _MEAS, **_OFF),
    _num("load_frequency", "Tần số tải", "loadFac", _HZ, _FREQ, _MEAS, **_OFF),
    _num("load_power", "Công suất tải", "loadCurrpac", _W, _POWER, _MEAS),
    _num("e_load_today", "Tiêu thụ tải hôm nay", "ELDay", _KWH, _ENERGY, _TOTAL),
    _num("e_load_total", "Tổng tiêu thụ tải", "ELTotal", _KWH, _ENERGY, _TOTAL),

    # ---------- Pin ----------
    _num("battery_soc", "Dung lượng pin (SOC)", "SOC", PERCENTAGE,
         SensorDeviceClass.BATTERY, _MEAS),
    _num("battery_soh", "Tình trạng sức khoẻ pin (SOH)", "SOH", PERCENTAGE, None, _MEAS,
         entity_category=_DIAG, icon="mdi:battery-heart-variant"),
    _num("battery_voltage", "Điện áp pin", "volt", _V, _VOLTAGE, _MEAS),
    _num("battery_current", "Dòng điện pin", "cur", _A, _CURRENT, _MEAS),
    _num("battery_temp", "Nhiệt độ pin", "BMS_temp", _C, _TEMP, _MEAS),
    # Công suất tức thời: toPbat = đang sạc vào pin, fromPbat = đang xả ra (W)
    _num("battery_charge_power", "Công suất sạc pin", "toPbat", _W, _POWER, _MEAS),
    _num("battery_discharge_power", "Công suất xả pin", "fromPbat", _W, _POWER, _MEAS),
    # Điện năng trong ngày: batChrg / batDischrg (kWh, reset mỗi ngày)
    _num("battery_e_charge_today", "Điện sạc vào pin hôm nay", "batChrg", _KWH,
         _ENERGY, _TOTAL),
    _num("battery_e_discharge_today", "Điện xả từ pin hôm nay", "batDischrg", _KWH,
         _ENERGY, _TOTAL),
    _num("battery_e_charge_total", "Tổng điện sạc vào pin", "Etotal_batChrg", _KWH,
         _ENERGY, _TOTAL),
    _num("battery_e_discharge_total", "Tổng điện xả từ pin", "Etotal_batDischrg", _KWH,
         _ENERGY, _TOTAL),
    _num("battery_capacity", "Dung lượng pin cấu hình", "capacity", "Ah", None, None,
         entity_category=_DIAG, **_OFF),
    _text("battery_status", "Trạng thái BMS", lambda d: d.get("BMS_Status"),
          entity_category=_DIAG, icon="mdi:battery-sync"),
    _text("battery_brand", "Hãng pin", lambda d: d.get("brand"),
          entity_category=_DIAG, **_OFF),
    _text("battery_num", "Số lượng pin", lambda d: d.get("Batterynum"),
          entity_category=_DIAG, **_OFF),

    # ---------- EPS (nguồn dự phòng) ----------
    _num("eps_voltage", "Điện áp EPS", "epsVac", _V, _VOLTAGE, _MEAS, **_OFF),
    _num("eps_current", "Dòng điện EPS", "epsIac", _A, _CURRENT, _MEAS, **_OFF),
    _num("eps_frequency", "Tần số EPS", "epsFac", _HZ, _FREQ, _MEAS, **_OFF),
    _num("eps_power", "Công suất EPS", "epsCurrpac", _W, _POWER, _MEAS),
    _num("eps_e_today", "Điện EPS hôm nay", "EPSDay", _KWH, _ENERGY, _TOTAL, **_OFF),
    _num("eps_e_total", "Tổng điện EPS", "EPSTotal", _KWH, _ENERGY, _TOTAL, **_OFF),

    # ---------- Máy phát điện ----------
    _num("gen_voltage", "Điện áp máy phát", "genVac", _V, _VOLTAGE, _MEAS, **_OFF),
    _num("gen_power", "Công suất máy phát", "genCurrpac", _W, _POWER, _MEAS, **_OFF),
    _num("gen_e_today", "Điện máy phát hôm nay", "GENDay", _KWH, _ENERGY, _TOTAL, **_OFF),
    _num("gen_e_total", "Tổng điện máy phát", "GENTotal", _KWH, _ENERGY, _TOTAL, **_OFF),

    # ---------- Couple (song song, nếu có) ----------
    _num("couple_power", "Công suất couple", "coupleCurrpac", _W, _POWER, _MEAS, **_OFF),

    # ---------- Trạng thái / chẩn đoán ----------
    _text("operating_status", "Trạng thái hoạt động", lambda d: d.get("Operatingstatus"),
          icon="mdi:state-machine", entity_category=_DIAG),
    _text("operating_mode", "Chế độ hoạt động", lambda d: d.get("Operatingmode"),
          icon="mdi:cog", entity_category=_DIAG),
    _text("drm_status", "Trạng thái DRM", lambda d: d.get("DRMstatus"),
          entity_category=_DIAG, **_OFF),
    _text("dry_contact_status", "Trạng thái Dry Contact",
          lambda d: d.get("DryContactStatus"), entity_category=_DIAG, **_OFF),
    _text("connect_type", "Kiểu kết nối", lambda d: d.get("connectType"),
          entity_category=_DIAG, **_OFF),
    _num("wifi_strength", "Cường độ Wifi", "WifiStrength", PERCENTAGE, None, None,
         entity_category=_DIAG, icon="mdi:wifi"),
    _text("firmware_version", "Phiên bản firmware", lambda d: d.get("FirmwareVersion"),
          entity_category=_DIAG),
    _text("csb_version", "Phiên bản CSB", lambda d: d.get("CSBVersion"),
          entity_category=_DIAG, **_OFF),
    _text("modbus_version", "Phiên bản Modbus", lambda d: d.get("ModbusVersion"),
          entity_category=_DIAG, **_OFF),
    _text("esp32_version", "Phiên bản ESP32 Wifi",
          lambda d: _get(d, "ESP32Version", "Version"), entity_category=_DIAG, **_OFF),
    _text("esp32_sn", "Serial ESP32 Wifi", lambda d: _get(d, "ESP32Version", "SN"),
          entity_category=_DIAG, **_OFF),
    _text("esp32_status", "Trạng thái module Wifi",
          lambda d: _get(d, "ESP32Version", "Status"), entity_category=_DIAG,
          icon="mdi:wifi-check"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Thiết lập sensor entities từ config entry."""
    coordinator: SenergyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    goods_id = entry.data[CONF_GOODS_ID]

    async_add_entities(
        SenergyInverterSensor(coordinator, description, goods_id, entry.title)
        for description in SENSOR_TYPES
    )


class SenergyInverterSensor(CoordinatorEntity[SenergyDataUpdateCoordinator], SensorEntity):
    """1 sensor đọc từ dữ liệu InverterDetailInfoNewone."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SenergyDataUpdateCoordinator,
        description: SenergySensorDescription,
        goods_id: str,
        device_name: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._goods_id = goods_id
        self._attr_unique_id = f"{goods_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, goods_id)},
            name=device_name,
            manufacturer="Senergy",
            model=(coordinator.data or {}).get("modelName", "Inverter"),
            sw_version=(coordinator.data or {}).get("FirmwareVersion"),
        )

    @property
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
