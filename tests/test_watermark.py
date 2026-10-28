# -*- coding: utf-8 -*-
"""水印专项测试：仅去水印不裁剪（标准画幅），验证环带填充效果。
用法: python test\test_watermark.py
"""
import json
import sys
import time
import urllib.request
import urllib.parse

BASE = 'http://127.0.0.1:8100'
SRC = r'C:\Users\Administrator\Doubao\dev\vidio_demo\水印测试.webm'


def call(method, path, body=None):
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode('utf-8'))


def main():
    print('[1] 创建项目')
    p = call('POST', '/api/project', {'src_path': SRC})
    pid = p['id']
    print(f'    项目#{pid} {p["width"]}x{p["height"]} 时长{p["duration"]}s')
    # 不设裁剪（仅去水印）
    print('[2] 不裁剪，添加水印区域（左上角"中新视频"台标区）')
    wm = call('POST', f'/api/project/{pid}/watermark',
              {'x': 30, 'y': 25, 'w': 180, 'h': 120, 'sigma': 30})
    print(f'    水印#{wm["id"]}')
    print('[3] 时间段 0.5s~3.5s，方向横屏（标准画幅，不裁剪）')
    call('POST', f'/api/project/{pid}/segments',
         {'start': 0.5, 'end': 3.5, 'direction': 'horizontal'})
    print('[4] 生成 + 启动 → 确认图')
    call('POST', f'/api/project/{pid}/tasks')
    tasks = call('GET', '/api/tasks?project_id=' + str(pid))
    for t in tasks:
        call('POST', f"/api/tasks/{t['id']}/start")
    time.sleep(4)
    tasks = call('GET', '/api/tasks?project_id=' + str(pid))
    for t in tasks:
        print(f"    任务#{t['id']} 状态:{t['state']} 预览:{t['preview_path']}")
        if t['state'] == 'WAIT_CONFIRM':
            call('POST', f"/api/tasks/{t['id']}/confirm")
    print('[5] 等待出片…')
    for t in tasks:
        for _ in range(60):
            rows = call('GET', '/api/tasks')
            cur = next((x for x in rows if x['id'] == t['id']), None)
            if cur and cur['state'] in ('DONE', 'FAILED'):
                print(f"    任务#{t['id']}: {cur['state']} -> {cur.get('output_path') or cur.get('error')}")
                break
            time.sleep(2)
    return 0


if __name__ == '__main__':
    sys.exit(main())
