# -*- coding: utf-8 -*-
"""补丁3：AI命名弹窗改显源视频选帧（不展现成品）；同一项目共用同一原视频。
后端 times 语义改为源视频绝对秒（不再 +seg.start）。"""
import io

def load(p):
    return io.open(p, encoding='utf-8').read()

def save(p, s):
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

def rep(s, old, new, tag):
    assert old in s, 'NOT FOUND: %s :: %s' % (tag, old[:70])
    assert s.count(old) == 1, 'AMBIG: %s' % tag
    return s.replace(old, new, 1)

# ---------- 1) web/js/app.js：openAi 加载源视频；aiPick 用源视频绝对秒 ----------
P4 = r'C:\Users\Administrator\Doubao\dev\video-crop-web\web\js\app.js'
s4 = load(P4)

s4 = rep(s4,
"""    // 弹窗内独立播放器加载成品视频供选帧（不再遮挡/占用主播放器）
    var ap = $('aiPlayer');
    if (t.output_path) {
      ap.src = '/api/video?path=' + encodeURIComponent(t.output_path);
      ap.load(); ap.play().catch(function () {});
    } else {
      ap.removeAttribute('src'); ap.load();
    }""",
"""    // 弹窗内播放器直接加载「源视频」供选帧（不展现修剪后的新视频；
    // 同一项目内多个任务共用同一原视频，已加载则保留进度不重置）
    var ap = $('aiPlayer');
    var srcUrl = '/api/video?path=' + encodeURIComponent(S.srcPath);
    if (ap.src !== srcUrl && S.srcPath) {
      ap.src = srcUrl; ap.load();
    }
    if (S.srcPath) ap.play().catch(function () {});""",
    'openAi load source video')

s4 = rep(s4,
"""    var tRel = v.currentTime || 0;
    var seg = S.segs.find(function (x) { return x.id === S.aiTask.segment_id; });
    var tAbs = (seg ? seg.start_time : 0) + tRel;
    var url = '/api/frame?path=' + encodeURIComponent(S.srcPath) + '&t=' + tAbs + '&w=300';""",
"""    // 播放器显示的是源视频 → 直接取源视频绝对时间
    var tAbs = v.currentTime || 0;
    var url = '/api/frame?path=' + encodeURIComponent(S.srcPath) + '&t=' + tAbs + '&w=300';""",
    'aiPick absolute time')

s4 = rep(s4,
"""    S.aiTimes[i] = tRel;
    $('aiTime' + i).textContent = fmt(tRel);
    var filled = S.aiTimes.filter(function (x) { return x !== null; }).length;
    $('btnAiRecog').disabled = filled === 0;
    toast('已截取帧' + (i + 1) + '（相对成品 ' + fmt(tRel) + '）');""",
"""    S.aiTimes[i] = tAbs;
    $('aiTime' + i).textContent = fmt(tAbs);
    var filled = S.aiTimes.filter(function (x) { return x !== null; }).length;
    $('btnAiRecog').disabled = filled === 0;
    toast('已截取帧' + (i + 1) + '（源视频 ' + fmt(tAbs) + '）');""",
    'aiPick store absolute')
save(P4, s4)
print('app.js OK')

# ---------- 2) server/app.py：times 改为源视频绝对秒 ----------
P2 = r'C:\Users\Administrator\Doubao\dev\video-crop-web\server\app.py'
s2 = load(P2)
s2 = rep(s2,
"""    for i, tt in enumerate(times[:3]):
        t_abs = seg['start_time'] + min(max(0.0, float(tt)), dur)
        out = cache / f'{Path(src_path).stem}_{i}.jpg'
        media.extract_frame(src_path, t_abs, out, scale_w=640)
        frame_paths.append(str(out))""",
"""    for i, tt in enumerate(times[:3]):
        # 前端传源视频绝对秒 → clamp 到时间段内
        t_abs = min(max(float(seg['start_time']), float(tt)), float(seg['end_time']))
        out = cache / f'{Path(src_path).stem}_{i}.jpg'
        media.extract_frame(src_path, t_abs, out, scale_w=640)
        frame_paths.append(str(out))""",
    'recognize absolute time')
save(P2, s2)
print('app.py OK')

# ---------- 3) web/index.html：提示文案 ----------
P3 = r'C:\Users\Administrator\Doubao\dev\video-crop-web\web\index.html'
s3 = load(P3)
s3 = rep(s3,
"""    <div class="ai-tip">在下方成品视频中拖动进度到目标画面 → 点「截取帧」选 3 帧 → AI 识别（画面 + 源文件名关键词）→ 应用命名</div>""",
"""    <div class="ai-tip">在下方<b>原视频</b>中拖动进度到目标画面 → 点「截取帧」选 3 帧 → AI 识别（画面 + 源文件名关键词）→ 确认/修改后应用命名<br>同一视频多个任务共用同一原视频，选帧位置一致</div>""",
    'index ai tip')
save(P3, s3)
print('index.html OK')
print('ALL PATCHED')
