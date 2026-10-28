# -*- coding: utf-8 -*-
"""补丁：style.css 段卡片新布局（时间独立行/选中态/段内任务）。"""
import io

P = r'C:\Users\Administrator\Doubao\dev\video-crop-web\web\css\style.css'
src = io.open(P, encoding='utf-8').read()
orig = src

old = """.seg-card{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin-bottom:8px}
.seg-card .head{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;gap:6px;flex-wrap:wrap}
.seg-card .head .seg-name{font-weight:700;color:var(--accent)}
.seg-card .head .seg-time{font-family:Consolas,monospace;font-size:12px;color:var(--text)}"""
new = """.seg-card{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin-bottom:8px;cursor:pointer;transition:border-color .15s}
.seg-card.selected{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent) inset}
.seg-card .head{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}
.seg-card .head .seg-name{font-weight:700;color:var(--accent)}
.seg-card .seg-time{font-family:Consolas,monospace;font-size:12px;color:var(--text);word-break:break-all;line-height:1.5;margin-bottom:6px}
.seg-card .seg-tasks{margin-top:6px;border-top:1px dashed var(--line);padding-top:6px}
.seg-card .seg-tasks .task-card{margin-bottom:6px}
.seg-card .seg-tasks .task-card:last-child{margin-bottom:0}
.seg-empty{font-size:12px;color:var(--muted);padding:2px 0}"""
assert old in src, 'CSS anchor not found'
src = src.replace(old, new, 1)
assert src != orig
io.open(P, 'w', encoding='utf-8', newline='\n').write(src)
print('CSS PATCHED OK')
