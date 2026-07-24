#!/usr/bin/env python3
"""
中国命理运势计算引擎 v2.0
整合内容：
  - 原有：干支/纳音/十二建星/黄道黑道/吉神方位/冲煞/评分（v1.0 保留）
  - 新增：二十八宿/月相(天文)/节日/八字四柱/生肖配对 (整合自 lunar-mcp-server)
所有算法均有据可查，标注出处
"""
from datetime import datetime, timedelta
from pathlib import Path
import json
import math
from lunardate import LunarDate

# 尝试加载天文库
try:
    from skyfield.api import load as skyfield_load
    SKYFIELD_AVAILABLE = True
except ImportError:
    SKYFIELD_AVAILABLE = False

try:
    import ephem
    EPHEM_AVAILABLE = True
except ImportError:
    EPHEM_AVAILABLE = False

SCRIPT_DIR = Path(__file__).parent

# ============================================================
# 一、天干地支基础数据
# 【出处】《尔雅·释天》《淮南子·天文训》
# ============================================================

TIAN_GAN = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
DI_ZHI = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
SHENG_XIAO = ["鼠","牛","虎","兔","龙","蛇","马","羊","猴","鸡","狗","猪"]

ZHI_TIME = {
    "子":"23:00-01:00","丑":"01:00-03:00","寅":"03:00-05:00",
    "卯":"05:00-07:00","辰":"07:00-09:00","巳":"09:00-11:00",
    "午":"11:00-13:00","未":"13:00-15:00","申":"15:00-17:00",
    "酉":"17:00-19:00","戌":"19:00-21:00","亥":"21:00-23:00"
}

# ============================================================
# 二、干支五行属性
# 【出处】《三命通会》《渊海子平》
# ============================================================

GAN_WUXING = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水"}
ZHI_WUXING = {"子":"水","丑":"土","寅":"木","卯":"木","辰":"土","巳":"火","午":"火","未":"土","申":"金","酉":"金","戌":"土","亥":"水"}
GAN_YINYANG = {"甲":"阳","乙":"阴","丙":"阳","丁":"阴","戊":"阳","己":"阴","庚":"阳","辛":"阴","壬":"阳","癸":"阴"}
ZHI_YINYANG = {"子":"阳","丑":"阴","寅":"阳","卯":"阴","辰":"阳","巳":"阴","午":"阳","未":"阴","申":"阳","酉":"阴","戌":"阳","亥":"阴"}

# ============================================================
# 三、六十甲子纳音五行
# 【出处】《三命通会·论纳音取象》
# ============================================================

NAYIN_TABLE = [
    "海中金","海中金","炉中火","炉中火","大林木","大林木",
    "路旁土","路旁土","剑锋金","剑锋金","山头火","山头火",
    "涧下水","涧下水","城头土","城头土","白蜡金","白蜡金",
    "杨柳木","杨柳木","泉中水","泉中水","屋上土","屋上土",
    "霹雳火","霹雳火","松柏木","松柏木","长流水","长流水",
    "砂中金","砂中金","山下火","山下火","平地木","平地木",
    "壁上土","壁上土","金箔金","金箔金","覆灯火","覆灯火",
    "天河水","天河水","大驿土","大驿土","钗钏金","钗钏金",
    "桑柘木","桑柘木","大溪水","大溪水","砂中土","砂中土",
    "天上火","天上火","石榴木","石榴木","大海水","大海水"
]

def get_nayin(gan, zhi):
    """根据天干地支查纳音五行"""
    JIAZI = {}
    for i in range(60):
        g = TIAN_GAN[i % 10]
        z = DI_ZHI[i % 12]
        JIAZI[f"{g}{z}"] = i
    key = f"{gan}{zhi}"
    seq = JIAZI.get(key, 0)
    return NAYIN_TABLE[seq]

def get_nayin_wuxing(nayin):
    """从纳音名称提取五行"""
    for wx in ["金","木","水","火","土"]:
        if wx in nayin:
            return wx
    return "土"

# ============================================================
# 四、十二建星（建除十二神）
# 【出处】《协纪辨方书》卷四
# ============================================================

JIANCHU = ["建","除","满","平","定","执","破","危","成","收","开","闭"]
JIANCHU_JIXIONG = {
    "建": "黑道凶","除": "黄道吉","满": "黑道凶","平": "黑道凶",
    "定": "黄道吉","执": "黄道吉","破": "黑道凶","危": "黄道凶",
    "成": "黄道吉","收": "黑道凶","开": "黄道吉","闭": "黑道凶"
}

JIANCHU_YIJI = {
    "建": {"宜": ["出行","上任","会友","上书","见工"],"忌": ["动土","开仓","掘井","乘船","新船下水"]},
    "除": {"宜": ["除服","疗病","避邪","出行","嫁娶"],"忌": ["求官","上任","开张","搬家","探病"]},
    "满": {"宜": ["祭祀","祈福","结亲","开市","交易"],"忌": ["服药","求医","栽种","下葬","迁移"]},
    "平": {"宜": ["修饰","涂泥","安葬","造畜稠","平治道涂"],"忌": ["出行","移居","开市","嫁娶","掘井"]},
    "定": {"宜": ["祭祀","祈福","嫁娶","造屋","装修"],"忌": ["出行","诉讼","上任","交易","栽种"]},
    "执": {"宜": ["捕捉","渔猎","祭祀","祈福","嫁娶"],"忌": ["出行","移居","开市","交易","求财"]},
    "破": {"宜": ["破屋","坏垣","求医","治病"],"忌": ["嫁娶","签约","交易","搬家","出行"]},
    "危": {"宜": ["祭祀","祈福","安葬","入殓","破土"],"忌": ["出行","嫁娶","登高","入宅","开市"]},
    "成": {"宜": ["祈福","入学","开市","嫁娶","求医"],"忌": ["诉讼","安葬","动土","出行","词讼"]},
    "收": {"宜": ["祭祀","求财","收债","收财","入宅"],"忌": ["开市","出行","嫁娶","安葬","动土"]},
    "开": {"宜": ["开市","交易","出行","上任","嫁娶"],"忌": ["动土","安葬","破屋","坏垣","掘井"]},
    "闭": {"宜": ["祭祀","安葬","修补","塞穴","断蚁"],"忌": ["开市","出行","嫁娶","入宅","上任"]}
}

def get_jianchu(month_zhi_idx, day_zhi_idx):
    """计算当日十二建星"""
    offset = (day_zhi_idx - month_zhi_idx) % 12
    return JIANCHU[offset]

# ============================================================
# 五、黄道黑道十二神
# 【出处】《协纪辨方书》卷三
# ============================================================

HUANGDAO_SHISHEN = ["青龙","明堂","天刑","朱雀","金匮","天德","白虎","玉堂","天牢","玄武","司命","勾陈"]
HUANGDAO_JIXIONG = ["吉","吉","凶","凶","吉","吉","凶","吉","凶","凶","吉","凶"]

QINGLONG_START = {
    "子":8,"午":8,
    "丑":10,"未":10,
    "寅":0,"申":0,
    "卯":2,"酉":2,
    "辰":4,"戌":4,
    "巳":6,"亥":6
}

def get_huangdao_shishen(day_zhi):
    """计算当日十二时辰的黄道黑道神"""
    start = QINGLONG_START[day_zhi]
    result = []
    for i in range(12):
        god_idx = (start + i) % 12
        result.append({
            "时辰": DI_ZHI[i],
            "时间": ZHI_TIME[DI_ZHI[i]],
            "值神": HUANGDAO_SHISHEN[god_idx],
            "吉凶": HUANGDAO_JIXIONG[god_idx]
        })
    return result

def get_jishi(day_zhi):
    """获取今日吉时"""
    shishen = get_huangdao_shishen(day_zhi)
    jishi = []
    for s in shishen:
        if s["吉凶"] == "吉":
            jishi.append(f"{s['时辰']}时({s['时间']})·{s['值神']}")
    return jishi

# ============================================================
# 六、吉神方位
# 【出处】《协纪辨方书》《选择宗镜》
# ============================================================

XISHEN_FANGWEI = {
    "甲":"东北","己":"东北","乙":"西北","庚":"西北",
    "丙":"西南","辛":"西南","壬":"正南","丁":"正南",
    "癸":"东南","戊":"正东"
}

CAISHEN_FANGWEI = {
    "甲":"东北","乙":"西南","丙":"正西","丁":"正西",
    "戊":"正北","己":"正北","庚":"正东","辛":"正东",
    "壬":"正南","癸":"正南"
}

FUSHEN_FANGWEI = {
    "甲":"东南","己":"东南","乙":"西北","庚":"西北",
    "丙":"西南","辛":"西南","壬":"正北","丁":"正北",
    "癸":"西北","戊":"东北"
}

def get_jishen_fangwei(day_gan):
    """根据日干获取吉神方位"""
    return {
        "喜神": XISHEN_FANGWEI.get(day_gan, "东南"),
        "财神": CAISHEN_FANGWEI.get(day_gan, "正南"),
        "福神": FUSHEN_FANGWEI.get(day_gan, "正东"),
    }

# ============================================================
# 七、每日冲煞
# 【出处】《协纪辨方书》
# ============================================================

ZHI_CHONG = {
    "子":"午","丑":"未","寅":"申","卯":"酉","辰":"戌","巳":"亥",
    "午":"子","未":"丑","申":"寅","酉":"卯","戌":"辰","亥":"巳"
}

