# -*- coding: utf-8 -*-
"""补丁：任务内嵌段卡片 + 点击段联动播放器（app.js 三处替换）。"""
import io

P = r'C:\Users\Administrator\Doubao\dev\video-crop-web\web\js\app.js'
src = io.open(P, encoding='utf-8').read()
orig = src

def rep(old, new, must=True):
    global src
    if old not in src:
        if must:
            raise SystemExit('NOT FOUND: ' + old[:80])
        return
    src = src.replace(old, new, 1)

# 1) S 增加 selSeg
rep("""    aiTask: null, aiTimes: [null, null, null],
    pollTimer: null""",
    """    aiTask: null, aiTimes: [null, null, null],
    selSeg: null,                      // 当前选中段索引（点击段卡片联动播放器）
    pollTimer: null""")

# 2) renderSegs/renderTasks/renderAll → 任务内嵌 + selectSeg
rep("""  function renderSegs() {
    $('segList').innerHTML = S.segs.length ? S.segs.map(function (s, i) {
      var d = s.direction || 'both';
      return '<div class="seg-card"><div class="head"><span class="seg-name">段' + (i + 1) + '</span><button class="btn small danger" data-delseg="' + i + '">删除</button></div>' +
        '<div class="seg-time">' + fmt(s.start_time) + ' ~ ' + fmt(s.end_time) + ' · ' + (s.end_time - s.start_time).toFixed(1) + 's</div>' +
        '<div class="dir-group">' +
        '<button class="btn' + (d === 'vertical' ? ' sel' : '') + '" data-dir="' + i + ':vertical">竖屏</button>' +
        '<button class="btn' + (d === 'horizontal' ? ' sel' : '') + '" data-dir="' + i + ':horizontal">横屏</button>' +
        '<button class="btn' + (d === 'both' ? ' sel' : '') + '" data-dir="' + i + ':both">两者都要</button></div></div>';
    }).join('') : '<div class="empty-hint">还没有时间段：播放器拖到目标画面，点「设起始帧 / 设结束帧」添加</div>';
  }
  function renderTasks() {
    $('taskList').innerHTML = S.tasks.length ? S.tasks.map(function (t) {
      var st = t.state, cls = '', label = '';
      if (st === 'PENDING') { cls = 'st-pend'; label = '待启动'; }
      else if (st === 'RUNNING') { cls = 'st-run'; label = '处理中…'; }
      else if (st === 'WAIT_CONFIRM') { cls = 'st-wait'; label = '待确认'; }
      else if (st === 'DONE') { cls = 'st-done'; label = '已完成'; }
      else { cls = 'st-fail'; label = '失败'; }
      var html = '<div class="task-card state-' + (st === 'WAIT_CONFIRM' ? 'wait' : st === 'DONE' ? 'done' : st === 'FAILED' ? 'fail' : '') + '">' +
        '<div class="t-head"><span class="t-name">任务#' + t.id + ' · ' + (t.direction === 'vertical' ? '竖屏' : '横屏') + '</span><span class="t-status ' + cls + '">' + label + '</span></div>';
      if (st === 'PENDING') html += '<div class="preview-ops"><button class="btn small primary" data-start="' + t.id + '">启动</button><button class="btn small danger" data-deltask="' + t.id + '">删除</button></div>';
      if (st === 'WAIT_CONFIRM') html += '<div class="preview-box"><img src="/api/file?path=' + encodeURIComponent(t.preview_path || '') + '" onerror="this.style.display=\\'none\\'" alt="确认预览帧"><div class="preview-ops"><button class="btn small primary" data-confirm="' + t.id + '">确认输出</button><button class="btn small" data-cancel="' + t.id + '">取消</button><button class="btn small danger" data-deltask="' + t.id + '">删除</button></div></div>';
      if (st === 'DONE') html += '<div class="preview-ops" style="margin-top:6px"><a class="btn small" href="/api/video?path=' + encodeURIComponent(t.output_path || '') + '" target="_blank">打开成品</a><button class="btn small" data-ai="' + t.id + '">AI 命名</button><button class="btn small danger" data-deltask="' + t.id + '">删除</button></div>';
      if (st === 'FAILED') html += '<div class="hint" style="margin-top:4px">' + esc(t.error || '处理失败') + ' <button class="btn small" data-start="' + t.id + '">重试</button><button class="btn small danger" data-deltask="' + t.id + '">删除</button></div>';
      return html + '</div>';
    }).join('') : '<div class="empty-hint">未生成任务：先添加时间段并选方向，再点「生成任务」</div>';
  }
  function renderAll() { renderSegs(); renderTasks(); drawCanvas(); }""",
    """  function taskCardHtml(t) {
    var st = t.state, cls = '', label = '';
    if (st === 'PENDING') { cls = 'st-pend'; label = '待启动'; }
    else if (st === 'RUNNING') { cls = 'st-run'; label = '处理中…'; }
    else if (st === 'WAIT_CONFIRM') { cls = 'st-wait'; label = '待确认'; }
    else if (st === 'DONE') { cls = 'st-done'; label = '已完成'; }
    else { cls = 'st-fail'; label = '失败'; }
    var html = '<div class="task-card state-' + (st === 'WAIT_CONFIRM' ? 'wait' : st === 'DONE' ? 'done' : st === 'FAILED' ? 'fail' : '') + '">' +
      '<div class="t-head"><span class="t-name">任务#' + t.id + ' · ' + (t.direction === 'vertical' ? '竖屏' : '横屏') + '</span><span class="t-status ' + cls + '">' + label + '</span></div>';
    if (st === 'PENDING') html += '<div class="preview-ops"><button class="btn small primary" data-start="' + t.id + '">启动</button><button class="btn small danger" data-deltask="' + t.id + '">删除</button></div>';
    if (st === 'WAIT_CONFIRM') html += '<div class="preview-box"><img src="/api/file?path=' + encodeURIComponent(t.preview_path || '') + '" onerror="this.style.display=\\'none\\'" alt="确认预览帧"><div class="preview-ops"><button class="btn small primary" data-confirm="' + t.id + '">确认输出</button><button class="btn small" data-cancel="' + t.id + '">取消</button><button class="btn small danger" data-deltask="' + t.id + '">删除</button></div></div>';
    if (st === 'DONE') html += '<div class="preview-ops" style="margin-top:6px"><a class="btn small" href="/api/video?path=' + encodeURIComponent(t.output_path || '') + '" target="_blank">打开成品</a><button class="btn small" data-ai="' + t.id + '">AI 命名</button><button class="btn small danger" data-deltask="' + t.id + '">删除</button></div>';
    if (st === 'FAILED') html += '<div class="hint" style="margin-top:4px">' + esc(t.error || '处理失败') + ' <button class="btn small" data-start="' + t.id + '">重试</button><button class="btn small danger" data-deltask="' + t.id + '">删除</button></div>';
    return html + '</div>';
  }
  function renderSegs() {
    if (!S.segs.length) { $('segList').innerHTML = '<div class="empty-hint">还没有时间段：播放器拖到目标画面，点「设起始帧 / 设结束帧」添加</div>'; return; }
    $('segList').innerHTML = S.segs.map(function (s, i) {
      var d = s.direction || 'both';
      var segTasks = S.tasks.filter(function (x) { return x.segment_id === s.id; });
      var taskHtml = segTasks.length ? segTasks.map(taskCardHtml).join('') : '<div class="seg-empty">未生成任务：点下方「生成任务」</div>';
      return '<div class="seg-card' + (S.selSeg === i ? ' selected' : '') + '" data-seg-index="' + i + '"><div class="head"><span class="seg-name">段' + (i + 1) + '</span><button class="btn small danger" data-delseg="' + i + '">删除</button></div>' +
        '<div class="seg-time">' + fmt(s.start_time) + ' ~ ' + fmt(s.end_time) + ' · ' + (s.end_time - s.start_time).toFixed(1) + 's</div>' +
        '<div class="dir-group">' +
        '<button class="btn' + (d === 'vertical' ? ' sel' : '') + '" data-dir="' + i + ':vertical">竖屏</button>' +
        '<button class="btn' + (d === 'horizontal' ? ' sel' : '') + '" data-dir="' + i + ':horizontal">横屏</button>' +
        '<button class="btn' + (d === 'both' ? ' sel' : '') + '" data-dir="' + i + ':both">两者都要</button></div>' +
        '<div class="seg-tasks">' + taskHtml + '</div></div>';
    }).join('');
  }
  function renderTasks() {
    // 兜底：渲染无时间段归属的任务（正常流程不会出现）
    var orphan = S.tasks.filter(function (t) { return !S.segs.some(function (s) { return s.id === t.segment_id; }); });
    $('taskList').innerHTML = orphan.length ? orphan.map(taskCardHtml).join('') : '<div class="empty-hint">任务显示在各时间段卡片下方</div>';
  }
  function renderAll() { renderSegs(); renderTasks(); drawCanvas(); }

  function selectSeg(idx) {
    var s = S.segs[idx];
    if (!s) return;
    S.selSeg = idx;
    var v = $('player');
    if (S.srcPath && v) {
      v.currentTime = Math.min(s.start_time, (S.srcInfo && S.srcInfo.duration) || s.start_time);
    }
    renderSegs();
    toast('已切到段' + (idx + 1) + '：' + fmt(s.start_time) + ' 起点');
  }""")

