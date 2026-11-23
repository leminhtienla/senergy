# Changelog

## 0.2.1
- Sửa sai công suất sạc/xả pin: `batChrg` / `batDischrg` là điện năng
  sạc/xả HÔM NAY (kWh), không phải công suất (W). Trước đây hai sensor
  "Công suất sạc/xả pin" hiển thị nhầm giá trị kWh với đơn vị W.
- "Công suất sạc pin" nay lấy từ `toPbat` (W), "Công suất xả pin" lấy từ
  `fromPbat` (W). Hai sensor `battery_power_from/to` trùng lặp đã bỏ.
- Thêm "Điện sạc vào pin hôm nay" và "Điện xả từ pin hôm nay" (kWh).
- Rút gọn `sensor.py` bằng hàm dựng sensor, giữ nguyên key/unique_id.

## 0.2.0
- Mở rộng từ 22 lên 69 sensor, map gần như toàn bộ field trả về từ
  `InverterDetailInfoNewone`: AC/DC theo từng string MPPT, EPS, máy
  phát điện, couple, pin (SOC/SOH/áp/dòng/nhiệt độ/sạc-xả), các phiên
  bản firmware/ESP32/CSB/Modbus, trạng thái BMS/DRM/Dry Contact...
- ~29 sensor ít dùng được set `entity_registry_enabled_default=False`
  (tắt sẵn), bật lại qua UI nếu cần.
- Thêm `sw_version` (firmware) vào Device Info.

## 0.1.0
- Phiên bản đầu tiên: config flow (MemberID/Password/login_sign/
  GoodsID/data_sign), tự đăng nhập lại khi token hết hạn, coordinator
  poll 60s, 22 sensor cơ bản (công suất, sản lượng, lưới, tải, pin,
  EPS, tỷ lệ tự dùng, wifi, trạng thái).
