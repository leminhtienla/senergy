"""Hằng số cho Senergy Cloud Inverter integration."""

DOMAIN = "senergy_inverter"

BASE_URL = (
    "https://www.cloudinverter.net/dist/server/api/CodeIgniter/"
    "index.php/Senergytec/web/v2/Inverterapi"
)

CONF_MEMBER_ID = "member_id"
CONF_PASSWORD = "password"
CONF_LOGIN_SIGN = "login_sign"
CONF_GOODS_ID = "goods_id"
CONF_DATA_SIGN = "data_sign"
CONF_DEVICE_NAME = "device_name"

DEFAULT_SCAN_INTERVAL = 60  # giây