# 3) reloadProject：selSeg 越界保护
rep("""      S.segs = d.segments;
      S.tasks = d.tasks;
      renderAll();""",
    """      S.segs = d.segments;
      S.tasks = d.tasks;
      if (S.selSeg !== null && S.selSeg >= S.segs.length) S.selSeg = S.segs.length ? 0 : null;
      renderAll();""")

# 4) startPoll：任务内嵌段卡片 → poll 刷新 renderSegs
rep("""      if (S.projectId) { API.listTasks(S.projectId).then(function (rows) { if (rows && !rows.error) { S.tasks = rows; renderTasks(); } }); }""",
    """      if (S.projectId) { API.listTasks(S.projectId).then(function (rows) { if (rows && !rows.error) { S.tasks = rows; renderSegs(); renderTasks(); } }); }""")

# 5) btnNew 重置 selSeg
rep("""      S.projectId = null; S.srcPath = null; S.segs = []; S.tasks = []; S.crop = null; S.wms = []; S.curSeg = null;""",
    """      S.projectId = null; S.srcPath = null; S.segs = []; S.tasks = []; S.crop = null; S.wms = []; S.curSeg = null; S.selSeg = null;""")

# 6) loadVideo 重置 selSeg
rep("""        S.segs = []; S.tasks = []; S.crop = null; S.wms = []; S.curSeg = null;
        renderAll();""",
    """        S.segs = []; S.tasks = []; S.crop = null; S.wms = []; S.curSeg = null; S.selSeg = null;
        renderAll();""")