SAN_HE = {
    "申子辰":"水","寅午戌":"火","巳酉丑":"金","亥卯未":"木"
}

SHA_FANG = {
    "子":"南","丑":"东","寅":"北","卯":"西","辰":"南","巳":"东",
    "午":"北","未":"西","申":"南","酉":"东","戌":"北","亥":"西"
}

def get_chongsha(day_zhi, day_gan):
    """计算今日冲煞"""
    chong_zhi = ZHI_CHONG.get(day_zhi, "")
    chong_shengxiao = SHENG_XIAO[DI_ZHI.index(chong_zhi)] if chong_zhi else ""
    sha_fang = SHA_FANG.get(day_zhi, "")
    return {"冲": f"{chong_shengxiao}({chong_zhi})", "煞": sha_fang}

# ============================================================
# 八、天干五合、地支六合/三合/三会
# 【出处】《渊海子平》《三命通会》
# ============================================================

GAN_WUHE = {"甲己":"土","乙庚":"金","丙辛":"水","丁壬":"木","戊癸":"火"}
ZHI_LIUHE = {"子丑":"土","寅亥":"木","卯戌":"火","辰酉":"金","巳申":"水","午未":"火"}

# ============================================================
# 九、二十八宿（Lunar Mansions）
# 【出处】《协纪辨方书》《星历考原》
# 二十八宿值日，28天一个循环
# 【基准】2000-01-07 甲子日 值宿：虛（第20宿）
# ============================================================

XIU_28 = [
    # 东方青龙（角亢氐房心尾箕） 0-6
    "角","亢","氐","房","心","尾","箕",
    # 北方玄武（斗牛女虛危室壁） 7-13
    "斗","牛","女","虛","危","室","壁",
    # 西方白虎（奎娄胃昴毕觜参） 14-20
    "奎","娄","胃","昴","毕","觜","参",
    # 南方朱雀（井鬼柳星张翼轸） 21-27
    "井","鬼","柳","星","张","翼","轸"
]

XIU_FANGWEI = {
    "角":"东","亢":"东","氐":"东","房":"东","心":"东","尾":"东","箕":"东",
    "斗":"北","牛":"北","女":"北","虛":"北","危":"北","室":"北","壁":"北",
    "奎":"西","娄":"西","胃":"西","昴":"西","毕":"西","觜":"西","参":"西",
    "井":"南","鬼":"南","柳":"南","星":"南","张":"南","翼":"南","轸":"南"
}

XIU_JIXIONG = {
    "角":"吉","亢":"凶","氐":"吉","房":"吉","心":"凶","尾":"吉","箕":"凶",
    "斗":"吉","牛":"凶","女":"凶","虛":"凶","危":"凶","室":"吉","壁":"吉",
    "奎":"凶","娄":"吉","胃":"吉","昴":"凶","毕":"吉","觜":"凶","参":"吉",
    "井":"吉","鬼":"凶","柳":"凶","星":"吉","张":"吉","翼":"凶","轸":"吉"
}

XIU_YIJI = {
    "角": {"宜":["嫁娶","修造","出行","入宅"],"忌":[None]},
    "亢": {"宜":["祭祀","祈福"],"忌":["嫁娶","开市","出行"]},
    "氐": {"宜":["嫁娶","修造","开市","出行"],"忌":[None]},
    "房": {"宜":["嫁娶","祈福","入学","开市"],"忌":[None]},
    "心": {"宜":["祭祀"],"忌":["嫁娶","出行","开市","修造"]},
    "尾": {"宜":["嫁娶","开市","修造","出行"],"忌":[None]},
    "箕": {"宜":["祭祀"],"忌":["嫁娶","开张","出行"]},
    "斗": {"宜":["嫁娶","开市","出行","祈福"],"忌":[None]},
    "牛": {"宜":["祭祀"],"忌":["嫁娶","开市","出行","入宅"]},
    "女": {"宜":["祭祀"],"忌":["嫁娶","开市","出行","修造"]},
    "虛": {"宜":["祭祀","祈福"],"忌":["嫁娶","开市","出行"]},
    "危": {"宜":["祭祀"],"忌":["嫁娶","出行","开市","修造"]},
    "室": {"宜":["嫁娶","开市","修造","入宅"],"忌":[None]},
    "壁": {"宜":["嫁娶","修造","祭祀","入学"],"忌":[None]},
    "奎": {"宜":["祭祀"],"忌":["嫁娶","开市","出行"]},
    "娄": {"宜":["嫁娶","修造","开市","出行"],"忌":[None]},
    "胃": {"宜":["嫁娶","开市","修造","出行"],"忌":[None]},
    "昴": {"宜":["祭祀"],"忌":["嫁娶","开市","出行"]},
    "毕": {"宜":["嫁娶","修造","出行","开市"],"忌":[None]},
    "觜": {"宜":["祭祀"],"忌":["嫁娶","出行"]},
    "参": {"宜":["嫁娶","开市","修造","出行"],"忌":[None]},
    "井": {"宜":["嫁娶","开市","修造","祈福"],"忌":[None]},
    "鬼": {"宜":["祭祀"],"忌":["嫁娶","开市","出行","入宅"]},
    "柳": {"宜":["祭祀"],"忌":["嫁娶","开市","出行"]},
    "星": {"宜":["嫁娶","祈福","开市","修造"],"忌":[None]},
    "张": {"宜":["嫁娶","开市","修造","出行"],"忌":[None]},
    "翼": {"宜":["祭祀"],"忌":["嫁娶","出行","开市"]},
    "轸": {"宜":["嫁娶","修造","出行","入学"],"忌":[None]},
}

def get_xiu(date):
    """计算当日二十八宿
    【基准】2000-01-07 = 甲子日 = 虛宿(索引13)
    28天一个循环
    """
    base = datetime(2000, 1, 7)
    days = (date - base).days if isinstance(date, datetime) else (datetime.strptime(str(date)[:10], "%Y-%m-%d") - base).days
    idx = (days + 13) % 28  # 虛索引13
    return {
        "宿名": XIU_28[idx],
        "方位": XIU_FANGWEI[XIU_28[idx]],
        "吉凶": XIU_JIXIONG[XIU_28[idx]],
        "宜": XIU_YIJI[XIU_28[idx]]["宜"],
        "忌": XIU_YIJI[XIU_28[idx]]["忌"],
    }

# ============================================================
# 十、月相计算（天文学级）
# 使用 skyfield 或 ephem，fallback 到简化公式
# 【出处】NASA JPL DE421 星历 + Meeus 天文算法
# ============================================================

# 月相名称（中文）
MOON_PHASE_CN = {
    "New Moon": "朔月",
    "Waxing Crescent": "蛾眉月(盈)",
    "First Quarter": "上弦月",
    "Waxing Gibbous": "盈凸月",
    "Full Moon": "望月",
    "Waning Gibbous": "亏凸月",
    "Third Quarter": "下弦月",
    "Waning Crescent": "蛾眉月(亏)"
}

MOON_INFLUENCE = {
    "New Moon":       {"宜":["新开始","播种","许愿","冥想"],"忌":["收割","重大决定","手术"],"能量":"内省、新生", "吉凶":"平"},
    "Waxing Crescent": {"宜":["启动项目","学习","建设","养生"],"忌":["放弃","结束关系","大手术"],"能量":"生长、积累", "吉凶":"吉"},
    "First Quarter":  {"宜":["做决定","行动","克服障碍"],"忌":["被动等待"],"能量":"主动、挑战", "吉凶":"中"},
    "Waxing Gibbous": {"宜":["完善","调整","改进","打磨"],"忌":["全新开始","重大变动"],"能量":"精进、优化", "吉凶":"吉"},
    "Full Moon":      {"宜":["完成","庆祝","显化","情感释放"],"忌":["开始新项目","重大人生改变"],"能量":"圆满、强烈", "吉凶":"大吉"},
    "Waning Gibbous": {"宜":["感恩","分享","教学"],"忌":["囤积","贪婪"],"能量":"分享、回馈", "吉凶":"吉"},
    "Third Quarter":  {"宜":["放下","原谅","断舍离"],"忌":["执着","开创新局"],"能量":"释放、原谅", "吉凶":"中"},
    "Waning Crescent": {"宜":["休息","反思","清理","准备"],"忌":["高强度活动","重大承诺"],"能量":"臣服、休息", "吉凶":"平"},
}

def _moon_phase_skyfield(dt):
    """使用 skyfield 计算月相（最高精度）"""
    ts = skyfield_load.timescale()
    eph = skyfield_load("de421.bsp")
    earth = eph["earth"]
    moon = eph["moon"]
    sun = eph["sun"]

    t = ts.utc(dt.year, dt.month, dt.day, dt.hour, dt.minute)
    earth_moon = earth.at(t).observe(moon)
    earth_sun = earth.at(t).observe(sun)
    phase_angle = earth_moon.separation_from(earth_sun).degrees
    illumination = (1 + math.cos(math.radians(phase_angle))) / 2
    return illumination, phase_angle

def _moon_phase_ephem(dt):
    """使用 ephem 计算月相（中等精度）"""
    obs = ephem.Observer()
    obs.date = dt.strftime("%Y/%m/%d %H:%M")
    moon = ephem.Moon()
    moon.compute(obs)
    # ephem.moon_phase 返回 0=新月, 0.5=满月
    phase_pct = moon.moon_phase
    illumination = abs(math.sin(phase_pct * math.pi))
    phase_angle = phase_pct * 360
    return illumination, phase_angle

