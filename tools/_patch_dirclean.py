# -*- coding: utf-8 -*-
"""补丁4：方向-任务一致性。改段方向时清理不符方向旧任务（RUNNING 除外）。"""
import io

def load(p):
    return io.open(p, encoding='utf-8').read()

def save(p, s):
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

def rep(s, old, new, tag):
    assert old in s, 'NOT FOUND: %s :: %s' % (tag, old[:70])
    assert s.count(old) == 1, 'AMBIG: %s' % tag
    return s.replace(old, new, 1)

# ---------- 1) server/app.py：PUT segments 联动清理 ----------
P2 = r'C:\Users\Administrator\Doubao\dev\video-crop-web\server\app.py'
s2 = load(P2)
s2 = rep(s2,
"""        conn.execute(
            'UPDATE segments SET start_time=?, end_time=?, frame_start=?, frame_end=?, direction=? '
            'WHERE id=? AND project_id=?',
            (float(d['start']), float(d['end']), d.get('frame_start'), d.get('frame_end'),
             d.get('direction', 'both'), sid, pid))
        conn.commit()
        return jsonify({'ok': True})""",
"""        conn.execute(
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
                'AND direction!=? AND state!=\\'RUNNING\\'',
                (sid, pid, new_dir))
            cleaned = cur.rowcount
        conn.commit()
        return jsonify({'ok': True, 'cleaned': cleaned})""",
    'app.py segments update cleanup')
save(P2, s2)
print('app.py OK')

# ---------- 2) web/js/app.js：setDir 提示清理 ----------
P4 = r'C:\Users\Administrator\Doubao\dev\video-crop-web\web\js\app.js'
s4 = load(P4)
s4 = rep(s4,
"""  function setDir(i, d) {
    var s = S.segs[i];
    API.updSeg(S.projectId, s.id, { start: s.start_time, end: s.end_time, direction: d }).then(function () { reloadProject(); });
  }""",
"""  function setDir(i, d) {
    var s = S.segs[i];
    API.updSeg(S.projectId, s.id, { start: s.start_time, end: s.end_time, direction: d }).then(function (r) {
      if (r && r.error) { toast(r.error); return; }
      if (r && r.cleaned > 0) {
        toast('已移除 ' + r.cleaned + ' 个与方向不符的旧任务（成品文件保留在源目录）');
      }
      reloadProject();
    });
  }""",
    'app.js setDir cleanup toast')
save(P4, s4)
print('app.js OK')
print('ALL PATCHED')
