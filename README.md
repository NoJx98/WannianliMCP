# 中国命理运势计算引擎 v2.0

> **授时于天，遵法于古** —— 整合传统命理算法与天文星历，全部算法有据可查，离线可用。

[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

---

## 目录

- [概览](#概览)
- [安装与依赖](#安装与依赖)
- [算法清单与出处](#算法清单与出处)
- [输出格式](#输出格式)
- [使用示例](#使用示例)
- [模块架构](#模块架构)
- [整合来源](#整合来源)
- [参考资料](#参考资料)
- [许可](#许可)

---

## 概览

`fortune_engine.py` 是一个**全本地、离线可用**的中国传统命理计算引擎，输出每日运势 JSON 数据。整合了以下模块：

| 模块 | 功能 | 精度级别 |
|------|------|----------|
| 干支纪法 | 年/月/日干支、六十甲子 | 公式推算 |
| 纳音五行 | 纳音取象、五行提取 | 查表 |
| 十二建星 | 建除十二神 + 宜忌 | 月建公式 |
| 黄道黑道 | 十二时辰值神 | 日支起青龙 |
| 吉神方位 | 喜神/财神/福神方位 | 日干口诀 |
| 冲煞 | 地支六冲 + 三合煞方 | 地支冲合 |
| 二十八宿 | 28宿值日 + 宜忌 | 28天循环 |
| 月相计算 | 亮度/相位角/宜忌/能量 | 天文级（skyfield） |
| 节日系统 | 9大传统节日检测 | 农历/公历双轨 |
| 八字四柱 | 年/月/日/时柱 + 日主 | 五虎遁 + 五鼠遁 |
| 生肖配对 | 三合/六冲 + 性格特质 | 传统生肖学 |
| 综合评分 | 五维评分 + 签等级 | 加权算法 |

---

## 安装与依赖

```bash
# 必需依赖
pip install lunardate

# 天文计算（提升月相精度至天文级，可选）
pip install skyfield ephem
```

**依赖说明：**

| 依赖 | 用途 | 是否必需 |
|------|------|----------|
| [`lunardate`](https://pypi.org/project/lunardate/) | 农历转换（SolarDate → LunarDate） | ✅ 必需 |
| [`skyfield`](https://pypi.org/project/skyfield/) | [JPL DE421](https://ssd.jpl.nasa.gov/planets/eph_export.html) 天文星历（月相最高精度） | 可选（fallback到 ephem/算法） |
| [`ephem`](https://pypi.org/project/ephem/) | PyEphem 天文库（月相中等精度） | 可选（fallback到简化公式） |

**首次运行：** skyfield 会自动下载 17MB 的 [`de421.bsp`](https://ssd.jpl.nasa.gov/planets/eph_export.html) JPL星历文件，缓存后完全离线。

---

## 算法清单与出处

### 一、天干地支基础

| 算法内容 | 出处 | 原文/链接 |
|----------|------|-----------|
| 十天干 | 《尔雅·释天》 | [ctext.org](https://ctext.org/er-ya/shi-tian) |
| 十二地支 | 《淮南子·天文训》 | [ctext.org](https://ctext.org/huainanzi/tian-wen-xun) |
| 十二生肖 | 《论衡·物势》 | [ctext.org](https://ctext.org/lunheng/wu-shi) |
| 地支时辰 | 《汉书·律历志》 | [ctext.org](https://ctext.org/han-shu/lu-li-zhi) |

### 二、干支五行与阴阳

| 算法内容 | 出处 | 原文/链接 |
|----------|------|-----------|
| 天干五行 | 《三命通会·卷一》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=755049) |
| 地支五行 | 《渊海子平·卷一》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=651645) |
| 天干阴阳 | 《三命通会·卷一》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=755049) |

### 三、六十甲子纳音五行

| 算法内容 | 出处 | 原文/链接 |
|----------|------|-----------|
| 纳音取象 | 《三命通会·论纳音取象》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=755049) — 卷一 |
| 六十甲子循环 | 《黄帝内经·六微旨大论》 | [ctext.org](https://ctext.org/huangdi-neijing/liu-wei-zhi-da-lun) |
| 纳音五行提取 | 派生算法 | — |

**30组纳音：** 海中金 → 炉中火 → 大林木 → 路旁土 → 剑锋金 → 山头火 → 涧下水 → 城头土 → 白蜡金 → 杨柳木 → 泉中水 → 屋上土 → 霹雳火 → 松柏木 → 长流水 → 砂中金 → 山下火 → 平地木 → 壁上土 → 金箔金 → 覆灯火 → 天河水 → 大驿土 → 钗钏金 → 桑柘木 → 大溪水 → 砂中土 → 天上火 → 石榴木 → 大海水

### 四、十二建星（建除十二神）

| 算法内容 | 出处 | 原文/链接 |
|----------|------|-----------|
| 建星排法 | 《协纪辨方书》卷四 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=896741) |
| 建星宜忌 | 《协纪辨方书》卷四 / 《玉匣记》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=896741) |
| 建星吉凶 | 《协纪辨方书》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=896741) |

**月建起建口诀：** 正月建寅（立春）、二月建卯（惊蛰）……十二月建丑（小寒），以月支对应日支序位推算建星。

### 五、黄道黑道十二神

| 算法内容 | 出处 | 原文/链接 |
|----------|------|-----------|
| 黄道黑道起青龙 | 《协纪辨方书》卷三 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=896741) |
| 十二值神 | 《星历考原》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=962898) |

**起青龙口诀：**
> 子午青龙起申位，丑未青龙起戌位，寅申青龙起子位，卯酉青龙起寅位，辰戌青龙起辰位，巳亥青龙起午位。

### 六、吉神方位

| 算法内容 | 出处 | 原文/链接 |
|----------|------|-----------|
| 喜神方位 | 《选择宗镜》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=444347) |
| 财神方位 | 《协纪辨方书》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=896741) |
| 福神方位 | 《选择宗镜》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=444347) |

**喜神口诀：**
> 甲己在艮乙庚乾，丙辛坤位喜神安。壬在离宫癸在巽，丁壬正北是喜源。

**财神口诀：**
> 甲艮乙坤丙丁兑，戊己财神坐坎位。庚辛正东壬癸南，此是财神正方位。

### 七、每日冲煞

| 算法内容 | 出处 | 原文/链接 |
|----------|------|-----------|
| 地支六冲 | 《渊海子平·卷一》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=651645) |
| 三合煞方 | 《三命通会·卷一》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=755049) |
| 冲煞生肖 | 派生 | — |

### 八、二十八宿（Lunar Mansions）🆕

| 算法内容 | 出处 | 原文/链接 |
|----------|------|-----------|
| 二十八宿名 | 《史记·天官书》 | [ctext.org](https://ctext.org/shiji/tian-guan-shu) |
| 二十八宿值日 | 《协纪辨方书》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=896741) |
| 二十八宿宜忌 | 《星历考原》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=962898) |

**基准日期：** 2000年1月7日（甲子日）值**虛宿**（第二十宿，索引13），以此为锚点，每28天循环推算出当日值宿。

**四象分布：**
- 🐉 东方青龙：角亢氐房心尾箕（7宿）
- 🐢 北方玄武：斗牛女虛危室壁（7宿）
- 🐅 西方白虎：奎娄胃昴毕觜参（7宿）
- 🐦 南方朱雀：井鬼柳星张翼轸（7宿）

### 九、月相计算 🆕（天文学级）

| 算法内容 | 出处 | 原文/链接 |
|----------|------|-----------|
| Skyfield 星历 | NASA JPL DE421 | [ssd.jpl.nasa.gov](https://ssd.jpl.nasa.gov/planets/eph_export.html) |
| PyEphem | Meeus 天文算法 | [《Astronomical Algorithms》](https://www.willbell.com/math/mc1.htm) — Jean Meeus |
| 简化公式 | 朔望月 29.530588853 天 | [Wikipedia: Lunar month](https://en.wikipedia.org/wiki/Lunar_month) |
| 月相宜忌 | 传统文化 + 现代月亮学 | — |

**三级fallback机制：**
```
skyfield (JPL星历) → ephem (天文库) → 简化公式 (纯算法)
   精度最高              精度中等          精度最低
```

### 十、节日系统 🆕

| 算法内容 | 出处 | 原文/链接 |
|----------|------|-----------|
| 节日数据库 | 中国传统节日 | 参见 [Wikipedia: 中国节日](https://zh.wikipedia.org/wiki/%E4%B8%AD%E5%9B%BD%E8%8A%82%E6%97%A5) |
| 农历节日检测 | 农历日期匹配 | — |
| 公历节日检测 | 公历日期匹配 | 清明约在 [4月4-6日](https://zh.wikipedia.org/wiki/%E6%B8%85%E6%98%8E) |
| 下一节日推算 | 顺序遍历（最多365天） | — |

**覆盖节日：**

| 节日 | 农历 | 传统 | 食物 |
|------|------|------|------|
| 春节 | 正月初一 | 团圆饭、放鞭炮、发红包 | 饺子、鱼、年糕 |
| 元宵节 | 正月十五 | 赏花灯、猜灯谜 | 汤圆、元宵 |
| 清明节 | 公历4月4日± | 扫墓祭祖、踏青 | 青团 |
| 端午节 | 五月初五 | 赛龙舟、挂艾草 | 粽子 |
| 七夕 | 七月初七 | 许愿、观星 | 巧果 |
| 中秋节 | 八月十五 | 赏月、团圆 | 月饼、柚子 |
| 重阳节 | 九月初九 | 登高、赏菊 | 菊花酒、重阳糕 |
| 腊八节 | 十二月初八 | 祈福、祭祖 | 腊八粥 |
| 除夕 | 十二月三十 | 守岁、贴春联 | 年夜饭 |

### 十一、八字四柱 🆕

| 算法内容 | 出处 | 原文/链接 |
|----------|------|-----------|
| 日柱推算 | 《三命通会·卷一》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=755049) |
| 月柱推算（五虎遁） | 《渊海子平·卷一》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=651645) |
| 时柱推算（五鼠遁） | 《渊海子平·卷一》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=651645) |
| 年柱推算 | 《三命通会·卷一》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=755049) |
| 日主（日干） | 《渊海子平·论日主》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=651645) |
| 五行分布分析 | 《三命通会·论五行》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=755049) |

**五虎遁口诀：** 甲己之年丙作首，乙庚之岁戊为头，丙辛必定寻庚起，丁壬壬位顺行流，若问戊癸何方发，甲寅之上好追求。

**五鼠遁口诀：** 甲己还加甲，乙庚丙作初，丙辛从戊起，丁壬庚子居，戊癸何方发，壬子是真途。

### 十二、生肖配对 🆕

| 算法内容 | 出处 | 原文/链接 |
|----------|------|-----------|
| 生肖三合 | 传统生肖学 | [Wikipedia: 生肖](https://zh.wikipedia.org/wiki/%E7%94%9F%E8%82%96) |
| 生肖六冲 | 《渊海子平》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=651645) |
| 生肖性格 | 传统生肖文化 | [Wikipedia: 生肖](https://zh.wikipedia.org/wiki/%E7%94%9F%E8%82%96) |

---

## 输出格式

```json
{
  "date": "2026-07-24",
  "year_gan_zhi": "丙午",
  "month_gan_zhi": "乙未",
  "day_gan_zhi": "己亥",
  "nayin": "平地木",
  "shengxiao": "马",
  "jianchu": "定",
  "jianchu_jixiong": "黄道吉",
  "jishen_fangwei": {"喜神": "东北", "财神": "正北", "福神": "东南"},
  "jishi": ["丑时(01:00-03:00)·玉堂", ...],
  "chongsha": {"冲": "蛇(巳)", "煞": "西"},
  "xiu": {"宿名": "参", "方位": "西", "吉凶": "吉", ...},          // 🆕 v2.0
  "moon_phase": {"月相": "蛾眉月(盈)", "亮度": 0.203, ...},       // 🆕 v2.0
  "festival": null,                                               // 🆕 v2.0
  "day_master": {"日干": "己", "日主五行": "土", ...},            // 🆕 v2.0
  "zodiac_compat": {"最佳配对": ["虎","狗","羊"], ...},           // 🆕 v2.0
  "personal_bazi": null,                                          // 🆕 v2.0
  "overall": 85,
  "career": 82, "wealth": 78, "love": 91, "health": 76, "social": 88,
  "lucky_color": "青绿色",
  "lucky_num": 6,
  "sign_grade": "上签"
}
```

---

## 使用示例

### 1. 命令行

```bash
python3 fortune_engine.py
```

### 2. Python API

```python
from fortune_engine import calculate_fortune, calculate_bazi, generate_tags
from datetime import datetime

# 今日运势
result = calculate_fortune()
print(result["day_gan_zhi"])              # "己亥"
print(result["xiu"]["宿名"])              # "参"
print(result["moon_phase"]["月相"])        # "蛾眉月(盈)"

# 指定日期
result = calculate_fortune("2026-08-15")

# 带生日的运势（含个人八字）
result = calculate_fortune(birth_date=datetime(1998, 6, 15, 12, 0))
bazi = result["personal_bazi"]
print(f"{bazi['年柱']} {bazi['月柱']} {bazi['日柱']} {bazi['时柱']}")
# "戊寅 庚午 癸巳 戊午"

# 纯八字计算
bazi = calculate_bazi(datetime(1998, 6, 15, 12, 0))
print(bazi["日主说明"])   # "日主癸水，代表自身核心"
print(bazi["五行分布"])   # {"金":1, "木":1, "水":1, "火":3, "土":2}

# 节日查询
from fortune_engine import get_today_festival, get_next_festival
nf = get_next_festival()
print(f"下一个节日: {nf['节日']['名称']}，{nf['距今天数']}天后")

# 标签生成（14个标签）
tags = generate_tags(result)
for t in tags:
    print(f"{t['icon']} {t['label']}: {t['value']}")
```

---

## 模块架构

```
fortune_engine.py v2.0
├── 一 天干地支基础          TIAN_GAN, DI_ZHI, SHENG_XIAO, ZHI_TIME
├── 二 干支五行属性          GAN_WUXING, GAN_YINYANG, ZHI_YINYANG
├── 三 六十甲子纳音          NAYIN_TABLE, get_nayin(), get_nayin_wuxing()
├── 四 十二建星              JIANCHU, JIANCHU_YIJI, get_jianchu()
├── 五 黄道黑道十二神        HUANGDAO_SHISHEN, get_huangdao_shishen(), get_jishi()
├── 六 吉神方位              get_jishen_fangwei()
├── 七 每日冲煞              get_chongsha()
├── 八 天干五合/地支六合     GAN_WUHE, ZHI_LIUHE
├── 九 二十八宿 🆕           XIU_28, get_xiu()
├── 十 月相计算 🆕           get_moon_phase() [skyfield > ephem > fallback]
├── 十一 节日系统 🆕         get_today_festival(), get_next_festival()
├── 十二 生肖配对 🆕         ZODIAC_TRAITS, ZODIAC_BEST_MATCH, ZODIAC_CLASH
├── 十三 八字四柱 🆕         calculate_bazi(), calculate_day_master()
├── 十四 综合运势            calculate_fortune()
├── 十五 评分算法            calculate_scores()
└── 十六 标签生成            generate_tags()
```

---

## 整合来源

| 来源 | 作者 | 整合内容 | 操作 |
|------|------|----------|------|
| [`lunar-mcp-server`](https://github.com/AngusHsu/lunar-mcp-server) | [AngusHsu](https://github.com/AngusHsu) | 八字四柱、二十八宿、月相、节日、生肖配对 | 取算法逻辑，用自有基准日期重写 |
| [`lunar-calendar-mcp`](https://github.com/RaoHai/lunar-calendar-mcp) | [RaoHai](https://github.com/RaoHai) | — | 跳过（仅2工具，功能不完备） |
| [JPL DE421](https://ssd.jpl.nasa.gov/planets/eph_export.html) | NASA JPL | 天文星历数据 | 通过 [skyfield](https://github.com/skyfielders/python-skyfield) 自动下载 |

> **整合原则：** 优先用自有基准日期（2000-01-07 甲子日）推算，确保干支纪法一致。宜忌/黄道/建星继续使用《协纪辨方书》算法，不替换。

---

## 参考资料

| 古籍 | 在线阅读 | 说明 |
|------|----------|------|
| 《协纪辨方书》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=896741) | 清·允禄等撰，选择学集大成 |
| 《三命通会》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=755049) | 明·万民英撰，八字命理经典 |
| 《渊海子平》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=651645) | 宋·徐子平撰，子平八字始祖 |
| 《星历考原》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=962898) | 清·李光地等撰，天文历算 |
| 《选择宗镜》 | [ctext.org](https://ctext.org/wiki.pl?if=en&res=444347) | 明·选择学要籍 |
| 《史记·天官书》 | [ctext.org](https://ctext.org/shiji/tian-guan-shu) | 西汉·司马迁，天文星官体系 |
| 《淮南子·天文训》 | [ctext.org](https://ctext.org/huainanzi/tian-wen-xun) | 西汉·刘安，干支系统起源 |
| 《论衡·物势》 | [ctext.org](https://ctext.org/lunheng/wu-shi) | 东汉·王充，生肖最早记载之一 |
| 《汉书·律历志》 | [ctext.org](https://ctext.org/han-shu/lu-li-zhi) | 东汉·班固，官方历法 |
| 《尔雅·释天》 | [ctext.org](https://ctext.org/er-ya/shi-tian) | 最早词典，天干系统化 |

**现代参考：**

| 资源 | 链接 | 说明 |
|------|------|------|
| NASA JPL 行星历表 | [ssd.jpl.nasa.gov](https://ssd.jpl.nasa.gov/planets/eph_export.html) | DE421 星历，月相最高精度来源 |
| Skyfield 天文库 | [github.com/skyfielders](https://github.com/skyfielders/python-skyfield) | Python 天文计算库 |
| 《Astronomical Algorithms》 | [willbell.com](https://www.willbell.com/math/mc1.htm) | Jean Meeus 著，天文算法权威 |
| Wikipedia: 农历 | [zh.wikipedia.org](https://zh.wikipedia.org/wiki/%E5%86%9C%E5%8E%86) | 中国农历概述 |
| Wikipedia: 中国节日 | [zh.wikipedia.org](https://zh.wikipedia.org/wiki/%E4%B8%AD%E5%9B%BD%E8%8A%82%E6%97%A5) | 节日日期与习俗 |
| Wikipedia: 生肖 | [zh.wikipedia.org](https://zh.wikipedia.org/wiki/%E7%94%9F%E8%82%96) | 生肖体系详解 |

---

## 许可

MIT License

---

*授时于天，遵法于古。算法皆有据，精度可溯源。*
