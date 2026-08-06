# -*- coding: utf-8 -*-
"""
make_stub.py — 生成 stub/parts.stub.json（B 的开发用假数据）

为什么存在：A 的 data/parts.json 没交之前，3D / 面板 / 中英切换都得有东西可跑。
真数据到了之后本文件不再参与运行时，只留作回归对照。

产物承诺（脚本末尾自检，不满足直接 SystemExit）：
  - 总条数 ≥ 350
  - has_mesh=true 恰好 110 条
  - 字段名与任务书冻结格式逐字一致，一个不多一个不少
  - id 唯一；parent / connects_to 指向的 id 都存在

所有零件号、供应商、规格都是编的（vehicle.data_kind = "stub"），
页面读到 stub 会在角上挂「示例数据」角标，不许当真。
"""

import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "stub", "parts.stub.json")

# 冻结字段：顺序无所谓，名字一个字不许改
FIELDS = [
    "id", "group", "subgroup_en", "subgroup_zh", "name_en", "name_zh",
    "oem_pn", "parent", "connects_to", "role_zh", "role_en",
    "qty", "qty_kind", "tags", "has_mesh", "spec", "suppliers",
]

G_BODY = "body"
G_ELEC = "electrical"
G_ENGN = "engine_fuel_tool"
G_PTCH = "powertrain_chassis"

# ---------------------------------------------------------------- 图组定义
# (subgroup_en, subgroup_zh) —— 仿丰田官方分解图的图组命名
SG = {
    "hood":      ("Hood & Front Fender", "发动机盖与前翼子板"),
    "fbumper":   ("Front Bumper & Bumper Stay", "前保险杠与保险杠支架"),
    "rbumper":   ("Rear Bumper & Bumper Stay", "后保险杠与保险杠支架"),
    "fdoor":     ("Front Door Panel & Glass", "前车门板与玻璃"),
    "rdoor":     ("Rear Door Panel & Glass", "后车门板与玻璃"),
    "roof":      ("Roof Panel & Back Panel", "车顶板与后围板"),
    "side":      ("Side Member & Rocker Panel", "侧围与门槛"),
    "trunk":     ("Luggage Compartment Door & Lock", "行李厢盖与锁"),
    "glass":     ("Windshield & Back Window Glass", "前后风窗玻璃"),
    "mirror":    ("Mirror", "后视镜"),
    "ip":        ("Instrument Panel & Glove Compartment", "仪表板与手套箱"),
    "seat":      ("Seat & Seat Track", "座椅与滑轨"),
    "console":   ("Console Box & Bracket", "中央扶手箱"),
    "radsup":    ("Radiator Support & Wind Guide", "水箱框架与导风板"),
    "cowl":      ("Cowl Panel & Water Deflector", "通风盖板与挡水板"),
    "ffloor":    ("Front Floor Panel & Member", "前地板与纵梁"),
    "rfloor":    ("Rear Floor Panel & Member", "后地板与纵梁"),
    "trim":      ("Door Trim & Inside Handle", "门内饰板与内把手"),
    "spoiler":   ("Spoiler & Side Mudguard", "扰流板与挡泥板"),
    "headlin":   ("Roof Headlining", "顶棚内衬"),

    "headlamp":  ("Headlamp", "前照灯"),
    "rearlamp":  ("Rear Combination Lamp", "后组合灯"),
    "foglamp":   ("Fog Lamp", "雾灯"),
    "battery":   ("Battery & Battery Cable", "蓄电池与电缆"),
    "fuse":      ("Fuse Box & Relay Block", "保险丝盒与继电器盒"),
    "alt":       ("Alternator", "发电机"),
    "starter":   ("Starter", "起动机"),
    "horn":      ("Horn", "喇叭"),
    "wiper":     ("Windshield Wiper & Washer", "雨刮与洗涤装置"),
    "audio":     ("Radio Receiver & Amplifier", "音响主机与功放"),
    "speaker":   ("Speaker", "扬声器"),
    "meter":     ("Meter & Gauge", "组合仪表"),
    "sensor":    ("Camera & Sensor", "摄像头与传感器"),
    "ecu":       ("ECU & Computer", "电脑与控制单元"),
    "lamp2":     ("Interior Lamp & License Plate Lamp", "车内灯与牌照灯"),

    "block":     ("Cylinder Block", "气缸体"),
    "head":      ("Cylinder Head", "气缸盖"),
    "manifold":  ("Manifold", "进排气歧管"),
    "aircl":     ("Air Cleaner", "空气滤清器"),
    "radiator":  ("Radiator & Water Outlet", "散热器与出水口"),
    "wpump":     ("Water Pump", "水泵"),
    "fueltank":  ("Fuel Tank & Tube", "燃油箱与油管"),
    "inject":    ("Fuel Injection System", "燃油喷射系统"),
    "exhaust":   ("Exhaust Pipe & Muffler", "排气管与消声器"),
    "oil":       ("Oil Filter & Oil Pump", "机油滤清器与机油泵"),
    "mount":     ("Engine Mounting", "发动机悬置"),
    "ac":        ("Air Conditioner", "空调装置"),
    "timing":    ("Timing Chain", "正时链条"),
    "tool":      ("Vehicle Tool & Jack", "随车工具与千斤顶"),

    "transaxle": ("Transaxle Case", "变速驱动桥壳"),
    "driveshaft":("Drive Shaft", "驱动轴"),
    "fsusp":     ("Front Spring & Shock Absorber", "前弹簧与减振器"),
    "rsusp":     ("Rear Spring & Shock Absorber", "后弹簧与减振器"),
    "farm":      ("Front Suspension Arm", "前悬架摆臂"),
    "raxle":     ("Rear Axle & Suspension", "后桥与后悬架"),
    "fhub":      ("Front Axle Hub", "前轮毂"),
    "rhub":      ("Rear Axle Hub", "后轮毂"),
    "fbrake":    ("Front Disc Brake", "前盘式制动器"),
    "rbrake":    ("Rear Disc Brake", "后盘式制动器"),
    "master":    ("Brake Master Cylinder & Booster", "制动主缸与真空助力器"),
    "column":    ("Steering Column", "转向管柱"),
    "gearbox":   ("Steering Gear", "转向器"),
    "wheel":     ("Wheel & Tire", "车轮与轮胎"),
    "crossmb":   ("Suspension Crossmember", "悬架副车架"),
    "stabar":    ("Stabilizer Bar", "横向稳定杆"),
    "parkbrk":   ("Parking Brake", "驻车制动"),
    "shift":     ("Transmission Control & Shift Lever", "换挡机构"),
}

