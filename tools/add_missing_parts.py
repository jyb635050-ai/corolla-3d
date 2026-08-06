# -*- coding: utf-8 -*-
"""把 audit_naming 挖出来的 12 个「整车其实没有」的真零件补进目录。

零件号来历：2026-07-31 逐条查 toyotapartsdeal 的 Corolla 分类页。
凡是号族能和库里已考证的件对上的（-F2010 是 E210 北美版机舱件族、-02xxx 是三厢车身件族），
标 confirmed；对不准发动机型号或年款的标 typical；两次抓不到页面的（前螺旋弹簧）
留空号，只把官方图组填准 —— 不猜号。

用法：uv run --no-project python tools/add_missing_parts.py [--write]
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'parts.json')
TPD = 'https://www.toyotapartsdeal.com/'

# id, 官方英文名, 中文名, 零件号, 号的把握, group, 官方图组(en/zh), parent,
# 连到, qty, tags, 建3D, 规格, 作用(zh), 作用(en), 供应商2, 供应商3
NEW = [
    ('radiator_assy', 'Radiator Assy', '散热器总成', '16400-F2010', 'confirmed',
     'engine_fuel_tool', 'Radiator & Water Outlet', '散热器与出水口', 'body_shell',
     ['fan_shroud', 'coolant_hose_inlet', 'radiator_cap'], 1, ['cooling'], True,
     '铝制芯体加塑料上下水室，通过两条橡胶软管与发动机水套相连，前部还叠着空调冷凝器',
     '把发动机冷却液带走的热量交给迎面气流，是水温能不能压住的最后一道。'
     '芯体被小石子打漏或散热带被泥堵死后，夏天堵车或长坡会先出现水温报警，继续开就是缸盖变形。',
     'Transfers the heat carried away by the coolant into the oncoming airflow, and it is the last line that keeps '
     'coolant temperature in check. Once the core is punctured by stones or the fins are packed with mud, the '
     'temperature warning shows up first in summer traffic or on long climbs, and pressing on warps the cylinder head.',
     ('电装 DENSO', '丰田系冷却模块主力配套厂，散热器与冷却风扇模块常见来源'),
     ('三五 Sanoh / 京滨 Keihin', '同品类常见配套，未逐条核实该零件号')),

    ('throttle_body', 'Throttle Body Assy', '节气门体总成', '22030-F2010', 'confirmed',
     'engine_fuel_tool', 'Fuel Injection System', '燃油喷射系统', 'engine_assy',
     ['intake_manifold', 'ecu_engine'], 1, ['electrical', 'motor'], True,
     '电子节气门，直流电机驱动蝶阀，带双路位置传感器冗余，与进气歧管法兰对接',
     '按油门踏板的意图控制进入发动机的空气量，电子节气门取消了拉线，怠速和巡航都由 ECU 直接调。'
     '阀片积碳后关不严，会出现怠速忽高忽低、冷启动抖动，清洗后通常还要做节气门学习。',
     'Meters how much air enters the engine according to what the accelerator pedal is asking for. Being '
     'drive-by-wire it has no cable, so idle and cruise are trimmed straight by the ECU. Carbon on the plate '
     'stops it closing fully, which shows up as a hunting idle and a rough cold start; after cleaning it '
     'usually needs a throttle relearn.',
     ('电装 DENSO', '丰田电子节气门体的长期主力供应商'),
     ('爱三工业 Aisan', '丰田系燃油与进气系统常见配套，未逐条核实该零件号')),

    ('exhaust_manifold', 'Manifold, Exhaust', '排气歧管', '17141-F2010', 'confirmed',
     'engine_fuel_tool', 'Manifold', '歧管', 'engine_assy',
     ['head_cover_gasket', 'exhaust_pipe_front', 'sensor_af_ratio'], 1, ['exhaust'], True,
     '不锈钢一体铸造，集成催化器（4-2-1 汇流后紧耦合），前氧传感器座在汇流处',
     '把四个气缸排出的高温废气汇到一根管里送进催化器，管长和汇流角度直接影响低扭。'
     '一体式集成催化器一旦开裂就是整体更换，费用远高于分体式，且开裂后排气泄漏会让前氧信号失真。',
     'Collects the hot exhaust from all four cylinders into one pipe and feeds the catalyst. Runner length and '
     'the merge angle have a direct effect on low-end torque. Because the catalyst is cast in, a crack means '
     'replacing the whole assembly, which costs far more than a separate one, and the leak upstream also '
     'corrupts the front oxygen sensor signal.',
     ('三五 Sango', '丰田系排气系统主力配套厂'),
     ('双叶产业 Futaba', '排气歧管与排气管同品类常见配套，未逐条核实该零件号')),

    ('camshaft_intake', 'Camshaft Sub-Assy, Intake', '进气凸轮轴', '13501-F2010', 'confirmed',
     'engine_fuel_tool', 'Camshaft & Valve', '凸轮轴与气门', 'engine_assy',
     ['camshaft_timing_gear', 'valve_intake'], 1, ['gear'], True,
     '铸铁空心轴，与可变气门正时执行器相连，轴颈处靠机油压力形成油膜支承',
     '靠轴上凸起的桃形轮廓按曲轴转角顶开进气门，决定气门什么时候开、开多大、开多久。'
     '机油长期不换导致轴颈磨损后，气门升程变小、动力下降，严重时凸轮桃尖被磨平直接失去升程。',
     'Its lobes push the intake valves open in step with crankshaft angle, setting when each valve opens, how '
     'far and for how long. If the oil is never changed the journals wear, valve lift drops and power falls '
     'away; in the worst case the lobe nose is worn flat and lift is lost altogether.',
     ('丰田自动织机 Toyota Industries', '丰田系发动机零部件配套'),
     ('日锻 Nittan / 理研 Riken', '气门与凸轮轴同品类常见配套，未逐条核实该零件号')),

    ('fuel_tank', 'Tank Sub-Assy, Fuel', '燃油箱', '77001-02850', 'confirmed',
     'engine_fuel_tool', 'Fuel Tank & Tube', '燃油箱与油管', 'body_shell',
     ['fuel_tank_main_tube', 'fuel_pump_assy', 'fuel_tank_cap'], 1, ['fuel'], True,
     '多层共挤吹塑塑料油箱，容积约 50 L，内置挡板抑制晃动，顶部集成燃油泵与油量传感器法兰',
     '装汽油并把油稳定送到油泵，多层塑料结构是为了挡住汽油分子渗透以满足蒸发排放法规。'
     '油箱磕漏后不能补焊，只能整体更换；长期只加半箱油还会让泵体散热变差、缩短油泵寿命。',
     'Holds the petrol and keeps a stable supply to the pump. The multi-layer plastic wall exists to block fuel '
     'molecules from permeating through, which is what evaporative emissions rules demand. A holed tank cannot '
     'be welded and has to be replaced whole; habitually running it half full also leaves the pump hotter and '
     'shortens its life.',
     ('八千代工业 Yachiyo', '丰田系塑料燃油箱常见配套厂'),
     ('小系 FTS / Kautex', '塑料油箱同品类常见配套，未逐条核实该零件号')),

    ('windshield_glass', 'Glass Sub-Assy, Windshield', '前风窗玻璃', '56101-02M91', 'confirmed',
     'body', 'Windshield Glass', '前风窗玻璃', 'body_shell',
     ['windshield_moulding_outer', 'forward_camera'], 1, ['glass', 'body_panel'], True,
     '夹层玻璃，两片玻璃中间夹 PVB 胶片；带辅助驾驶摄像头安装座与遮蔽黑边',
     '挡风挡雨之外，它是车身结构的一部分，翻滚时和 A 柱一起撑住车顶，还是副驾气囊弹开时的反射面。'
     '夹层结构让它破了也不会飞溅；换过之后必须重新标定前视摄像头，否则车道保持和自动刹车会偏。',
     'Beyond keeping out wind and rain it is part of the body structure: in a rollover it braces the roof '
     'together with the A-pillars, and it is the surface the passenger airbag bounces off. The laminated build '
     'means it will not shatter into fragments. After replacement the forward camera must be recalibrated, or '
     'lane keeping and automatic braking will aim off.',
     ('旭硝子 AGC', '丰田系汽车玻璃主力配套厂'),
     ('日本板硝子 NSG / 福耀 Fuyao', '汽车玻璃同品类常见配套，未逐条核实该零件号')),

    ('cylinder_head', 'Head Sub-Assy, Cylinder', '气缸盖', '11101-F9030', 'typical',
     'engine_fuel_tool', 'Cylinder Head', '气缸盖', 'engine_assy',
     ['head_cover_gasket', 'camshaft_intake', 'valve_intake', 'spark_plug'], 1, ['gear'], True,
     '铝合金压铸，内有进排气道、水套与气门导管；与缸体之间靠多层钢缸垫密封。'
     '注：零件号对应 2019–2024 款，未能核准到具体发动机型号，按 typical 标注',
     '扣在缸体上方形成燃烧室的顶，容纳气门、火花塞和进排气道，是压缩压力能不能建立的关键。'
     '长期高温或缺冷却液后，铝制缸盖会翘曲导致缸垫冲缸，症状是水箱冒泡、机油乳化，必须下缸盖平面磨削。',
     'Caps the block to form the roof of the combustion chamber and carries the valves, spark plugs and the '
     'intake and exhaust ports, so it decides whether compression can build at all. After sustained overheating '
     'or a coolant loss the aluminium warps and blows the head gasket, which shows as bubbling in the header '
     'tank and milky oil, and the deck has to be skimmed flat.',
     ('丰田自动织机 Toyota Industries', '丰田系发动机本体零部件配套'),
     ('爱信 Aisin', '发动机本体同品类常见配套，未逐条核实该零件号')),

    ('rear_shock_absorber', 'Shock Absorber Assy, Rear', '后减振器总成', '48530-8Z111', 'typical',
     'powertrain_chassis', 'Rear Spring & Shock Absorber', '后弹簧与减振器', 'rear_suspension_assy',
     ['rear_trailing_arm_rh', 'rear_coil_spring'], 2, ['suspension'], True,
     '筒式液压减振器，多连杆后悬的阻尼元件。注：零件号覆盖 2020–2023 款整套，'
     '未核准到三厢北美版单侧号，按 typical 标注',
     '把弹簧压缩释放出来的能量转成热耗掉，没有它车过一个坎会持续弹跳好几下。'
     '漏油失效后制动距离变长、过弯侧倾加剧，轮胎还会出现锯齿状偏磨，是很多人误以为"轮胎坏了"的真凶。',
     'Turns the energy the spring gives back into heat and dumps it; without it the car would keep bouncing for '
     'several cycles after one bump. Once it leaks, braking distances stretch, body roll in corners grows, and '
     'the tyre develops a saw-tooth wear pattern that many people mistake for a bad tyre.',
     ('KYB', '丰田系减振器主力配套厂'),
     ('日立安斯泰莫 Hitachi Astemo / Showa', '减振器同品类常见配套，未逐条核实该零件号')),

    ('front_coil_spring', 'Spring, Coil, Front', '前螺旋弹簧', '', 'guess',
     'powertrain_chassis', 'Front Spring & Shock Absorber', '前弹簧与减振器', 'front_suspension_assy',
     ['front_strut_mount_rh', 'front_strut'], 2, ['suspension'], True,
     '弹簧钢冷卷成型，麦弗逊前悬的承载元件。注：该零件的官方分类页两次抓取失败（HTTP 404），'
     '未取到零件号，按「宁缺毋滥」留空，官方图组已填准',
     '承受整车前轴的静载与动载，弹簧刚度直接决定悬架的软硬和车身高度。'
     '弹簧断裂多发生在钢圈末端锈蚀处，断后车身一角明显下沉，断口还可能扎穿轮胎，属于必须立刻停车的故障。',
     'Carries both the static and dynamic load on the front axle, and its rate sets how firm the suspension '
     'feels and how high the body sits. Breakage usually starts where the end coil has corroded; once it snaps '
     'that corner of the car visibly drops and the broken end can spear the tyre, which makes it a stop-driving-now '
     'fault.',
     ('中央发条 Chuo Spring', '丰田系悬架弹簧常见配套厂'),
     ('三菱制钢 Mitsubishi Steel', '悬架弹簧同品类常见配套，未逐条核实该零件号')),

    ('hood_lock', 'Lock Assy, Hood', '发动机盖锁总成', '', 'guess',
     'body', 'Hood Lock & Hinge', '机盖锁与铰链', 'body_shell',
     ['hood_panel', 'hood_support'], 1, ['body_panel'], False,
     '两级锁止机构，主锁扣加安全钩，通过拉索连到驾驶席下方的开启拉手。注：未取到零件号',
     '把发动机盖牢牢扣在车身上，第一道锁失效时还有安全钩兜底，防止高速行驶中机盖掀起挡住视线。'
     '拉索锈死或锁体缺润滑后会出现拉不开或关不严，关不严时仪表会亮机盖未关警告。',
     'Holds the hood down on the body, with a secondary safety catch that still holds if the primary latch '
     'lets go, so the hood cannot fly up at speed and block the view. A seized cable or a dry latch leads to '
     'a hood that will not open or will not shut properly, and the instrument cluster warns when it is ajar.',
     ('三井金属 Mitsui Kinzoku', '丰田系锁体常见配套厂'),
     ('安通林 Antolin / 有信 Youxin', '锁体同品类常见配套，未逐条核实该零件号')),

    ('brake_pedal', 'Pedal Sub-Assy, Brake', '制动踏板', '', 'guess',
     'powertrain_chassis', 'Brake Pedal & Bracket', '制动踏板与支架', 'brake_system_assy',
     ['brake_pedal_support', 'brake_master_cyl'], 1, ['brake'], False,
     '冲压钢踏板臂，杠杆比约 4:1，推杆直连真空助力器。注：未取到零件号',
     '把脚上的力放大若干倍传给真空助力器，杠杆比决定了踩下去的脚感是硬还是软。'
     '踏板行程变长且发软，通常不是踏板本身的问题，而是制动液里进了空气或某处管路在渗漏。',
     'Multiplies the force from the driver foot several times over and passes it to the vacuum booster; the '
     'lever ratio is what makes the pedal feel firm or soft. A pedal that goes long and spongy is rarely the '
     'pedal itself but air in the brake fluid or a line weeping somewhere.',
     ('丰田纺织 Toyota Boshoku', '丰田系踏板与支架常见配套'),
     ('KSR / 光洋 Koyo', '踏板总成同品类常见配套，未逐条核实该零件号')),

    ('seat_belt_front_lh', 'Belt Assy, Front Seat, LH', '前排安全带总成 左', '', 'guess',
     'body', 'Seat Belt & Child Restraint Seat', '安全带与儿童座椅固定', 'body_shell',
     ['belt_anchor_bracket_lh', 'front_seat_cushion_lh'], 1, ['seat'], False,
     '三点式，带预紧器与限力器；预紧器为火药式，碰撞时由气囊 ECU 点火。注：未取到零件号',
     '碰撞瞬间先由预紧器把安全带收紧消除松弛，再由限力器让织带受控放出，把胸部受力压在肋骨能承受的范围内。'
     '预紧器是一次性的火药件，只要触发过就必须整条更换，不能只换织带。',
     'In a crash the pretensioner first pulls the slack out of the belt, then the load limiter pays webbing '
     'back out in a controlled way so the load on the chest stays inside what the ribcage can take. The '
     'pretensioner is a one-shot pyrotechnic device: once it has fired the whole belt assembly must be '
     'replaced, not just the webbing.',
     ('奥托立夫 Autoliv', '丰田系安全带主力配套厂'),
     ('均胜安全 Joyson Safety Systems', '安全带同品类常见配套，未逐条核实该零件号')),
]


def main():
    write = '--write' in sys.argv
    doc = json.load(open(SRC, encoding='utf-8'))
    have = {p['id'] for p in doc['parts']}
    added = []
    for (pid, en, zh, pn, conf, grp, sg_en, sg_zh, parent, conn, qty,
         tags, mesh, spec, role_zh, role_en, sup2, sup3) in NEW:
        if pid in have:
            print('！%s 已存在，跳过' % pid)
            continue
        sups = []
        if pn:
            sups.append({'name': '丰田原厂 Toyota Genuine Parts',
                         'note': '官方零件目录中以该零件号在售，可按零件号直接查到官方零件名与适配车型',
                         'confidence': conf,
                         'source': TPD + 'search?q=' + pn})
        else:
            sups.append({'name': '丰田原厂 Toyota Genuine Parts',
                         'note': '官方目录中有该零件，但本轮未取到具体零件号，故不标 confirmed',
                         'confidence': 'guess', 'source': ''})
        sups.append({'name': sup2[0], 'note': sup2[1], 'confidence': 'typical', 'source': ''})
        sups.append({'name': sup3[0], 'note': sup3[1], 'confidence': 'guess', 'source': ''})
        doc['parts'].append({
            'id': pid, 'group': grp, 'subgroup_en': sg_en, 'subgroup_zh': sg_zh,
            'name_en': en, 'name_zh': zh, 'oem_pn': pn, 'parent': parent,
            'connects_to': [c for c in conn if c in have] or ['body_shell'],
            'role_zh': role_zh, 'role_en': role_en, 'qty': qty, 'qty_kind': 'exact',
            'tags': tags, 'has_mesh': mesh, 'spec': spec, 'suppliers': sups,
        })
        added.append((pid, pn or '（留空）', zh))
    print('补入 %d 条：' % len(added))
    for pid, pn, zh in added:
        print('  %-26s %-14s %s' % (pid, pn, zh))
    if write:
        json.dump(doc, open(SRC, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('\n已写回。记得再跑 enrich_parts.py --write 给新件补材料/工艺/重量。')
    else:
        print('\n（试跑，没写。加 --write 才落盘）')


if __name__ == '__main__':
    main()
