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
# 十四、综合运势计算（整合版）
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

    return {
        # 基础字段
        "date": date.strftime("%Y-%m-%d"),
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
    }

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

    # 测一个生日八字
    print("\n=== 测试八字 ===")
    bazi = calculate_bazi(datetime(1998, 6, 15, 12, 0))
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
