# -*- coding: utf-8 -*-
"""任务状态机：PENDING → RUNNING → WAIT_CONFIRM → DONE / FAILED / CANCELED。
确认图机制：启动任务先渲染 1 帧完整滤镜链预览图（WAIT_CONFIRM），
用户确认后编码最终视频。后台线程执行，并发受信号量限制。
"""
import threading
from pathlib import Path

from . import db, crop_engine, media

_SEM = threading.BoundedSemaphore(2)  # 本机安全并发 = 2


class TaskError(Exception):
    pass


def make_output_path(src_path, seg_index, direction, output_dir=None):
    """输出命名：<源名>_段N_竖屏|横屏.mp4；重名自动追加 _01。"""
    src = Path(src_path)
    stem = src.stem
    tag = '竖屏' if direction == 'vertical' else '横屏'
    base = f'{stem}_段{seg_index}_{tag}.mp4'
    out_dir = Path(output_dir) if output_dir else src.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    cand = out_dir / base
    n = 1
    while cand.exists():
        cand = out_dir / f'{stem}_段{seg_index}_{tag}_{n:02d}.mp4'
        n += 1
    return str(cand)


def get_project_ctx(project_id):
    """读取项目 + 水印区 + 段信息，组装任务执行上下文。"""
    conn = db.get_conn()
    try:
        p = conn.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone()
        if p is None:
            raise TaskError('项目不存在')
        wms = conn.execute(
            'SELECT x,y,width,height,blur_sigma FROM watermark_regions WHERE project_id=?',
            (project_id,)).fetchall()
        return {
            'project': dict(p),
            'wms': [dict(w) for w in wms],
        }
    finally:
        conn.close()


def _run_task(task_id):
    """执行单任务：渲染预览（未确认时）或编码最终视频。"""
    conn = db.get_conn()
    try:
        t = conn.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
        if t is None:
            return
        t = dict(t)
        ctx = get_project_ctx(t['project_id'])
        p = ctx['project']
        conn.execute("UPDATE tasks SET state='RUNNING', progress=0 WHERE id=?", (task_id,))
        conn.commit()

        seg = conn.execute('SELECT * FROM segments WHERE id=?', (t['segment_id'],)).fetchone()
        if seg is None:
            raise TaskError('时间段不存在')
        seg = dict(seg)

        crop = None
        if p.get('crop_w'):
            crop = {'x': p['crop_x'], 'y': p['crop_y'], 'w': p['crop_w'], 'h': p['crop_h']}

        filters, label, out_w, out_h, regions = crop_engine.build_vf(
            p['src_w'], p['src_h'], crop, t['direction'], ctx['wms'],
            enhance=None, vwidth=p.get('vwidth') or 1080,
        )
        src = p['src_path']
        start = seg['start_time']
        dur = max(0.05, seg['end_time'] - seg['start_time'])
        fps = media.probe(src)['fps']

        blur_after = max((w.get('blur_sigma') or 0) for w in ctx['wms']) if ctx['wms'] else 0

        if not t['preview_approved']:
            # 第一阶段：渲染确认图
            preview = str(Path(p['src_path']).parent / f'{Path(p["src_path"]).stem}_段{seg["seg_index"]}_{t["direction"]}_预览.png')
            crop_engine.render_preview(src, start, filters, label, out_w, out_h, regions, preview,
                                       method='telea', blur_after=blur_after)
            conn.execute(
                "UPDATE tasks SET state='WAIT_CONFIRM', preview_path=?, progress=100 WHERE id=?",
                (preview, task_id))
            conn.commit()
            return

        # 第二阶段：编码最终视频
        out = crop_engine.render_video(src, start, dur, filters, label, out_w, out_h, regions, fps,
                                       make_output_path(src, seg['seg_index'], t['direction']),
                                       method='telea', blur_after=blur_after)
        conn.execute("UPDATE tasks SET state='DONE', output_path=?, progress=100 WHERE id=?",
                     (out, task_id))
        conn.commit()
    except Exception as e:  # noqa: BLE001
        conn.execute("UPDATE tasks SET state='FAILED', error=? WHERE id=?",
                     (str(e), task_id))
        conn.commit()
    finally:
        conn.close()


def start_task(task_id):
    """启动任务（仅 PENDING/FAILED/CANCELED 可启动）。"""
    conn = db.get_conn()
    try:
        t = conn.execute('SELECT state FROM tasks WHERE id=?', (task_id,)).fetchone()
        if t is None:
            return False, '任务不存在'
        if t['state'] in ('RUNNING', 'WAIT_CONFIRM', 'DONE'):
            return False, '任务当前状态不允许启动'
        conn.execute("UPDATE tasks SET state='PENDING', error='' WHERE id=?", (task_id,))
        conn.commit()
    finally:
        conn.close()
    _submit(task_id)
    return True, '已启动'


def confirm_task(task_id):
    """确认预览图 → 编码最终视频（仅 WAIT_CONFIRM）。"""
    conn = db.get_conn()
    try:
        t = conn.execute('SELECT state FROM tasks WHERE id=?', (task_id,)).fetchone()
        if t is None:
            return False, '任务不存在'
        if t['state'] != 'WAIT_CONFIRM':
            return False, '任务不在待确认状态'
        conn.execute("UPDATE tasks SET preview_approved=1, state='PENDING', error='' WHERE id=?",
                     (task_id,))
        conn.commit()
    finally:
        conn.close()
    _submit(task_id)
    return True, '已确认，开始输出'


def cancel_task(task_id):
    """取消待确认任务 → 回到待启动。"""
    conn = db.get_conn()
    try:
        t = conn.execute('SELECT state FROM tasks WHERE id=?', (task_id,)).fetchone()
        if t is None:
            return False, '任务不存在'
        if t['state'] == 'WAIT_CONFIRM':
            conn.execute("UPDATE tasks SET state='PENDING', preview_approved=0 WHERE id=?",
                         (task_id,))
            conn.commit()
            return True, '已取消确认'
        return False, '仅待确认任务可取消'
    finally:
        conn.close()


def _submit(task_id):
    def worker():
        with _SEM:
            _run_task(task_id)
    threading.Thread(target=worker, daemon=True).start()