# ---------------------------------------------------------- 110 个有网格零件
# (id, name_en, name_zh, group, sg_key, qty, qty_kind, tags, role_zh, role_en, spec)
MESH = [
    # ---- BODY 外覆盖件 ----
    ("body-hood", "Hood Sub-Assembly", "发动机盖总成", G_BODY, "hood", 1, "exact", ["exterior", "panel", "steel"],
     "盖住发动机舱的那块大盖板，掀开就能加机油、看水箱。", "The big lid over the engine bay; lift it to reach oil, coolant and the engine.", "钢制冲压件，约 12 kg"),
    ("body-fender-lh", "Front Fender LH", "左前翼子板", G_BODY, "hood", 1, "exact", ["exterior", "panel", "steel"],
     "前轮上方那块钣金，挡住轮胎甩起来的泥水。", "Sheet metal above the front wheel that blocks mud and spray.", "钢板 0.65 mm"),
    ("body-fender-rh", "Front Fender RH", "右前翼子板", G_BODY, "hood", 1, "exact", ["exterior", "panel", "steel"],
     "前轮上方那块钣金，挡住轮胎甩起来的泥水。", "Sheet metal above the front wheel that blocks mud and spray.", "钢板 0.65 mm"),
    ("body-fbumper-cover", "Front Bumper Cover", "前保险杠皮", G_BODY, "fbumper", 1, "exact", ["exterior", "plastic"],
     "车头最前面那层塑料外皮，低速磕碰先撞它。", "The plastic skin at the very front; it takes the hit in a low-speed bump.", "PP+EPDM 注塑件"),
    ("body-fbumper-reinf", "Front Bumper Reinforcement", "前防撞梁", G_BODY, "fbumper", 1, "exact", ["structure", "steel"],
     "藏在保险杠皮后面的横梁，真正扛撞的是它。", "The steel beam hidden behind the cover; this is what actually absorbs a crash.", "高强钢辊压成型"),
    ("body-fbumper-absorber", "Front Bumper Energy Absorber", "前保险杠吸能块", G_BODY, "fbumper", 1, "exact", ["safety", "foam"],
     "泡沫块，撞行人腿部时把冲击缓一缓。", "Foam block that softens the blow to a pedestrian's legs.", "EPP 发泡"),
    ("body-rbumper-cover", "Rear Bumper Cover", "后保险杠皮", G_BODY, "rbumper", 1, "exact", ["exterior", "plastic"],
     "车尾最外面那层塑料外皮。", "The outermost plastic skin at the rear.", "PP 注塑件"),
    ("body-rbumper-reinf", "Rear Bumper Reinforcement", "后防撞梁", G_BODY, "rbumper", 1, "exact", ["structure", "steel"],
     "后保险杠皮里面的横梁，被追尾时扛冲击。", "Beam behind the rear cover that takes a rear-end impact.", "高强钢"),
    ("body-door-front-lh", "Front Door Panel LH", "左前车门板", G_BODY, "fdoor", 1, "exact", ["exterior", "door", "steel"],
     "驾驶员上下车的那扇门的钣金主体。", "The sheet-metal body of the driver's door.", "内外板点焊总成"),
    ("body-door-front-rh", "Front Door Panel RH", "右前车门板", G_BODY, "fdoor", 1, "exact", ["exterior", "door", "steel"],
     "副驾那扇门的钣金主体。", "The sheet-metal body of the front passenger door.", "内外板点焊总成"),
    ("body-door-rear-lh", "Rear Door Panel LH", "左后车门板", G_BODY, "rdoor", 1, "exact", ["exterior", "door", "steel"],
     "后排左边那扇门的钣金主体。", "The sheet-metal body of the left rear door.", "内外板点焊总成"),
    ("body-door-rear-rh", "Rear Door Panel RH", "右后车门板", G_BODY, "rdoor", 1, "exact", ["exterior", "door", "steel"],
     "后排右边那扇门的钣金主体。", "The sheet-metal body of the right rear door.", "内外板点焊总成"),
    ("body-door-glass-front-lh", "Front Door Glass LH", "左前车门玻璃", G_BODY, "fdoor", 1, "exact", ["glass"],
     "能升降的那块前门玻璃。", "The roll-down glass in the front door.", "钢化玻璃 3.5 mm"),
    ("body-door-glass-front-rh", "Front Door Glass RH", "右前车门玻璃", G_BODY, "fdoor", 1, "exact", ["glass"],
     "能升降的那块前门玻璃。", "The roll-down glass in the front door.", "钢化玻璃 3.5 mm"),
    ("body-door-glass-rear-lh", "Rear Door Glass LH", "左后车门玻璃", G_BODY, "rdoor", 1, "exact", ["glass"],
     "后门那块能升降的玻璃。", "The roll-down glass in the rear door.", "钢化玻璃 3.5 mm"),
    ("body-door-glass-rear-rh", "Rear Door Glass RH", "右后车门玻璃", G_BODY, "rdoor", 1, "exact", ["glass"],
     "后门那块能升降的玻璃。", "The roll-down glass in the rear door.", "钢化玻璃 3.5 mm"),
    ("body-windshield", "Windshield Glass", "前风窗玻璃", G_BODY, "glass", 1, "exact", ["glass", "safety"],
     "前挡风玻璃，夹层的，碎了也不会掉渣扎人。", "The laminated front screen; if it breaks it holds together instead of shattering.", "夹层玻璃 4.76 mm"),
    ("body-backwindow", "Back Window Glass", "后风窗玻璃", G_BODY, "glass", 1, "exact", ["glass", "heated"],
     "后挡风玻璃，里面那些横线是电加热除雾丝。", "The rear screen; those thin lines are the electric defogger.", "钢化玻璃，含电热丝"),
    ("body-roof", "Roof Panel", "车顶板", G_BODY, "roof", 1, "exact", ["exterior", "panel", "steel"],
     "整块车顶钣金，同时也是车身刚性的一部分。", "The whole roof skin; it also stiffens the body shell.", "钢板 0.65 mm"),
    ("body-trunk-lid", "Luggage Compartment Door", "行李厢盖", G_BODY, "trunk", 1, "exact", ["exterior", "panel"],
     "后备厢盖，掀开放行李。", "The trunk lid you lift to load luggage.", "钢制内外板"),
    ("body-quarter-lh", "Quarter Panel LH", "左后侧围板", G_BODY, "side", 1, "exact", ["exterior", "panel", "steel"],
     "后门到尾灯之间那块大钣金，和车身焊死的。", "The big panel between rear door and tail lamp, welded to the shell.", "钢板冲压"),
    ("body-quarter-rh", "Quarter Panel RH", "右后侧围板", G_BODY, "side", 1, "exact", ["exterior", "panel", "steel"],
     "后门到尾灯之间那块大钣金，和车身焊死的。", "The big panel between rear door and tail lamp, welded to the shell.", "钢板冲压"),
    ("body-rocker-lh", "Rocker Panel LH", "左门槛梁", G_BODY, "side", 1, "exact", ["structure", "steel"],
     "车门下面那条梁，侧撞时是主要承力件。", "The sill beam under the doors; a main load path in a side impact.", "1470 MPa 热成型钢"),
    ("body-rocker-rh", "Rocker Panel RH", "右门槛梁", G_BODY, "side", 1, "exact", ["structure", "steel"],
     "车门下面那条梁，侧撞时是主要承力件。", "The sill beam under the doors; a main load path in a side impact.", "1470 MPa 热成型钢"),
    ("body-pillar-a-lh", "Front Body Pillar LH (A-Pillar)", "左 A 柱", G_BODY, "side", 1, "exact", ["structure"],
     "前风窗两侧那根斜柱，翻车时撑住车顶。", "The slanted post beside the windshield; holds the roof up in a rollover.", "热成型钢闭口断面"),
    ("body-pillar-a-rh", "Front Body Pillar RH (A-Pillar)", "右 A 柱", G_BODY, "side", 1, "exact", ["structure"],
     "前风窗两侧那根斜柱，翻车时撑住车顶。", "The slanted post beside the windshield; holds the roof up in a rollover.", "热成型钢闭口断面"),
    ("body-pillar-b-lh", "Center Body Pillar LH (B-Pillar)", "左 B 柱", G_BODY, "side", 1, "exact", ["structure", "safety"],
     "前后门之间那根柱子，侧碰最关键的一根。", "The post between front and rear doors; the most critical one in a side crash.", "热成型钢，含加强板"),
    ("body-pillar-b-rh", "Center Body Pillar RH (B-Pillar)", "右 B 柱", G_BODY, "side", 1, "exact", ["structure", "safety"],
     "前后门之间那根柱子，侧碰最关键的一根。", "The post between front and rear doors; the most critical one in a side crash.", "热成型钢，含加强板"),
    ("body-pillar-c-lh", "Rear Body Pillar LH (C-Pillar)", "左 C 柱", G_BODY, "side", 1, "exact", ["structure"],
     "后风窗两侧那根柱子。", "The post beside the rear screen.", "钢制闭口断面"),
    ("body-pillar-c-rh", "Rear Body Pillar RH (C-Pillar)", "右 C 柱", G_BODY, "side", 1, "exact", ["structure"],
     "后风窗两侧那根柱子。", "The post beside the rear screen.", "钢制闭口断面"),
    ("body-grille-upper", "Radiator Grille Upper", "上格栅", G_BODY, "fbumper", 1, "exact", ["exterior", "plastic"],
     "车头那张「嘴」，进气同时也是脸面。", "The car's 'mouth' — lets air in and defines the face.", "ABS 电镀件"),
    ("body-grille-lower", "Radiator Grille Lower", "下格栅", G_BODY, "fbumper", 1, "exact", ["exterior", "plastic"],
     "保险杠下方的大开口，冷却空气主要从这儿进。", "The big lower opening; most cooling air comes in here.", "PP 注塑网格"),
    ("body-mirror-lh", "Outer Rear View Mirror LH", "左外后视镜", G_BODY, "mirror", 1, "exact", ["exterior", "electric"],
     "看后方来车的镜子，能电动调角度、加热。", "The mirror for traffic behind; power-adjusted and heated.", "含电动调节与加热"),
    ("body-mirror-rh", "Outer Rear View Mirror RH", "右外后视镜", G_BODY, "mirror", 1, "exact", ["exterior", "electric"],
     "看后方来车的镜子，能电动调角度、加热。", "The mirror for traffic behind; power-adjusted and heated.", "含电动调节与加热"),
    ("body-door-handle-outside", "Outside Door Handle", "车门外把手", G_BODY, "fdoor", 4, "exact", ["exterior", "trim"],
     "从外面开门抓的那个把手，四个门各一个。", "The handle you grab from outside; one per door.", "本体色喷涂"),
    ("body-cowl", "Cowl Top Panel", "通风盖板", G_BODY, "cowl", 1, "exact", ["exterior", "plastic"],
     "前风窗下面那条黑塑料板，雨水和进风都从这儿走。", "The black strip under the windshield; rain and cabin air both pass here.", "PP 注塑"),
    ("body-wiper-arm", "Windshield Wiper Arm & Blade", "雨刮臂与刮片", G_BODY, "wiper", 2, "exact", ["exterior", "wear"],
     "刮雨水的那两根，胶条属于易损件。", "The two arms that sweep the rain; the rubber is a wear item.", "驾驶侧 650 mm / 副驾 400 mm"),
    ("body-radiator-support", "Radiator Support Sub-Assembly", "水箱框架总成", G_BODY, "radsup", 1, "exact", ["structure"],
     "车头那个「口」字框，水箱、风扇、大灯都挂在它上面。", "The rectangular frame at the nose; radiator, fan and headlamps all bolt to it.", "钢塑混合"),
    ("body-floor-front", "Front Floor Panel", "前地板", G_BODY, "ffloor", 1, "exact", ["structure", "panel"],
     "前排脚下踩的那块大钢板。", "The big steel panel under the front footwells.", "冲压钢板，带加强筋"),
    ("body-floor-rear", "Rear Floor Panel", "后地板", G_BODY, "rfloor", 1, "exact", ["structure", "panel"],
     "后排和后备厢底下那块钢板，备胎槽也在上面。", "The panel under the rear seats and trunk, including the spare-wheel well.", "冲压钢板"),
    ("body-dash-panel", "Dash Panel (Firewall)", "前围板（防火墙）", G_BODY, "ffloor", 1, "exact", ["structure", "nvh"],
     "把发动机舱和乘客舱隔开的那道墙，隔热隔噪。", "The wall between engine bay and cabin; blocks heat and noise.", "钢板 + 隔音垫"),
    ("body-instrument-panel", "Instrument Panel Sub-Assembly", "仪表台总成", G_BODY, "ip", 1, "exact", ["interior", "plastic"],
     "方向盘前面那一整条台面，仪表、出风口都长在上面。", "The whole dash top; gauges and vents are built into it.", "PP 搪塑表皮"),
    ("body-glove-box", "Glove Compartment Door", "手套箱盖", G_BODY, "ip", 1, "exact", ["interior"],
     "副驾前面能打开的储物盒，空调滤芯常藏在后面。", "The passenger-side storage box; the cabin filter usually hides behind it.", "PP 注塑"),
    ("body-console", "Console Box Sub-Assembly", "中央扶手箱总成", G_BODY, "console", 1, "exact", ["interior"],
     "两个前座之间的箱子，放水杯和手机。", "The box between the front seats for cups and phones.", "含杯架与储物盖"),
    ("body-seat-front-lh", "Front Seat Assembly LH", "左前座椅总成", G_BODY, "seat", 1, "exact", ["interior", "safety"],
     "驾驶座整张椅子，含滑轨、靠背和头枕。", "The whole driver's seat: rails, backrest and headrest.", "含侧气囊接口"),
    ("body-seat-front-rh", "Front Seat Assembly RH", "右前座椅总成", G_BODY, "seat", 1, "exact", ["interior", "safety"],
     "副驾整张椅子，座垫里通常有乘员识别垫。", "The whole front passenger seat; usually has an occupant sensor in the cushion.", "含乘员检测传感器"),
    ("body-seat-rear-cushion", "Rear Seat Cushion", "后排座垫", G_BODY, "seat", 1, "exact", ["interior"],
     "后排屁股底下那块垫子。", "The rear bench you sit on.", "发泡 + 织物面套"),
    ("body-seat-rear-back", "Rear Seat Back", "后排靠背", G_BODY, "seat", 1, "exact", ["interior"],
     "后排靠背，多数车型能 6/4 放倒装长物件。", "The rear backrest; usually splits 60/40 to carry long items.", "6/4 分割可放倒"),
    ("body-headliner", "Roof Headlining", "顶棚内衬", G_BODY, "headlin", 1, "exact", ["interior", "nvh"],
     "车顶里面那层软板，遮住钢板也吸噪音。", "The soft board inside the roof; hides the steel and absorbs noise.", "PU 模压 + 无纺布"),
    ("body-carpet", "Floor Carpet", "地板毯", G_BODY, "ffloor", 1, "exact", ["interior", "nvh"],
     "整块地毯，脚下的隔音主力。", "One-piece carpet; the main sound insulation underfoot.", "含背胶隔音层"),
    ("body-door-trim", "Door Trim Board", "车门内饰板", G_BODY, "trim", 4, "exact", ["interior", "plastic"],
     "门内侧那块板，扶手、按键、喇叭都在上面。", "The inner door panel carrying the armrest, switches and speaker.", "四门各一"),
    ("body-fuel-lid", "Fuel Filler Opening Lid", "加油口盖", G_BODY, "side", 1, "exact", ["exterior"],
     "车侧那个小翻盖，加油时打开。", "The small flap on the side you open to refuel.", "钢制，含铰链"),
    ("body-spoiler", "Rear Spoiler", "后扰流板", G_BODY, "spoiler", 1, "exact", ["exterior", "aero"],
     "行李厢盖后缘那道小鸭尾，整理尾部气流。", "The small lip on the trunk edge that tidies airflow off the tail.", "PP 注塑，本体色"),
    ("body-mudguard", "Side Mudguard", "挡泥板", G_BODY, "spoiler", 4, "exact", ["exterior"],
     "轮子后方那片小胶皮，挡石子和泥。", "The small flap behind each wheel that catches stones and mud.", "TPO，四轮各一"),

    # ---- ELECTRICAL ----
    ("elec-headlamp-lh", "Headlamp Assembly LH", "左前照灯总成", G_ELEC, "headlamp", 1, "exact", ["lighting", "led"],
     "左边大灯，近光远光日行灯都在这一个壳里。", "The left headlamp; low beam, high beam and DRL all in one housing.", "LED 光源，含调光电机"),
    ("elec-headlamp-rh", "Headlamp Assembly RH", "右前照灯总成", G_ELEC, "headlamp", 1, "exact", ["lighting", "led"],
     "右边大灯，近光远光日行灯都在这一个壳里。", "The right headlamp; low beam, high beam and DRL all in one housing.", "LED 光源，含调光电机"),
    ("elec-taillamp-lh", "Rear Combination Lamp LH", "左后组合灯", G_ELEC, "rearlamp", 1, "exact", ["lighting"],
     "左尾灯，刹车灯、位置灯、转向灯合在一起。", "Left tail lamp: brake, position and turn signal combined.", "LED，含转向灯"),
    ("elec-taillamp-rh", "Rear Combination Lamp RH", "右后组合灯", G_ELEC, "rearlamp", 1, "exact", ["lighting"],
     "右尾灯，刹车灯、位置灯、转向灯合在一起。", "Right tail lamp: brake, position and turn signal combined.", "LED，含转向灯"),
    ("elec-foglamp", "Fog Lamp Assembly", "雾灯总成", G_ELEC, "foglamp", 2, "exact", ["lighting"],
     "保险杠下方两颗小灯，大雾天照近处路面。", "Two small lamps low in the bumper; they light the road close-in in fog.", "左右各一"),
    ("elec-stop-lamp-high", "High Mounted Stop Lamp", "高位刹车灯", G_ELEC, "rearlamp", 1, "exact", ["lighting", "safety"],
     "后风窗上沿那条灯，让后车更早看见你在刹车。", "The strip at the top of the rear screen so the car behind sees you brake sooner.", "LED 条形"),
    ("elec-license-lamp", "License Plate Lamp", "牌照灯", G_ELEC, "lamp2", 2, "exact", ["lighting"],
     "照亮后牌照的小灯，法规强制。", "Small lamps that light the rear plate; required by law.", "LED"),
    ("elec-battery", "Battery 12V", "12V 蓄电池", G_ELEC, "battery", 1, "exact", ["power"],
     "启动电瓶，熄火后所有用电也靠它。", "The starter battery; it also powers everything with the engine off.", "LN2 / 60 Ah 级"),
    ("elec-battery-tray", "Battery Carrier Tray", "蓄电池托盘", G_ELEC, "battery", 1, "exact", ["bracket"],
     "托住电瓶的盘子，防止电瓶晃动。", "The tray that holds the battery still.", "钢制，含压板"),
    ("elec-engine-ecu", "Engine Control Computer (ECU)", "发动机电脑", G_ELEC, "ecu", 1, "exact", ["ecu", "control"],
     "发动机的大脑，喷多少油、什么时候点火它说了算。", "The engine's brain: it decides fuel quantity and ignition timing.", "32 bit MCU，铝壳"),
    ("elec-body-ecu", "Body Control Module", "车身控制模块", G_ELEC, "ecu", 1, "exact", ["ecu", "control"],
     "管灯光、车窗、中控锁这些「杂事」的电脑。", "The computer that runs lights, windows and locks.", "CAN 网关集成"),
    ("elec-fusebox-engine", "Engine Room Relay Block", "机舱保险丝继电器盒", G_ELEC, "fuse", 1, "exact", ["power"],
     "机舱里那个黑盒子，大电流的保险丝都在里面。", "The black box in the engine bay holding the high-current fuses.", "含 MEGA 熔断器"),
    ("elec-junction-cabin", "Instrument Panel Junction Block", "车内接线盒", G_ELEC, "fuse", 1, "exact", ["power"],
     "仪表台下面的保险丝盒，车内电器从这儿分电。", "The fuse box under the dash that feeds the cabin circuits.", "含 30 余路熔断器"),
    ("elec-alternator", "Alternator", "发电机", G_ELEC, "alt", 1, "exact", ["power", "belt"],
     "发动机带着它转，一边给电瓶充电一边供全车用电。", "Driven by the engine belt; it charges the battery and powers the car.", "100 A 级，带单向皮带轮"),
    ("elec-starter", "Starter Motor", "起动机", G_ELEC, "starter", 1, "exact", ["motor"],
     "拧钥匙时把发动机拖转起来的那个马达。", "The motor that cranks the engine when you start it.", "1.0 kW 减速式"),
    ("elec-horn", "Horn Assembly", "喇叭总成", G_ELEC, "horn", 2, "exact", ["audio"],
     "按方向盘中间响的那个，通常高低音两只。", "What sounds when you press the wheel centre; usually a high and a low tone.", "高音 + 低音各一"),
    ("elec-wiper-motor", "Windshield Wiper Motor & Link", "雨刮电机与连杆", G_ELEC, "wiper", 1, "exact", ["motor"],
     "藏在通风盖板下面，带动两根雨刮臂来回摆。", "Hidden under the cowl; it swings both wiper arms.", "含四连杆机构"),
    ("elec-washer-tank", "Washer Tank & Pump", "洗涤液壶与泵", G_ELEC, "wiper", 1, "exact", ["fluid"],
     "装玻璃水的塑料壶，底下带小水泵。", "The plastic bottle of screen wash with a small pump at the bottom.", "约 4.0 L"),
    ("elec-cooling-fan", "Radiator Cooling Fan Assembly", "散热风扇总成", G_ELEC, "radiator", 1, "exact", ["motor", "cooling"],
     "水箱后面那个大风扇，堵车时全靠它吹风降温。", "The big fan behind the radiator; in traffic it does all the cooling.", "双速无刷电机 + 护风罩"),
    ("elec-head-unit", "Radio Receiver & Display", "音响主机与显示屏", G_ELEC, "audio", 1, "exact", ["infotainment"],
     "中控那块屏，导航、蓝牙、倒车影像都走它。", "The centre screen: navigation, Bluetooth and the reversing camera.", "8 英寸电容屏"),
    ("elec-speaker-front", "Front Door Speaker", "前门扬声器", G_ELEC, "speaker", 2, "exact", ["audio"],
     "前门内饰板里的喇叭。", "The speakers inside the front door trims.", "6×9 英寸"),
    ("elec-speaker-rear", "Rear Door Speaker", "后门扬声器", G_ELEC, "speaker", 2, "exact", ["audio"],
     "后门内饰板里的喇叭。", "The speakers inside the rear door trims.", "6×9 英寸"),
    ("elec-meter-cluster", "Combination Meter", "组合仪表", G_ELEC, "meter", 1, "exact", ["display"],
     "方向盘后面那组表，车速、转速、油量、故障灯。", "The gauges behind the wheel: speed, revs, fuel and warning lights.", "7 英寸 TFT + 指针"),
    ("elec-steering-pad", "Steering Wheel Pad & Switch", "方向盘按键与喇叭盖", G_ELEC, "ecu", 1, "exact", ["switch"],
     "方向盘上那几组按键，也是喇叭和气囊的盖板。", "The wheel-mounted buttons; also the horn pad and airbag cover.", "含音量与巡航键"),
    ("elec-front-camera", "Forward Recognition Camera", "前视摄像头", G_ELEC, "sensor", 1, "exact", ["adas", "sensor"],
     "贴在前风窗上方的小盒子，认车道线和前车。", "The small box at the top of the windshield that reads lane lines and traffic ahead.", "单目，含 LKA/PCS 功能"),
    ("elec-radar-front", "Millimeter Wave Radar Sensor", "毫米波雷达", G_ELEC, "sensor", 1, "exact", ["adas", "sensor"],
     "藏在前格栅后面，量前车距离和相对速度。", "Hidden behind the grille; measures distance and closing speed to the car ahead.", "77 GHz"),
    ("elec-park-sensor", "Ultrasonic Parking Sensor", "倒车雷达探头", G_ELEC, "sensor", 4, "exact", ["sensor"],
     "保险杠上那几个小圆点，倒车时嘀嘀响。", "The little round dots in the bumper that beep when you reverse.", "后保 4 颗"),
    ("elec-bsm-sensor", "Blind Spot Monitor Sensor", "盲区监测雷达", G_ELEC, "sensor", 2, "exact", ["adas", "sensor"],
     "后保险杠两角里的雷达，后视镜亮黄灯就是它报的。", "Radars in the rear bumper corners; they trigger the amber light in the mirror.", "24 GHz，左右各一"),
    ("elec-abs-actuator", "Skid Control ECU & Actuator (ABS)", "ABS 泵与电脑", G_ELEC, "ecu", 1, "exact", ["brake", "ecu"],
     "急刹时「哒哒哒」响的那个泵，管 ABS 和车身稳定。", "The pump that chatters in a panic stop; it runs ABS and stability control.", "含 8 只电磁阀"),
    ("elec-airbag-ecu", "Airbag Sensor Assembly", "安全气囊电脑", G_ELEC, "ecu", 1, "exact", ["safety", "ecu"],
     "装在中央通道上，判断撞得够不够狠、要不要弹气囊。", "Mounted on the tunnel; it decides whether a crash is hard enough to fire the bags.", "含加速度传感器"),
    ("elec-interior-lamp", "Interior Room Lamp", "车内顶灯", G_ELEC, "lamp2", 2, "exact", ["lighting"],
     "顶棚上开门就亮的那盏灯。", "The roof lamp that comes on when you open a door.", "前后各一"),
    ("elec-mirror-turn", "Mirror Turn Signal Lamp", "后视镜转向灯", G_ELEC, "lamp2", 2, "exact", ["lighting"],
     "后视镜壳上那条会流动的灯带。", "The signal strip on the mirror housing.", "LED，左右各一"),

    # ---- ENGINE / FUEL / TOOL ----
    ("eng-cylinder-block", "Cylinder Block", "气缸体", G_ENGN, "block", 1, "exact", ["engine", "aluminium"],
     "发动机的身子，四个活塞在里面上下跑。", "The engine's body; four pistons run up and down inside.", "2ZR-FAE 级，铝合金"),
    ("eng-cylinder-head", "Cylinder Head", "气缸盖", G_ENGN, "head", 1, "exact", ["engine", "aluminium"],
     "扣在气缸体上面的盖，气门、凸轮轴都在里面。", "The lid on top of the block; valves and camshafts live inside.", "双顶置凸轮轴，16 气门"),
    ("eng-head-cover", "Cylinder Head Cover", "气缸盖罩", G_ENGN, "head", 1, "exact", ["engine"],
     "打开机盖最先看到的那个黑盖子。", "The black cover you see first when you open the hood.", "尼龙一体成型"),
    ("eng-oil-pan", "Oil Pan", "油底壳", G_ENGN, "oil", 1, "exact", ["engine", "fluid"],
     "发动机最下面那个盘，机油平时都存在这儿。", "The tray at the bottom of the engine where the oil sits.", "铝合金，约 4.2 L"),
    ("eng-intake-manifold", "Intake Manifold", "进气歧管", G_ENGN, "manifold", 1, "exact", ["engine", "air"],
     "把空气分成四路送进四个缸的塑料件。", "The plastic piece that splits incoming air into four runners.", "尼龙焊接件"),
    ("eng-exhaust-manifold", "Exhaust Manifold with Converter", "排气歧管与前催化器", G_ENGN, "manifold", 1, "exact", ["engine", "hot"],
     "把四缸的废气汇到一起，紧挨着的催化器先净化一道。", "Collects exhaust from all four cylinders; the close-coupled catalyst cleans it first.", "不锈钢，集成三元催化"),
    ("eng-throttle-body", "Throttle Body", "节气门体", G_ENGN, "inject", 1, "exact", ["engine", "electronic"],
     "控制进多少气的电子阀门，油门踏板其实是在指挥它。", "The electronic valve that meters air; your pedal really commands this.", "电子节气门 ETCS-i"),
    ("eng-air-cleaner-case", "Air Cleaner Case", "空气滤清器壳", G_ENGN, "aircl", 1, "exact", ["air", "plastic"],
     "装空气滤芯的塑料盒，发动机呼吸的第一站。", "The plastic box holding the air filter — the engine's first breath.", "PP，含滤芯"),
    ("eng-intake-duct", "Air Cleaner Inlet Duct", "进气管道", G_ENGN, "aircl", 1, "exact", ["air"],
     "从格栅接到滤清器盒的那根粗管。", "The fat tube from the grille to the filter box.", "吹塑 PE"),
    ("eng-radiator", "Radiator Assembly", "散热器（水箱）总成", G_ENGN, "radiator", 1, "exact", ["cooling"],
     "车头那片薄薄的「格栅」，把冷却液的热吹掉。", "The thin core at the nose that dumps coolant heat into the air.", "铝芯 + 塑料水室"),
    ("eng-radiator-hose-up", "Radiator Upper Hose", "散热器上水管", G_ENGN, "radiator", 1, "exact", ["cooling", "rubber"],
     "从发动机到水箱上部那根粗胶管，摸着最烫。", "The thick hose from engine to radiator top; it's the hottest one.", "EPDM 橡胶"),
    ("eng-radiator-hose-lo", "Radiator Lower Hose", "散热器下水管", G_ENGN, "radiator", 1, "exact", ["cooling", "rubber"],
     "水箱下部回发动机那根管。", "The hose returning coolant from the radiator bottom to the engine.", "EPDM 橡胶"),
    ("eng-reservoir-tank", "Coolant Reservoir Tank", "冷却液副水壶", G_ENGN, "radiator", 1, "exact", ["cooling"],
     "半透明的小壶，看液位就看它。", "The translucent bottle; check coolant level here.", "PP，带 MIN/MAX 刻度"),
    ("eng-water-pump", "Water Pump", "水泵", G_ENGN, "wpump", 1, "exact", ["cooling"],
     "推着冷却液在发动机里循环的泵。", "The pump that keeps coolant circulating through the engine.", "皮带驱动，含机械密封"),
    ("eng-thermostat", "Thermostat Housing", "节温器壳", G_ENGN, "wpump", 1, "exact", ["cooling"],
     "水温没到就不放行的小阀门，帮发动机快点热起来。", "A small valve that blocks flow until warm, so the engine heats up faster.", "开启温度约 82 °C"),
    ("eng-oil-filter", "Oil Filter", "机油滤清器", G_ENGN, "oil", 1, "exact", ["filter", "wear"],
     "滤掉机油里金属屑的小罐，每次保养都换。", "The small can that filters metal debris from the oil; replaced at every service.", "纸芯式，随保养更换"),
    ("eng-oil-pump", "Oil Pump", "机油泵", G_ENGN, "oil", 1, "exact", ["engine"],
     "把机油从油底壳抽上来送到各处的泵。", "Draws oil from the pan and pushes it everywhere it's needed.", "可变排量摆线泵"),
    ("eng-timing-chain", "Timing Chain & Tensioner", "正时链条与张紧器", G_ENGN, "timing", 1, "exact", ["engine"],
     "把曲轴和凸轮轴锁在同一个节拍上的链条，理论上终身免维护。", "The chain keeping crankshaft and camshafts in step; normally lasts the engine's life.", "静音链，含液压张紧"),
    ("eng-drive-belt", "Serpentine Drive Belt", "多楔带（附件皮带）", G_ENGN, "alt", 1, "exact", ["belt", "wear"],
     "一根皮带带动发电机、空调压缩机和水泵。", "One belt driving alternator, A/C compressor and water pump.", "6PK 多楔带"),
    ("eng-mount-rh", "Engine Mounting Insulator RH", "右发动机悬置", G_ENGN, "mount", 1, "exact", ["nvh", "rubber"],
     "把发动机吊在车身上的橡胶脚，主要挡抖动。", "The rubber foot hanging the engine off the body; it soaks up vibration.", "液压阻尼式"),
    ("eng-mount-lh", "Transmission Mounting Insulator LH", "左变速器悬置", G_ENGN, "mount", 1, "exact", ["nvh", "rubber"],
     "变速器那一侧的悬置脚。", "The mount on the transmission side.", "橡胶 + 金属骨架"),
    ("eng-mount-rear", "Rear Engine Mounting (Torque Rod)", "后悬置扭力杆", G_ENGN, "mount", 1, "exact", ["nvh"],
     "斜拉在下方的一根杆，防止起步时发动机往前翻。", "A rod low down that stops the engine rocking under acceleration.", "含橡胶衬套"),
    ("eng-fuel-tank", "Fuel Tank", "燃油箱", G_ENGN, "fueltank", 1, "exact", ["fuel"],
     "后排座椅底下的油箱，多数是塑料吹塑的。", "The tank under the rear seat, usually blow-moulded plastic.", "约 50 L，六层 HDPE"),
    ("eng-fuel-pump", "Fuel Pump & Sender Assembly", "燃油泵与油位传感器", G_ENGN, "fueltank", 1, "exact", ["fuel", "electric"],
     "泡在油箱里的泵，供油同时也报油量。", "Sits inside the tank; supplies fuel and reports the level.", "含滤网与浮子"),
    ("eng-fuel-filler-pipe", "Fuel Filler Pipe", "加油管", G_ENGN, "fueltank", 1, "exact", ["fuel"],
     "从加油口通到油箱的那根管。", "The pipe from the filler flap down to the tank.", "含防误加油口"),
    ("eng-fuel-rail", "Fuel Delivery Pipe (Rail)", "燃油分配管", G_ENGN, "inject", 1, "exact", ["fuel"],
     "横在气缸盖上的高压管，四个喷油嘴插在上面。", "The high-pressure rail across the head; the four injectors plug into it.", "不锈钢，含压力脉动阻尼"),
    ("eng-injector", "Fuel Injector", "喷油嘴", G_ENGN, "inject", 4, "exact", ["fuel", "precision"],
     "把汽油雾化喷进缸里的电磁阀，每缸一个。", "Solenoid nozzles that atomise petrol into the cylinders, one per cylinder.", "缸内直喷 + 歧管喷射"),
    ("eng-exhaust-front", "Exhaust Front Pipe", "排气前管", G_ENGN, "exhaust", 1, "exact", ["exhaust", "hot"],
     "催化器后面第一段管，常带一个柔性波纹节。", "The first pipe after the catalyst, usually with a flexible bellows.", "不锈钢，含挠性接头"),
    ("eng-catalytic", "Under-floor Catalytic Converter", "地板下三元催化器", G_ENGN, "exhaust", 1, "exact", ["exhaust", "emission"],
     "第二级净化器，把剩下的有害气体再烧一遍。", "The second-stage cleaner that finishes off the remaining pollutants.", "陶瓷载体，含铂钯铑"),
    ("eng-muffler", "Main Muffler & Tail Pipe", "主消声器与尾管", G_ENGN, "exhaust", 1, "exact", ["exhaust", "nvh"],
     "车尾那个大罐子，把排气声压下去。", "The big can at the tail that quiets the exhaust.", "不锈钢，三腔结构"),
    ("eng-ac-compressor", "A/C Compressor", "空调压缩机", G_ENGN, "ac", 1, "exact", ["hvac", "belt"],
     "空调的心脏，皮带带着它压缩冷媒。", "The heart of the A/C; the belt drives it to compress refrigerant.", "外控可变排量斜盘式"),
    ("eng-ac-condenser", "A/C Condenser", "空调冷凝器", G_ENGN, "ac", 1, "exact", ["hvac", "cooling"],
     "贴在水箱前面那片，把冷媒的热排到车外。", "The core in front of the radiator that dumps refrigerant heat outside.", "平行流铝制"),
    ("eng-hvac-unit", "Heater & Cooling Unit (HVAC Box)", "暖风与蒸发器总成", G_ENGN, "ac", 1, "exact", ["hvac"],
     "仪表台里面那个大黑箱，冷热风都从这儿分配。", "The big black box inside the dash that mixes and routes the air.", "含蒸发器、暖风芯体、风门电机"),
    ("eng-blower-motor", "Blower Motor", "鼓风机", G_ENGN, "ac", 1, "exact", ["hvac", "motor"],
     "吹风的那个小马达，风量档位就是调它。", "The little motor that blows air; the fan-speed knob controls it.", "含风扇蜗壳"),
    ("eng-vapor-canister", "Charcoal Canister", "炭罐", G_ENGN, "fueltank", 1, "exact", ["emission"],
     "吸住油箱蒸出来的汽油味，再送回发动机烧掉。", "Traps petrol vapour from the tank and feeds it back to be burned.", "活性炭，含电磁阀"),
    ("eng-jack", "Jack Assembly", "随车千斤顶", G_ENGN, "tool", 1, "exact", ["tool"],
     "换备胎时把车顶起来的剪式千斤顶。", "The scissor jack for lifting the car to change a wheel.", "剪式，1.0 t"),

    # ---- POWERTRAIN / CHASSIS ----
    ("pt-transaxle", "Transaxle Case (CVT)", "变速驱动桥壳（CVT）", G_PTCH, "transaxle", 1, "exact", ["driveline", "aluminium"],
     "变速箱，和差速器做成一体，直接接两根驱动轴。", "The gearbox; it houses the differential and drives both front shafts.", "Direct Shift-CVT 级"),
    ("pt-torque-converter", "Torque Converter", "液力变矩器", G_PTCH, "transaxle", 1, "exact", ["driveline"],
     "发动机和变速箱之间那个「油做的离合器」。", "The fluid coupling between engine and gearbox — a clutch made of oil.", "含锁止离合"),
    ("pt-driveshaft-lh", "Front Drive Shaft LH", "左前驱动轴", G_PTCH, "driveshaft", 1, "exact", ["driveline"],
     "把动力从变速箱送到左前轮的轴，两头是万向节。", "Carries torque from the gearbox to the left front wheel; CV joints at both ends.", "含内外等速万向节"),
    ("pt-driveshaft-rh", "Front Drive Shaft RH", "右前驱动轴", G_PTCH, "driveshaft", 1, "exact", ["driveline"],
     "右边那根驱动轴，通常比左边长、中间带减振块。", "The right shaft; usually longer, often with a damper.", "含中间支撑"),
    ("pt-strut-lh", "Front Shock Absorber Strut LH", "左前减振器支柱", G_PTCH, "fsusp", 1, "exact", ["suspension"],
     "前轮上方那根粗柱子，减振器和弹簧套在一起。", "The thick post above the front wheel: damper and spring in one unit.", "麦弗逊式，含顶胶轴承"),
    ("pt-strut-rh", "Front Shock Absorber Strut RH", "右前减振器支柱", G_PTCH, "fsusp", 1, "exact", ["suspension"],
     "前轮上方那根粗柱子，减振器和弹簧套在一起。", "The thick post above the front wheel: damper and spring in one unit.", "麦弗逊式，含顶胶轴承"),
    ("pt-coil-spring-front", "Front Coil Spring", "前螺旋弹簧", G_PTCH, "fsusp", 2, "exact", ["suspension"],
     "套在减振器外面的大弹簧，撑住车身重量。", "The big spring around the damper that carries the car's weight.", "左右各一"),
    ("pt-shock-rear", "Rear Shock Absorber", "后减振器", G_PTCH, "rsusp", 2, "exact", ["suspension"],
     "后轮的筒式减振器，管住弹簧别一直弹。", "The rear damper that stops the spring bouncing on and on.", "双筒充气式"),
    ("pt-coil-spring-rear", "Rear Coil Spring", "后螺旋弹簧", G_PTCH, "rsusp", 2, "exact", ["suspension"],
     "后轮那两根弹簧，和减振器分开装。", "The two rear springs, mounted separately from the dampers.", "左右各一"),
    ("pt-lower-arm-lh", "Front Lower Suspension Arm LH", "左前下摆臂", G_PTCH, "farm", 1, "exact", ["suspension"],
     "连接副车架和转向节的 L 形臂，决定前轮怎么动。", "The L-shaped arm from subframe to knuckle; it guides how the wheel moves.", "钢制冲焊，含球头"),
    ("pt-lower-arm-rh", "Front Lower Suspension Arm RH", "右前下摆臂", G_PTCH, "farm", 1, "exact", ["suspension"],
     "连接副车架和转向节的 L 形臂，决定前轮怎么动。", "The L-shaped arm from subframe to knuckle; it guides how the wheel moves.", "钢制冲焊，含球头"),
    ("pt-knuckle-lh", "Front Steering Knuckle LH", "左前转向节", G_PTCH, "fhub", 1, "exact", ["suspension", "cast"],
     "轮子、刹车、摆臂、拉杆全挂在这块铸件上。", "The casting that ties wheel, brake, arm and tie-rod together.", "铸铝或球铁"),
    ("pt-knuckle-rh", "Front Steering Knuckle RH", "右前转向节", G_PTCH, "fhub", 1, "exact", ["suspension", "cast"],
     "轮子、刹车、摆臂、拉杆全挂在这块铸件上。", "The casting that ties wheel, brake, arm and tie-rod together.", "铸铝或球铁"),
    ("pt-hub-front", "Front Axle Hub & Bearing", "前轮毂轴承单元", G_PTCH, "fhub", 2, "exact", ["bearing"],
     "轮子转起来靠它，异响、抖动常是它坏了。", "What the wheel actually spins on; hum or shimmy usually means it's worn.", "第三代轮毂单元，含 ABS 磁环"),
    ("pt-hub-rear", "Rear Axle Hub & Bearing", "后轮毂轴承单元", G_PTCH, "rhub", 2, "exact", ["bearing"],
     "后轮的轮毂轴承，结构比前轮简单。", "The rear hub bearing; simpler than the front.", "带法兰一体式"),
    ("pt-brake-disc-front", "Front Brake Disc Rotor", "前制动盘", G_PTCH, "fbrake", 2, "exact", ["brake", "wear"],
     "刹车片夹住的那个大铁盘，前轮的更大更厚。", "The big iron disc the pads squeeze; the fronts are larger and thicker.", "通风盘 φ275×22 级"),
    ("pt-brake-caliper-front", "Front Disc Brake Caliper", "前制动钳", G_PTCH, "fbrake", 2, "exact", ["brake"],
     "跨在刹车盘上的卡钳，里面的活塞把刹车片顶出去。", "The caliper straddling the disc; its piston pushes the pads out.", "单活塞浮钳"),
    ("pt-brake-pad-front", "Front Disc Brake Pad Kit", "前制动片", G_PTCH, "fbrake", 4, "exact", ["brake", "wear"],
     "真正磨损的摩擦块，薄了就得换。", "The friction blocks that actually wear; replace them when thin.", "低金属配方，一车四片"),
    ("pt-brake-disc-rear", "Rear Brake Disc Rotor", "后制动盘", G_PTCH, "rbrake", 2, "exact", ["brake", "wear"],
     "后轮的刹车盘，通常是实心的。", "The rear disc; usually solid rather than vented.", "实心盘 φ281×10 级"),
    ("pt-brake-caliper-rear", "Rear Disc Brake Caliper", "后制动钳", G_PTCH, "rbrake", 2, "exact", ["brake"],
     "后轮卡钳，常兼做驻车制动。", "The rear caliper; it often doubles as the parking brake.", "含驻车机构"),
    ("pt-brake-master", "Brake Master Cylinder & Booster", "制动主缸与真空助力器", G_PTCH, "master", 1, "exact", ["brake", "safety"],
     "踩下踏板先推它，再靠真空放大力气。", "Your pedal pushes this first; vacuum multiplies the effort.", "含制动液储液罐"),
    ("pt-brake-pedal", "Brake Pedal & Bracket", "制动踏板与支架", G_PTCH, "master", 1, "exact", ["control"],
     "脚下那块踏板和它的杠杆支架。", "The pedal underfoot and its lever bracket.", "钢制，含开关"),
    ("pt-steering-gear", "Steering Gear Assembly (EPS Rack)", "电动助力转向器", G_PTCH, "gearbox", 1, "exact", ["steering"],
     "横在副车架上的齿条，方向盘转它就推着两个前轮偏。", "The rack across the subframe; turning the wheel makes it push both front wheels.", "齿条式 EPS，含电机"),
    ("pt-tie-rod", "Steering Tie Rod End", "转向横拉杆球头", G_PTCH, "gearbox", 2, "exact", ["steering", "wear"],
     "齿条和转向节之间那根小杆，四轮定位调的就是它。", "The short link from rack to knuckle; wheel alignment is set here.", "含防尘罩，左右各一"),
    ("pt-steering-column", "Steering Column Assembly", "转向管柱总成", G_PTCH, "column", 1, "exact", ["steering", "safety"],
     "方向盘到齿条之间那根轴，撞车时会溃缩。", "The shaft from wheel to rack; it collapses in a crash.", "可溃缩，四向可调"),
    ("pt-steering-wheel", "Steering Wheel", "方向盘", G_PTCH, "column", 1, "exact", ["steering", "interior"],
     "手握的那个圈，中间藏着驾驶员气囊。", "The rim you hold; the driver airbag sits in the middle.", "φ370 mm，真皮包覆"),
    ("pt-wheel", "Disc Wheel (Rim)", "车轮轮辋", G_PTCH, "wheel", 4, "exact", ["wheel"],
     "轮胎套在上面的那个圈，铝的钢的都有。", "The rim the tyre mounts on; steel or alloy.", "16×6.5J 或 17×7J"),
    ("pt-tire", "Tire", "轮胎", G_PTCH, "wheel", 4, "exact", ["wheel", "wear"],
     "唯一接触地面的零件，四个巴掌大的接地面撑起整台车。", "The only parts touching the road; four palm-sized patches carry the whole car.", "205/55R16 或 225/40R18"),
    ("pt-spare-tire", "Spare Wheel & Tire", "备胎", G_PTCH, "wheel", 1, "exact", ["wheel"],
     "后备厢地板下的备用轮，多数是窄的临时胎。", "The spare under the trunk floor; usually a narrow temporary one.", "T125/70D16 临时胎"),
    ("pt-torsion-beam", "Rear Torsion Beam Axle", "后扭力梁", G_PTCH, "raxle", 1, "exact", ["suspension", "structure"],
     "把两个后轮连在一起的那根横梁（部分车型是多连杆）。", "The beam tying the rear wheels together (some trims use multi-link instead).", "闭口断面扭力梁"),
    ("pt-rear-carrier", "Rear Axle Carrier", "后轮支架", G_PTCH, "raxle", 2, "exact", ["suspension"],
     "后轮毂固定在上面的支架。", "The bracket the rear hub bolts to.", "钢制冲焊，左右各一"),
    ("pt-subframe-front", "Front Suspension Crossmember", "前副车架", G_PTCH, "crossmb", 1, "exact", ["structure"],
     "托住发动机、摆臂和转向器的那个大框，也叫元宝梁。", "The big cradle carrying engine, arms and steering rack.", "钢制焊接框架"),
    ("pt-stabilizer-front", "Front Stabilizer Bar", "前横向稳定杆", G_PTCH, "stabar", 1, "exact", ["suspension"],
     "一根 U 形钢棍，过弯时减少车身侧倾。", "A U-shaped bar that cuts body roll in corners.", "φ24 mm 空心杆"),
    ("pt-stabilizer-link", "Stabilizer Link", "稳定杆连接杆", G_PTCH, "stabar", 2, "exact", ["suspension", "wear"],
     "稳定杆两端的小连杆，坏了过坎会「咯噔」响。", "The short links at each end; worn ones knock over bumps.", "含球头，左右各一"),
    ("pt-parking-brake-lever", "Parking Brake Lever", "驻车制动手柄", G_PTCH, "parkbrk", 1, "exact", ["brake", "control"],
     "手刹拉杆（或电子手刹开关）。", "The handbrake lever, or the electric parking-brake switch.", "机械拉索式或电子式"),
    ("pt-shift-lever", "Transmission Shift Lever", "换挡杆总成", G_PTCH, "shift", 1, "exact", ["control"],
     "中控台上挂挡的那根杆。", "The lever on the console you shift with.", "含挡位指示与锁止"),
    ("pt-fuel-tank-guard", "Fuel Tank Protector", "油箱护板", G_PTCH, "crossmb", 1, "exact", ["protection"],
     "油箱下面那块挡板，防止石子砸中。", "The plate under the tank that stops stones hitting it.", "钢板 1.2 mm"),
    ("pt-engine-undercover", "Engine Under Cover", "发动机下护板", G_PTCH, "crossmb", 1, "exact", ["protection", "aero"],
     "机舱底下那块大塑料板，既护底也整流。", "The big plastic tray under the engine; it protects and smooths airflow.", "PP 复合板"),
]

