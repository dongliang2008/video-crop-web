/* 视频裁剪 Web · 前端主控（原生 JS，无依赖） */
(function () {
  'use strict';

  var S = {
    srcPath: null, srcInfo: null,      // 源视频路径 + 探测信息
    projectId: null,
    crop: null,                        // {x,y,w,h} 基于源画面像素（640x360 画布换算）
    wms: [],                           // [{x,y,w,h,sigma}]
    mode: 'crop',
    segs: [], tasks: [],
    curSeg: null,                      // 正在设的段 {start:null,end:null}
    aiTask: null, aiTimes: [null, null, null],
    selSeg: null,                      // 当前选中段索引（点击段卡片联动播放器）
    pollTimer: null
  };

  var $ = function (id) { return document.getElementById(id); };
  var API = {
    j: function (url, opt) { return fetch(url, opt).then(function (r) { return r.json(); }); },
    probe: function (path) { return API.j('/api/probe?path=' + encodeURIComponent(path)); },
    videos: function (dir) { return API.j('/api/videos?dir=' + encodeURIComponent(dir)); },
    createProject: function (path) { return API.j('/api/project', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ src_path: path }) }); },
    getProject: function (id) { return API.j('/api/project/' + id); },
    saveCrop: function (id, crop) { return API.j('/api/project/' + id + '/crop', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ crop: crop }) }); },
    addWm: function (id, wm) { return API.j('/api/project/' + id + '/watermark', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(wm) }); },
    delWm: function (id, wid) { return API.j('/api/project/' + id + '/watermark/' + wid, { method: 'DELETE' }); },
    addSeg: function (id, seg) { return API.j('/api/project/' + id + '/segments', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(seg) }); },
    updSeg: function (id, sid, seg) { return API.j('/api/project/' + id + '/segments/' + sid, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(seg) }); },
    delSeg: function (id, sid) { return API.j('/api/project/' + id + '/segments/' + sid, { method: 'DELETE' }); },
    genTasks: function (id) { return API.j('/api/project/' + id + '/tasks', { method: 'POST' }); },
    listTasks: function (id) { return API.j('/api/tasks?project_id=' + id); },
    taskStart: function (tid) { return API.j('/api/tasks/' + tid + '/start', { method: 'POST' }); },
    taskConfirm: function (tid) { return API.j('/api/tasks/' + tid + '/confirm', { method: 'POST' }); },
    taskCancel: function (tid) { return API.j('/api/tasks/' + tid + '/cancel', { method: 'POST' }); },
    delTask: function (tid) { return API.j('/api/tasks/' + tid, { method: 'DELETE' }); },
    aiRecognize: function (tid, times) { return API.j('/api/ai/recognize', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ task_id: tid, times: times }) }); },
    rename: function (path, newName) { return API.j('/api/rename', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path: path, new_name: newName }) }); }
  };

  function toast(msg) {
    var t = $('toast'); t.textContent = msg; t.style.display = 'block';
    clearTimeout(t._tm); t._tm = setTimeout(function () { t.style.display = 'none'; }, 2500);
  }
  function fmt(t) {
    t = Math.max(0, t || 0);
    var m = Math.floor(t / 60), s = Math.floor(t % 60), ms = Math.floor((t % 1) * 1000);
    return (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s + '.' + String(ms).padStart(3, '0');
  }
  function fmtSize(sz) {
    if (!sz) return '--';
    if (sz > 1024 * 1024) return (sz / 1024 / 1024).toFixed(1) + ' MB';
    return Math.round(sz / 1024) + ' KB';
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  /* ============ 目录选择 ============ */
  function openDir() {
    var path = ($('pathInput').value || '').trim();
    if (!path) { toast('请输入目录路径'); return; }
    // 输入直接是文件 → 跳过列表
    if (path.toLowerCase().endsWith('.mp4') || path.toLowerCase().endsWith('.webm') ||
        path.toLowerCase().endsWith('.mov') || path.toLowerCase().endsWith('.mkv') ||
        path.toLowerCase().endsWith('.avi') || path.toLowerCase().endsWith('.m4v') ||
        path.toLowerCase().endsWith('.flv') || path.toLowerCase().endsWith('.wmv')) {
      loadVideo(path);
      return;
    }
    API.videos(path).then(function (d) {
      if (d.error) { toast(d.error); return; }
      $('dirPath').textContent = d.dir + '（共 ' + d.count + ' 个视频）';
      $('dirList').innerHTML = d.files.length ? d.files.map(function (f) {
        return '<div class="dir-item" data-path="' + esc(f.path) + '"><span class="dn">' + esc(f.rel) + '</span><span class="ds">' + fmtSize(f.size) + '</span></div>';
      }).join('') : '<div class="dir-empty">该目录下没有视频文件</div>';
      $('dirModal').classList.add('open');
    }).catch(function (e) { toast('扫描失败：' + e.message); });
  }
  function closeDir() { $('dirModal').classList.remove('open'); }

  /* ============ 视频加载 ============ */
  function loadVideo(path) {
    path = (path || '').trim();
    if (!path) { toast('请输入视频路径'); return; }
    API.probe(path).then(function (info) {
      if (info.error) { toast(info.error); return; }
      S.srcPath = path; S.srcInfo = info;
      return API.createProject(path).then(function (r) {
        if (r.error) { toast(r.error); return; }
        S.projectId = r.id;
        $('srcLabel').textContent = '已选文件：' + path;
        $('srcMeta').textContent = '(' + info.width + '×' + info.height + ' · ' + info.duration + 's · ' + info.fps + 'fps)';
        $('footProj').textContent = '项目：' + r.id;
        $('btnSave').disabled = false;
        $('player').src = '/api/video?path=' + encodeURIComponent(path);
        $('player').load();
        S.segs = []; S.tasks = []; S.crop = null; S.wms = []; S.curSeg = null; S.selSeg = null;
        renderAll();
        toast('已加载：' + path);
        startPoll();
      });
    }).catch(function (e) { toast('加载失败：' + e.message); });
  }

  /* ============ 播放与帧步进 ============ */
  function frameStep(d) {
    var v = $('player'); if (!S.srcPath) return;
    var fps = S.srcInfo.fps || 30;
    var t = Math.min(S.srcInfo.duration - 0.001, Math.max(0, (v.currentTime || 0) + d / fps));
    v.currentTime = t; updateTime();
  }
  function secStep(d) {
    var v = $('player'); if (!S.srcPath) return;
    var t = Math.min(S.srcInfo.duration, Math.max(0, (v.currentTime || 0) + d));
    v.currentTime = t; updateTime();
  }
  function updateTime() {
    var v = $('player');
    $('curTime').textContent = fmt(v.currentTime || 0);
  }

  /* ============ 时间段 ============ */
  function segStart() {
    if (!S.srcPath) return toast('先加载视频');
    var v = $('player');
    if (!S.curSeg || S.curSeg.start !== null && S.curSeg.end !== null) {
      S.curSeg = { start: v.currentTime, end: null };
    } else if (S.curSeg.start === null) {
      S.curSeg.start = v.currentTime;
    } else {
      toast('当前段已设起始，请先设结束或新建'); return;
    }
    toast('起始帧：' + fmt(S.curSeg.start));
  }
  function segEnd() {
    if (!S.curSeg || S.curSeg.start === null) { toast('先设起始帧'); return; }
    var v = $('player');
    if (v.currentTime <= S.curSeg.start) { toast('结束帧需晚于起始帧'); return; }
    S.curSeg.end = v.currentTime;
    API.addSeg(S.projectId, { start: S.curSeg.start, end: S.curSeg.end, direction: 'both' }).then(function (r) {
      if (r.error) { toast(r.error); return; }
      S.curSeg = null;
      return reloadProject();
    });
  }
  function setDir(i, d) {
    var s = S.segs[i];
    API.updSeg(S.projectId, s.id, { start: s.start_time, end: s.end_time, direction: d }).then(function (r) {
      if (r && r.error) { toast(r.error); return; }
      if (r && r.cleaned > 0) {
        toast('已移除 ' + r.cleaned + ' 个与方向不符的旧任务（成品文件保留在源目录）');
      }
      reloadProject();
    });
  }
  function delSeg(i) {
    API.delSeg(S.projectId, S.segs[i].id).then(function () { reloadProject(); });
  }

  /* ============ 画布框选 ============ */
  var sc = $('selCanvas'), drag = null, baseImg = null;
  function canvasXY(e) {
    var r = sc.getBoundingClientRect();
    // clamp 到画布内；r.width=0（未渲染）时按最大值兜底，杜绝 NaN
    var w = r.width || sc.width, h = r.height || sc.height;
    return {
      x: Math.max(0, Math.min(sc.width, (e.clientX - r.left) * sc.width / w)),
      y: Math.max(0, Math.min(sc.height, (e.clientY - r.top) * sc.height / h))
    };
  }
  // 画布坐标(640×360) → 源分辨率坐标（入库/提交用）
  function cvToSrc(r) {
    var info = S.srcInfo;
    if (!info || !info.width || !info.height || !sc.width || !sc.height) return r;
    var kx = info.width / sc.width, ky = info.height / sc.height;
    var x = Math.max(0, Math.round(r.x * kx));
    var y = Math.max(0, Math.round(r.y * ky));
    return {
      x: x, y: y,
      w: Math.max(1, Math.min(info.width - x, Math.round(r.w * kx))),
      h: Math.max(1, Math.min(info.height - y, Math.round(r.h * ky)))
    };
  }
  // 源分辨率坐标 → 画布坐标（读取项目后显示用）
  function srcToCv(r) {
    var info = S.srcInfo;
    if (!info || !info.width || !info.height || !sc.width || !sc.height) return r;
    var kx = sc.width / info.width, ky = sc.height / info.height;
    return {
      x: Math.round(r.x * kx), y: Math.round(r.y * ky),
      w: Math.round(r.w * kx), h: Math.round(r.h * ky)
    };
  }
  function loadCanvasBase() {
    if (!S.srcPath) return;
    var v = $('player');
    var t = v.currentTime || 0;
    var url = '/api/frame?path=' + encodeURIComponent(S.srcPath) + '&t=' + t + '&w=' + sc.width;
    var img = new Image();
    img.onload = function () { baseImg = img; drawCanvas(); };
    img.onerror = function () { toast('抽帧失败（该时间点不可解码）'); };
    img.src = url;
  }
  function drawCanvas() {
    var ctx = sc.getContext('2d');
    if (baseImg) { ctx.drawImage(baseImg, 0, 0, sc.width, sc.height); }
    else { ctx.fillStyle = '#0c0e12'; ctx.fillRect(0, 0, sc.width, sc.height); }
    if (S.mode === 'crop' && S.crop && isFinite(S.crop.x)) drawRect(ctx, S.crop, '#4f8fd6', '裁剪区');
    S.wms.forEach(function (w, i) { drawRect(ctx, w, '#d0453b', '水印' + (i + 1)); });
    renderCropInfo();
  }
  function drawRect(ctx, r, color, label) {
    ctx.strokeStyle = color; ctx.lineWidth = 2;
    ctx.strokeRect(r.x, r.y, r.w, r.h);
    ctx.fillStyle = color.indexOf('#4f8fd6') === 0 ? 'rgba(79,143,214,.14)' : 'rgba(208,69,59,.14)';
    ctx.fillRect(r.x, r.y, r.w, r.h);
    ctx.fillStyle = color; ctx.font = '11px Microsoft YaHei';
    ctx.fillText(label + ' ' + Math.round(r.x) + ',' + Math.round(r.y) + ' ' + Math.round(r.w) + 'x' + Math.round(r.h), r.x, Math.max(12, r.y - 4));
  }
  // 起点在画布上按下；移动/松开全程监听 document（拖出画布也能完成框选）
  sc.addEventListener('mousedown', function (e) {
    if (!S.srcPath) return;
    drag = canvasXY(e);
  });
  document.addEventListener('mousemove', function (e) {
    if (!drag) return;
    var p = canvasXY(e);
    drawCanvas();
    var ctx = sc.getContext('2d');
    var d = normRect({ x: drag.x, y: drag.y, w: p.x - drag.x, h: p.y - drag.y });
    drawRect(ctx, d, S.mode === 'crop' ? '#4f8fd6' : '#d0453b', S.mode === 'crop' ? '裁剪区' : '水印');
  });
  document.addEventListener('mouseup', function (e) {
    if (!drag) return;
    var p = canvasXY(e);
    var d = normRect({ x: drag.x, y: drag.y, w: p.x - drag.x, h: p.y - drag.y });
    drag = null;
    if (d.w < 4 || d.h < 4) { drawCanvas(); return; }
    d = { x: Math.round(d.x), y: Math.round(d.y), w: Math.round(d.w), h: Math.round(d.h) };
    if (S.mode === 'crop') {
      S.crop = d;
      API.saveCrop(S.projectId, cvToSrc(S.crop)).then(function (r) {
        drawCanvas();
        toast(r && r.error ? r.error : ('裁剪区域已保存：' + d.w + '×' + d.h + '（源 ' + cvToSrc(d).w + '×' + cvToSrc(d).h + '）'));
      });
    } else {
      var wmSrc = cvToSrc(d);
      API.addWm(S.projectId, { x: wmSrc.x, y: wmSrc.y, w: wmSrc.w, h: wmSrc.h, sigma: 3 }).then(function (r) {
        if (r && r.id) {
          S.wms.push({ id: r.id, x: d.x, y: d.y, w: d.w, h: d.h, sigma: 3 });
          drawCanvas();
          toast('已添加水印区域' + S.wms.length + ' 个（源坐标 ' + wmSrc.w + '×' + wmSrc.h + '）');
        } else {
          toast((r && r.error) || '水印添加失败');
          drawCanvas();
        }
      });
    }
  });
  function normRect(d) {
    return { x: Math.min(d.x, d.x + d.w), y: Math.min(d.y, d.y + d.h), w: Math.abs(d.w), h: Math.abs(d.h) };
  }
  function setMode(m) {
    S.mode = m;
    $('modeCrop').classList.toggle('active', m === 'crop');
    $('modeWm').classList.toggle('active', m === 'wm');
    drawCanvas();
  }

  /* ============ 渲染 ============ */
  function renderCropInfo() {
    var hasCrop = S.crop && isFinite(S.crop.x) && isFinite(S.crop.y) && isFinite(S.crop.w) && isFinite(S.crop.h);
    $('cropInfo').innerHTML = hasCrop
      ? '裁剪区域：<b>(' + S.crop.x + ', ' + S.crop.y + ') ' + S.crop.w + '×' + S.crop.h + '</b>（画布像素，输出前换算源分辨率）<button class="btn small danger" data-clear-crop style="margin-left:8px">清除裁剪</button>'
      : '裁剪区域：未框选（输出整帧画面）';
    $('wmList').innerHTML = S.wms.length ? S.wms.map(function (w, i) {
      return '<div class="wm-item"><span><span class="num">' + (i + 1) + '</span>(' + w.x + ',' + w.y + ') ' + w.w + '×' + w.h + ' · 模糊σ' + w.sigma + '</span><button class="btn small danger" data-delwm="' + w.id + '">删除</button></div>';
    }).join('') : '<div class="empty-hint">未框选水印区域（可多个）</div>';
  }
  function taskCardHtml(t) {
    var st = t.state, cls = '', label = '';
    if (st === 'PENDING') { cls = 'st-pend'; label = '待启动'; }
    else if (st === 'RUNNING') { cls = 'st-run'; label = '处理中…'; }
    else if (st === 'WAIT_CONFIRM') { cls = 'st-wait'; label = '待确认'; }
    else if (st === 'DONE') { cls = 'st-done'; label = '已完成'; }
    else { cls = 'st-fail'; label = '失败'; }
    var html = '<div class="task-card state-' + (st === 'WAIT_CONFIRM' ? 'wait' : st === 'DONE' ? 'done' : st === 'FAILED' ? 'fail' : '') + '">' +
      '<div class="t-head"><span class="t-name">任务#' + t.id + ' · ' + (t.direction === 'vertical' ? '竖屏' : '横屏') + '</span><span class="t-status ' + cls + '">' + label + '</span></div>';
    if (st === 'PENDING') html += '<div class="preview-ops"><button class="btn small primary" data-start="' + t.id + '">启动</button><button class="btn small danger" data-deltask="' + t.id + '">删除</button></div>';
    if (st === 'WAIT_CONFIRM') html += '<div class="preview-box"><img src="/api/file?path=' + encodeURIComponent(t.preview_path || '') + '" onerror="this.style.display=\'none\'" alt="确认预览帧"><div class="preview-ops"><button class="btn small primary" data-confirm="' + t.id + '">确认输出</button><button class="btn small" data-cancel="' + t.id + '">取消</button><button class="btn small danger" data-deltask="' + t.id + '">删除</button></div></div>';
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
  }

  function reloadProject() {
    if (!S.projectId) return Promise.resolve();
    return API.getProject(S.projectId).then(function (d) {
      if (d.error) return;
      S.crop = d.project.crop_w ? srcToCv({ x: d.project.crop_x, y: d.project.crop_y, w: d.project.crop_w, h: d.project.crop_h }) : null;
      S.wms = d.watermarks.map(function (w) { var c = srcToCv({ x: w.x, y: w.y, w: w.width, h: w.height }); return { id: w.id, x: c.x, y: c.y, w: c.w, h: c.h, sigma: w.blur_sigma }; });
      S.segs = d.segments;
      S.tasks = d.tasks;
      if (S.selSeg !== null && S.selSeg >= S.segs.length) S.selSeg = S.segs.length ? 0 : null;
      renderAll();
    });
  }
  function startPoll() {
    clearInterval(S.pollTimer);
    S.pollTimer = setInterval(function () {
      if (S.projectId) { API.listTasks(S.projectId).then(function (rows) { if (rows && !rows.error) { S.tasks = rows; renderSegs(); renderTasks(); } }); }
    }, 2000);
  }

  /* ============ 任务操作 ============ */
  function genTasks() {
    API.genTasks(S.projectId).then(function (r) {
      if (r && r.error) { toast(r.error); return; }
      if (r && r.segments === 0) { toast('没有时间段：先设起始帧/结束帧，再生成任务'); return; }
      var n = (r && r.created) || 0;
      if (n > 0) {
        toast('已生成任务（新增 ' + n + ' 条）');
      } else {
        toast('这些时间段的任务已全部生成过；如需重跑，先删除对应任务再点生成');
      }
      reloadProject();
    });
  }
  function startAll() {
    var any = false;
    S.tasks.forEach(function (t) { if (t.state === 'PENDING') { any = true; API.taskStart(t.id); } });
    if (!any) toast('没有待启动任务');
    setTimeout(reloadProject, 600);
  }

  /* ============ AI 命名 ============ */
  function openAi(taskId) {
    var t = S.tasks.find(function (x) { return x.id === taskId; });
    if (!t) return;
    S.aiTask = t; S.aiTimes = [null, null, null];
    $('aiTitle').textContent = '｜ 任务#' + t.id + '（' + t.output_path + '）';
    for (var i = 0; i < 3; i++) {
      $('aiSlot' + i).innerHTML = '未截取'; $('aiTime' + i).textContent = '--';
    }
    $('aiKwAll').textContent = '未识别'; $('aiSrcWords').textContent = '--'; $('aiName').value = '（等待识别）';
    $('btnAiRecog').disabled = true; $('btnAiApply').disabled = true;
    // 弹窗内播放器直接加载「源视频」供选帧（不展现修剪后的新视频；
    // 同一项目内多个任务共用同一原视频，已加载则保留进度不重置）
    var ap = $('aiPlayer');
    var srcUrl = '/api/video?path=' + encodeURIComponent(S.srcPath);
    if (ap.src !== srcUrl && S.srcPath) {
      ap.src = srcUrl; ap.load();
    }
    if (S.srcPath) ap.play().catch(function () {});
    $('aiModal').classList.add('open');
  }
  function closeAi() {
    $('aiModal').classList.remove('open');
    var ap = $('aiPlayer');
    if (ap) { ap.pause(); ap.removeAttribute('src'); ap.load(); }
  }
  function aiPick(i) {
    if (!S.aiTask) return;
    var v = $('aiPlayer');
    if (!v || !v.src) { toast('先加载成品视频（任务需已完成并确认）'); return; }
    // 播放器显示的是源视频 → 直接取源视频绝对时间
    var tAbs = v.currentTime || 0;
    var url = '/api/frame?path=' + encodeURIComponent(S.srcPath) + '&t=' + tAbs + '&w=300';
    var img = new Image();
    img.onload = function () { $('aiSlot' + i).innerHTML = ''; $('aiSlot' + i).appendChild(img); };
    img.src = url;
    S.aiTimes[i] = tAbs;
    $('aiTime' + i).textContent = fmt(tAbs);
    var filled = S.aiTimes.filter(function (x) { return x !== null; }).length;
    $('btnAiRecog').disabled = filled === 0;
    toast('已截取帧' + (i + 1) + '（源视频 ' + fmt(tAbs) + '）');
  }
  function aiRecog() {
    var times = S.aiTimes.filter(function (x) { return x !== null; });
    if (!times.length) return toast('先截取至少 1 帧');
    $('aiKwAll').textContent = '识别中…';
    API.aiRecognize(S.aiTask.id, times).then(function (r) {
      if (r.error) { $('aiKwAll').textContent = r.error; return; }
      $('aiKwAll').innerHTML = r.words.map(function (w) { return '<span class="tag">' + esc(w) + '</span>'; }).join(' ');
      $('aiSrcWords').textContent = (r.src_words || []).join('、') || '（无）';
      $('aiName').value = r.name;
      $('btnAiApply').disabled = false;
      toast('综合命名完成');
    }).catch(function (e) { $('aiKwAll').textContent = '识别失败：' + e.message; });
  }
  function aiApply() {
    var name = $('aiName').value;
    if (!S.aiTask || name.indexOf('（') === 0) return toast('先完成识别');
    API.rename(S.aiTask.output_path, name).then(function (r) {
      if (r.error) { toast(r.error); return; }
      toast('已重命名：' + r.name);
      closeAi();
      reloadProject();
    });
  }

  /* ============ 事件绑定 ============ */
  function bind() {
    $('btnOpen').addEventListener('click', openDir);
    $('pathInput').addEventListener('keydown', function (e) { if (e.key === 'Enter') openDir(); });
    $('btnDirClose').addEventListener('click', closeDir);
    $('dirList').addEventListener('click', function (e) {
      var item = e.target.closest('.dir-item');
      if (item) { closeDir(); loadVideo(item.getAttribute('data-path')); }
    });
    $('btnNew').addEventListener('click', function () {
      S.projectId = null; S.srcPath = null; S.segs = []; S.tasks = []; S.crop = null; S.wms = []; S.curSeg = null; S.selSeg = null;
      $('srcLabel').textContent = '未加载源视频'; $('srcMeta').textContent = ''; $('footProj').textContent = '项目：无';
      $('player').removeAttribute('src'); $('btnSave').disabled = true;
      clearInterval(S.pollTimer);
      renderAll();
    });
    $('btnSave').addEventListener('click', function () { toast('项目数据已自动持久化到本地 SQLite'); });
    $('btnF-1').addEventListener('click', function () { frameStep(-1); });
    $('btnF+1').addEventListener('click', function () { frameStep(1); });
    $('btnS-1').addEventListener('click', function () { secStep(-1); });
    $('btnS+1').addEventListener('click', function () { secStep(1); });
    $('btnS-5').addEventListener('click', function () { secStep(-5); });
    $('btnS+5').addEventListener('click', function () { secStep(5); });
    $('player').addEventListener('timeupdate', updateTime);
    $('player').addEventListener('seeked', function () { updateTime(); loadCanvasBase(); });
    $('btnSegStart').addEventListener('click', segStart);
    $('btnSegEnd').addEventListener('click', segEnd);
    $('modeCrop').addEventListener('click', function () { setMode('crop'); });
    $('modeWm').addEventListener('click', function () { setMode('wm'); });
    $('btnRefreshCanvas').addEventListener('click', loadCanvasBase);
    $('btnGen').addEventListener('click', genTasks);
    $('btnStartAll').addEventListener('click', startAll);
    $('segList').addEventListener('click', function (e) {
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
    });
    $('taskList').addEventListener('click', function (e) {
      var a = e.target.getAttribute('data-start'), b = e.target.getAttribute('data-confirm'),
          c = e.target.getAttribute('data-cancel'), d = e.target.getAttribute('data-ai'),
          dt = e.target.getAttribute('data-deltask');
      if (a) { API.taskStart(+a).then(function (r) { toast(r.msg || '已启动'); reloadProject(); }); }
      if (b) { API.taskConfirm(+b).then(function (r) { toast(r.msg || '已确认'); reloadProject(); }); }
      if (c) { API.taskCancel(+c).then(function (r) { toast(r.msg || '已取消'); reloadProject(); }); }
      if (d) openAi(+d);
      if (dt) { API.delTask(+dt).then(function (r) { toast(r.msg || (r.ok ? '任务已删除' : '删除失败')); reloadProject(); }); }
    });
    $('wmList').addEventListener('click', function (e) {
      var w = e.target.getAttribute('data-delwm');
      if (w !== null) API.delWm(S.projectId, +w).then(function () { reloadProject(); });
    });
    $('cropInfo').addEventListener('click', function (e) {
      if (e.target.getAttribute('data-clear-crop') === null) return;
      S.crop = null;
      API.saveCrop(S.projectId, null).then(function (r) {
        toast(r && r.error ? r.error : '已清除裁剪区域（输出整帧画面）');
        reloadProject();
      });
    });
    $('btnAiClose').addEventListener('click', closeAi);
    $('btnAiPick0').addEventListener('click', function () { aiPick(0); });
    $('btnAiPick1').addEventListener('click', function () { aiPick(1); });
    $('btnAiPick2').addEventListener('click', function () { aiPick(2); });
    $('btnAiRecog').addEventListener('click', aiRecog);
    $('btnAiApply').addEventListener('click', aiApply);
    $('srvAddr').textContent = 'http://127.0.0.1:8010';
    $('pathInput').focus();
  }
  bind();
})();