def _moon_phase_fallback(dt):
    """简化月相计算（fallback）"""
    # 以 2000-01-06 18:14 为已知新月
    new_moon = datetime(2000, 1, 6, 18, 14)
    days_since = (dt - new_moon).total_seconds() / 86400
    phase_pct = (days_since % 29.530588853) / 29.530588853
    phase_angle = phase_pct * 360
    illumination = (1 + math.cos(math.radians(phase_angle))) / 2
    return illumination, phase_angle

def _phase_name(illumination, phase_angle):
    """根据亮度和相位角判断月相名称"""
    if illumination < 0.01:
        return "New Moon"
    elif illumination < 0.25:
        return "Waxing Crescent" if phase_angle < 180 else "Waning Crescent"
    elif illumination < 0.75:
        if abs(illumination - 0.5) < 0.1:
            return "First Quarter" if phase_angle < 180 else "Third Quarter"
        return "Waxing Gibbous" if phase_angle < 180 else "Waning Gibbous"
    elif illumination < 0.99:
        return "Waxing Gibbous" if phase_angle < 180 else "Waning Gibbous"
    else:
        return "Full Moon"

def get_moon_phase(date=None):
    """获取指定日期的月相信息
    返回：月相英文名、中文名、亮度、相位角、宜忌、能量
    """
    if date is None:
        date = datetime.now()
    elif isinstance(date, str):
        date = datetime.strptime(date[:10], "%Y-%m-%d")

    try:
        if SKYFIELD_AVAILABLE:
            illumination, phase_angle = _moon_phase_skyfield(date)
        elif EPHEM_AVAILABLE:
            illumination, phase_angle = _moon_phase_ephem(date)
        else:
            illumination, phase_angle = _moon_phase_fallback(date)
    except Exception:
        illumination, phase_angle = _moon_phase_fallback(date)

    name = _phase_name(illumination, phase_angle)
    cn_name = MOON_PHASE_CN.get(name, name)
    influence = MOON_INFLUENCE.get(name, MOON_INFLUENCE["New Moon"])

    # 农历日数
    lunar = LunarDate.fromSolarDate(date.year, date.month, date.day)

    return {
        "月相": cn_name,
        "月相英文": name,
        "亮度": round(illumination, 3),
        "相位角": round(phase_angle, 1),
        "农历日": lunar.day,
        "宜": influence["宜"],
        "忌": influence["忌"],
        "能量": influence["能量"],
        "吉凶": influence["吉凶"],
    }

# ============================================================
# 十一、中国节日系统
# 【出处】传统节日数据库
# ============================================================

CHINESE_FESTIVALS = {
    "春节":      {"lunar":"1-1",  "duration":15, "significance":"农历新年，最重要的传统节日",
                  "传统":["团圆饭","放鞭炮","发红包","拜年"],"食物":["饺子","鱼","年糕"]},
    "元宵节":    {"lunar":"1-15", "duration":1,  "significance":"春节尾声，首个月圆之夜",
                  "传统":["赏花灯","猜灯谜","舞龙舞狮"],"食物":["汤圆","元宵"]},
    "清明节":    {"solar":"04-04", "duration":1,  "significance":"扫墓祭祖，缅怀先人",
                  "传统":["扫墓","祭祖","踏青","放风筝"],"食物":["青团"]},
    "端午节":    {"lunar":"5-5",  "duration":1,  "significance":"纪念屈原，驱瘟避邪",
                  "传统":["赛龙舟","挂艾草","系五彩绳"],"食物":["粽子","雄黄酒"]},
    "七夕":      {"lunar":"7-7",  "duration":1,  "significance":"中国情人节，牛郎织女",
                  "传统":["许愿","观星","乞巧"],"食物":["巧果"]},
    "中秋节":    {"lunar":"8-15", "duration":1,  "significance":"月圆人团圆，丰收庆祝",
                  "传统":["赏月","挂灯笼","家庭聚会"],"食物":["月饼","柚子","桂花酒"]},
    "重阳节":    {"lunar":"9-9",  "duration":1,  "significance":"登高敬老，避邪祈福",
                  "传统":["登高","赏菊","佩茱萸"],"食物":["菊花酒","重阳糕"]},
    "腊八节":    {"lunar":"12-8", "duration":1,  "significance":"释迦牟尼成道日，祈求丰收",
                  "传统":["祈福","祭祖"],"食物":["腊八粥","腊八蒜"]},
    "除夕":      {"lunar":"12-30","duration":1,  "significance":"辞旧迎新，阖家团圆",
                  "传统":["守岁","贴春联","放鞭炮"],"食物":["年夜饭"]},
}

def get_today_festival(date=None):
    """获取今日是否有节日"""
    if date is None:
        date = datetime.now()
    elif isinstance(date, str):
        date = datetime.strptime(date[:10], "%Y-%m-%d")

    lunar = LunarDate.fromSolarDate(date.year, date.month, date.day)
    lunar_str = f"{lunar.month}-{lunar.day}"
    solar_str = f"{date.month:02d}-{date.day:02d}"

    festivals_found = []
    for name, fdata in CHINESE_FESTIVALS.items():
        if fdata.get("lunar") == lunar_str:
            festivals_found.append({"名称": name, **fdata})
        elif fdata.get("solar") == solar_str:
            festivals_found.append({"名称": name, **fdata})

    return festivals_found if festivals_found else None

def get_next_festival(date=None, limit=365):
    """找下一个即将到来的节日"""
    if date is None:
        date = datetime.now()
    elif isinstance(date, str):
        date = datetime.strptime(date[:10], "%Y-%m-%d")

    for d in range(1, limit + 1):
        check = date + timedelta(days=d)
        f = get_today_festival(check)
        if f:
            return {"日期": check.strftime("%Y-%m-%d"), "距今天数": d, "节日": f[0]}
    return None

# ============================================================
# 十二、生肖配对与特质
# 【出处】传统生肖学说
# ============================================================

ZODIAC_TRAITS = {
    "鼠": {"性格":"机智、灵活、善于社交","幸运色":["蓝","金","绿"],"幸运数":[2,3]},
    "牛": {"性格":"稳重、勤奋、有毅力","幸运色":["白","黄","绿"],"幸运数":[1,9]},
    "虎": {"性格":"勇敢、自信、有领导力","幸运色":["橙","灰","白"],"幸运数":[1,3,4]},
    "兔": {"性格":"温柔、优雅、心思细腻","幸运色":["粉","紫","蓝"],"幸运数":[3,4,9]},
    "龙": {"性格":"自信、有魅力、充满活力","幸运色":["金","银","灰"],"幸运数":[1,6,7]},
    "蛇": {"性格":"智慧、优雅、直觉敏锐","幸运色":["黑","红","黄"],"幸运数":[2,8,9]},
    "马": {"性格":"活泼、热情、自由奔放","幸运色":["黄","绿","紫"],"幸运数":[2,3,7]},
    "羊": {"性格":"温和、善良、有艺术感","幸运色":["绿","红","紫"],"幸运数":[3,9,4]},
    "猴": {"性格":"聪明、灵巧、好奇心强","幸运色":["白","金","蓝"],"幸运数":[1,8,7]},
    "鸡": {"性格":"敏锐、勤奋、有正义感","幸运色":["金","棕","黄"],"幸运数":[5,7,8]},
    "狗": {"性格":"忠诚、诚实、有责任感","幸运色":["绿","红","紫"],"幸运数":[3,4,9]},
    "猪": {"性格":"宽厚、诚实、乐观","幸运色":["黄","灰","棕"],"幸运数":[2,5,8]},
}

# 生肖三合（最佳配对）
ZODIAC_BEST_MATCH = {
    "鼠": ["龙","猴","牛"], "牛": ["蛇","鸡","鼠"],
    "虎": ["马","狗","猪"], "兔": ["羊","猪","狗"],
    "龙": ["鼠","猴","鸡"], "蛇": ["牛","鸡","猴"],
    "马": ["虎","狗","羊"], "羊": ["兔","猪","马"],
    "猴": ["鼠","龙","蛇"], "鸡": ["牛","蛇","龙"],
    "狗": ["虎","马","兔"], "猪": ["兔","羊","虎"],
}

# 生肖六冲（最差配对）
ZODIAC_CLASH = {
    "鼠":"马","牛":"羊","虎":"猴","兔":"鸡",
    "龙":"狗","蛇":"猪","马":"鼠","羊":"牛",
    "猴":"虎","鸡":"兔","狗":"龙","猪":"蛇",
}

# ============================================================
# 十三、八字四柱计算
# 【出处】《三命通会》《渊海子平》
# 五虎遁月法 + 五鼠遁时法
# ============================================================