# MESH 表里这 50 个降级为 has_mesh=false：太小、被埋在里面、或者建出来也认不出，
# 建了只会让画面变糊、draw call 白涨。任务书要的是恰好 110 个网格件，这里就是那把刀。
DEMOTE = {
    # body 12
    "body-fbumper-absorber", "body-glove-box", "body-carpet", "body-mudguard",
    "body-fuel-lid", "body-door-handle-outside", "body-headliner",
    "body-pillar-c-lh", "body-pillar-c-rh", "body-cowl",
    "body-rbumper-reinf", "body-dash-panel",
    # electrical 14
    "elec-license-lamp", "elec-interior-lamp", "elec-mirror-turn",
    "elec-battery-tray", "elec-body-ecu", "elec-airbag-ecu", "elec-steering-pad",
    "elec-park-sensor", "elec-bsm-sensor", "elec-speaker-rear",
    "elec-washer-tank", "elec-junction-cabin", "elec-horn", "elec-front-camera",
    # engine 13
    "eng-thermostat", "eng-oil-pump", "eng-timing-chain", "eng-injector",
    "eng-fuel-rail", "eng-vapor-canister", "eng-jack", "eng-blower-motor",
    "eng-fuel-filler-pipe", "eng-oil-filter", "eng-drive-belt",
    "eng-mount-rear", "eng-intake-duct",
    # powertrain / chassis 11
    "pt-brake-pad-front", "pt-tie-rod", "pt-stabilizer-link",
    "pt-parking-brake-lever", "pt-shift-lever", "pt-fuel-tank-guard",
    "pt-rear-carrier", "pt-torque-converter", "pt-coil-spring-rear",
    "pt-hub-rear", "pt-spare-tire",
}

