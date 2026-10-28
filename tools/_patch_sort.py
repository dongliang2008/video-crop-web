# -*- coding: utf-8 -*-
"""补丁7：目录视频列表按文件名自然排序（数字按数值，忽略目录前缀）。"""
import io, re

def load(p):
    return io.open(p, encoding='utf-8').read()

def save(p, s):
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

P = r'C:\Users\Administrator\Doubao\dev\video-crop-web\server\app.py'
s = load(P)

old = """    root = Path(d)
    files = []
    for p in sorted(root.rglob('*')):
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
    return jsonify({'dir': d, 'count': len(files), 'files': files})"""

new = """    root = Path(d)
    _nat = re.compile(r'(\\d+)')

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
    return jsonify({'dir': d, 'count': len(files), 'files': files})"""

assert old in s, 'anchor not found'
assert s.count(old) == 1, 'ambiguous'
s = s.replace(old, new, 1)
save(P, s)
print('app.py OK — 按文件名自然排序')