def calculate_bazi(birth_date):
    """计算八字四柱
    Args:
        birth_date: datetime 对象，含出生时间
    Returns:
        {"年柱":"甲子","月柱":"丙寅","日柱":"戊辰","时柱":"壬子",
         "日主":{"五行":"土","阴阳":"阳","说明":"日主戊土，代表自身"},
         "四柱详情":[...],
         "五行分布":{"木":1,"火":2,...},
         "五行分析":"..."}
    """
    if isinstance(birth_date, str):
        birth_date = datetime.strptime(birth_date[:19], "%Y-%m-%dT%H:%M:%S")
        if birth_date.hour == 0 and birth_date.minute == 0:
            birth_date = birth_date.replace(hour=12)  # 默认中午

    # 日柱（以2000-01-07甲子日为基准）
    base = datetime(2000, 1, 7)
    day_offset = (birth_date - base).days
    day_gan = TIAN_GAN[day_offset % 10]
    day_zhi = DI_ZHI[day_offset % 12]

    # 年柱（立春为界）
    year = birth_date.year
    lichun = datetime(year, 2, 4)
    if birth_date < lichun:
        year -= 1
    year_gan = TIAN_GAN[(year - 4) % 10]
    year_zhi = DI_ZHI[(year - 4) % 12]

    # 月柱（节气 - 近似日期）
    solar_terms = [
        (2,4,2),(3,6,3),(4,5,4),(5,6,5),(6,6,6),
        (7,7,7),(8,8,8),(9,8,9),(10,8,10),(11,7,11),(12,7,0),(1,6,1)
    ]
    month_branch_idx = 0
    for m, d, b_idx in solar_terms:
        if (birth_date.month == m and birth_date.day >= d) or \
           (birth_date.month == (m % 12) + 1 and birth_date.day < d):
            month_branch_idx = b_idx
            break

    month_zhi = DI_ZHI[month_branch_idx]
    # 五虎遁月法
    year_gan_idx = (year - 4) % 10
    zheng_yue_gan = [2,4,6,8,0][year_gan_idx % 5]
    month_gan = TIAN_GAN[(zheng_yue_gan + month_branch_idx) % 10]

    # 时柱（五鼠遁时法）
    hour = birth_date.hour
    if hour == 23:
        hour_zhi_idx = 0
    else:
        hour_zhi_idx = (hour + 1) // 2

    hour_zhi = DI_ZHI[hour_zhi_idx]
    # 日干起时干
    day_gan_idx = TIAN_GAN.index(day_gan)
    hour_stem_base = [0,2,4,6,8,0,2,4,6,8][day_gan_idx]  # 五鼠遁
    hour_gan = TIAN_GAN[(hour_stem_base + hour_zhi_idx) % 10]

    # 四柱
    pillars = [
        {"柱":"年柱","干支":f"{year_gan}{year_zhi}","天干":year_gan,"地支":year_zhi,
         "天干五行":GAN_WUXING[year_gan],"地支五行":ZHI_WUXING[year_zhi],
         "天干阴阳":GAN_YINYANG[year_gan],"地支阴阳":ZHI_YINYANG[year_zhi],
         "含义":"祖辈、童年(0-15)、家族背景"},
        {"柱":"月柱","干支":f"{month_gan}{month_zhi}","天干":month_gan,"地支":month_zhi,
         "天干五行":GAN_WUXING[month_gan],"地支五行":ZHI_WUXING[month_zhi],
         "天干阴阳":GAN_YINYANG[month_gan],"地支阴阳":ZHI_YINYANG[month_zhi],
         "含义":"父母、青年(16-30)、事业发展"},
        {"柱":"日柱","干支":f"{day_gan}{day_zhi}","天干":day_gan,"地支":day_zhi,
         "天干五行":GAN_WUXING[day_gan],"地支五行":ZHI_WUXING[day_zhi],
         "天干阴阳":GAN_YINYANG[day_gan],"地支阴阳":ZHI_YINYANG[day_zhi],
         "含义":"自身、配偶、中年(31-45)、婚姻",
         "日主":{"五行":GAN_WUXING[day_gan],"阴阳":GAN_YINYANG[day_gan],
                  "说明":f"日主{day_gan}{GAN_WUXING[day_gan]}，代表自身核心"}},
        {"柱":"时柱","干支":f"{hour_gan}{hour_zhi}","天干":hour_gan,"地支":hour_zhi,
         "天干五行":GAN_WUXING[hour_gan],"地支五行":ZHI_WUXING[hour_zhi],
         "天干阴阳":GAN_YINYANG[hour_gan],"地支阴阳":ZHI_YINYANG[hour_zhi],
         "含义":"子女、晚年(46+)、传承",
         "时辰":ZHI_TIME[hour_zhi]},
    ]

    # 五行分布统计
    element_count = {"金":0,"木":0,"水":0,"火":0,"土":0}
    for p in pillars:
        element_count[p["天干五行"]] += 1
        element_count[p["地支五行"]] += 1

    strongest = max(element_count, key=element_count.get)
    weakest = min(element_count, key=element_count.get)

    # 五行分析
    gap = element_count[strongest] - element_count[weakest]
    if gap <= 2:
        balance = "五行均衡，命局和谐"
    elif gap <= 4:
        balance = "五行略偏，可适当调整"
    else:
        balance = f"五行失衡，{strongest}过旺、{weakest}过弱，需调和"

    return {
        "年柱": f"{year_gan}{year_zhi}",
        "月柱": f"{month_gan}{month_zhi}",
        "日柱": f"{day_gan}{day_zhi}",
        "时柱": f"{hour_gan}{hour_zhi}",
        "日主": {"五行": GAN_WUXING[day_gan], "阴阳": GAN_YINYANG[day_gan]},
        "日主说明": f"日主{day_gan}{GAN_WUXING[day_gan]}，代表自身核心",
        "四柱详情": pillars,
        "五行分布": element_count,
        "五行分析": balance,
        "最强五行": strongest,
        "最弱五行": weakest,
    }

def calculate_day_master(date=None):
    """仅计算当日日柱天干（日主），用于每日运势
    【出处】以2000-01-07为甲子日推算
    """
    if date is None:
        date = datetime.now()
    elif isinstance(date, str):
        date = datetime.strptime(date[:10], "%Y-%m-%d")

    base = datetime(2000, 1, 7)
    days = (date - base).days
    gan = TIAN_GAN[days % 10]
    zhi = DI_ZHI[days % 12]
    nayin = get_nayin(gan, zhi)

    return {
        "日干": gan,
        "日支": zhi,
        "日柱": f"{gan}{zhi}",
        "日主五行": GAN_WUXING[gan],
        "日主阴阳": GAN_YINYANG[gan],
        "纳音": nayin,
        "纳音五行": get_nayin_wuxing(nayin),
    }

# ============================================================
# 十四、十神（Ten Gods）
# 【出处】《渊海子平·论十神》
# 以日主天干为"我"，判断其他天干与我的关系
# ============================================================

def get_shishen(day_master_gan, other_gan):
    """计算十神关系：其他天干 → 日主的关系
    【规则】
    - 同我：比肩（同阴阳）/劫财（异阴阳）
    - 生我：正印（异阴阳）/偏印（同阴阳）
    - 我生：伤官（异阴阳）/食神（同阴阳）
    - 克我：正官（异阴阳）/七杀（同阴阳）
    - 我克：正财（异阴阳）/偏财（同阴阳）
    """
    dm_wx = GAN_WUXING[day_master_gan]
    other_wx = GAN_WUXING[other_gan]
    dm_yy = GAN_YINYANG[day_master_gan]
    other_yy = GAN_YINYANG[other_gan]
    same_yy = (dm_yy == other_yy)

    # 五行生克关系
    SHENG = {"木":"火","火":"土","土":"金","金":"水","水":"木"}  # A生B
    KE = {"木":"土","土":"水","水":"火","火":"金","金":"木"}      # A克B

    if dm_wx == other_wx:
        return "比肩" if same_yy else "劫财"
    elif SHENG.get(other_wx) == dm_wx:
        return "偏印" if same_yy else "正印"
    elif SHENG.get(dm_wx) == other_wx:
        return "食神" if same_yy else "伤官"
    elif KE.get(other_wx) == dm_wx:
        return "七杀" if same_yy else "正官"
    elif KE.get(dm_wx) == other_wx:
        return "偏财" if same_yy else "正财"
    return "未知"

SHISHEN_MEANING = {
    "比肩": "同辈、朋友、竞争、自我",
    "劫财": "兄弟姐妹、合作、争夺",
    "正印": "母亲、学业、贵人、庇护",
    "偏印": "继母、偏门学问、灵感、孤僻",
    "食神": "子女、才华、口福、乐观",
    "伤官": "才华外露、叛逆、创造力",
    "正官": "上司、纪律、丈夫（女）、事业",
    "七杀": "权威、挑战、小人、魄力",
    "正财": "妻子（男）、稳定收入、节俭",
    "偏财": "父亲、意外之财、慷慨、投资",
}

SHISHEN_RANK = {
    "正印": 5, "偏印": 4, "比肩": 3, "劫财": 2,
    "食神": 2, "伤官": 1, "正财": 3, "偏财": 4,
    "正官": 4, "七杀": 1
}

def calculate_shishen_all(pillars):
    """计算八字中所有十神关系，返回每个天干的十神"""
    day_gan = None
    for p in pillars:
        if p["柱"] == "日柱":
            day_gan = p["天干"]
    if not day_gan:
        return {}

    result = {}
    for p in pillars:
        gan = p["天干"]
        zhi = p["地支"]
        zhi_hidden = ZHI_CANGGAN.get(zhi, [])
        # 天干十神
        result[f"{p['柱']}天干{gan}"] = {
            "干支": gan, "十神": get_shishen(day_gan, gan),
            "含义": SHISHEN_MEANING.get(get_shishen(day_gan, gan), ""),
            "位置": p["柱"]
        }
        # 地支藏干十神
        for hg in zhi_hidden:
            result[f"{p['柱']}地支藏{gan}{hg}"] = {
                "干支": hg, "十神": get_shishen(day_gan, hg),
                "含义": SHISHEN_MEANING.get(get_shishen(day_gan, hg), ""),
                "位置": p["柱"]
            }
    return result

# ============================================================
# 十五、地支藏干
# 【出处】《三命通会》《渊海子平》
# ============================================================

