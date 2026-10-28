# -*- coding: utf-8 -*-
"""video-crop-web 接口自测：探测 → 建项目 → 裁剪区 → 时间段 → 任务 → 启动(预览) → 确认(出片)。
用法：python test\test_api.py [源视频路径] [起始] [结束]
默认用 vidio_demo 的素材10_test_竖版.mp4，5~12 秒段，竖屏。
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

BASE = 'http://127.0.0.1:8100'


def call(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode('utf-8'))


def wait_task(tid, timeout=120):
    """轮询任务状态直到非 PENDING/RUNNING/WAIT_CONFIRM 或超时。"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        rows = call('GET', '/api/tasks?project_id=0')
        # 直接用任务详情
        tasks = call('GET', '/api/tasks')
        for t in tasks:
            if t['id'] == tid:
                print(f'  任务#{tid} 状态: {t["state"]} 进度: {t["progress"]}')
                if t['state'] in ('DONE', 'FAILED', 'CANCELED'):
                    return t
                time.sleep(2)
                break
        else:
            time.sleep(2)
    raise TimeoutError('任务超时')


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else r'C:\Users\Administrator\Doubao\dev\vidio_demo\素材10_test_竖版.mp4'
    start = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
    end = float(sys.argv[3]) if len(sys.argv) > 3 else 12.0
    if not Path(src).is_file():
        print(f'源视频不存在: {src}')
        return 1

    print(f'[1] 探测: {src}')
    info = call('GET', '/api/probe?path=' + urllib.parse.quote(src))
    print(f'    分辨率 {info["width"]}x{info["height"]} 时长 {info["duration"]}s fps {info["fps"]}')

    print('[2] 创建项目')
    p = call('POST', '/api/project', {'src_path': src})
    pid = p['id']
    print(f'    项目#{pid}')

    print('[3] 保存裁剪区域（画布 640x360 的左上 480x270 → 源像素换算由引擎按比例做，先存画布坐标）')
    call('PUT', f'/api/project/{pid}/crop', {'crop': {'x': 40, 'y': 20, 'w': 480, 'h': 270}})

    print('[4] 添加水印区域')
    wm = call('POST', f'/api/project/{pid}/watermark', {'x': 500, 'y': 300, 'w': 120, 'h': 40, 'sigma': 30})
    print(f'    水印#{wm["id"]}')

    print('[5] 添加时间段')
    seg = call('POST', f'/api/project/{pid}/segments',
               {'start': start, 'end': end, 'direction': 'both', 'frame_start': None, 'frame_end': None})
    print(f'    段#{seg["id"]} {start}s~{end}s 方向 both')

    print('[6] 生成任务（both → 2 条）')
    r = call('POST', f'/api/project/{pid}/tasks')
    print(f'    新增 {r["created"]} 条')

    print('[7] 启动任务 → 渲染确认图')
    tasks = call('GET', '/api/tasks?project_id=' + str(pid))
    for t in tasks:
        call('POST', f"/api/tasks/{t['id']}/start")
        print(f"    任务#{t['id']} 已启动")
    time.sleep(3)
    tasks = call('GET', '/api/tasks?project_id=' + str(pid))
    for t in tasks:
        print(f"    任务#{t['id']} 状态: {t['state']} 预览: {t['preview_path']}")

    print('[8] 确认输出 → 编码 MP4')
    for t in tasks:
        call('POST', f"/api/tasks/{t['id']}/confirm")
        print(f"    任务#{t['id']} 已确认，等待编码完成…")
    for t in tasks:
        r = wait_task(t['id'])
        if r['state'] == 'DONE':
            print(f"    任务#{t['id']} DONE 输出: {r['output_path']}")
        else:
            print(f"    任务#{t['id']} FAILED: {r['error']}")

    print('[9] AI 命名（如智谱可用）')
    try:
        done = [t for t in tasks if t['state'] == 'DONE']
        if done:
            r = call('POST', '/api/ai/recognize',
                     {'task_id': done[0]['id'], 'times': [0.5, 2.0, 4.0]})
            print(f'    建议名: {r.get("name")} 关键词: {r.get("words")}')
            rr = call('POST', '/api/rename', {'path': done[0]['output_path'], 'new_name': r['name']})
            print(f'    已重命名 → {rr.get("name")}')
    except Exception as e:  # noqa: BLE001
        print('    AI 命名跳过（网络/Key 不可用）:', e)

    print('[10] 完成 ✅')
    return 0


if __name__ == '__main__':
    import urllib.parse
    sys.exit(main())