# ---------------------------------------------------------- 非网格零件生成模板
# (en, zh, tags, qty_lo, qty_hi, qty_kind, role_zh, role_en)
SMALL = [
    ("Bolt", "螺栓", ["fastener"], 2, 8, "exact", "把它固定住的螺栓，扭矩有讲究，不能凭手感。", "The bolt that holds it; torque matters, don't guess by feel."),
    ("Nut", "螺母", ["fastener"], 2, 8, "exact", "配套的螺母，多数是自锁的，拆了建议换新。", "The matching nut; usually self-locking, best replaced once removed."),
    ("Washer", "垫圈", ["fastener"], 2, 8, "exact", "垫在螺栓下面分散压力，防止压坏薄板。", "Spreads load under the bolt so thin metal doesn't dent."),
    ("Clip", "卡扣", ["fastener", "plastic"], 4, 16, "approx", "塑料卡扣，拆内饰时最容易崩断的就是它。", "The plastic clip that most often snaps when trim comes off."),
    ("Screw", "自攻螺钉", ["fastener"], 2, 10, "approx", "直接拧进塑料件的小螺钉。", "A small screw driven straight into plastic."),
    ("Grommet", "护线套", ["seal", "rubber"], 1, 4, "exact", "线束穿过钣金孔时套的胶圈，防磨也防水。", "Rubber ring where a harness passes through metal; stops chafing and leaks."),
    ("Gasket", "垫片", ["seal"], 1, 2, "exact", "两个面之间的密封垫，漏油漏水常是它老化。", "The seal between two faces; leaks usually mean it's aged."),
    ("O-Ring", "O 形圈", ["seal", "rubber"], 1, 4, "exact", "圆截面胶圈，靠压缩量密封。", "A round-section rubber ring that seals by being squashed."),
    ("Weatherstrip", "密封条", ["seal", "rubber"], 1, 2, "exact", "挡风挡雨挡噪音的那圈胶条。", "The rubber strip that keeps out wind, water and noise."),
    ("Bracket", "支架", ["bracket"], 1, 3, "exact", "把它挂到车身上的金属支架。", "The metal bracket that hangs it on the body."),
    ("Bushing", "衬套", ["rubber", "nvh"], 1, 4, "exact", "橡胶衬套，允许小幅摆动又不传震。", "A rubber bush that allows small movement without passing vibration on."),
    ("Retainer", "扣件", ["fastener"], 2, 8, "approx", "起固定作用的小扣件。", "A small retaining piece."),
    ("Cushion", "缓冲垫", ["rubber", "nvh"], 1, 4, "exact", "橡胶缓冲块，防止金属直接磕碰。", "A rubber pad so metal never hits metal."),
    ("Cover", "护盖", ["cover", "plastic"], 1, 2, "exact", "遮丑兼防尘的盖子。", "A cover for looks and to keep dirt out."),
    ("Hose", "软管", ["hose", "rubber"], 1, 3, "exact", "输送液体或气体的软管。", "A flexible line carrying fluid or air."),
    ("Clamp", "卡箍", ["fastener"], 1, 4, "exact", "箍住软管接头的金属环。", "The metal band that clamps a hose onto its spigot."),
    ("Connector", "接插件", ["electric"], 1, 3, "exact", "线束插头，接触不良会导致偶发故障。", "A harness plug; a poor contact causes intermittent faults."),
    ("Wire Harness", "线束", ["electric"], 1, 1, "exact", "一束电线，车上的神经。", "A bundle of wires — the car's nerves."),
    ("Seal Ring", "密封环", ["seal"], 1, 2, "exact", "环形密封件。", "A ring-shaped seal."),
    ("Plug", "堵盖", ["plastic"], 1, 6, "approx", "堵住工艺孔的小塞子。", "A small plug filling a manufacturing hole."),
    ("Spacer", "衬垫块", ["bracket"], 1, 4, "exact", "调整间隙用的垫块。", "A block used to set a gap."),
    ("Insulator", "隔热垫", ["nvh", "heat"], 1, 2, "exact", "隔热或隔音的一片垫。", "A pad that blocks heat or sound."),
    ("Stopper", "限位块", ["rubber"], 1, 4, "exact", "限制行程的小块，防止走过头。", "A small block that limits travel."),
    ("Hinge", "铰链", ["hinge"], 1, 2, "exact", "转动的合页，开合都靠它。", "The hinge everything pivots on."),
    ("Moulding", "装饰条", ["trim", "exterior"], 1, 2, "exact", "外观装饰条，也兼顾密封。", "A trim strip that also helps seal."),
    ("Sensor", "传感器", ["sensor", "electric"], 1, 2, "exact", "测某个量再报给电脑的小元件。", "A small device that measures something and reports it to a computer."),
    ("Switch", "开关", ["switch", "electric"], 1, 2, "exact", "手动或被动触发的开关。", "A switch, operated by hand or by motion."),
    ("Filter", "滤芯", ["filter", "wear"], 1, 1, "exact", "过滤脏东西的芯子，属易损件。", "A filter element; a routine wear item."),
    ("Bearing", "轴承", ["bearing"], 1, 2, "exact", "让轴转得顺的滚动件。", "The rolling element that lets a shaft spin freely."),
    ("Pin", "销", ["fastener"], 1, 4, "exact", "定位或连接用的销钉。", "A pin for locating or linking two parts."),
]