ZHI_CANGGAN = {
    "子": ["癸"],
    "丑": ["己","癸","辛"],
    "寅": ["甲","丙","戊"],
    "卯": ["乙"],
    "辰": ["戊","乙","癸"],
    "巳": ["丙","戊","庚"],
    "午": ["丁","己"],
    "未": ["己","丁","乙"],
    "申": ["庚","壬","戊"],
    "酉": ["辛"],
    "戌": ["戊","辛","丁"],
    "亥": ["壬","甲"],
}

ZHI_CANGGAN_LABEL = {
    "寅": {"甲":"本气","丙":"中气","戊":"余气"},
    "午": {"丁":"本气","己":"中气"},
    "巳": {"丙":"本气","戊":"中气","庚":"余气"},
}

def get_canggan_detail(pillars):
    """获取四柱地支藏干详情"""
    result = []
    for p in pillars:
        zhi = p["地支"]
        hidden = ZHI_CANGGAN.get(zhi, [])
        labels = ZHI_CANGGAN_LABEL.get(zhi, {})
        cg_list = []
        for hg in hidden:
            label = labels.get(hg, "")
            wx = GAN_WUXING.get(hg, "")
            cg_list.append({"藏干": hg, "五行": wx, "气": label, "十神": get_shishen(
                [pp["天干"] for pp in pillars if pp["柱"]=="日柱"][0] if any(pp["柱"]=="日柱" for pp in pillars) else "甲", hg
            )})
        result.append({"柱": p["柱"], "地支": zhi, "藏干详情": cg_list})
    return result

# ============================================================
# 十六、用神分析
# 【出处】《子平真诠》《滴天髓》
# ============================================================

def analyze_yongshen(bazi):
    """分析八字用神
    规则：扶抑法——身弱补印比，身强补财官食
    """
    wx_count = bazi.get("五行分布", {})
    day_wx = bazi.get("日主", {}).get("五行", "土")
    day_rank = sum(1 for p in bazi.get("四柱详情", []) if p.get("天干五行") == day_wx or p.get("地支五行") == day_wx)

    # 判断身强身弱：日主五行出现>=4次为强，<=2次为弱
    if day_rank <= 2:
        shen = "身弱"
    elif day_rank >= 4:
        shen = "身强"
    else:
        shen = "中和"

    # 五行生克链
    SHENG = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
    KE = {"木":"土","土":"水","水":"火","火":"金","金":"木"}
    BEI_SHENG = {v:k for k,v in SHENG.items()}  # 谁生我
    BEI_KE = {v:k for k,v in KE.items()}         # 谁克我

    if shen == "身弱":
        yong = BEI_SHENG.get(day_wx, "金")  # 印星（生我）
        xi = day_wx  # 比劫（同我）
        ji = KE.get(day_wx, "火")  # 官杀（克我）
        chou = SHENG.get(day_wx, "土")  # 食伤（我生）
    elif shen == "身强":
        yong = KE.get(day_wx, "火")  # 官杀
        xi = SHENG.get(day_wx, "土")  # 食伤
        ji = BEI_SHENG.get(day_wx, "金")  # 印星
        chou = day_wx  # 比劫
    else:
        yong = "调和"
        xi = "均衡"
        ji = "极端"
        chou = "偏颇"

    WUXING_MEANING = {
        "金": "加强执行力、决断力，宜从事金融/法律/管理","木": "培养仁德、拓展人脉，宜从事教育/文化/医疗",
        "水": "增强智慧、灵活应变，宜从事交通/通讯/贸易","火": "提升热情、展现魅力，宜从事传媒/餐饮/公益",
        "土": "培养诚信、稳扎稳打，宜从事地产/农业/咨询"
    }

    return {
        "日主": day_wx,
        "日主出现次数": day_rank,
        "身强身弱": shen,
        "用神": yong,
        "用神说明": WUXING_MEANING.get(yong, "平衡为宜"),
        "喜神": xi,
        "忌神": ji,
        "仇神": chou,
        "喜用神": [yong, xi] if yong != xi else [yong],
        "建议": f"日主{day_wx}{shen}，用神取{yong}，喜{xi}，忌{ji}。{WUXING_MEANING.get(yong,'')}",
    }

# ============================================================
# 十七、神煞
# 【出处】《渊海子平》《星平会海》
# ============================================================

def calculate_shensha(pillars, day_zhi=None, year_zhi=None):
    """计算常见神煞
    - 天乙贵人：日干+年干为主
    - 文昌：日干查
    - 桃花（咸池）：日支查
    - 驿马：日支查
    - 华盖：日支查
    - 羊刃：日干查
    - 禄神：日干查
    """
    if not pillars:
        return {}

    day_gan = None
    for p in pillars:
        if p["柱"] == "日柱":
            day_gan = p["天干"]
            day_zhi_val = p["地支"]
            break
    if not day_gan:
        day_gan = pillars[2]["天干"] if len(pillars) > 2 else "甲"
        day_zhi_val = ""
    if not day_zhi:
        day_zhi = day_zhi_val

    year_gan = pillars[0]["天干"] if pillars else "甲"
    year_zhi_val = pillars[0]["地支"] if pillars else "子"
    if not year_zhi:
        year_zhi = year_zhi_val

    # 天乙贵人（日干+年干）
    TIANYI = {
        "甲":"丑未","戊":"丑未","庚":"丑未",
        "乙":"子申","己":"子申",
        "丙":"亥酉","丁":"亥酉",
        "辛":"午寅","壬":"卯巳","癸":"卯巳"
    }

    # 文昌（日干）
    WENCHANG = {
        "甲":"巳","乙":"午","丙":"申","丁":"酉","戊":"申",
        "己":"酉","庚":"亥","辛":"子","壬":"寅","癸":"卯"
    }

    # 桃花/咸池（日支三合局首位）
    TAOHUA = {"亥卯未":"子","寅午戌":"卯","巳酉丑":"午","申子辰":"酉"}
    YIMA = {"亥卯未":"巳","寅午戌":"申","巳酉丑":"亥","申子辰":"寅"}
    HUAGAI = {"亥卯未":"未","寅午戌":"戌","巳酉丑":"丑","申子辰":"辰"}
    YANGREN = {"甲":"卯","乙":"寅","丙":"午","丁":"巳","戊":"午","己":"巳","庚":"酉","辛":"申","壬":"子","癸":"亥"}
    LUSHEN = {"甲":"寅","乙":"卯","丙":"巳","丁":"午","戊":"巳","己":"午","庚":"申","辛":"酉","壬":"亥","癸":"子"}

    sanhe_group = None
    for group, zhi in {"亥卯未":"子","寅午戌":"卯","巳酉丑":"午","申子辰":"酉"}.items():
        if day_zhi in group:
            sanhe_group = group
            break

    results = []
    # 天乙贵人
    ty = TIANYI.get(day_gan, "")
    for z in DI_ZHI:
        if z in ty:
            results.append({"神煞": "天乙贵人", "对应": z, "含义": "逢凶化吉，贵人相助", "级别": "大吉"})

    # 文昌
    wc = WENCHANG.get(day_gan, "")
    results.append({"神煞": "文昌", "对应": wc, "含义": "学业有成，文采出众", "级别": "吉"})

    # 禄神
    ls = LUSHEN.get(day_gan, "")
    results.append({"神煞": "禄神", "对应": ls, "含义": "福禄寿喜，衣食无忧", "级别": "吉"})

    # 桃花
    if sanhe_group:
        th = TAOHUA.get(sanhe_group, "")
        results.append({"神煞": "桃花(咸池)", "对应": th, "含义": "异性缘佳，人缘好", "级别": "中"})

    # 驿马
    if sanhe_group:
        ym = YIMA.get(sanhe_group, "")
        results.append({"神煞": "驿马", "对应": ym, "含义": "奔波劳碌，变动频繁", "级别": "中"})

    # 华盖
    if sanhe_group:
        hg = HUAGAI.get(sanhe_group, "")
        results.append({"神煞": "华盖", "对应": hg, "含义": "孤芳自赏，艺术天赋", "级别": "中"})

    # 羊刃
    yr = YANGREN.get(day_gan, "")
    results.append({"神煞": "羊刃", "对应": yr, "含义": "刚强果断，易冲动", "级别": "凶"})

    # 检查日支是否有神煞
    ri_zhi_shensha = []
    for s in results:
        if s.get("对应") == day_zhi:
            ri_zhi_shensha.append(s)

    return {
        "所有神煞": results,
        "日支神煞": ri_zhi_shensha,
        "日支": day_zhi,
    }

# ============================================================
# 十八、大运计算
# 【出处】《三命通会》《渊海子平》
# ============================================================

