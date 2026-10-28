# -*- coding: utf-8 -*-
"""补丁2：①AI命名合并源文件名关键词去重 ②弹窗新名可编辑确认后应用 ③显示源文件关键词。"""
import io

def load(p):
    return io.open(p, encoding='utf-8').read()

def save(p, s):
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

def rep(s, old, new, tag):
    assert old in s, 'NOT FOUND: %s :: %s' % (tag, old[:70])
    assert s.count(old) == 1, 'AMBIG: %s' % tag
    return s.replace(old, new, 1)

# ---------- 1) server/ai_naming.py ----------
P1 = r'C:\Users\Administrator\Doubao\dev\video-crop-web\server\ai_naming.py'
s1 = load(P1)

s1 = rep(s1,
"""def merge_name(src_path, words, direction):
    \"\"\"组装规范文件名：{国家或通用}_{词1}_{词2}_..._{横屏|竖屏}（不含扩展名）。
    80 字符截断兜底。\"\"\"
    first = pick_country(words, path=src_path)
    tail = [w for w in words if w != first]
    parts = [first] + tail""",
"""def _clean_src_words(src_path):
    \"\"\"源文件名关键词二次清洗：去噪声/方向/段序号/纯数字/重复。\"\"\"
    noise = set(NAMING.get('noise_words', []))
    out, seen = [], set()
    for w in media.parse_video_name(src_path):
        if not w or w in seen or w in noise:
            continue
        if re.match(r'^段\\d*$', w):
            continue
        if w.isdigit() or re.fullmatch(r'\\d{2,}', w):
            continue
        if w.lower() in ('vertical', 'horizontal', 'both', 'mp4', 'webm', 'mov'):
            continue
        if len(w) < 2:
            continue
        seen.add(w)
        out.append(w)
    return out


def merge_name(src_path, words, direction):
    \"\"\"组装规范文件名：{国家或通用}_{源文件名关键词}_{AI识别词}..._{横屏|竖屏}。
    源文件名关键词与 AI 词去重合并（AI 词中出现过的源词不重复拼）；
    80 字符截断兜底。\"\"\"
    first = pick_country(words, path=src_path)
    src_kw = [w for w in _clean_src_words(src_path) if w != first]
    ai_tail = [w for w in words if w != first and w not in src_kw]
    parts = [first] + src_kw + ai_tail""",
    'ai_naming merge_name')

s1 = rep(s1,
"""    # 去掉可能残留的模板词/占位
    parts = [w for w in parts if w not in set(NAMING.get('noise_words', []))
             and w != NAMING.get('placeholder', 'XX')]""",
"""    # 去掉可能残留的模板词/占位
    parts = [w for w in parts if w not in set(NAMING.get('noise_words', []))
             and w != NAMING.get('placeholder', 'XX')
             and not re.match(r'^段\\d*$', w)]""",
    'ai_naming parts filter')
save(P1, s1)
print('ai_naming.py OK')

# ---------- 2) server/app.py：返回 src_words ----------
P2 = r'C:\Users\Administrator\Doubao\dev\video-crop-web\server\app.py'
s2 = load(P2)
s2 = rep(s2,
"""    name = ai_naming.merge_name(src_path, words, t['direction'])
    return jsonify({'name': name, 'words': words, 'frame_paths': frame_paths})""",
"""    name = ai_naming.merge_name(src_path, words, t['direction'])
    return jsonify({'name': name, 'words': words, 'src_words': src_words, 'frame_paths': frame_paths})""",
    'app recognize return')
save(P2, s2)
print('app.py OK')

# ---------- 3) web/index.html：aiName 可编辑 + 源关键词行 ----------
P3 = r'C:\Users\Administrator\Doubao\dev\video-crop-web\web\index.html'
s3 = load(P3)
s3 = rep(s3,
"""    <div style="display:flex;gap:8px;margin:10px 0;flex-wrap:wrap;align-items:center">
      <button class="btn warn" id="btnAiRecog" disabled>AI 识别（综合3帧+源文件名）</button>
      <div class="slotKw" id="aiKwAll" style="flex:1;min-width:180px">未识别</div>
    </div>""",
"""    <div style="display:flex;gap:8px;margin:10px 0;flex-wrap:wrap;align-items:center">
      <button class="btn warn" id="btnAiRecog" disabled>AI 识别（综合3帧+源文件名）</button>
      <div class="slotKw" id="aiKwAll" style="flex:1;min-width:180px">未识别</div>
    </div>
    <div class="hint" style="margin-bottom:6px">源文件关键词：<span id="aiSrcWords">--</span></div>""",
    'index ai recog row')
s3 = rep(s3,
"""        <div class="hint">综合命名结果</div>
        <input id="aiName" readonly value="（等待识别）">""",
"""        <div class="hint">综合命名结果（可修改后应用）</div>
        <input id="aiName" value="（等待识别）" placeholder="AI 综合源文件名关键词+画面内容生成，可在此修改">""",
    'index aiName editable')
save(P3, s3)
print('index.html OK')

# ---------- 4) web/js/app.js：显示源关键词 ----------
P4 = r'C:\Users\Administrator\Doubao\dev\video-crop-web\web\js\app.js'
s4 = load(P4)
s4 = rep(s4,
"""      $('aiKwAll').innerHTML = r.words.map(function (w) { return '<span class="tag">' + esc(w) + '</span>'; }).join(' ');
      $('aiName').value = r.name;""",
"""      $('aiKwAll').innerHTML = r.words.map(function (w) { return '<span class="tag">' + esc(w) + '</span>'; }).join(' ');
      $('aiSrcWords').textContent = (r.src_words || []).join('、') || '（无）';
      $('aiName').value = r.name;""",
    'app.js recog fill')
s4 = rep(s4,
"""    $('aiKwAll').textContent = '未识别'; $('aiName').value = '（等待识别）';""",
"""    $('aiKwAll').textContent = '未识别'; $('aiSrcWords').textContent = '--'; $('aiName').value = '（等待识别）';""",
    'app.js openAi reset')
save(P4, s4)
print('app.js OK')
print('ALL PATCHED')
