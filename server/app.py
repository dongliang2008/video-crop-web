# -*- coding: utf-8 -*-
"""视频裁剪 Web 平台 · Flask 入口（localhost:8100，纯本地离线）。
路由：项目/时间段/水印/任务/确认图/AI命名/播放/截帧。
"""
import os
import re
import time
from pathlib import Path
from urllib.parse import unquote

from flask import Flask, jsonify, request, send_from_directory, Response

from . import db, media, tasks as task_mgr, ai_naming
from .config import CFG

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / 'web'
app = Flask(__name__, static_folder=None)
db.init_db()

HOST = CFG['server']['host']
PORT = CFG['server']['port']


# ---------------- 页面与服务 ----------------

@app.route('/')
def index():
    resp = send_from_directory(str(WEB), 'index.html')
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@app.route('/<path:name>')
def web_files(name):
    # 只服务 web 目录内的静态资源（css/js），防路径穿越
    target = (WEB / name).resolve()
    if not str(target).startswith(str(WEB.resolve())):
        return jsonify({'error': 'forbidden'}), 403
    if target.is_file():
        resp = send_from_directory(str(WEB), name)
        resp.headers['Cache-Control'] = 'no-store'
        return resp
    return jsonify({'error': 'not found'}), 404


@app.route('/api/config')
def api_config():
    return jsonify({
        'naming': CFG['naming'],
        'processing': CFG['processing'],
        'default_output_dir': CFG.get('default_output_dir', ''),
    })


# ---------------- 播放 / 探测 / 截帧 ----------------

@app.route('/api/file')
def api_file():
    """本地图片文件服务（确认预览图/帧图）：仅允许常见图片扩展名。"""
    path = unquote(request.args.get('path', ''))
    if not os.path.isfile(path):
        return jsonify({'error': '文件不存在'}), 400
    ext = Path(path).suffix.lower()
    if ext not in ('.png', '.jpg', '.jpeg', '.webp', '.gif'):
        return jsonify({'error': '仅支持图片文件'}), 400
    mime = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.webp': 'image/webp', '.gif': 'image/gif'}.get(ext, 'application/octet-stream')
    return Response(open(path, 'rb').read(), 200, mimetype=mime)


@app.route('/api/videos')
def api_videos():
    """列出目录下全部视频文件（递归，含子目录）。返回 名称/相对路径/大小。"""
    d = unquote(request.args.get('dir', ''))
    if not os.path.isdir(d):
        return jsonify({'error': '目录不存在'}), 400
    exts = set(CFG.get('video_exts', ['.mp4', '.webm', '.mov', '.m4v', '.avi', '.mkv', '.flv', '.wmv']))
    root = Path(d)
    _nat = re.compile(r'(\d+)')

    def _nat_key(s):
        # 自然排序：数字段按数值比较，其余按小写字符串（类似资源管理器）
        return [int(t) if t.isdigit() else t.lower() for t in _nat.split(s)]

    files = []
    for p in root.rglob('*'):
        if p.is_file() and p.suffix.lower() in exts:
            try:
                sz = p.stat().st_size
            except OSError:
                sz = 0
            files.append({
                'path': str(p),
                'name': p.name,
                'rel': str(p.relative_to(root)),
                'size': sz,
            })
    files.sort(key=lambda f: _nat_key(f['name']))
    return jsonify({'dir': d, 'count': len(files), 'files': files})


@app.route('/api/probe')
def api_probe():
    path = unquote(request.args.get('path', ''))
    if not os.path.isfile(path):
        return jsonify({'error': '文件不存在'}), 400
    try:
        return jsonify(media.probe(path))
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)}), 500


@app.route('/api/video')
def api_video():
    """流式播放（支持 Range 拖动）。"""
    path = unquote(request.args.get('path', ''))
    if not os.path.isfile(path):
        return jsonify({'error': '文件不存在'}), 400
    size = os.path.getsize(path)
    range_h = request.headers.get('Range')
    mime = 'video/mp4' if path.lower().endswith('.mp4') else 'video/webm'
    if range_h:
        m = __import__('re').match(r'bytes=(\d*)-(\d*)', range_h)
        start, end = (m.group(1), m.group(2)) if m else (None, None)
        start = int(start) if start else 0
        end = int(end) if end else min(size - 1, start + 1024 * 1024 - 1)
        length = end - start + 1
        with open(path, 'rb') as f:
            f.seek(start)
            data = f.read(length)
        resp = Response(data, 206, mimetype=mime,
                        content_type=f'{mime}; charset=utf-8')
        resp.headers['Content-Range'] = f'bytes {start}-{end}/{size}'
        resp.headers['Accept-Ranges'] = 'bytes'
        resp.headers['Content-Length'] = str(length)
        return resp
    return Response(open(path, 'rb').read(), 200, mimetype=mime,
                    headers={'Accept-Ranges': 'bytes'})