def calculate_dayun(birth_date, bazi):
    """计算大运
    规则：
    - 阳年男/阴年女 → 顺排（从月柱往下顺数）
    - 阴年男/阳年女 → 逆排
    - 起运年龄 = 出生日到下一个/上一个节气天数 ÷ 3
    """
    year_gan = bazi["年柱"][0]
    year_yy = GAN_YINYANG.get(year_gan, "阳")
    is_yang = (year_yy == "阳")
    is_male = True  # 默认男性
    forward = (is_yang == is_male)

    month_gan = bazi["月柱"][0]
    month_zhi = bazi["月柱"][1]
    month_gan_idx = TIAN_GAN.index(month_gan)
    month_zhi_idx = DI_ZHI.index(month_zhi)

    # 节气列表（日期为当月大约日期）
    jieqi_dates = [
        (1,6,"小寒"), (2,4,"立春"), (3,6,"惊蛰"), (4,5,"清明"),
        (5,6,"立夏"), (6,6,"芒种"), (7,7,"小暑"), (8,8,"立秋"),
        (9,8,"白露"), (10,8,"寒露"), (11,7,"立冬"), (12,7,"大雪"),
    ]

    # 找到出生日之后的第一个节气（顺排）/ 出生日之前的最后一个节气（逆排）
    if forward:
        # 找下一个节气
        target_jq = None
        for m, d, name in jieqi_dates:
            jq_date = datetime(birth_date.year, m, d)
            if jq_date > birth_date:
                target_jq = jq_date
                break
        if not target_jq:
            target_jq = datetime(birth_date.year + 1, 1, 6)
    else:
        # 找上一个节气
        target_jq = None
        for m, d, name in reversed(jieqi_dates):
            jq_date = datetime(birth_date.year, m, d)
            if jq_date < birth_date:
                target_jq = jq_date
                break
        if not target_jq:
            target_jq = datetime(birth_date.year - 1, 12, 7)

    days_diff = abs((target_jq - birth_date).days)
    qiyun_age = max(1, round(days_diff / 3))

    # 生成大运（10年一步，共8步）
    dayun_list = []
    for i in range(8):
        age = qiyun_age + i * 10
        if forward:
            g_idx = (month_gan_idx + i + 1) % 10
            z_idx = (month_zhi_idx + i + 1) % 12
        else:
            g_idx = (month_gan_idx - i - 1) % 10
            z_idx = (month_zhi_idx - i - 1) % 12
        gz = f"{TIAN_GAN[g_idx]}{DI_ZHI[z_idx]}"
        wx = GAN_WUXING[TIAN_GAN[g_idx]]
        yy = GAN_YINYANG[TIAN_GAN[g_idx]]

        # 判断当前是否在此大运中
        current_age = (datetime.now() - birth_date).days / 365.25
        is_current = age <= current_age < age + 10

        yy_str = "正运" if yy == bazi.get("日主",{}).get("阴阳","阴") else "偏运"
        impact = "好" if (wx in [bazi.get("日主",{}).get("五行","土"), "金"]) else "挑战"

        dayun_list.append({
            "步数": i+1, "年龄": f"{age}-{age+9}岁",
            "干支": gz, "天干": TIAN_GAN[g_idx],
            "五行": wx, "阴阳": yy, "运性": yy_str,
            "影响": impact,
            "当前": is_current,
            "年份": f"{birth_date.year+age}-{birth_date.year+age+9}"
        })

    return {
        "起运年龄": qiyun_age,
        "起运年份": birth_date.year + qiyun_age,
        "大运列表": dayun_list,
        "当前大运": [d for d in dayun_list if d.get("当前")],
    }

# ============================================================
# 十九、流日吉凶
# 【出处】《三命通会》《渊海子平》
# ============================================================

def calculate_liuri_jixiong(bazi, today_date=None):
    """计算今日流日对命主的吉凶影响"""
    if today_date is None:
        today_date = datetime.now()

    # 今日日柱
    base = datetime(2000, 1, 7)
    days = (today_date - base).days
    today_gan = TIAN_GAN[days % 10]
    today_zhi = DI_ZHI[days % 12]

    day_master_gan = bazi.get("日柱","")[0] if bazi.get("日柱") else "甲"
    day_master_zhi = bazi.get("日柱","")[1] if bazi.get("日柱") else "子"
    dm_wx = GAN_WUXING.get(day_master_gan, "土")

    # 天干关系
    gan_shishen = get_shishen(day_master_gan, today_gan)

    # 地支关系
    zhi_clash = ZHI_CHONG.get(day_master_zhi) == today_zhi
    zhi_liuhe = any(today_zhi in pair and day_master_zhi in pair
                    for pair in ["子丑","寅亥","卯戌","辰酉","巳申","午未"])

    # 五行生克
    today_wx = GAN_WUXING.get(today_gan, "土")
    SHENG = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
    KE = {"木":"土","土":"水","水":"火","火":"金","金":"木"}

    if SHENG.get(today_wx) == dm_wx:
        wx_rel = "今日生你"
    elif SHENG.get(dm_wx) == today_wx:
        wx_rel = "你生今日"
    elif KE.get(today_wx) == dm_wx:
        wx_rel = "今日克你"
    elif KE.get(dm_wx) == today_wx:
        wx_rel = "你克今日"
    else:
        wx_rel = "五行比和"

    # 综合判断
    score = 3  # 0-5分
    if gan_shishen in ["正印","比肩","正财"]: score += 1
    if gan_shishen in ["七杀","伤官"]: score -= 1
    if zhi_clash: score -= 2
    if zhi_liuhe: score += 1
    if wx_rel == "今日生你": score += 1
    if wx_rel == "今日克你": score -= 1
    score = max(0, min(5, score))

    levels = ["大凶","凶","平","吉","大吉","上上"]
    level = levels[score]

    tips = {
        "正印": "宜学习、求教、静养",
        "偏印": "宜独处思考、研究",
        "比肩": "宜合作、社交、团队活动",
        "劫财": "注意财务、谨防破耗",
        "食神": "宜享受生活、发挥才华",
        "伤官": "谨言慎行、避免冲突",
        "正官": "宜守规矩、展现专业",
        "七杀": "注意压力、避免冒险",
        "正财": "宜理财、稳扎稳打",
        "偏财": "宜投资、把握机会",
    }

    return {
        "日期": today_date.strftime("%Y-%m-%d"),
        "今日日柱": f"{today_gan}{today_zhi}",
        "今日天干": today_gan,
        "十神关系": gan_shishen,
        "十神含义": SHISHEN_MEANING.get(gan_shishen, ""),
        "五行关系": wx_rel,
        "地支冲合": "六冲！" if zhi_clash else ("六合！" if zhi_liuhe else "无冲合"),
        "吉凶": level,
        "评分": score,
        "建议": tips.get(gan_shishen, "保持平常心"),
    }

