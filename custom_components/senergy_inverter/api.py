"""Client gọi API cloudinverter.net (Senergytec) cho biến tần Senergy.

Ghi chú quan trọng về tham số "sign":
Cổng cloudinverter.net yêu cầu mỗi request POST phải có trường "sign"
được ký/mã hoá phía client bằng JS (SM4/AES) với key nhúng trong bundle
chính của web app. Từ file HAR chụp lại, không có bundle chứa key đó
nên KHÔNG thể tự sinh "sign" từ server/HA.

Tuy nhiên, quan sát thực tế: "sign" chỉ phụ thuộc vào GIÁ TRỊ tham số
gửi đi (không phụ thuộc thời gian, không phụ thuộc endpoint). Nghĩa là
với cùng {MemberID, Password, remember, type} thì "sign" của
UserLogin_v1 luôn giống nhau; với cùng {GoodsID, MemberAutoID} thì
"sign" của InverterDetailInfoNewone / getHybridFlowgraph cũng luôn
giống nhau.

=> Người dùng chỉ cần bắt gói tin 1 LẦN bằng DevTools (F12 > Network,
lọc "Inverterapi") để lấy 2 giá trị:
  - login_sign: sign trong request UserLogin_v1
  - data_sign : sign trong request InverterDetailInfoNewone (hoặc
                getHybridFlowgraph, giá trị giống nhau)
rồi nhập vào config flow. Tích hợp sẽ dùng lại các giá trị này mãi mãi,
kể cả khi cần đăng nhập lại lấy token mới (chỉ password đổi thì mới
phải bắt lại sign).
"""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import BASE_URL

_LOGGER = logging.getLogger(__name__)


class SenergyApiError(Exception):
    """Lỗi chung khi gọi API."""


class SenergyAuthError(SenergyApiError):
    """Lỗi đăng nhập / token hết hạn và không đăng nhập lại được."""


class SenergyCloudApi:
    """Wrapper gọi các endpoint cần thiết của cloudinverter.net."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        member_id: str,
        password: str,
        login_sign: str,
        token: str | None = None,
        member_auto_id: str | None = None,
    ) -> None:
        self._session = session
        self._member_id = member_id
        self._password = password
        self._login_sign = login_sign
        self.token: str | None = token
        self.member_auto_id: str | None = member_auto_id

    async def _post(
        self, endpoint: str, payload: dict[str, Any], auth: bool = True
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if auth:
            if not self.token:
                await self.async_login()
            headers["Authorization"] = self.token or ""

        url = f"{BASE_URL}/{endpoint}"
        async with self._session.post(url, json=payload, headers=headers) as resp:
            if resp.status == 401 and auth:
                # token hết hạn -> đăng nhập lại 1 lần rồi thử lại
                await self.async_login()
                headers["Authorization"] = self.token or ""
                async with self._session.post(
                    url, json=payload, headers=headers
                ) as resp2:
                    resp2.raise_for_status()
                    return await resp2.json(content_type=None)
            resp.raise_for_status()
            return await resp.json(content_type=None)

    async def async_login(self) -> None:
        """Đăng nhập bằng login_sign đã bắt sẵn để lấy JWT token mới."""
        payload = {
            "sign": self._login_sign,
            "MemberID": self._member_id,
            "Password": self._password,
            "remember": True,
            "type": "1",
        }
        url = f"{BASE_URL}/UserLogin_v1"
        async with self._session.post(
            url, json=payload, headers={"Content-Type": "application/json"}
        ) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)

        if data.get("status") != "ok" or not data.get("token"):
            raise SenergyAuthError(
                f"Đăng nhập thất bại, kiểm tra lại login_sign/MemberID/Password: {data}"
            )

        self.token = data["token"]
        self.member_auto_id = data.get("MemberAutoID")
        _LOGGER.debug("Senergy: đăng nhập thành công, MemberAutoID=%s", self.member_auto_id)

    async def async_get_group_list(self) -> dict[str, Any]:
        """Lấy danh sách trạm/nhà máy (cần data_sign ứng với tham số này riêng)."""
        return await self._post(
            "GroupList",
            {"MemberAutoID": self.member_auto_id, "inputValue": ""},
        )

    async def async_get_inverter_detail(
        self, goods_id: str, data_sign: str
    ) -> dict[str, Any]:
        """Lấy dữ liệu chi tiết realtime của 1 biến tường (endpoint chính)."""
        payload = {
            "sign": data_sign,
            "GoodsID": goods_id,
            "MemberAutoID": self.member_auto_id,
        }
        return await self._post("InverterDetailInfoNewone", payload)
