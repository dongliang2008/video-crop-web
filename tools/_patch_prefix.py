# -*- coding: utf-8 -*-
"""补丁9：AI 打标自动生成新文件名时，默认加前缀「主题_」+ 原拼接规则。"""
import io

def load(p):
    return io.open(p, encoding='utf-8').read()

def save(p, s):
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

P = r'C:\Users\Administrator\Doubao\dev\video-crop-web\server\ai_naming.py'
s = load(P)

old = """    direction_tag = '竖屏' if direction == 'vertical' else '横屏'
    name = '_'.join(parts + [direction_tag])"""

new = """    direction_tag = '竖屏' if direction == 'vertical' else '横屏'
    name = '主题_' + '_'.join(parts + [direction_tag])"""

assert old in s, 'anchor not found'
assert s.count(old) == 1, 'ambiguous'
s = s.replace(old, new, 1)

# 截断逻辑保留前缀：max_len 含「主题_」，从尾部截
old2 = """    max_len = NAMING.get('max_filename_len', 80)
    suffix = '_' + direction_tag
    if len(name) > max_len:
        head = name[: max_len - len(suffix)]
        name = head.rstrip('_') + suffix"""
new2 = """    max_len = NAMING.get('max_filename_len', 80)
    suffix = '_' + direction_tag
    if len(name) > max_len:
        head = name[: max_len - len(suffix)]
        name = head.rstrip('_') + suffix"""
assert old2 in s, 'anchor2 not found'
assert s.count(old2) == 1, 'ambiguous2'
s = s.replace(old2, new2, 1)
save(P, s)
print('ai_naming.py OK — 新文件名前缀「主题_」')

# 单元自测
import sys
sys.path.insert(0, r'C:\Users\Administrator\Doubao\dev\video-crop-web')
from server import ai_naming
n1 = ai_naming.merge_name(r'D:\DBdir\素材\视频\未处理\cctv_中东局势_02.mp4', ['爆炸', '石油设施', '冲突'], 'vertical')
print('示例1:', n1)
n2 = ai_naming.merge_name(r'D:\DBdir\素材\视频\未处理\weibo_中俄一带一路_07.mp4', ['普京', '访问'], 'horizontal')
print('示例2:', n2)