@app.route('/api/frame')
def api_frame():
    """按时间截帧：?path=&t=&w=（缩放宽，可选）→ JPEG。"""
    path = unquote(request.args.get('path', ''))
    t = float(request.args.get('t', 0))
    w = request.args.get('w', '')
    if not os.path.isfile(path):
        return jsonify({'error': '文件不存在'}), 400
    cache = Path(path).parent / CFG['frame']['dir_name'] / (Path(path).stem + '_preview')
    cache.mkdir(parents=True, exist_ok=True)
    out = cache / f'{int(time.time() * 1000)}.jpg'
    try:
        media.extract_frame(path, t, out, int(w) if w else None)
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)}), 500
    return Response(out.read_bytes(), 200, mimetype='image/jpeg')


# ---------------- 项目 ----------------

@app.route('/api/project', methods=['POST'])
def api_project_create():
    data = request.get_json(force=True)
    src_path = data.get('src_path', '')
    if not os.path.isfile(src_path):
        return jsonify({'error': '源视频不存在'}), 400
    info = media.probe(src_path)
    conn = db.get_conn()
    try:
        cur = conn.execute(
            'INSERT INTO projects (name, src_path, src_w, src_h, src_duration, src_fps) '
            'VALUES (?,?,?,?,?,?)',
            (Path(src_path).stem, src_path, info['width'], info['height'],
             info['duration'], info['fps']))
        conn.commit()
        pid = cur.lastrowid
    finally:
        conn.close()
    return jsonify({'id': pid, **info})


@app.route('/api/project/<int:pid>')
def api_project_get(pid):
    conn = db.get_conn()
    try:
        p = conn.execute('SELECT * FROM projects WHERE id=?', (pid,)).fetchone()
        if p is None:
            return jsonify({'error': '项目不存在'}), 404
        wms = conn.execute('SELECT * FROM watermark_regions WHERE project_id=?', (pid,)).fetchall()
        segs = conn.execute('SELECT * FROM segments WHERE project_id=? ORDER BY seg_index', (pid,)).fetchall()
        tasks = conn.execute('SELECT * FROM tasks WHERE project_id=? ORDER BY id', (pid,)).fetchall()
        return jsonify({'project': dict(p), 'watermarks': [dict(w) for w in wms],
                        'segments': [dict(s) for s in segs], 'tasks': [dict(t) for t in tasks]})
    finally:
        conn.close()


@app.route('/api/project/<int:pid>/crop', methods=['PUT'])
def api_project_crop(pid):
    data = request.get_json(force=True)
    c = data.get('crop')
    conn = db.get_conn()
    try:
        if c:
            conn.execute(
                'UPDATE projects SET crop_x=?, crop_y=?, crop_w=?, crop_h=? WHERE id=?',
                (int(c.get('x', 0)), int(c.get('y', 0)), int(c.get('w', 0)), int(c.get('h', 0)), pid))
        else:
            conn.execute('UPDATE projects SET crop_x=NULL, crop_y=NULL, crop_w=NULL, crop_h=NULL WHERE id=?', (pid,))
        conn.commit()
    finally:
        conn.close()
    return jsonify({'ok': True})


@app.route('/api/project/<int:pid>/watermark', methods=['POST'])
def api_watermark_add(pid):
    d = request.get_json(force=True)
    conn = db.get_conn()
    try:
        cur = conn.execute(
            'INSERT INTO watermark_regions (project_id, x, y, width, height, blur_sigma) '
            'VALUES (?,?,?,?,?,?)',
            (pid, int(d['x']), int(d['y']), int(d['w']), int(d['h']), float(d.get('sigma', 30))))
        conn.commit()
        return jsonify({'id': cur.lastrowid})
    finally:
        conn.close()


@app.route('/api/project/<int:pid>/watermark/<int:wid>', methods=['DELETE'])
def api_watermark_del(pid, wid):
    conn = db.get_conn()
    try:
        conn.execute('DELETE FROM watermark_regions WHERE id=? AND project_id=?', (wid, pid))
        conn.commit()
    finally:
        conn.close()
    return jsonify({'ok': True})


