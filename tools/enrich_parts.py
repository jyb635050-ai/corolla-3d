# -*- coding: utf-8 -*-
"""给 data/parts.json 补专业拆解基准的四个维度：材料 / 成型工艺 / 连接方式 / 重量。

为什么不从 3D 几何算重量：这套 3D 是示意模型不是数模——覆盖件是零厚度单层壳，
同槽位的多个零件还共用同一份占位几何（车顶板和天窗玻璃算出来的体积一模一样）。
拿它乘密度会得到看着精确、实则错误的数。所以重量走「按品类的工程经验值」，
逐条记 basis 和 conf，整车合计对整备质量做自检。

材料 / 工艺 / 连接方式用受控词表（枚举码），不用自由文本 —— 否则没法做
「整车材料构成」「焊点总数」这类聚合，而聚合正是专业基准工具的价值所在。

用法：uv run --no-project python tools/enrich_parts.py         # 只看会改什么
     uv run --no-project python tools/enrich_parts.py --write # 真写回
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'parts.json')

# ── 受控词表：材料。密度只用于合理性自检，不参与重量赋值。
MATERIALS = {
    'steel_mild':    ('低碳钢板', 'Mild steel sheet', 7850),
    'steel_hss':     ('高强度钢', 'High-strength steel', 7850),
    'steel_spring':  ('弹簧钢', 'Spring steel', 7850),
    'steel_bearing': ('轴承钢 GCr15', 'Bearing steel (100Cr6)', 7850),
    'cast_iron':     ('灰铸铁', 'Grey cast iron', 7200),
    'alu_cast':      ('铸铝合金', 'Cast aluminium', 2700),
    'alu_sheet':     ('铝板', 'Aluminium sheet', 2700),
    'copper':        ('铜', 'Copper', 8960),
    'plastic_pp':    ('聚丙烯 PP', 'Polypropylene (PP)', 950),
    'plastic_pa66':  ('玻纤增强尼龙 PA66-GF', 'Glass-filled PA66', 1350),
    'plastic_abs':   ('ABS', 'ABS', 1050),
    'plastic_pc':    ('聚碳酸酯 PC', 'Polycarbonate (PC)', 1200),
    'rubber_epdm':   ('三元乙丙橡胶 EPDM', 'EPDM rubber', 1200),
    'rubber_nr':     ('天然橡胶复合', 'Rubber compound', 1150),
    'glass_lam':     ('夹层玻璃', 'Laminated glass', 2500),
    'glass_temp':    ('钢化玻璃', 'Tempered glass', 2500),
    'foam_pu':       ('聚氨酯发泡', 'PU foam', 45),
    'textile':       ('织物 / 面料', 'Textile', 300),
    'lead_acid':     ('铅酸（铅+电解液）', 'Lead-acid', 2100),
    'ceramic':       ('陶瓷载体', 'Ceramic substrate', 1700),
    'friction':      ('摩擦材料', 'Friction material', 2200),
    'mixed':         ('多材料总成', 'Multi-material assembly', 2000),
}

# ── 受控词表：成型工艺
PROCESSES = {
    'stamping':   ('冲压', 'Stamping'),
    'casting_die':('压铸', 'High-pressure die casting'),
    'casting_sand':('砂型铸造', 'Sand casting'),
    'forging':    ('锻造', 'Forging'),
    'machining':  ('机加工', 'Machining'),
    'grinding':   ('磨削', 'Grinding'),
    'injection':  ('注塑', 'Injection moulding'),
    'blow_mold':  ('吹塑', 'Blow moulding'),
    'extrusion':  ('挤出', 'Extrusion'),
    'welding':    ('焊接总成', 'Welded assembly'),
    'winding':    ('绕线 / 电机装配', 'Winding / motor assembly'),
    'assembly':   ('装配总成', 'Assembly'),
    'float_glass':('浮法+钢化/夹层', 'Float glass, tempered/laminated'),
    'foaming':    ('发泡成型', 'Foam moulding'),
    'electronic': ('电子件装配', 'Electronics assembly'),
}

# ── 参数化成本模型
# 这不是丰田的真实采购价，也没人公开那个。这是一个透明的估算模型：
#     单件成本 = 重量kg × (材料单价 + 该工艺的加工费率) + 紧固件数 × 单价
# 三张系数表全摆在下面，可查、可改、可复算 —— 这正是 Munro「快速成本估算」的原理。
# 界面上一律标 cost_basis=parametric_model，不许当成真实成本用。
# 系数量级参考中国市场 2024 年前后的常见水平，单位人民币元。
MAT_PRICE = {          # 元/kg，含材料利用率损耗
    'steel_mild': 7, 'steel_hss': 9, 'steel_spring': 13, 'steel_bearing': 20,
    'cast_iron': 6, 'alu_cast': 24, 'alu_sheet': 28, 'copper': 72,
    'plastic_pp': 13, 'plastic_pa66': 34, 'plastic_abs': 17, 'plastic_pc': 32,
    'rubber_epdm': 19, 'rubber_nr': 17, 'glass_lam': 30, 'glass_temp': 22,
    'foam_pu': 32, 'textile': 48, 'lead_acid': 15, 'ceramic': 130,
    'friction': 42, 'mixed': 32,
}
PROC_RATE = {          # 元/kg，含设备折旧与人工
    'stamping': 5, 'casting_die': 13, 'casting_sand': 9, 'forging': 11,
    'machining': 26, 'grinding': 36, 'injection': 9, 'blow_mold': 7,
    'extrusion': 6, 'welding': 16, 'winding': 62, 'assembly': 22,
    'float_glass': 11, 'foaming': 13, 'electronic': 160,
}
FASTENER_COST = 0.6    # 元/个，含件本身与装配工时分摊

# ── 连接方式词表
FASTEN = {
    'bolt':       ('螺栓', 'Bolt'),
    'screw':      ('螺钉', 'Screw'),
    'nut':        ('螺母', 'Nut'),
    'clip':       ('卡扣', 'Clip'),
    'weld_spot':  ('电阻点焊', 'Spot weld'),
    'weld_seam':  ('连续焊缝', 'Seam weld'),
    'rivet':      ('铆接', 'Rivet'),
    'adhesive':   ('结构胶粘接', 'Structural adhesive'),
    'press_fit':  ('过盈压装', 'Press fit'),
    'snap':       ('卡接', 'Snap fit'),
    'hose_clamp': ('管夹', 'Hose clamp'),
    'connector':  ('电气插接件', 'Electrical connector'),
    'thread_in':  ('螺纹旋入', 'Threaded in'),
}

# ── 规则表：命中即赋值。顺序即优先级，先具体后笼统。
# (匹配器, 材料, 工艺, 连接方式, 单件重量克, 把握度)
# 重量是该品类在紧凑级轿车上的常见量级，来源是通用工程经验，不是丰田官方数据 —— 一律标 typical。
def kw(*words):
    # 只按传进来的那段文字匹配。零件名和图组名分两遍打，不能混：
    # 官方图组名往往含好几个零件（「Front Disc Brake Caliper & Dust Cover」），
    # 混在一起打，前制动钳就会继承防尘套的规则，被判成橡胶注塑件。实测踩过。
    pat = re.compile('|'.join(words), re.I)
    return lambda text: pat.search(text or '')

def tag(*ts):
    s = set(ts)
    f = lambda text: False           # noqa: E731  占位，tag 规则走 p 而不是文字
    f.tags = s
    return f

RULES = [
    # ── 小五金必须排最前。规则是按名字里的关键词匹配的，而丰田的小件名里带着它所属总成的名字
    #    （「缸盖螺栓」含 cylinder head、「轮毂盖」含 hub）。排在后面就会继承总成的重量：
    #    实测出现过缸盖螺栓 14kg、轮毂盖 9.2kg、放油螺塞垫片 92kg。顺序即优先级，别往后挪。
    (kw(r'\bbolt\b|\bnut\b|\bscrew\b|\bwasher\b|\bstud\b'), 'steel_hss', 'forging', [('thread_in', '', 1)], 35),
    (kw(r'gasket|\bseal\b|\bo-?ring\b|packing|grommet|\bring\b'), 'rubber_nr', 'injection', [('press_fit', '', 1)], 25),
    (kw(r'\bclip\b|\bclamp\b|retainer|\bcap\b|\bplug\b|\bcover,? hole\b'), 'plastic_pp', 'injection', [('snap', '', 1)], 30),
    (kw(r'\bpin\b|\bkey\b|\bshim\b|spacer|bushing'), 'steel_mild', 'machining', [('press_fit', '', 1)], 60),
    (kw(r'\bvalve,? (intake|exhaust)\b|valve stem'), 'steel_hss', 'forging', [('press_fit', '', 1)], 85),
    (kw(r'piston ring|\bring set\b'),   'cast_iron',   'machining',   [('press_fit', '', 1)],               45),
    (kw(r'\bcenter cap\b|ornament|\bemblem\b|badge'), 'plastic_abs', 'injection', [('snap', '', 3)],        120),
    (kw(r'valve,? tire pressure|tire pressure|\bvalve stem\b'), 'mixed', 'electronic', [('thread_in', '', 1)], 55),

    # ── 零件类型规则。用 ^ 锚定，专门配合 head_noun 的第零遍匹配：
    #    「Bearing(For Alternator Drive End Frame)」的主体词就是 Bearing，是个轴承，
    #    不是发电机。没有这批规则，主体词匹配会落空，又掉回去继承总成的重量。
    (kw(r'^bearing'),                   'steel_bearing', 'grinding',  [('press_fit', '', 1)],              250),
    (kw(r'^race\b|^outer race|^inner race'), 'steel_bearing', 'grinding', [('press_fit', '', 1)],          120),
    (kw(r'^pulley'),                    'steel_hss',   'machining',   [('bolt', 'M10', 1)],                700),
    (kw(r'^rotor'),                     'copper',      'winding',     [('press_fit', '', 1)],             2500),
    (kw(r'^stator|^coil assy'),         'copper',      'winding',     [('bolt', 'M6', 3)],                2000),
    (kw(r'^regulator'),                 'mixed',       'electronic',  [('screw', 'M5', 3)],                200),
    (kw(r'^lamp\b|^bulb'),              'plastic_pc',  'injection',   [('screw', 'M4', 2)],                300),
    (kw(r'^register\b'),                'plastic_pp',  'injection',   [('clip', '', 4)],                   380),
    (kw(r'^duct\b'),                    'plastic_pp',  'injection',   [('clip', '', 4)],                   380),
    (kw(r'^case\b|^housing'),           'plastic_pp',  'injection',   [('screw', 'M5', 4)],                420),
    (kw(r'^cable\b|^wire\b|^harness'),  'copper',      'assembly',    [('connector', '', 4)],              600),
    (kw(r'^switch\b|^relay\b'),         'plastic_abs', 'electronic',  [('clip', '', 2)],                   150),
    (kw(r'^sensor\b'),                  'mixed',       'electronic',  [('bolt', 'M6', 1)],                  90),
    (kw(r'^fork\b|^shift fork'),        'steel_hss',   'forging',     [('press_fit', '', 1)],              320),
    (kw(r'^disc\b'),                    'cast_iron',   'casting_sand',[('bolt', 'M12×1.25', 5)],          8400),
    (kw(r'^terminal'),                  'copper',      'stamping',    [('bolt', 'M6', 1)],                  80),
    (kw(r'^shield\b'),                  'plastic_pp',  'injection',   [('clip', '', 6)],                   380),
    (kw(r'^hinge\b'),                   'steel_hss',   'stamping',    [('bolt', 'M8', 4)],                 900),
    (kw(r'^lock\b|^striker'),           'steel_hss',   'stamping',    [('bolt', 'M8', 3)],                 700),
    (kw(r'^heater\b'),                  'mixed',       'assembly',    [('clip', '', 4)],                   260),
    (kw(r'^adjuster|^slide rail'),      'steel_hss',   'stamping',    [('bolt', 'M8', 4)],                1600),
    (kw(r'^air bag|^inflator'),         'mixed',       'assembly',    [('bolt', 'M6', 2)],                 900),
    (kw(r'^headrest|^head rest'),       'foam_pu',     'foaming',     [('press_fit', '', 1)],              900),
    # 座椅里的弹簧是坐垫/靠背的蛇形弹簧（几百克），不是悬架的螺旋弹簧（3kg 级），
    # 主体词都叫 Spring，必须靠这条排在悬架弹簧规则之前把它们分开。
    (kw(r'spring sub-?assy,? (front|rear) seat|seat (cushion|back) spring'),
                                        'steel_spring', 'forging',    [('clip', '', 6)],                   600),

    # ── 审计（tools/audit_weights.py）挑出来后补的具名规则。
    #    这些原来落到兜底 350g，被「总成却只有 350g」那条抓出来。
    (kw(r'steering wheel'),             'mixed',       'assembly',    [('nut', 'M16', 1)],                2600),
    (kw(r'evaporator'),                 'alu_sheet',   'assembly',    [('bolt', 'M6', 3)],                2100),
    (kw(r'combination meter|meter assy|instrument cluster'), 'mixed', 'electronic', [('screw', 'M5', 4)], 780),
    (kw(r'spoiler'),                    'plastic_pp',  'injection',   [('bolt', 'M6', 6)],                1500),
    (kw(r'mirror'),                     'mixed',       'assembly',    [('bolt', 'M6', 3)],                 620),
    (kw(r'duct|register'),              'plastic_pp',  'injection',   [('clip', '', 4)],                   380),
    (kw(r'tensioner|idler'),            'steel_hss',   'machining',   [('bolt', 'M10', 1)],                620),
    (kw(r'cup holder|console box|glove'), 'plastic_abs','injection',  [('screw', 'M5', 4)],                680),
    (kw(r'release cylinder|clutch release'), 'alu_cast','casting_die',[('bolt', 'M8', 2)],                 540),
    (kw(r'injector'),                   'steel_hss',   'machining',   [('clip', '', 1)],                    95),
    (kw(r'\bcamera\b'),                 'mixed',       'electronic',  [('screw', 'M4', 3)],                160),
    (kw(r'reflector|reflex'),           'plastic_pc',  'injection',   [('snap', '', 2)],                    60),
    (kw(r'license plate lamp|number plate'), 'plastic_pc','injection',[('screw', 'M4', 2)],                 80),
    (kw(r'smart key|transmitter|key,? transmitter'), 'mixed', 'electronic', [('snap', '', 1)],              40),
    (kw(r'\bjack\b|wheel wrench|handle,? jack'), 'steel_mild', 'stamping', [('bolt', 'M8', 1)],           2200),
    (kw(r'egr cooler'),                 'steel_hss',   'welding',     [('bolt', 'M8', 4)],                2400),
    (kw(r'throttle'),                   'alu_cast',    'casting_die', [('bolt', 'M6', 4)],                 850),
    (kw(r'\bboot\b|\bcover,? drive shaft\b|dust cover'), 'rubber_epdm', 'injection', [('hose_clamp', '', 2)], 180),
    (kw(r'filler plug|drain plug|plug,? .*(filler|drain)'), 'steel_mild', 'machining', [('thread_in', '', 1)], 45),
    (kw(r'\bspeaker\b'),                'mixed',       'assembly',    [('screw', 'M5', 4)],                460),

    (kw(r'\btire\b|\btyre\b'),          'rubber_nr',   'assembly',    [('press_fit', '', 1)],            9000),
    (kw(r'disc wheel|\brim\b|wheel,? disc'), 'alu_cast','casting_die', [('bolt', 'M12×1.25', 5)],         9200),
    (kw(r'brake.*disc|disc,? (front|rear)|rotor'), 'cast_iron', 'casting_sand', [('bolt', 'M12×1.25', 5)], 8400),
    (kw(r'pad kit|brake pad'),          'friction',    'assembly',    [('clip', '', 4)],                  1100),
    (kw(r'caliper|cylinder assy.*disc brake|disc brake.*cylinder'), 'alu_cast', 'casting_die', [('bolt', 'M12', 2)], 3600),
    (kw(r'hub|knuckle'),                'steel_hss',   'forging',     [('bolt', 'M12', 4)],               4200),
    (tag('bearing'),                    'steel_bearing','grinding',   [('press_fit', '', 1)],              420),
    (kw(r'coil spring|spring,? coil'),  'steel_spring','forging',     [('press_fit', '', 1)],             3100),
    (kw(r'shock absorber|strut|absorber'), 'steel_mild','assembly',   [('bolt', 'M12', 3)],               4300),
    (kw(r'stabilizer|suspension arm|control arm|trailing arm|lower arm'), 'steel_hss', 'stamping', [('bolt', 'M14', 2)], 3400),
    (kw(r'crossmember|sub-?frame|suspension member'), 'steel_hss', 'welding', [('bolt', 'M14', 6)],      16000),
    (kw(r'drive shaft|half shaft|axle shaft'), 'steel_hss', 'forging', [('press_fit', '', 1)],            8600),
    (kw(r'transaxle|transmission case|torque converter|planetary|valve body|differential'), 'alu_cast', 'casting_die', [('bolt', 'M10', 8)], 6500),
    # 整机和裸缸体不能共用一条规则：Engine Assy Partial 是带缸盖曲柄连杆的半总成（约 92kg），
    # Cylinder Block 是光缸体（约 30kg）。混在一起，气缸体就顶着整机的重量。
    (kw(r'sprocket|timing gear|gear or sprocket'), 'steel_hss', 'forging', [('bolt', 'M10', 1)],           800),
    (kw(r'engine assy|partial engine'), 'alu_cast', 'casting_die', [('bolt', 'M12', 8)],                 92000),
    (kw(r'cylinder block|block sub-?assy'), 'alu_cast', 'casting_die', [('bolt', 'M12', 10)],            30000),
    (kw(r'cylinder head'),              'alu_cast',    'casting_die', [('bolt', 'M11', 10)],             14000),
    (kw(r'head cover|cylinder head cover'), 'plastic_pa66', 'injection', [('bolt', 'M6', 12)],            1300),
    (kw(r'crankshaft'),                 'steel_hss',   'forging',     [('bolt', 'M10', 5)],              14500),
    (kw(r'camshaft'),                   'cast_iron',   'casting_sand',[('bolt', 'M8', 5)],                2600),
    (kw(r'piston'),                     'alu_cast',    'forging',     [('press_fit', '', 1)],              320),
    (kw(r'connecting rod'),             'steel_hss',   'forging',     [('bolt', 'M9', 2)],                 560),
    (kw(r'flywheel|drive plate'),       'cast_iron',   'casting_sand',[('bolt', 'M10', 6)],               8200),
    (kw(r'intake manifold|manifold,? intake'), 'plastic_pa66', 'injection', [('bolt', 'M8', 6)],          2400),
    (kw(r'exhaust manifold|manifold'),  'cast_iron',   'casting_sand',[('nut', 'M10', 8)],                4800),
    (kw(r'oil pan'),                    'alu_cast',    'casting_die', [('bolt', 'M6', 14)],               2100),
    (kw(r'radiator(?!.*support)'),      'alu_sheet',   'assembly',    [('bolt', 'M8', 4)],                4600),
    (kw(r'condenser'),                  'alu_sheet',   'assembly',    [('bolt', 'M6', 4)],                2800),
    (kw(r'muffler|exhaust pipe|tail pipe|front pipe'), 'steel_mild', 'welding', [('bolt', 'M8', 4)],      6200),
    (kw(r'catalytic|converter'),        'ceramic',     'assembly',    [('weld_seam', '', 2)],             3900),
    (kw(r'fuel tank'),                  'plastic_pa66','blow_mold',   [('bolt', 'M8', 6)],                8500),
    (kw(r'battery'),                    'lead_acid',   'assembly',    [('bolt', 'M8', 2)],               14000),
    (kw(r'alternator|generator'),       'mixed',       'winding',     [('bolt', 'M10', 3)],               5400),
    (kw(r'starter'),                    'mixed',       'winding',     [('bolt', 'M10', 2)],               3100),
    (kw(r'compressor'),                 'alu_cast',    'casting_die', [('bolt', 'M8', 4)],                5800),
    (kw(r'water pump'),                 'alu_cast',    'casting_die', [('bolt', 'M8', 4)],                1200),
    (tag('motor'),                      'mixed',       'winding',     [('bolt', 'M6', 3)],                 900),
    (kw(r'wind ?shield glass|glass sub-?assy,? wind'), 'glass_lam', 'float_glass', [('adhesive', '', 1)], 11500),
    (kw(r'back window|rear window'),    'glass_temp',  'float_glass', [('adhesive', '', 1)],              7200),
    (kw(r'door glass|glass sub-?assy'), 'glass_temp',  'float_glass', [('press_fit', '', 1)],             3800),
    (kw(r'\bglass\b|\bwindow\b'),       'glass_temp',  'float_glass', [('clip', '', 4)],                   900),
    (kw(r'\bseat\b|seat cushion|seat back'), 'mixed',  'assembly',    [('bolt', 'M10', 4)],              14000),
    (kw(r'seat cushion pad|seat back pad|pad sub-?assy'), 'foam_pu', 'foaming', [('clip', '', 6)],        2200),
    (kw(r'instrument panel'),           'plastic_abs', 'injection',   [('bolt', 'M6', 10)],               8000),
    (kw(r'head ?lamp|head ?light'),     'plastic_pc',  'injection',   [('bolt', 'M6', 3)],                3400),
    (kw(r'rear combination|tail ?lamp|lamp'), 'plastic_pc','injection',[('bolt', 'M6', 3)],               1200),
    (kw(r'bumper (cover|assembly)|cover,? bumper'), 'plastic_pp', 'injection', [('clip', '', 14)],        4600),
    (kw(r'bumper reinforcement|reinforcement,? bumper|bumper stay'), 'steel_hss', 'stamping', [('bolt', 'M10', 6)], 5200),
    (kw(r'\bhood\b'),                   'steel_mild',  'stamping',    [('bolt', 'M8', 4)],               13500),
    (kw(r'luggage compartment door|trunk lid|back door'), 'steel_mild', 'stamping', [('bolt', 'M8', 4)], 11000),
    (kw(r'\bfender\b'),                 'steel_mild',  'stamping',    [('bolt', 'M6', 8)],                4800),
    (kw(r'door.*panel|panel.*door'),    'steel_mild',  'stamping',    [('bolt', 'M8', 4)],               17000),
    (kw(r'roof|quarter panel|floor|body|pillar|member|reinforcement|panel'), 'steel_hss', 'stamping', [('weld_spot', '', 24)], 3200),
    (kw(r'weatherstrip|seal|packing'),  'rubber_epdm', 'extrusion',   [('clip', '', 10)],                  700),
    (kw(r'hose|tube'),                  'rubber_epdm', 'extrusion',   [('hose_clamp', '', 2)],             320),
    (kw(r'wire|harness|cable'),         'copper',      'assembly',    [('connector', '', 4)],              850),
    (tag('sensor'),                     'mixed',       'electronic',  [('bolt', 'M6', 1)],                  90),
    (kw(r'computer|control module|\becu\b|amplifier|receiver'), 'mixed', 'electronic', [('bolt', 'M6', 3)], 700),
    (kw(r'speaker'),                    'mixed',       'assembly',    [('screw', 'M5', 4)],                 460),
    (kw(r'switch|relay|fuse|junction'), 'plastic_abs', 'electronic',  [('clip', '', 2)],                   180),
    (kw(r'bolt|nut|screw|washer|clip|clamp|grommet|plug\b'), 'steel_mild', 'forging', [('thread_in', '', 1)], 45),
    (kw(r'bracket|stay|support|holder'),'steel_mild',  'stamping',    [('bolt', 'M8', 2)],                 420),
    (kw(r'cover|garnish|moulding|trim|carpet|lining|mat'), 'plastic_pp', 'injection', [('clip', '', 8)],   950),
    (kw(r'filter'),                     'mixed',       'assembly',    [('clip', '', 2)],                   260),
    (kw(r'gear|shaft|pinion|sprocket'), 'steel_hss',   'machining',   [('press_fit', '', 1)],              900),
    (kw(r'pump'),                       'alu_cast',    'casting_die', [('bolt', 'M8', 3)],                1400),
    (kw(r'valve'),                      'steel_hss',   'machining',   [('thread_in', '', 1)],              210),
    (kw(r'pipe'),                       'steel_mild',  'extrusion',   [('bolt', 'M6', 2)],                 480),
]

FALLBACK = ('mixed', 'assembly', [('bolt', 'M6', 2)], 350)


# 图组名回退时的重量上限：图组只说明这件属于哪一族（据此定材料工艺是合理的），
# 完全不说明它多大。油底壳的官方图组就叫 Cylinder Block，照搬就成了 92kg 的发动机。
# 所以回退时材料工艺照用，重量一律压到这个上限以下 —— 一个族里名字没直接对上的，
# 基本都是那族里的小件，大件的名字通常能直接匹配上。
SUBGROUP_WEIGHT_CAP = 500

# 蹭来的匹配（不是靠自己的类型词挣的）能拿到的最大重量
BORROWED_WEIGHT_CAP = 1500


def inverted(n):
    """丰田官方名是逗号倒装的：Rod Sub-Assy, Connecting → Connecting Rod Sub-Assy。
    car.js 早就按这条归一化了，这里当初漏了，导致连杆退到图组去拿了曲轴的重量。"""
    segs = [s.strip() for s in (n or '').split(',') if s.strip()]
    return ' '.join(reversed(segs)) if len(segs) > 1 else (n or '')


def head_noun(n):
    """丰田官方名把零件类型写在第一个逗号之前：Pulley, Alternator W/Clutch 是皮带轮，
    Rotor Assy, Alternator 是转子，Lamp Assy, Instrument Panel 是灯。
    先只拿这一段匹配，小件才不会继承它所属总成的重量 —— 实测发电机的轴承、皮带轮、
    调节器全被判成 5.4kg 的发电机，仪表台照明灯被判成 8kg 的仪表台。"""
    s = re.sub(r'\([^)]*\)', ' ', n or '')          # 去掉括号里的「(For Alternator …)」
    s = s.split(',')[0]
    s = re.sub(r'\b(sub-?assy|assy|assembly|kit|set)\b', ' ', s, flags=re.I)
    return s.strip()


def enrich(p):
    tags = set(p.get('tags') or [])
    # 第零遍：只拿官方名的主体词打。这是最强的信号，见 head_noun 的说明。
    hn = head_noun(p.get('name_en'))
    if hn:
        for m, mat, proc, fas, w in RULES:
            if not getattr(m, 'tags', None) and m(hn):
                return mat, proc, fas, w
    # 主体词没认出来，后面几遍都是靠「名字里提到的总成」蹭上的。
    # 这种蹭来的匹配不许带走总成级的重量 —— 一个只是「属于座椅」的护板、手柄、铰链，
    # 不可能有 14kg。护栏放在这里，比一条条补规则可靠：补规则永远补不完。
    def guard(mat, proc, fas, w):
        return mat, proc, fas, (min(w, BORROWED_WEIGHT_CAP) if w > BORROWED_WEIGHT_CAP else w)
    # 第一遍：只看官方零件名，这是最可信的依据。标签规则这一遍要跳过 ——
    # 标签是「这件跟轴承有关」，不是「这件是轴承」：空调压缩机带 bearing 标签
    # （皮带轮里有深沟球轴承），照标签判就成了轴承钢磨削件，而它是铸铝压铸的。实测踩过。
    for m, mat, proc, fas, w in RULES:
        if not getattr(m, 'tags', None) and m(p.get('name_en')):
            return mat, proc, fas, w
    # 第二遍：把逗号倒装的官方名翻正再打一遍
    inv = inverted(p.get('name_en'))
    if inv != (p.get('name_en') or ''):
        for m, mat, proc, fas, w in RULES:
            if not getattr(m, 'tags', None) and m(inv):
                return mat, proc, fas, w
    # 第三遍：名字认不出来，才让标签规则上
    for m, mat, proc, fas, w in RULES:
        if getattr(m, 'tags', None) and m.tags & tags:
            return guard(mat, proc, fas, w)
    # 第四遍：退而看官方图组名 —— 材料工艺照用，重量必须限住，理由见 SUBGROUP_WEIGHT_CAP
    for m, mat, proc, fas, w in RULES:
        if not getattr(m, 'tags', None) and m(p.get('subgroup_en')):
            return mat, proc, fas, min(w, SUBGROUP_WEIGHT_CAP)
    return FALLBACK


def main():
    write = '--write' in sys.argv
    doc = json.load(open(SRC, encoding='utf-8'))
    parts = doc['parts']
    byid = {p['id']: p for p in parts}

    # 谁有子件谁就是总成。总成不带独立重量，它的重量 = 子件之和，
    # 否则「发动机半总成 92kg」会和它下面的曲轴、活塞、连杆重复计一遍。
    children = {}
    for p in parts:
        par = p.get('parent')
        if par and par in byid:
            children.setdefault(par, []).append(p['id'])

    for p in parts:
        mat, proc, fas, w = enrich(p)
        p['material'] = mat
        p['process'] = proc
        p['fastening'] = [{'type': t, 'spec': s, 'count': c} for t, s, c in fas]
        p['weight_g'] = w
        p['weight_basis'] = 'category_typical'
        p['weight_conf'] = 'typical'

    # 自底向上算总成重量。
    # 单用「子件之和」不行：这份目录的装配树不完整，空调压缩机下面只挂了一个轴承，
    # 滚上去就是 210g（实际约 6kg）；发电机反过来挂多了，滚成 24.6kg（实际约 5kg）。
    # 判据改成 max(已知子件之和, 品类经验值)：一个总成不可能轻于它已知子件的总和，
    # 也不该轻于同类总成的常见量级。哪个胜出就在 weight_basis 里记明。
    def roll(pid, seen):
        if pid in seen:
            return 0
        seen.add(pid)
        kids = children.get(pid)
        p = byid[pid]
        if not kids:
            return p['weight_g'] * (p.get('qty') or 1)
        s = sum(roll(k, seen) for k in kids)
        own = p['weight_g'] * (p.get('qty') or 1)
        if own > s:
            p['weight_basis'] = 'category_typical'   # 树不完整，子件之和偏低，按品类走
            return own
        p['weight_g'] = round(s / max(1, p.get('qty') or 1))
        p['weight_basis'] = 'sum_of_children'
        return s

    def cost_of(p):
        kg = (p.get('weight_g') or 0) / 1000.0
        unit = MAT_PRICE.get(p['material'], 30) + PROC_RATE.get(p['process'], 20)
        fast = sum(f.get('count', 0) for f in p.get('fastening') or [])
        return round(kg * unit + fast * FASTENER_COST, 2)

    total = 0
    seen = set()
    roots = [p['id'] for p in parts if not p.get('parent') or p['parent'] not in byid]
    for r in roots:
        total += roll(r, seen)
    for p in parts:                      # 挂不到树上的（不该有）也别漏掉
        if p['id'] not in seen:
            total += p['weight_g'] * (p.get('qty') or 1)

    # 成本：叶子件按模型算；总成同样取 max(子件之和, 自身模型值)，理由与重量一致
    for p in parts:
        p['cost_cny'] = cost_of(p)
        p['cost_basis'] = 'parametric_model'

    def rollc(pid, seen):
        if pid in seen:
            return 0
        seen.add(pid)
        kids = children.get(pid)
        p = byid[pid]
        if not kids:
            return p['cost_cny'] * (p.get('qty') or 1)
        s = sum(rollc(k, seen) for k in kids)
        own = p['cost_cny'] * (p.get('qty') or 1)
        if own > s:
            return own
        p['cost_cny'] = round(s / max(1, p.get('qty') or 1), 2)
        p['cost_basis'] = 'sum_of_children'
        return s

    cost_total, seenc = 0, set()
    for r in roots:
        cost_total += rollc(r, seenc)
    for p in parts:
        if p['id'] not in seenc:
            cost_total += p['cost_cny'] * (p.get('qty') or 1)

    by_mat, by_proc, fasten_total, by_grp_cost = {}, {}, {}, {}
    for p in parts:
        if children.get(p['id']):        # 总成不进材料/工艺统计，避免重复
            continue
        q = p.get('qty') or 1
        by_mat[p['material']] = by_mat.get(p['material'], 0) + p['weight_g'] * q
        by_proc[p['process']] = by_proc.get(p['process'], 0) + p['weight_g'] * q
        by_grp_cost[p['group']] = by_grp_cost.get(p['group'], 0) + p['cost_cny'] * q
        for f in p['fastening']:
            fasten_total[f['type']] = fasten_total.get(f['type'], 0) + f['count'] * q

    doc.setdefault('vehicle', {})['weight_note'] = (
        '零件重量为按品类的工程经验值（weight_basis=category_typical），'
        '不是丰田官方数据，也不是从 3D 几何算出来的——这套 3D 是示意模型不是数模。'
        '整车合计仅用于量级自检。')

    doc['vehicle']['cost_note'] = (
        '成本为参数化估算模型：单件成本 = 重量kg × (材料单价 + 该工艺加工费率) + 紧固件数 × 0.6 元。'
        '系数表在 tools/enrich_parts.py 里，可查可改可复算。这不是丰田的采购价，'
        '公开渠道也拿不到那个数，只能当量级参考。')

    # 对外只报「叶子件合计」这一个口径，界面上的汇总用的也是它。
    # 从根滚上来的那个数（总成取 max 时把差额也算进去）会比叶子和大，
    # 两处显示不同的数就是缺陷 —— 所以滚加值只留在 body_shell 自己的 weight_g 上，不当合计报。
    leaf_kg = sum(p['weight_g'] * (p.get('qty') or 1)
                  for p in parts if not children.get(p['id']))
    leaf_cost = sum(p['cost_cny'] * (p.get('qty') or 1)
                    for p in parts if not children.get(p['id']))
    print('覆盖零件 %d 条' % len(doc['parts']))
    print('叶子件合计：%.0f kg  —— E210 整备质量约 1310~1405 kg（覆盖 %.0f%%）'
          % (leaf_kg / 1000, leaf_kg / 1000 / 1357 * 100))
    print('参数化成本合计：%.0f 元（模型估算，不是采购价）' % leaf_cost)
    print('（从根滚加值 %.0f kg / %.0f 元，含总成取 max 的修正，只记在 body_shell 上，不当合计报）'
          % (total / 1000, cost_total))
    print('\n按部分的成本：')
    for k, v in sorted(by_grp_cost.items(), key=lambda kv: -kv[1]):
        print('  %-20s %8.0f 元' % (k, v))
    print('\n按材料（前 8）：')
    for k, v in sorted(by_mat.items(), key=lambda kv: -kv[1])[:8]:
        print('  %-14s %7.1f kg  %5.1f%%  %s' % (k, v / 1000, v / total * 100, MATERIALS[k][0]))
    print('\n按工艺（前 6）：')
    for k, v in sorted(by_proc.items(), key=lambda kv: -kv[1])[:6]:
        print('  %-14s %7.1f kg  %s' % (k, v / 1000, PROCESSES[k][0]))
    print('\n紧固件合计：')
    for k, v in sorted(fasten_total.items(), key=lambda kv: -kv[1]):
        print('  %-12s %5d  %s' % (k, v, FASTEN[k][0]))

    if write:
        json.dump(doc, open(SRC, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('\n已写回 data/parts.json')
    else:
        print('\n（试跑，没写。加 --write 才落盘）')


if __name__ == '__main__':
    main()