# 7) segList 事件委托：任务操作 + 段点击联动
rep("""    $('segList').addEventListener('click', function (e) {
      var dir = e.target.getAttribute('data-dir');
      var ds = e.target.getAttribute('data-delseg');
      if (dir) { var p = dir.split(':'); setDir(+p[0], p[1]); }
      if (ds !== null) delSeg(+ds);
    });""",
    """    $('segList').addEventListener('click', function (e) {
      // 段内任务操作（任务卡片内嵌在段卡片中）
      var a = e.target.getAttribute('data-start'), b = e.target.getAttribute('data-confirm'),
          c = e.target.getAttribute('data-cancel'), d = e.target.getAttribute('data-ai'),
          dt = e.target.getAttribute('data-deltask');
      if (a) { API.taskStart(+a).then(function (r) { toast(r.msg || '已启动'); reloadProject(); }); return; }
      if (b) { API.taskConfirm(+b).then(function (r) { toast(r.msg || '已确认'); reloadProject(); }); return; }
      if (c) { API.taskCancel(+c).then(function (r) { toast(r.msg || '已取消'); reloadProject(); }); return; }
      if (d) { openAi(+d); return; }
      if (dt) { API.delTask(+dt).then(function (r) { toast(r.msg || (r.ok ? '任务已删除' : '删除失败')); reloadProject(); }); return; }
      // 段操作
      var dir = e.target.getAttribute('data-dir');
      var ds = e.target.getAttribute('data-delseg');
      if (dir) { var p = dir.split(':'); setDir(+p[0], p[1]); return; }
      if (ds !== null) { delSeg(+ds); return; }
      // 点击段卡片 → 联动播放器跳到该段起点
      var card = e.target.closest('.seg-card');
      if (card) selectSeg(+(card.getAttribute('data-seg-index')));
    });""")

assert src != orig, 'NO CHANGES'
io.open(P, 'w', encoding='utf-8', newline='\n').write(src)
print('PATCHED OK, %d bytes' % len(src))