def generate_personal_scenario(bazi, liuri, fortune_data):
    """根据八字+流日+今日天象，生成一个详细的个人场景建议
    综合静态分析（八字/大运/用神）和动态数据（流日/建星/月相/二十八宿）
    """
    dm = bazi.get("日主", {})
    dm_wx = dm.get("五行", "土")
    dm_yy = dm.get("阴阳", "阴")
    dayun_current = [d for d in (bazi.get("_dayun_list") or []) if d.get("当前")]
    
    # 今日数据
    liuri_ss = liuri.get("十神关系", "")
    liuri_level = liuri.get("吉凶", "平")
    liuri_score = liuri.get("评分", 3)
    liuri_tip = liuri.get("建议", "")
    liuri_wx = liuri.get("五行关系", "")
    liuri_chonghe = liuri.get("地支冲合", "")
    
    jianchu = fortune_data.get("jianchu", "")
    jianchu_jx = fortune_data.get("jianchu_jixiong", "")
    xiu_name = fortune_data.get("xiu", {}).get("宿名", "")
    xiu_jx = fortune_data.get("xiu", {}).get("吉凶", "")
    moon_phase = fortune_data.get("moon_phase", {}).get("月相", "")
    moon_energy = fortune_data.get("moon_phase", {}).get("能量", "")
    jishi = fortune_data.get("jishi", [])
    chongsha = fortune_data.get("chongsha", {})
    
    # 用神分析
    yongshen = bazi.get("_yongshen") or {}
    ys_wx = yongshen.get("用神", "金")
    ys_shen = yongshen.get("身强身弱", "中和")
    
    # 神煞
    shensha = bazi.get("_shensha_list") or []
    tianyi_zhi = [s["对应"] for s in shensha if s["神煞"] == "天乙贵人"]
    taohua_zhi = [s["对应"] for s in shensha if "桃花" in s["神煞"]]
    wenchang_zhi = [s["对应"] for s in shensha if s["神煞"] == "文昌"]
    
    # ---- 构建场景 ----
    scenarios = []
    
    # 1. 流日解读
    if liuri_level in ("大吉", "上上"):
        today_mood = "顺遂"
    elif liuri_level == "吉":
        today_mood = "平稳向好"
    elif liuri_level == "凶":
        today_mood = "有挑战"
    else:
        today_mood = "需谨慎"
    
    # 2. 大运 + 流日合力
    if dayun_current:
        dy_ganzhi = dayun_current[0]["干支"]
        dy_wx = dayun_current[0]["五行"]
        dy_impact = dayun_current[0]["影响"]
    
    # 七杀日特别提醒
    if liuri_ss == "七杀":
        seven_kill = True
    else:
        seven_kill = False
    
    # 正官日
    if liuri_ss == "正官":
        zhengguan = True
    else:
        zhengguan = False
    
    # 正印日
    if liuri_ss == "正印":
        zhengyin = True
    else:
        zhengyin = False
    
    # 3. 今日场景构建
    date_str = fortune_data.get("date", "")
    
    # 主体场景
    if seven_kill:
        main_scene = (
            f"今日{liuri_ss}日，七杀代表压力、挑战与权威。"
            f"对你而言，今日可能遇到需要快速决策的局面，或面临来自上级/客户的严格要求。"
        )
        if liuri_chonghe and "六冲" in liuri_chonghe:
            main_scene += "加上地支六冲，变动感强烈，不宜做重大决策。"
        elif liuri_chonghe and "六合" in liuri_chonghe:
            main_scene += "好在有六合星照临，人际关系能帮你化解部分压力。"
        
        if "癸酉" in (dayun_current[0]["干支"] if dayun_current else ""):
            main_scene += (
                f"\n\n不过你正走癸酉水运——水是你的喜神，酉金是你的用神。"
                f"大运给你灌水补身，让你在面对七杀压力时有足够底气。"
                f"这就像你已经练好了内功，今日的挑战正是检验修行成果的时候。"
            )
        
        advice = (
            f"**应对策略：** 避开{chongsha.get('冲','')}相的同事/朋友直接冲突，"
            f"将压力转化为执行力。七杀日的优势在于行动力爆发，"
            f"适合集中处理积压的工作。吉时{jishi[0].split('·')[0] if jishi else '上午'}开始最有效。"
        )
    
    elif zhengguan:
        main_scene = (
            f"今日正官日，正官代表规矩、事业、责任感。"
            f"对身弱的你来说，正官是克身但有情——就像一位严格的老师，"
            f"虽然让你有压力，但目的是让你成长。"
        )
        advice = "宜展现专业能力，守规矩办事，上级会看在眼里。"
    
    elif zhengyin:
        main_scene = (
            f"今日正印日，正印生身，是你的贵人星。"
            f"正印如母亲般温柔滋养，特别适合学习、求教、整理思绪。"
        )
        advice = "宜读书充电、向长辈请教、处理文书工作。"
    
    else:
        main_scene = (
            f"今日{liuri_ss}日，整体运势{liuri_level}。"
        )
        advice = liuri_tip
    
    # 4. 天象加持
    celestial = (
        f"\n\n**天象加持：** 今日建星「{jianchu}」为{jianchu_jx}，"
        f"值宿「{xiu_name}」属{xiu_jx}，月相「{moon_phase}」能量为{moon_energy}。"
    )
    
    if jianchu in ("定","成","开","除","执"):
        celestial += f"建星为吉，适合{','.join(fortune_data.get('jianchu_yi',[])[:3])}。"
    
    if xiu_jx == "吉":
        celestial += f"{xiu_name}宿宜{','.join([x for x in fortune_data.get('xiu',{}).get('宜',[]) if x][:2])}。"
    
    # 5. 吉时窗口
    if jishi:
        top_jishi = jishi[:3]
        time_window = f"\n\n**黄金时段：** " + "、".join(j.split("·")[0] for j in top_jishi) + "，适合重要活动。"
    else:
        time_window = ""
    
    # 6. 今日关键词
    keywords_map = {
        "七杀":"突破·抗压·行动力","正官":"规矩·专业·上级","正印":"学习·贵人·静养",
        "偏印":"独处·研究·灵感","比肩":"合作·社交·分享","劫财":"谨慎·防破财·低调",
        "食神":"享受·创造·美食","伤官":"表达·创新·谨慎","正财":"稳健·理财·守成","偏财":"机遇·投资·灵活"
    }
    keywords = keywords_map.get(liuri_ss, "平常心·稳扎稳打")
    
    return {
        "场景": main_scene.strip(),
        "建议": advice.strip(),
        "天象": celestial.strip(),
        "时机": time_window.strip(),
        "今日关键词": keywords,
        "整体基调": today_mood,
        "隐藏机遇": (
            f"七杀之下藏偏印——今日地支亥中藏壬甲，壬水是你的劫财帮身，"
            f"甲木是你的伤官泄秀。压力之中有朋友暗中相助，"
            f"不妨主动联系属{','.join(fortune_data.get('zodiac_compat',{}).get('最佳配对',[])[:2])}的朋友聊聊。"
        ) if seven_kill and liuri_chonghe == "六冲！" else "",
    }

# ============================================================
# 二十、综合运势计算（整合版 v2.1）
# ============================================================

def calculate_fortune(date=None, birth_date=None):
    """计算今日完整运势数据（整合版 v2.0）"""
    if date is None:
        date = datetime.now()
    elif isinstance(date, str):
        date = datetime.strptime(date[:10], "%Y-%m-%d")

    # --- 日柱干支 ---
    base_date = datetime(2000, 1, 7)
    day_offset = (date - base_date).days
    day_gan_idx = day_offset % 10
    day_zhi_idx = day_offset % 12
    day_gan = TIAN_GAN[day_gan_idx]
    day_zhi = DI_ZHI[day_zhi_idx]

    # --- 月柱 ---
    lunar = LunarDate.fromSolarDate(date.year, date.month, date.day)
    month_zhi_idx = (lunar.month + 1) % 12
    month_zhi = DI_ZHI[month_zhi_idx]
    year_gan_idx = (date.year - 4) % 10
    zheng_yue_gan = [2, 4, 6, 8, 0][year_gan_idx % 5]
    month_gan_idx = (zheng_yue_gan + lunar.month - 1) % 10
    month_gan = TIAN_GAN[month_gan_idx]

    # --- 年柱 ---
    year_gan_idx = (date.year - 4) % 10
    year_zhi_idx = (date.year - 4) % 12
    year_gan = TIAN_GAN[year_gan_idx]
    year_zhi = DI_ZHI[year_zhi_idx]

    # --- 纳音 ---
    nayin = get_nayin(day_gan, day_zhi)
    nayin_wuxing = get_nayin_wuxing(nayin)

    # --- 生肖 ---
    shengxiao = SHENG_XIAO[year_zhi_idx]

    # --- 十二建星 ---
    jianchu = get_jianchu(month_zhi_idx, day_zhi_idx)
    jianchu_info = JIANCHU_YIJI.get(jianchu, {"宜":[],"忌":[]})

    # --- 吉神方位 ---
    jishen = get_jishen_fangwei(day_gan)

    # --- 吉时 ---
    jishi = get_jishi(day_zhi)

    # --- 冲煞 ---
    chongsha = get_chongsha(day_zhi, day_gan)

    # --- 黄道黑道 ---
    huangdao = get_huangdao_shishen(day_zhi)
    huangdao_summary = [f"{h['时辰']}时{h['值神']}" for h in huangdao if h["吉凶"] == "吉"]

    # --- 【新增】二十八宿 ---
    xiu = get_xiu(date)

    # --- 【新增】月相 ---
    moon = get_moon_phase(date)

    # --- 【新增】节日 ---
    festival = get_today_festival(date)

    # --- 【新增】日主 ---
    day_master = calculate_day_master(date)

    # --- 【新增】生肖配对（今日日支） ---
    day_zodiac = SHENG_XIAO[day_zhi_idx]
    year_zodiac_compat = {
        "最佳配对": ZODIAC_BEST_MATCH.get(shengxiao, []),
        "最忌配对": [ZODIAC_CLASH.get(shengxiao, "")],
    }

    # --- 评分 ---
    scores = calculate_scores(day_gan, day_zhi, nayin_wuxing, jianchu, jianchu_info, jishi, chongsha)

    # --- 【新增】当前时辰 ---
    now = datetime.now()
    current_hour = now.hour
    # 时辰公式：0,23→子; 1,2→子; 3,4→寅; ... 21,22→亥
    if current_hour == 0 or current_hour == 23:
        current_shichen_zhi = '子'
        current_shichen_idx = 0
    elif current_hour == 1 or current_hour == 2:
        current_shichen_zhi = '丑'
        current_shichen_idx = 1
    else:
        current_shichen_idx = current_hour // 2
        current_shichen_zhi = DI_ZHI[current_shichen_idx]
    
    # 当前时辰的黄道黑道信息
    current_huangdao = None
    for h in huangdao:
        if h['时辰'] == current_shichen_zhi:
            current_huangdao = h
            break
    
    # 当前时辰干支（需要日干来推算）
    # 甲己日起甲子时，乙庚起丙子时...
    day_gan_idx = TIAN_GAN.index(day_gan)
    start_gan_idx = (day_gan_idx * 2) % 10
    hour_gan_idx = (start_gan_idx + current_shichen_idx) % 10
    current_shichen_gan = TIAN_GAN[hour_gan_idx]
    current_shichen_ganzhi = f"{current_shichen_gan}{current_shichen_zhi}"
    
    # 时间范围
    shichen_time_ranges = {
        '子': '23:00-01:00', '丑': '01:00-03:00', '寅': '03:00-05:00',
        '卯': '05:00-07:00', '辰': '07:00-09:00', '巳': '09:00-11:00',
        '午': '11:00-13:00', '未': '13:00-15:00', '申': '15:00-17:00',
        '酉': '17:00-19:00', '戌': '19:00-21:00', '亥': '21:00-23:00'
    }
    
    result = {
        # 基础字段
        "date": date.strftime("%Y-%m-%d"),
        "weekday": ["一","二","三","四","五","六","日"][date.weekday()],
        "time": now.strftime("%H:%M"),
        "current_shichen": {
            "name": current_shichen_zhi,
            "ganzhi": current_shichen_ganzhi,
            "time_range": shichen_time_ranges[current_shichen_zhi],
            "huangdao": current_huangdao['值神'] if current_huangdao else None,
            "jixiong": current_huangdao['吉凶'] if current_huangdao else None,
        },
        "year_gan_zhi": f"{year_gan}{year_zhi}",
        "month_gan_zhi": f"{month_gan}{month_zhi}",
        "day_gan_zhi": f"{day_gan}{day_zhi}",
        "nayin": nayin,
        "nayin_wuxing": nayin_wuxing,
        "shengxiao": shengxiao,
        "day_gan": day_gan,
        "day_zhi": day_zhi,
        "jianchu": jianchu,
        "jianchu_jixiong": JIANCHU_JIXIONG.get(jianchu, ""),
        "jianchu_yi": jianchu_info.get("宜", []),
        "jianchu_ji": jianchu_info.get("忌", []),
        "jishen_fangwei": jishen,
        "jishi": jishi,
        "chongsha": chongsha,
        "huangdao_shishen": huangdao,
        "huangdao_jishi": huangdao_summary,

        # 【新增】二十八宿
        "xiu": xiu,

        # 【新增】月相
        "moon_phase": moon,

        # 【新增】节日
        "festival": festival,

        # 【新增】日主
        "day_master": day_master,

        # 【新增】生肖配对
        "zodiac_compat": year_zodiac_compat,

        # 评分
        **scores,
        "lucky_color": get_lucky_color(nayin_wuxing),
        "lucky_num": get_lucky_num(day_gan, day_zhi),
        "sign_grade": get_sign_grade(scores["overall"]),

        # 【新增】个人八字（如果提供了出生日期）
        "personal_bazi": calculate_bazi(birth_date) if birth_date else None,

        # 🆕 v2.1 十神/藏干/用神/神煞/大运/流日
        "shishen": None,
        "canggan": None,
        "yongshen": None,
        "shensha": None,
        "dayun": None,
        "liuri": None,
        "personal_scenario": None,
    }

    # 如果有个人八字，计算所有新增模块
    if result["personal_bazi"]:
        bz = result["personal_bazi"]
        pillars = bz.get("四柱详情", [])
        result["shishen"] = calculate_shishen_all(pillars)
        result["canggan"] = get_canggan_detail(pillars)
        result["yongshen"] = analyze_yongshen(bz)
        result["shensha"] = calculate_shensha(pillars)
        result["dayun"] = calculate_dayun(birth_date, bz)
        result["liuri"] = calculate_liuri_jixiong(bz)

        # 🆕 v2.2 个人场景建议
        bz["_dayun_list"] = result["dayun"]["大运列表"]
        bz["_yongshen"] = result["yongshen"]
        bz["_shensha_list"] = result["shensha"]["所有神煞"]
        result["personal_scenario"] = generate_personal_scenario(bz, result["liuri"], result)

    return result

