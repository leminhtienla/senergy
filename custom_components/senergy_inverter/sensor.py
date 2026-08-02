"""Sensor entities cho Senergy Cloud Inverter.

Danh sách sensor được map gần như đầy đủ từ toàn bộ field trả về của
endpoint InverterDetailInfoNewone. Sensor nào không cần, bạn có thể vô
hiệu hoá trực tiếp trong HA: Settings > Devices & Services > thiết bị
Senergy > chọn entity > bánh răng > "Enabled" tắt đi, không cần sửa code.
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


SENSOR_TYPES: tuple[SenergySensorDescription, ...] = (
    # ---------- Tổng quan AC / sản lượng ----------
    SenergySensorDescription(
        key="pac",
        name="Công suất AC",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _to_float(_get(d, "data", "Pac")),
    ),
    SenergySensorDescription(
        key="ac_voltage",
        name="Điện áp AC đầu ra",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _to_float(_get(d, "data", "Vac")),
    ),
    SenergySensorDescription(
        key="ac_current",
        name="Dòng điện AC đầu ra",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _to_float(_get(d, "data", "Iac")),
    ),
    SenergySensorDescription(
        key="ac_frequency",
        name="Tần số AC đầu ra",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _to_float(_get(d, "data", "Fac")),
    ),
    SenergySensorDescription(
        key="e_today",
        name="Sản lượng hôm nay",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: _to_float(d.get("EToday")),
    ),
    SenergySensorDescription(
        key="e_total",
        name="Tổng sản lượng",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: _to_float(d.get("ETotal")),
    ),
    SenergySensorDescription(
        key="peak_power",
        name="Công suất đỉnh",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: _to_float(d.get("Peackpower")),
    ),
    SenergySensorDescription(
        key="total_dc_power",
        name="Tổng công suất DC (PV)",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _to_float(d.get("TotalDCpower")),
    ),
    SenergySensorDescription(
        key="temperature",
        name="Nhiệt độ biến tần",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _to_float(d.get("Tntc")),
    ),
    SenergySensorDescription(
        key="self_use_rate",
        name="Tỷ lệ tự dùng",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:home-lightning-bolt",
        value_fn=lambda d: _to_float(d.get("Dailyself_userate")),
    ),
    SenergySensorDescription(
        key="self_sufficiency_rate",
        name="Tỷ lệ tự cung tự cấp",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power",
        value_fn=lambda d: _to_float(d.get("Dailyself_sufficiencyrate")),
    ),

    # ---------- DC / chuỗi PV (MPPT string 1 & 2) ----------
    SenergySensorDescription(
        key="dc_voltage_string1",
        name="Điện áp PV chuỗi 1",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _to_float(_get(d, "data", "Vdc"), 0),
    ),
    SenergySensorDescription(
        key="dc_current_string1",
        name="Dòng điện PV chuỗi 1",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _to_float(_get(d, "data", "Idc"), 0),
    ),
    SenergySensorDescription(
        key="dc_power_string1",
        name="Công suất PV chuỗi 1",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _to_float(_get(d, "data", "Pdc"), 0),
    ),
    SenergySensorDescription(
        key="dc_voltage_string2",
        name="Điện áp PV chuỗi 2",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _to_float(_get(d, "data", "Vdc"), 1),
    ),
    SenergySensorDescription(
        key="dc_current_string2",
        name="Dòng điện PV chuỗi 2",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _to_float(_get(d, "data", "Idc"), 1),
    ),
    SenergySensorDescription(
        key="dc_power_string2",
        name="Công suất PV chuỗi 2",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _to_float(_get(d, "data", "Pdc"), 1),
    ),

    # ---------- Lưới điện ----------
    SenergySensorDescription(
        key="grid_voltage",
        name="Điện áp lưới",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _to_float(d.get("gridVac")),
    ),
    SenergySensorDescription(
        key="grid_current",
        name="Dòng điện lưới",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _to_float(d.get("gridIac")),
    ),
    SenergySensorDescription(
        key="grid_frequency",
        name="Tần số lưới",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _to_float(d.get("gridFac")),
    ),
    SenergySensorDescription(
        key="grid_power",
        name="Công suất lưới",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _to_float(d.get("gridCurrpac")),
    ),
    SenergySensorDescription(
        key="e_to_grid_today",
        name="Điện bán lưới hôm nay",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: _to_float(d.get("ETDay")),
    ),
    SenergySensorDescription(
        key="e_from_grid_today",
        name="Điện mua lưới hôm nay",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: _to_float(d.get("EFDay")),
    ),
    SenergySensorDescription(
        key="e_to_grid_total",
        name="Tổng điện bán lưới",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: _to_float(d.get("ETTotal")),
    ),
    SenergySensorDescription(
        key="e_from_grid_total",
        name="Tổng điện mua lưới",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: _to_float(d.get("EFTotal")),
    ),

    # ---------- Tải tiêu thụ ----------
    SenergySensorDescription(
        key="load_voltage",
        name="Điện áp tải",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _to_float(d.get("loadVac")),
    ),
    SenergySensorDescription(
        key="load_current",
        name="Dòng điện tải",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _to_float(d.get("loadIac")),
    ),
    SenergySensorDescription(
        key="load_frequency",
        name="Tần số tải",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _to_float(d.get("loadFac")),
    ),
    SenergySensorDescription(
        key="load_power",
        name="Công suất tải",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _to_float(d.get("loadCurrpac")),
    ),
    SenergySensorDescription(
        key="e_load_today",
        name="Tiêu thụ tải hôm nay",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: _to_float(d.get("ELDay")),
    ),
    SenergySensorDescription(
        key="e_load_total",
        name="Tổng tiêu thụ tải",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: _to_float(d.get("ELTotal")),
    ),

    # ---------- Pin (battery bank 1) ----------
    SenergySensorDescription(
        key="battery_soc",
        name="Dung lượng pin (SOC)",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _to_float(d.get("SOC")),
    ),
    SenergySensorDescription(
        key="battery_soh",
        name="Tình trạng sức khoẻ pin (SOH)",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:battery-heart-variant",
        value_fn=lambda d: _to_float(d.get("SOH")),
    ),
    SenergySensorDescription(
        key="battery_voltage",
        name="Điện áp pin",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _to_float(d.get("volt")),
    ),
    SenergySensorDescription(
        key="battery_current",
        name="Dòng điện pin",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _to_float(d.get("cur")),
    ),
    SenergySensorDescription(
        key="battery_temp",
        name="Nhiệt độ pin",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _to_float(d.get("BMS_temp")),
    ),
    SenergySensorDescription(
        key="battery_charge_power",
        name="Công suất sạc pin",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _to_float(d.get("batChrg")),
    ),
    SenergySensorDescription(
        key="battery_discharge_power",
        name="Công suất xả pin",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _to_float(d.get("batDischrg")),
    ),
    SenergySensorDescription(
        key="battery_power_from",
        name="Công suất từ pin (fromPbat)",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _to_float(d.get("fromPbat")),
    ),
    SenergySensorDescription(
        key="battery_power_to",
        name="Công suất vào pin (toPbat)",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _to_float(d.get("toPbat")),
    ),
    SenergySensorDescription(
        key="battery_e_charge_total",
        name="Tổng điện sạc vào pin",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: _to_float(d.get("Etotal_batChrg")),
    ),
    SenergySensorDescription(
        key="battery_e_discharge_total",
        name="Tổng điện xả từ pin",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: _to_float(d.get("Etotal_batDischrg")),
    ),
    SenergySensorDescription(
        key="battery_capacity",
        name="Dung lượng pin cấu hình",
        native_unit_of_measurement="Ah",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _to_float(d.get("capacity")),
    ),
    SenergySensorDescription(
        key="battery_status",
        name="Trạng thái BMS",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:battery-sync",
        value_fn=lambda d: d.get("BMS_Status"),
    ),
    SenergySensorDescription(
        key="battery_brand",
        name="Hãng pin",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("brand"),
    ),
    SenergySensorDescription(
        key="battery_num",
        name="Số lượng pin",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("Batterynum"),
    ),

    # ---------- EPS (nguồn dự phòng) ----------
    SenergySensorDescription(
        key="eps_voltage",
        name="Điện áp EPS",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _to_float(d.get("epsVac")),
    ),
    SenergySensorDescription(
        key="eps_current",
        name="Dòng điện EPS",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _to_float(d.get("epsIac")),
    ),
    SenergySensorDescription(
        key="eps_frequency",
        name="Tần số EPS",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _to_float(d.get("epsFac")),
    ),
    SenergySensorDescription(
        key="eps_power",
        name="Công suất EPS",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _to_float(d.get("epsCurrpac")),
    ),
    SenergySensorDescription(
        key="eps_e_today",
        name="Điện EPS hôm nay",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _to_float(d.get("EPSDay")),
    ),
    SenergySensorDescription(
        key="eps_e_total",
        name="Tổng điện EPS",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _to_float(d.get("EPSTotal")),
    ),

    # ---------- Máy phát điện (Generator) ----------
    SenergySensorDescription(
        key="gen_voltage",
        name="Điện áp máy phát",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _to_float(d.get("genVac")),
    ),
    SenergySensorDescription(
        key="gen_power",
        name="Công suất máy phát",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _to_float(d.get("genCurrpac")),
    ),
    SenergySensorDescription(
        key="gen_e_today",
        name="Điện máy phát hôm nay",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _to_float(d.get("GENDay")),
    ),
    SenergySensorDescription(
        key="gen_e_total",
        name="Tổng điện máy phát",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _to_float(d.get("GENTotal")),
    ),

    # ---------- Couple (liên kết song song, nếu có) ----------
    SenergySensorDescription(
        key="couple_power",
        name="Công suất couple",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _to_float(d.get("coupleCurrpac")),
    ),

    # ---------- Trạng thái / chẩn đoán ----------
    SenergySensorDescription(
        key="operating_status",
        name="Trạng thái hoạt động",
        icon="mdi:state-machine",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("Operatingstatus"),
    ),
    SenergySensorDescription(
        key="operating_mode",
        name="Chế độ hoạt động",
        icon="mdi:cog",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("Operatingmode"),
    ),
    SenergySensorDescription(
        key="drm_status",
        name="Trạng thái DRM",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("DRMstatus"),
    ),
    SenergySensorDescription(
        key="dry_contact_status",
        name="Trạng thái Dry Contact",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("DryContactStatus"),
    ),
    SenergySensorDescription(
        key="connect_type",
        name="Kiểu kết nối",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("connectType"),
    ),
    SenergySensorDescription(
        key="wifi_strength",
        name="Cường độ Wifi",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:wifi",
        value_fn=lambda d: _to_float(d.get("WifiStrength")),
    ),
    SenergySensorDescription(
        key="firmware_version",
        name="Phiên bản firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("FirmwareVersion"),
    ),
    SenergySensorDescription(
        key="csb_version",
        name="Phiên bản CSB",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("CSBVersion"),
    ),
    SenergySensorDescription(
        key="modbus_version",
        name="Phiên bản Modbus",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("ModbusVersion"),
    ),
    SenergySensorDescription(
        key="esp32_version",
        name="Phiên bản ESP32 Wifi",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _get(d, "ESP32Version", "Version"),
    ),
    SenergySensorDescription(
        key="esp32_sn",
        name="Serial ESP32 Wifi",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _get(d, "ESP32Version", "SN"),
    ),
    SenergySensorDescription(
        key="esp32_status",
        name="Trạng thái module Wifi",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:wifi-check",
        value_fn=lambda d: _get(d, "ESP32Version", "Status"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Thiết lập sensor entities từ config entry."""
    coordinator: SenergyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    goods_id = entry.data[CONF_GOODS_ID]

    entities = [
        SenergyInverterSensor(coordinator, description, goods_id, entry.title)
        for description in SENSOR_TYPES
    ]
    async_add_entities(entities)


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
