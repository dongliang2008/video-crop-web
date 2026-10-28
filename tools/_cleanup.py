# -*- coding: utf-8 -*-
"""一次性清理：清空数据库表 + 删除旧产物文件（不触碰源素材）。"""
import sqlite3
from pathlib import Path

DB = Path(r'C:\Users\Administrator\Doubao\dev\video-crop-web\data\videocrop.db')
FILES = [
    # 未处理目录产物
    r'D:\DBdir\素材\视频\未处理\cctv_中东局势_02_段1_horizontal_预览.png',
    r'D:\DBdir\素材\视频\未处理\cctv_中东局势_02_段1_横屏.mp4',
    # vidio_demo 产物
    r'C:\Users\Administrator\Doubao\dev\vidio_demo\水印测试_段1_horizontal_预览.png',
    r'C:\Users\Administrator\Doubao\dev\vidio_demo\水印测试_段1_横屏.mp4',
    r'C:\Users\Administrator\Doubao\dev\vidio_demo\水印测试_段1_横屏_01.mp4',
    r'C:\Users\Administrator\Doubao\dev\vidio_demo\素材10_test_竖版_段1_horizontal_预览.png',
    r'C:\Users\Administrator\Doubao\dev\vidio_demo\素材10_test_竖版_段1_vertical_预览.png',
    r'C:\Users\Administrator\Doubao\dev\vidio_demo\素材10_test_竖版_段1_横屏.mp4',
    r'C:\Users\Administrator\Doubao\dev\vidio_demo\素材10_test_竖版_段1_竖屏.mp4',
]

# 1) 清空数据库表
conn = sqlite3.connect(str(DB))
for t in ('tasks', 'segments', 'watermark_regions', 'projects'):
    n = conn.execute(f'DELETE FROM {t}').rowcount
    print(f'表 {t}: 清空 {n} 行')
conn.commit()
conn.close()

# 2) 删除产物文件
for p in FILES:
    f = Path(p)
    if f.exists():
        f.unlink()
        print('已删除:', p)
    else:
        print('不存在(跳过):', p)
print('清理完成')