SUPPLIER_POOL = {
    "lighting": [("Koito Manufacturing", "丰田系灯具主力供应商，日系车前照灯份额长期第一。", "medium"),
                 ("Stanley Electric", "常见于丰田后组合灯与雾灯。", "low")],
    "brake":    [("Advics", "爱信 / 电装 / 住友合资的制动件公司，丰田制动系统常见来源。", "medium"),
                 ("Akebono Brake", "Brake friction and caliper supplier widely used by Japanese OEMs.", "low")],
    "driveline":[("Aisin", "变速器与驱动系大厂，丰田持股。", "medium"),
                 ("JTEKT", "Driveline and steering components; a Toyota Group company.", "low")],
    "steering": [("JTEKT", "电动助力转向系统主要厂商之一。", "medium"),
                 ("NSK", "Steering columns and bearings.", "low")],
    "engine":   [("Denso", "丰田系最大的零部件厂，发动机电控件覆盖极广。", "medium"),
                 ("Aisin", "Engine ancillaries and water pumps.", "low")],
    "electric": [("Denso", "ECU、传感器、空调件的常见来源。", "medium"),
                 ("Tokai Rika", "Switches, locks and column modules.", "low")],
    "ecu":      [("Denso", "发动机与车身电脑的主要供应商。", "medium"),
                 ("Aisin AW", "Powertrain control units.", "low")],
    "interior": [("Toyota Boshoku", "座椅、内饰与滤清器，丰田集团内企业。", "medium"),
                 ("Toyoda Gosei", "Rubber and plastic interior/exterior parts.", "low")],
    "wheel":    [("Bridgestone", "原厂配套轮胎常见品牌之一。", "medium"),
                 ("Toyo Tire", "Also seen as OE fitment on Corolla in some markets.", "low")],
    "suspension":[("KYB", "减振器主流厂商。", "medium"),
                 ("Showa", "Shock absorbers and struts.", "low")],
    "hvac":     [("Denso", "空调系统几乎是丰田的默认选择。", "high"),
                 ("Toyota Industries", "A/C compressors.", "low")],
    "exhaust":  [("Sango", "排气系统长期配套丰田。", "medium"),
                 ("Futaba Industrial", "Exhaust and stamped body parts.", "low")],
    "fuel":     [("Denso", "燃油泵与喷油嘴。", "medium"),
                 ("Yachiyo Industry", "Plastic fuel tanks.", "low")],
    "glass":    [("AGC", "汽车玻璃三大厂之一。", "medium"),
                 ("Nippon Sheet Glass", "Automotive glazing.", "low")],
    "panel":    [("Toyota Auto Body", "车身冲压与总装，丰田全资子公司。", "medium"),
                 ("Futaba Industrial", "Stamped structural panels.", "low")],
    "power":    [("GS Yuasa", "日系车原厂电瓶常见品牌。", "medium"),
                 ("Denso", "Alternators and starters.", "medium")],
    "_default": [("Toyota Group supplier", "该品类的公开信息里常见的配套厂商，未逐件核实。", "low")],
}

