import os, json
from flask import Flask, request, jsonify, render_template
import requests

app = Flask(__name__)

# ====== ENV (set in Render) ======
GAS_WEBAPP_URL = os.environ.get("GAS_WEBAPP_URL", "").strip()  # e.g. https://script.google.com/macros/s/.../exec
LIFF_ID = os.environ.get("LIFF_ID", "").strip()
SHOP_NAME = os.environ.get("SHOP_NAME", "H.R燈藝").strip()
GEOFENCE_METERS = int(os.environ.get("GEOFENCE_METERS", "50"))

if not GAS_WEBAPP_URL:
    print("WARN: GAS_WEBAPP_URL is not set.")
if not LIFF_ID:
    print("WARN: LIFF_ID is not set.")

def _render_index():
    return render_template(
        "index.html",
        LIFF_ID=LIFF_ID,
        SHOP_NAME=SHOP_NAME,
        GEOFENCE_METERS=GEOFENCE_METERS,
    )

@app.get("/")
def home():
    return _render_index()

# ✅ 防呆：任何路徑（含 /favicon.ico、/index.html、LINE 帶的奇怪路徑）都回到打卡頁，避免 NOT FOUND
@app.get("/<path:any_path>")
def catch_all(any_path):
    return _render_index()

@app.post("/api/clock")
def api_clock():
    """Proxy endpoint to avoid CORS: Frontend -> Render -> GAS (server-to-server)."""
    if not GAS_WEBAPP_URL:
        return jsonify({"ok": False, "code": "NO_GAS_URL", "message": "系統尚未設定 GAS_WEBAPP_URL"}), 500

    data = request.get_json(silent=True) or {}
    action = str(data.get("action", "")).upper()
    user_id = str(data.get("userId", "")).strip()
    lat = data.get("lat")
    lng = data.get("lng")

    if action not in ("IN", "OUT"):
        return jsonify({"ok": False, "code": "BAD_ACTION", "message": "無效的打卡類型"}), 400
    if not user_id:
        return jsonify({"ok": False, "code": "NO_USER", "message": "缺少使用者資訊，請重新開啟打卡頁"}), 400
    if lat is None or lng is None:
        return jsonify({"ok": False, "code": "NO_GPS", "message": "無法取得定位，請允許定位權限後再試一次"}), 400

    payload = {
        "action": action,
        "userId": user_id,
        "lat": lat,
        "lng": lng,
        "device": data.get("device", ""),
        "note": data.get("note", "")
    }

    try:
        r = requests.post(
            GAS_WEBAPP_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        try:
            out = r.json()
        except Exception:
            out = {"ok": False, "code": "BAD_GAS_RESPONSE", "message": "GAS 回應格式錯誤", "raw": r.text[:500]}
        return jsonify(out), 200 if r.status_code < 400 else 500
    except requests.RequestException as e:
        return jsonify({"ok": False, "code": "GAS_UNREACHABLE", "message": "無法連線到 GAS，請稍後再試", "detail": str(e)}), 502

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
