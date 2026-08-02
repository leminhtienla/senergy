# Senergy Cloud Inverter – Custom Component cho Home Assistant

Integration này đọc dữ liệu realtime từ biến tần Senergy thông qua cổng
`cloudinverter.net` (Senergytec) và hiển thị dưới dạng sensor trong Home
Assistant: công suất AC, sản lượng hôm nay/tổng, điện áp/tần số lưới,
công suất tải, pin (SOC, sạc/xả), EPS, nhiệt độ, tỷ lệ tự dùng...

## Vì sao cần "sign"?

Cổng cloudinverter.net bắt buộc mỗi request phải kèm tham số `sign`
được mã hoá phía JavaScript của web app bằng key không public. Không
có cách nào server/HA tự sinh được `sign` này.

Tin vui: qua phân tích, `sign` **không đổi theo thời gian**, chỉ phụ
thuộc vào giá trị tham số gửi đi. Nghĩa là:

- `sign` của đăng nhập (`UserLogin_v1`) chỉ phụ thuộc `MemberID` + `Password` → bắt 1 lần, dùng mãi (trừ khi bạn đổi mật khẩu).
- `sign` của lấy dữ liệu (`InverterDetailInfoNewone`) chỉ phụ thuộc `GoodsID` + `MemberAutoID` của bạn → bắt 1 lần, dùng mãi.

=> Bạn chỉ cần bắt gói tin **1 lần duy nhất**, sau đó HA tự động đăng
nhập lại lấy token mới mỗi khi token cũ hết hạn (dùng lại `login_sign`
đã lưu), không cần tương tác gì thêm.

## Cách lấy `login_sign` và `data_sign`

1. Mở https://www.cloudinverter.net trên Chrome/Edge, bấm **F12** để mở
   DevTools, chuyển sang tab **Network**, gõ `Inverterapi` vào ô lọc.
2. Đăng nhập vào tài khoản của bạn như bình thường.
3. Trong danh sách request, click vào `UserLogin_v1` → tab **Payload**
   (hoặc **Request**), copy giá trị của trường `"sign"` → đây là
   **login_sign**.
4. Vào trang chi tiết 1 biến tần bất kỳ (để nó tự gọi API lấy dữ liệu).
   Click vào request `InverterDetailInfoNewone` → copy giá trị `"sign"`
   → đây là **data_sign**. Đồng thời ghi lại `GoodsID` trong payload đó
   (vd: `2616-85081020PH`) — chính là mã biến tần cần cấu hình.

> Nếu bạn có nhiều biến tần, mỗi biến tần có `GoodsID` khác nhau nên
> `data_sign` cũng khác nhau — lặp lại bước 4 cho từng biến tần, và
> thêm integration này nhiều lần (mỗi lần 1 biến tần).

## Cài đặt qua HACS

1. HACS → Integrations → menu 3 chấm → **Custom repositories** → thêm
   URL repo này, loại **Integration**.
2. Tìm "Senergy Cloud Inverter" → Install → khởi động lại HA.
3. Settings → Devices & Services → **Add integration** → tìm "Senergy
   Cloud Inverter" → điền: MemberID, Password, login_sign, GoodsID,
   data_sign, tên thiết bị.

## Giới hạn hiện tại

- Nếu Senergytec thay đổi thuật toán ký (`sign`) hoặc bạn đổi mật khẩu,
  bạn cần bắt lại `login_sign`/`data_sign` theo hướng dẫn trên và sửa
  lại trong **Settings → Devices & Services → Senergy → Configure**
  (có thể cần thêm bước reconfigure vào config_flow nếu muốn sửa qua UI;
  hiện tại đơn giản nhất là xoá và thêm lại integration).
- Chu kỳ polling mặc định 60 giây, chỉnh trong `const.py`
  (`DEFAULT_SCAN_INTERVAL`).