TAG_TO_SUPPLIER = [
    ("lighting", "lighting"), ("brake", "brake"), ("driveline", "driveline"),
    ("steering", "steering"), ("hvac", "hvac"), ("exhaust", "exhaust"),
    ("fuel", "fuel"), ("glass", "glass"), ("ecu", "ecu"), ("power", "power"),
    ("suspension", "suspension"), ("wheel", "wheel"), ("interior", "interior"),
    ("engine", "engine"), ("panel", "panel"), ("electric", "electric"),
]


def pick_suppliers(rng, tags):
    key = "_default"
    for tag, sk in TAG_TO_SUPPLIER:
        if tag in tags:
            key = sk
            break
    pool = SUPPLIER_POOL[key]
    n = 1 if rng.random() < 0.45 else min(2, len(pool))
    out = []
    for name, note, conf in pool[:n]:
        out.append({
            "name": name,
            "note": note,
            "confidence": conf,
            "source": "stub-generated / 示例数据，非官方 BOM",
        })
    return out


def make_pn(rng, has=True):
    if not has:
        return ""
    return "%05d-%05d" % (rng.randint(10000, 99999), rng.randint(10000, 99999))


def build():
    rng = random.Random(20260730)
    parts = []
    ids = set()

    def add(rec):
        assert rec["id"] not in ids, "duplicate id: " + rec["id"]
        ids.add(rec["id"])
        parts.append(rec)

    # 四个顶层总成，作为 parent 的根
    roots = [
        ("asm-body", G_BODY, "Body Group Assembly", "车身部分总成", "把车身钣金、玻璃、内外饰算作一块看。",
         "Everything that makes the shell, glass and trim."),
        ("asm-electrical", G_ELEC, "Electrical Group Assembly", "电气部分总成", "灯光、电脑、传感器、音响这一整套。",
         "Lighting, computers, sensors and audio as one system."),
        ("asm-engine", G_ENGN, "Engine / Fuel / Tool Group Assembly", "发动机与燃油部分总成", "发动机本体、冷却、燃油、排气和空调。",
         "The engine itself plus cooling, fuel, exhaust and A/C."),
        ("asm-chassis", G_PTCH, "Power Train / Chassis Group Assembly", "传动与底盘部分总成", "变速箱、传动轴、悬架、制动、转向、车轮。",
         "Gearbox, driveshafts, suspension, brakes, steering and wheels."),
    ]
    for rid, g, en, zh, rzh, ren in roots:
        add({
            "id": rid, "group": g,
            "subgroup_en": "Group Root", "subgroup_zh": "部分总成",
            "name_en": en, "name_zh": zh, "oem_pn": "", "parent": "",
            "connects_to": [], "role_zh": rzh, "role_en": ren,
            "qty": 1, "qty_kind": "exact", "tags": ["assembly"],
            "has_mesh": False, "spec": "", "suppliers": [],
        })

    root_of = {G_BODY: "asm-body", G_ELEC: "asm-electrical",
               G_ENGN: "asm-engine", G_PTCH: "asm-chassis"}

    # 主表：110 个有网格 + 50 个降级的整件
    by_sub = {}
    for (pid, en, zh, grp, sgk, qty, qk, tags, rzh, ren, spec) in MESH:
        sub_en, sub_zh = SG[sgk]
        by_sub.setdefault((grp, sgk), []).append(pid)
        add({
            "id": pid, "group": grp,
            "subgroup_en": sub_en, "subgroup_zh": sub_zh,
            "name_en": en, "name_zh": zh,
            "oem_pn": make_pn(rng, rng.random() < 0.82),
            "parent": root_of[grp], "connects_to": [],
            "role_zh": rzh, "role_en": ren,
            "qty": qty, "qty_kind": qk, "tags": tags,
            "has_mesh": pid not in DEMOTE, "spec": spec,
            "suppliers": pick_suppliers(rng, tags),
        })

    # 同图组内互相 connects_to，跨图组再连一两条
    idx = {p["id"]: p for p in parts}
    all_mesh_ids = [p["id"] for p in parts if p["has_mesh"]]
    for key, members in by_sub.items():
        for pid in members:
            peers = [m for m in members if m != pid]
            rng.shuffle(peers)
            links = peers[:2]
            outsider = rng.choice(all_mesh_ids)
            if outsider != pid and outsider not in links:
                links.append(outsider)
            idx[pid]["connects_to"] = links

    # 非网格小件：每个网格零件挂 2~3 个
    templates = list(SMALL)
    for (pid, en, zh, grp, sgk, qty, qk, tags, rzh, ren, spec) in MESH:
        sub_en, sub_zh = SG[sgk]
        n = 2 if rng.random() < 0.55 else 3
        chosen = rng.sample(templates, n)
        for i, (ten, tzh, ttags, qlo, qhi, tqk, trzh, tren) in enumerate(chosen):
            sid = "%s-%s%d" % (pid, ten.lower().replace(" ", "-"), i + 1)
            q = rng.randint(qlo, qhi)
            add({
                "id": sid, "group": grp,
                "subgroup_en": sub_en, "subgroup_zh": sub_zh,
                "name_en": "%s for %s" % (ten, en),
                "name_zh": "%s（%s）" % (tzh, zh),
                "oem_pn": make_pn(rng, rng.random() < 0.55),
                "parent": pid, "connects_to": [pid],
                "role_zh": trzh, "role_en": tren,
                "qty": q, "qty_kind": tqk,
                "tags": ttags, "has_mesh": False,
                "spec": "", "suppliers": pick_suppliers(rng, ttags) if rng.random() < 0.5 else [],
            })

    return parts


