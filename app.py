from flask import Flask, render_template, request, jsonify, send_from_directory
import os

app = Flask(__name__)

UPLOAD_FOLDER = "videos"
LOGO_FOLDER = "logo"
HLS_FOLDER = "hls"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(LOGO_FOLDER, exist_ok=True)
os.makedirs(HLS_FOLDER, exist_ok=True)

from ffmpeg_manager import stream_manager

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    files = request.files.getlist('videos')
    uploaded = []
    for file in files:
        if file.filename != "":
            path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(path)
            uploaded.append(file.filename)
    return jsonify({"status": "success", "files": uploaded})

@app.route('/upload_logo', methods=['POST'])
def upload_logo():
    file = request.files['logo']
    path = os.path.join(LOGO_FOLDER, file.filename)
    file.save(path)
    return jsonify({"status": "success", "logo": file.filename})

@app.route('/logo/<path:filename>')
def logo(filename):
    return send_from_directory(LOGO_FOLDER, filename)

@app.route('/hls/<path:filename>')
def hls(filename):
    response = send_from_directory("hls", filename)
    if filename.endswith('.m3u8'):
        response.headers['Content-Type'] = 'application/vnd.apple.mpegurl'
    elif filename.endswith('.ts'):
        response.headers['Content-Type'] = 'video/MP2T'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

# API MỚI: TỰ ĐỘNG LẤY DANH SÁCH FILE TỪ Ổ CỨNG TRẢ VỀ CHO WEB
@app.route('/api/get_files')
def get_files():
    try:
        videos = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(('.mp4', '.mkv', '.avi', '.ts'))]
    except: videos = []
    try:
        logos = [f for f in os.listdir(LOGO_FOLDER) if f.endswith(('.png', '.jpg', '.jpeg'))]
    except: logos = []
    return jsonify({"videos": videos, "logos": logos})

@app.route('/start_multicast', methods=['POST'])
def start_multicast():
    data = request.json
    target = f"{data['ip']}:{data['port']}"
    stream_manager.start_playlist(data['videos'], "multicast", target, data['bitrate'], data['overlay'], data['logo'], data['logo_position'], data['ticker'])
    return jsonify({"status": "running", "url": f"udp://@{target}"})

@app.route('/start_hls', methods=['POST'])
def start_hls():
    data = request.json
    stream_manager.start_playlist(data['videos'], "hls", "hls", data['bitrate'], data['overlay'], data['logo'], data['logo_position'], data['ticker'])
    return jsonify({"status": "running"})

@app.route('/start_rtsp_stream', methods=['POST'])
def start_rtsp_stream():
    data = request.json
    target = "rtsp://0.0.0.0:8554/live"
    stream_manager.start_playlist(data['videos'], "rtsp", target, data['bitrate'], data['overlay'], data['logo'], data['logo_position'], data['ticker'])
    return jsonify({"status": "running", "url": "rtsp://SERVER_IP:8554/live"})

@app.route('/start_rtsp_camera', methods=['POST'])
def start_rtsp_camera():
    data = request.json
    stream_manager.start_rtsp_camera(data['url'])
    return jsonify({"status": "running"})

# === TÍNH NĂNG MỚI: NETWORK RELAY ===
@app.route('/start_network_relay', methods=['POST'])
def start_network_relay():
    data = request.json
    url = data['url']
    mode = data.get('mode', 'hls')
    
    target = "hls"
    if mode == "multicast":
        target = f"{data['ip']}:{data['port']}"
    elif mode == "rtsp":
        target = "rtsp://0.0.0.0:8554/live"

    stream_manager.start_network_relay(
        url=url,
        mode=mode,
        target=target,
        bitrate=data.get('bitrate', '4000k'),
        overlay=data.get('overlay', False),
        logo=data.get('logo', ''),
        logo_position=data.get('logo_position', 'top-left'),
        ticker=data.get('ticker', '')
    )
    return jsonify({"status": "running"})
# =====================================

@app.route('/stop', methods=['POST'])
def stop():
    stream_manager.stop()
    return jsonify({"status": "stopped"})

@app.route('/stats')
def stats():
    return jsonify(stream_manager.get_system_stats())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)