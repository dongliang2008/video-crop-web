# -*- coding: utf-8 -*-
"""补丁：app.py 增加任务独立删除接口 + 生成任务返回段数。"""
import io
from pathlib import Path

p = Path(r'C:\Users\Administrator\Doubao\dev\video-crop-web\server\app.py')
src = io.open(p, encoding='utf-8').read()

# 1) 生成任务返回 segments 数量
old1 = "        conn.commit()\n        return jsonify({'created': created})\n    finally:\n        conn.close()\n\n\n@app.route('/api/tasks')"
new1 = ("        conn.commit()\n"
        "        return jsonify({'created': created, 'segments': len(segs)})\n"
        "    finally:\n"
        "        conn.close()\n\n\n"
        "@app.route('/api/tasks/<int:tid>', methods=['DELETE'])\n"
        "def api_task_delete(tid):\n"
        "    \"\"\"删除任务（RUNNING 中不允许删除）。\"\"\"\n"
        "    conn = db.get_conn()\n"
        "    try:\n"
        "        t = conn.execute('SELECT state FROM tasks WHERE id=?', (tid,)).fetchone()\n"
        "        if t is None:\n"
        "            return jsonify({'ok': False, 'msg': '任务不存在'}), 404\n"
        "        if t['state'] == 'RUNNING':\n"
        "            return jsonify({'ok': False, 'msg': '任务处理中，暂不能删除'}), 400\n"
        "        conn.execute('DELETE FROM tasks WHERE id=?', (tid,))\n"
        "        conn.commit()\n"
        "        return jsonify({'ok': True})\n"
        "    finally:\n"
        "        conn.close()\n\n\n"
        "@app.route('/api/tasks')")

if old1 not in src:
    raise SystemExit('PATCH FAIL: old1 not found')
src = src.replace(old1, new1, 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(src)
print('app.py patched ok')
