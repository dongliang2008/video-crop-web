# -*- coding: utf-8 -*-
"""端到端测试：新引擎（OpenCV inpaint）+ 任务删除接口。
模拟用户流程：加载 cctv 视频 → 框裁剪+3水印 → 设段 → 生成任务 → 启动(确认图) → 确认 → 成品。"""
import json
import time
import urllib.request

BASE = 'http://127.0.0.1:8010'
SRC = r'D:\DBdir\素材\视频\未处理\cctv_中东局势_02.mp4'


def call(method, path, body=None):
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))


def wait_task_state(tid, want, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        rows = call('GET', '/api/tasks?project_id=%d' % pid)
        t = next((x for x in rows if x['id'] == tid), None)
        if t and t['state'] in want:
            return t
        time.sleep(1.5)
    return None


# 1) 新建项目
p = call('POST', '/api/project', {'src_path': SRC})
pid = p['id']
print('project', pid)

# 2) 裁剪区（画布 (5,1) 635x259 → 源约 (3,1) 476x194）
call('PUT', f'/api/project/{pid}/crop', {'crop': {'x': 3, 'y': 1, 'w': 476, 'h': 194}})

# 3) 水印（源坐标：左上台标 / 右上台标 / 底部字幕）
w1 = call('POST', f'/api/project/{pid}/watermark', {'x': 27, 'y': 18, 'w': 72, 'h': 32, 'blur_sigma': 30})
w2 = call('POST', f'/api/project/{pid}/watermark', {'x': 374, 'y': 14, 'w': 90, 'h': 38, 'blur_sigma': 30})
w3 = call('POST', f'/api/project/{pid}/watermark', {'x': 23, 'y': 211, 'w': 457, 'h': 43, 'blur_sigma': 30})
print('watermarks', w1.get('id'), w2.get('id'), w3.get('id'))

# 4) 时间段 15~25s，横屏
call('POST', f'/api/project/{pid}/segments', {'start': 15.0, 'end': 25.0, 'direction': 'horizontal'})

# 5) 生成任务
g = call('POST', f'/api/project/{pid}/tasks')
print('gen tasks:', g)
assert g['created'] == 1, '应为1条横屏任务'

rows = call('GET', '/api/tasks?project_id=%d' % pid)
tid = rows[0]['id']
print('task', tid, rows[0]['state'])

# 6) 启动 → WAIT_CONFIRM（确认图）
call('POST', f'/api/tasks/{tid}/start')
t = wait_task_state(tid, ['WAIT_CONFIRM', 'FAILED'], timeout=90)
print('after start:', t['state'], 'preview:', t.get('preview_path'))
assert t['state'] == 'WAIT_CONFIRM', t.get('error', t['state'])

# 7) 确认 → DONE（编码成品）
call('POST', f'/api/tasks/{tid}/confirm')
t = wait_task_state(tid, ['DONE', 'FAILED'], timeout=180)
print('after confirm:', t['state'], 'output:', t.get('output_path'))
assert t['state'] == 'DONE', t.get('error', t['state'])

# 8) 任务删除接口（DONE 任务可删）
d = call('DELETE', f'/api/tasks/{tid}')
print('delete done-task:', d)

# 用新段生成新任务再删
call('POST', f'/api/project/{pid}/segments', {'start': 30.0, 'end': 40.0, 'direction': 'vertical'})
g2 = call('POST', f'/api/project/{pid}/tasks')
print('gen tasks2:', g2)
rows = call('GET', '/api/tasks?project_id=%d' % pid)
tid2 = [x['id'] for x in rows if x['state'] == 'PENDING'][0]
d2 = call('DELETE', f'/api/tasks/{tid2}')
print('delete pending-task:', d2)
rows = call('GET', '/api/tasks?project_id=%d' % pid)
print('final tasks:', [(x['id'], x['state']) for x in rows])
print('E2E OK')