# ---------------- 时间段 ----------------

@app.route('/api/project/<int:pid>/segments', methods=['POST'])
def api_segment_add(pid):
    d = request.get_json(force=True)
    conn = db.get_conn()
    try:
        idx = conn.execute(
            'SELECT COALESCE(MAX(seg_index),0)+1 FROM segments WHERE project_id=?', (pid,)).fetchone()[0]
        cur = conn.execute(
            'INSERT INTO segments (project_id, seg_index, frame_start, frame_end, start_time, end_time, direction) '
            'VALUES (?,?,?,?,?,?,?)',
            (pid, idx, d.get('frame_start'), d.get('frame_end'),
             float(d['start']), float(d['end']), d.get('direction', 'both')))
        conn.commit()
        return jsonify({'id': cur.lastrowid})
    finally:
        conn.close()


@app.route('/api/project/<int:pid>/segments/<int:sid>', methods=['PUT', 'DELETE'])
def api_segment_update(pid, sid):
    conn = db.get_conn()
    try:
        if request.method == 'DELETE':
            conn.execute('DELETE FROM segments WHERE id=? AND project_id=?', (sid, pid))
            conn.execute('DELETE FROM tasks WHERE segment_id=? AND project_id=?', (sid, pid))
            conn.commit()
            return jsonify({'ok': True})
        d = request.get_json(force=True)
        conn.execute(
            'UPDATE segments SET start_time=?, end_time=?, frame_start=?, frame_end=?, direction=? '
            'WHERE id=? AND project_id=?',
            (float(d['start']), float(d['end']), d.get('frame_start'), d.get('frame_end'),
             d.get('direction', 'both'), sid, pid))
        new_dir = d.get('direction', 'both')
        cleaned = 0
        if new_dir in ('vertical', 'horizontal'):
            # 方向与任务强一致：移除不符方向的旧任务（RUNNING 不删，成品文件保留在磁盘）
            cur = conn.execute(
                'DELETE FROM tasks WHERE segment_id=? AND project_id=? '
                'AND direction!=? AND state!=\'RUNNING\'',
                (sid, pid, new_dir))
            cleaned = cur.rowcount
        conn.commit()
        return jsonify({'ok': True, 'cleaned': cleaned})
    finally:
        conn.close()


# ---------------- 任务 ----------------

@app.route('/api/project/<int:pid>/tasks', methods=['POST'])
def api_tasks_generate(pid):
    """按每段各自方向生成任务：竖→1、横→1、双→2。已有任务不重复生成。"""
    conn = db.get_conn()
    try:
        segs = conn.execute('SELECT * FROM segments WHERE project_id=? ORDER BY seg_index', (pid,)).fetchall()
        existing = conn.execute('SELECT segment_id, direction FROM tasks WHERE project_id=?', (pid,)).fetchall()
        have = {(r['segment_id'], r['direction']) for r in existing}
        created = 0
        for s in segs:
            for d in ('vertical', 'horizontal'):
                if s['direction'] == d or s['direction'] == 'both':
                    if (s['id'], d) not in have:
                        conn.execute(
                            'INSERT INTO tasks (project_id, segment_id, direction, state) VALUES (?,?,?,?)',
                            (pid, s['id'], d, 'PENDING'))
                        created += 1
        conn.commit()
        return jsonify({'created': created, 'segments': len(segs)})
    finally:
        conn.close()


@app.route('/api/tasks/<int:tid>', methods=['DELETE'])
def api_task_delete(tid):
    """删除任务（RUNNING 中不允许删除）。"""
    conn = db.get_conn()
    try:
        t = conn.execute('SELECT state FROM tasks WHERE id=?', (tid,)).fetchone()
        if t is None:
            return jsonify({'ok': False, 'msg': '任务不存在'}), 404
        if t['state'] == 'RUNNING':
            return jsonify({'ok': False, 'msg': '任务处理中，暂不能删除'}), 400
        conn.execute('DELETE FROM tasks WHERE id=?', (tid,))
        conn.commit()
        return jsonify({'ok': True})
    finally:
        conn.close()


@app.route('/api/tasks')
def api_tasks_list():
    pid = request.args.get('project_id', type=int)
    conn = db.get_conn()
    try:
        if pid:
            rows = conn.execute('SELECT * FROM tasks WHERE project_id=? ORDER BY id', (pid,)).fetchall()
        else:
            rows = conn.execute('SELECT * FROM tasks ORDER BY id DESC LIMIT 100').fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@app.route('/api/tasks/<int:tid>/start', methods=['POST'])
