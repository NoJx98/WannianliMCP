# 中国命理运势计算引擎 v2.0

整合八字四柱、二十八宿、月相(天文级)、节日、生肖配对、干支纳音、建星、黄道黑道、吉神方位、冲煞、评分。

**全部算法有据可查，离线可用。**

## 使用

```bash
python3 fortune_engine.py  # 输出今日运势JSON
```

## 依赖

```bash
pip install lunardate skyfield ephem
```

首次运行 skyfield 会下载 17MB JPL星历文件(de421.bsp)，之后完全离线。
