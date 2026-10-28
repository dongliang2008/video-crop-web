# -*- coding: utf-8 -*-
"""水印处理（方案②）：OpenCV 传统修复 inpaint（Telea / Navier-Stokes）。
替代原「周边环带填充」：沿边界等照线平滑推进重建，消除马赛克块，
静态背景下接近完美；依赖 opencv-python（本地离线）。

性能优化：不再对整帧 inpaint，而是只对「水印区 + 周边 padding」的局部
子图做修复再贴回；超大区域（如整行字幕映射后 1800×270）先降采样 1/2
修复再放大回贴，速度提升约 10 倍以上。
"""
import cv2
import numpy as np

_PAD = 24          # 局部修复时水印四周留的修复过渡带（像素）
_SCALE_TH = 400    # 子图短边超过该阈值时降采样修复（像素）


def apply_inpaint(frame, regions, method='telea', pad=_PAD, blur_after=0):
    """对单帧做水印区修复（就地返回新帧）。
    frame: BGR numpy 数组 (H, W, 3)
    regions: 当前画幅坐标 [{x, y, width, height}]，越界自动 clamp
    method: 'telea'（默认） | 'ns'
    blur_after: 修复后对水印框选区追加的高斯模糊强度（sigmaX），0=不模糊
    """
    if not regions:
        return frame
    h, w = frame.shape[:2]
    # 计算水印包围盒（含 padding）
    xs0 = [max(0, int(r['x'])) for r in regions]
    ys0 = [max(0, int(r['y'])) for r in regions]
    xs1 = [min(w, int(r['x']) + int(r['width'])) for r in regions]
    ys1 = [min(h, int(r['y']) + int(r['height'])) for r in regions]
    x0 = max(0, min(xs0) - pad)
    y0 = max(0, min(ys0) - pad)
    x1 = min(w, max(xs1) + pad)
    y1 = min(h, max(ys1) + pad)
    if x1 - x0 <= 1 or y1 - y0 <= 1:
        return frame

    sub = frame[y0:y1, x0:x1].copy()
    sh, sw = sub.shape[:2]
    # 局部 mask
    mask = np.zeros((sh, sw), np.uint8)
    for r in regions:
        mx0 = max(0, int(r['x']) - x0)
        my0 = max(0, int(r['y']) - y0)
        mx1 = min(sw, mx0 + int(r['width']))
        my1 = min(sh, my0 + int(r['height']))
        if mx1 - mx0 > 1 and my1 - my0 > 1:
            mask[my0:my1, mx0:mx1] = 255
    if not mask.any():
        return frame

    flags = cv2.INPAINT_TELEA if method != 'ns' else cv2.INPAINT_NS
    work, wmask = sub, mask
    # 超大子图降采样 1/2 修复，再放大回贴（速度优先，视觉可接受）
    if min(sh, sw) > _SCALE_TH:
        nw, nh = sw // 2, sh // 2
        work = cv2.resize(sub, (nw, nh), interpolation=cv2.INTER_AREA)
        wmask = cv2.resize(mask, (nw, nh), interpolation=cv2.INTER_NEAREST)
        fixed = cv2.inpaint(work, wmask, 3, flags)
        fixed = cv2.resize(fixed, (sw, sh), interpolation=cv2.INTER_LINEAR)
    else:
        fixed = cv2.inpaint(work, wmask, 3, flags)

    # 修复后追加高斯模糊（可选）：对水印框选区（+1px 扩张过渡）做模糊软化
    if blur_after and blur_after > 0:
        blurred = cv2.GaussianBlur(fixed, (0, 0), sigmaX=float(blur_after))
        km = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)
        fixed = fixed.copy()
        fixed[km > 0] = blurred[km > 0]

    out = frame.copy()
    out[y0:y1, x0:x1] = fixed
    return out