def main():
    parts = build()
    mesh_n = sum(1 for p in parts if p["has_mesh"])

    doc = {
        "vehicle": {
            "make": "Toyota",
            "model": "Corolla",
            "model_zh": "卡罗拉",
            "generation": "E210 (12th gen)",
            "body_style": "Sedan",
            "market": "generic",
            "data_kind": "stub",
            "note_zh": "示例数据：零件号、供应商、规格均为程序生成，不可当真，仅供 B 开发 3D 与界面时占位。",
            "note_en": "Stub data: part numbers, suppliers and specs are generated placeholders. Not real. For UI development only.",
            "generated_by": "tools/make_stub.py",
        },
        "parts": parts,
    }

    # ------- 自检：不满足就别写文件 -------
    errs = []
    if len(parts) < 350:
        errs.append("总条数 %d < 350" % len(parts))
    if mesh_n != 110:
        errs.append("has_mesh=true 条数 %d != 110" % mesh_n)
    ids = set()
    for p in parts:
        if set(p.keys()) != set(FIELDS):
            errs.append("字段不符 %s: 多 %s 少 %s" % (
                p["id"], sorted(set(p.keys()) - set(FIELDS)), sorted(set(FIELDS) - set(p.keys()))))
            break
        if p["id"] in ids:
            errs.append("id 重复 " + p["id"])
        ids.add(p["id"])
        if p["group"] not in (G_BODY, G_ELEC, G_ENGN, G_PTCH):
            errs.append("group 非法 %s: %s" % (p["id"], p["group"]))
        if p["qty_kind"] not in ("exact", "approx"):
            errs.append("qty_kind 非法 %s" % p["id"])
        if not isinstance(p["has_mesh"], bool):
            errs.append("has_mesh 不是布尔 %s" % p["id"])
    for p in parts:
        if p["parent"] and p["parent"] not in ids:
            errs.append("parent 悬空 %s -> %s" % (p["id"], p["parent"]))
        for c in p["connects_to"]:
            if c not in ids:
                errs.append("connects_to 悬空 %s -> %s" % (p["id"], c))

    if errs:
        for e in errs[:20]:
            print("SELFCHECK FAIL:", e)
        raise SystemExit(1)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    approx = sum(1 for p in parts if p["qty_kind"] == "approx")
    subs = len({(p["group"], p["subgroup_en"]) for p in parts})
    print("wrote", OUT)
    print("  parts        =", len(parts))
    print("  has_mesh=true=", mesh_n)
    print("  qty approx   =", approx)
    print("  subgroups    =", subs)
    print("  bytes        =", os.path.getsize(OUT))
    print("SELFCHECK OK")


if __name__ == "__main__":
    sys.exit(main())
