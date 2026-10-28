# -*- coding: utf-8 -*-
"""补丁8：选中视频后，顶栏独立整行显示所选文件详细路径（不再与元数据混排/被挤压）。"""
import io

def load(p):
    return io.open(p, encoding='utf-8').read()

def save(p, s):
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

def rep(s, old, new, tag):
    assert old in s, 'NOT FOUND: %s :: %s' % (tag, old[:80])
    assert s.count(old) == 1, 'AMBIG: %s' % tag
    return s.replace(old, new, 1)

# 1) CSS：src-label 独占一行、完整换行显示
P1 = r'C:\Users\Administrator\Doubao\dev\video-crop-web\web\css\style.css'
s1 = load(P1)
s1 = rep(s1,
'.src-label{color:var(--dim);font-size:12px;flex:1;min-width:160px;word-break:break-all}',
'.src-label{color:var(--dim);font-size:12px;flex-basis:100%;min-width:100%;word-break:break-all;order:99;margin-top:2px;padding:2px 2px 0}',
'css src-label')
save(P1, s1)
print('style.css OK')

# 2) JS：srcLabel 只显示文件完整路径；srcMeta 补 fps 保留元数据
P2 = r'C:\Users\Administrator\Doubao\dev\video-crop-web\web\js\app.js'
s2 = load(P2)
s2 = rep(s2,
"$('srcLabel').textContent = '源：' + path + '（' + info.width + '×' + info.height + ' · ' + info.duration + 's · ' + info.fps + 'fps）';",
"$('srcLabel').textContent = '已选文件：' + path;",
'js srcLabel')
s2 = rep(s2,
"$('srcMeta').textContent = '(' + info.width + '×' + info.height + ' · ' + info.duration + 's)';",
"$('srcMeta').textContent = '(' + info.width + '×' + info.height + ' · ' + info.duration + 's · ' + info.fps + 'fps)';",
'js srcMeta')
save(P2, s2)
print('app.js OK')
