# -*- coding: utf-8 -*-
import io
p = r'C:\Users\Administrator\Doubao\dev\video-crop-web\server\config.json'
s = io.open(p, encoding='utf-8').read()
old = '"max_concurrent": 2,\n    "crf": 23'
new = '"max_concurrent": 2,\n    "crf": 26'
assert old in s, 'anchor not found'
s = s.replace(old, new, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
import json
c = json.load(io.open(p, encoding='utf-8'))
print('config crf ->', c['processing']['crf'])