# ============================================================
# 十五、真实评分算法（保留 v1.0 不变）
# ============================================================

def calculate_scores(day_gan, day_zhi, nayin_wuxing, jianchu, jianchu_info, jishi, chongsha):
    import hashlib
    seed = int(hashlib.md5(f"{day_gan}{day_zhi}".encode()).hexdigest()[:8], 16)

    base = 60

    jianchu_bonus = {
        "建": -5, "除": 10, "满": 0, "平": -8,
        "定": 12, "执": 8, "破": -15, "危": -3,
        "成": 15, "收": -5, "开": 12, "闭": -10
    }
    jianchu_score = jianchu_bonus.get(jianchu, 0)

    jishi_count = len(jishi)
    jishi_score = (jishi_count - 4) * 3

    chong_zhi = chongsha.get("冲", "")
    chong_score = -5 if "蛇" in chong_zhi or "虎" in chong_zhi else 0

    day_wx = GAN_WUXING.get(day_gan, "土")
    SHENG = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
    KE = {"木":"土","土":"水","水":"火","火":"金","金":"木"}
    if SHENG.get(day_wx) == nayin_wuxing:
        nayin_score = 8
    elif KE.get(day_wx) == nayin_wuxing:
        nayin_score = -5
    elif KE.get(nayin_wuxing) == day_wx:
        nayin_score = -8
    else:
        nayin_score = 5

    yi_count = len(jianchu_info.get("宜", []))
    ji_count = len(jianchu_info.get("忌", []))
    yiji_score = (yi_count - ji_count) * 2

    overall = max(40, min(98, base + jianchu_score + jishi_score + chong_score + nayin_score + yiji_score))
    career = max(40, min(98, base + jianchu_score * 1.5 + jishi_score * 0.5 + seed % 10 - 5))
    wealth = max(40, min(98, base + nayin_score * 2 + jishi_score * 0.8 + seed % 8 - 4))
    love = max(40, min(98, base + yiji_score * 1.5 + chong_score * 0.5 + seed % 12 - 6))
    health = max(40, min(98, base + nayin_score * 1.5 + jianchu_score * 0.5 + seed % 8 - 4))
    social = max(40, min(98, base + chong_score * 1.5 + jishi_score * 0.8 + seed % 10 - 5))

    return {
        "overall": overall,
        "career": career,
        "wealth": wealth,
        "love": love,
        "health": health,
        "social": social,
    }

def get_lucky_color(nayin_wuxing):
    COLOR_MAP = {"木":"青绿色","火":"红色/紫色","土":"黄色/棕色","金":"白色/银色","水":"黑色/蓝色"}
    return COLOR_MAP.get(nayin_wuxing, "金色")

def get_lucky_num(day_gan, day_zhi):
    GAN_NUM = {"甲":1,"乙":2,"丙":3,"丁":4,"戊":5,"己":6,"庚":7,"辛":8,"壬":9,"癸":10}
    ZHI_NUM = {"子":1,"丑":2,"寅":3,"卯":4,"辰":5,"巳":6,"午":7,"未":8,"申":9,"酉":10,"戌":11,"亥":12}
    total = GAN_NUM.get(day_gan, 5) + ZHI_NUM.get(day_zhi, 6)
    return total % 10 if total > 9 else total

def get_sign_grade(overall):
    if overall >= 90: return "上上签"
    elif overall >= 80: return "上签"
    elif overall >= 70: return "中上签"
    elif overall >= 60: return "中签"
    elif overall >= 50: return "中下签"
    else: return "下签"

# ============================================================
# 十六、生成运势标签（整合版）
# ============================================================

def generate_tags(fortune):
    """生成今日命理要素标签（整合版）"""
    weekday = ["星期一","星期二","星期三","星期四","星期五","星期六","星期日"]
    date = datetime.strptime(fortune["date"], "%Y-%m-%d")
    wd = weekday[date.weekday()]

    tags = [
        {"icon": "📅", "label": "公历", "value": f"{date.strftime('%Y年%m月%d日')} {wd}"},
        {"icon": "🌙", "label": "农历", "value": f"{fortune['year_gan_zhi']}年"},
        {"icon": "☯️", "label": "干支", "value": f"{fortune['year_gan_zhi']}年 {fortune['month_gan_zhi']}月 {fortune['day_gan_zhi']}日"},
        {"icon": "🐴", "label": "生肖", "value": fortune["shengxiao"]},
        {"icon": "🌿", "label": "五行", "value": f"{fortune['day_gan_zhi']}{fortune['nayin']}({fortune['nayin_wuxing']})"},
        {"icon": "⭐", "label": "建星", "value": f"{fortune['jianchu']}日({fortune['jianchu_jixiong']})"},

        # 【新增】日主
        {"icon": "🧬", "label": "日主", "value": f"{fortune['day_master']['日干']}{fortune['day_master']['日主五行']}({fortune['day_master']['日主阴阳']})"},

        # 【新增】二十八宿
        {"icon": "🌌", "label": "值宿", "value": f"{fortune['xiu']['宿名']}宿({fortune['xiu']['吉凶']})·{fortune['xiu']['方位']}方"},

        # 【新增】月相
        {"icon": "🌓", "label": "月相", "value": f"{fortune['moon_phase']['月相']}({fortune['moon_phase']['吉凶']})·{fortune['moon_phase']['能量']}"},

        {"icon": "💰", "label": "财神", "value": fortune["jishen_fangwei"]["财神"]},
        {"icon": "🧧", "label": "喜神", "value": fortune["jishen_fangwei"]["喜神"]},
        {"icon": "🍀", "label": "福神", "value": fortune["jishen_fangwei"]["福神"]},
        {"icon": "⏰", "label": "吉时", "value": "、".join(fortune["jishi"][:4])},
        {"icon": "⚠️", "label": "冲煞", "value": f"冲{fortune['chongsha']['冲']} 煞{fortune['chongsha']['煞']}"},
    ]

    # 【新增】节日标签
    if fortune.get("festival"):
        for f in fortune["festival"]:
            tags.append({"icon": "🎊", "label": "节日", "value": f"{f['名称']} — {f['significance']}"})

    return tags

# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    result = calculate_fortune()
    print(json.dumps(result, ensure_ascii=False, indent=2))

    print("\n=== 命理标签 ===")
    for tag in generate_tags(result):
        print(f"  {tag['icon']} {tag['label']}: {tag['value']}")

    # 测试八字（用示例日期，不代表任何人）
    print("\n=== 测试八字 ===")
    bazi = calculate_bazi(datetime(2000, 1, 1, 12, 0))
    print(f"  四柱: {bazi['年柱']} {bazi['月柱']} {bazi['日柱']} {bazi['时柱']}")
    print(f"  日主: {bazi['日主说明']}")
    print(f"  五行分布: {bazi['五行分布']}")
    print(f"  分析: {bazi['五行分析']}")

    # 测节日
    print("\n=== 测试节日 ===")
    festival = get_today_festival()
    if festival:
        for f in festival:
            print(f"  🎊 {f['名称']}: {f['significance']}")
            print(f"     食物: {', '.join(f['食物'])}")

    # 测下一个节日
    nf = get_next_festival()
    if nf:
        print(f"  下一个节日: {nf['日期']} ({nf['距今天数']}天后) — {nf['节日']['名称']}")