def api_task_start(tid):
    ok, msg = task_mgr.start_task(tid)
    return (jsonify({'ok': ok, 'msg': msg}) if ok else jsonify({'ok': False, 'msg': msg})), (200 if ok else 400)


@app.route('/api/tasks/<int:tid>/confirm', methods=['POST'])
def api_task_confirm(tid):
    ok, msg = task_mgr.confirm_task(tid)
    return (jsonify({'ok': ok, 'msg': msg}) if ok else jsonify({'ok': False, 'msg': msg})), (200 if ok else 400)


@app.route('/api/tasks/<int:tid>/cancel', methods=['POST'])
def api_task_cancel(tid):
    ok, msg = task_mgr.cancel_task(tid)
    return (jsonify({'ok': ok, 'msg': msg}) if ok else jsonify({'ok': False, 'msg': msg})), (200 if ok else 400)


# ---------------- AI 命名 ----------------

@app.route('/api/ai/recognize', methods=['POST'])
def api_ai_recognize():
    """输入：task_id + 3 帧时刻 → 截帧 → 智谱识别（带源文件名关键词）→ 建议名。
    返回 {name, words, frame_paths}（不实际重命名）。
    """
    d = request.get_json(force=True)
    tid = int(d.get('task_id', 0))
    times = d.get('times', [])
    if not times:
        return jsonify({'error': '请提供 1~3 个帧时刻'}), 400
    conn = db.get_conn()
    try:
        t = conn.execute('SELECT * FROM tasks WHERE id=?', (tid,)).fetchone()
        if t is None:
            return jsonify({'error': '任务不存在'}), 404
        t = dict(t)
        p = conn.execute('SELECT * FROM projects WHERE id=?', (t['project_id'],)).fetchone()
        p = dict(p)
        seg = conn.execute('SELECT * FROM segments WHERE id=?', (t['segment_id'],)).fetchone()
        seg = dict(seg)
    finally:
        conn.close()

    src_path = p['src_path']
    # 截帧：基于源视频在时间段内取样（先探测源 fps/时长）
    info = media.probe(src_path)
    dur = max(0.05, seg['end_time'] - seg['start_time'])
    cache = Path(src_path).parent / CFG['frame']['dir_name'] / (Path(src_path).stem + '_ai')
    cache.mkdir(parents=True, exist_ok=True)
    frame_paths = []
    for i, tt in enumerate(times[:3]):
        # 前端传源视频绝对秒 → clamp 到时间段内
        t_abs = min(max(float(seg['start_time']), float(tt)), float(seg['end_time']))
        out = cache / f'{Path(src_path).stem}_{i}.jpg'
        media.extract_frame(src_path, t_abs, out, scale_w=640)
        frame_paths.append(str(out))

    src_words = media.parse_video_name(src_path)
    try:
        words = ai_naming.recognize(frame_paths, Path(src_path).name, src_words, t['direction'])
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'AI 识别失败: ' + str(e)}), 500

    name = ai_naming.merge_name(src_path, words, t['direction'])
    return jsonify({'name': name, 'words': words, 'src_words': src_words, 'frame_paths': frame_paths})


@app.route('/api/rename', methods=['POST'])
def api_rename():
    """重命名产出文件：后缀不变、重名自动 _01；同步更新任务 output_path。"""
    d = request.get_json(force=True)
    path = d.get('path', '')
    new_name = d.get('new_name', '')
    if not os.path.isfile(path) or not new_name:
        return jsonify({'error': '参数不完整'}), 400
    p = Path(path)
    ext = p.suffix
    base = new_name if new_name.lower().endswith(ext.lower()) else new_name + ext
    target = p.parent / base
    n = 1
    while target.exists() and target != p:
        target = p.parent / f'{new_name}_{n:02d}{ext}'
        n += 1
    try:
        os.rename(p, target)
    except OSError as e:
        return jsonify({'error': '重命名失败: ' + str(e)}), 500
    # 同步任务表
    conn = db.get_conn()
    try:
        conn.execute('UPDATE tasks SET output_path=? WHERE output_path=?', (str(target), str(p)))
        conn.commit()
    finally:
        conn.close()
    return jsonify({'ok': True, 'path': str(target), 'name': target.name})


if __name__ == '__main__':
    app.run(host=HOST, port=PORT, threaded=True)
