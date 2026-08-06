# -*- coding: utf-8 -*-
"""把 id 与官方零件名对不上的条目改名，并把「整车缺了这些真零件」记下来。

来历：tools/audit_naming.py 按「丰田官方名的主体词在第一个逗号之前」这条规律
扫出 42 条可疑，人工逐条过完确认 14 条真错 —— id 声称自己是散热器/节气门体/
前螺旋弹簧，官方零件号对应的其实是导风罩/燃油管/上支座。

处理原则：
  1. 只改 id，不碰 oem_pn / name_en / name_zh —— 官方零件号和官方名是考证过的，
     错的是 id 这个自己起的名字。
  2. 改 id 的同时把 parent 和 connects_to 里的引用一起改，否则装配树会断。
  3. 绝不编零件号去补缺件。缺的那些真零件（真散热器、真节气门体…）写进
     BLOCKED_A.md，等有人回官方目录考证。

用法：uv run --no-project python tools/fix_ids.py [--write]
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'parts.json')

# 旧 id → 新 id（新 id 按官方名的主体词起）
RENAME = {
    'radiator_assy':        'fan_shroud',
    'throttle_body':        'fuel_pipe_no1',
    'exhaust_manifold':     'manifold_stay',
    'front_coil_spring':    'front_strut_mount_rh',
    'rear_shock_absorber':  'rear_trailing_arm_rh',
    'camshaft_intake':      'camshaft_timing_gear',
    'fuel_tank':            'fuel_tank_main_tube',
    'cylinder_head_assy':   'head_cover_gasket',
    'windshield_glass':     'windshield_moulding_outer',
    'hood_lock':            'hood_support',
    'brake_pedal':          'brake_pedal_support',
    'seat_belt_front_lh':   'belt_anchor_bracket_lh',
    'child_lock_note':      'door_handle_cover_rh',
    'electrical_main':      'engine_room_wire_main',
}

# 因为上面这些位置被占，整车实际缺的真零件（连带它们的官方图组，方便后续考证）
MISSING = [
    ('散热器总成',        'Radiator Assy',                 'Radiator & Water Outlet'),
    ('节气门体总成',      'Throttle Body Assy',            'Fuel Injection System'),
    ('排气歧管',          'Manifold, Exhaust',             'Manifold'),
    ('前螺旋弹簧',        'Spring, Coil, Front',           'Front Spring & Shock Absorber'),
    ('后减振器总成',      'Shock Absorber Assy, Rear',     'Rear Spring & Shock Absorber'),
    ('进气凸轮轴',        'Camshaft, Intake',              'Camshaft & Valve'),
    ('燃油箱',            'Tank Assy, Fuel',               'Fuel Tank & Tube'),
    ('气缸盖',            'Head Sub-Assy, Cylinder',       'Cylinder Head'),
    ('前风窗玻璃',        'Glass Sub-Assy, Windshield',    'Windshield Glass'),
    ('发动机盖锁',        'Lock Assy, Hood',               'Hood Lock & Hinge'),
    ('制动踏板',          'Pedal Sub-Assy, Brake',         'Brake Pedal & Bracket'),
    ('前排安全带总成',    'Belt Assy, Front Seat, LH',     'Seat Belt & Child Restraint Seat'),
]


def main():
    write = '--write' in sys.argv
    doc = json.load(open(SRC, encoding='utf-8'))
    parts = doc['parts']
    have = {p['id'] for p in parts}
    for old, new in RENAME.items():
        if old not in have:
            print('！找不到 %s，跳过' % old)
        if new in have:
            print('！新 id %s 已存在，会撞车' % new)

    n = 0
    for p in parts:
        if p['id'] in RENAME:
            p['id'] = RENAME[p['id']]
            n += 1
        if p.get('parent') in RENAME:
            p['parent'] = RENAME[p['parent']]
        p['connects_to'] = [RENAME.get(c, c) for c in (p.get('connects_to') or [])]
    print('改名 %d 条，引用已同步' % n)

    if write:
        json.dump(doc, open(SRC, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('已写回 data/parts.json')
        print('\n提醒：改完 id 后 3D 的槽位识别不受影响（它按 name_en 认），'
              '但 verify.py 抽查用的随机 id 会变，重跑一遍即可。')
    else:
        print('（试跑，没写。加 --write 才落盘）')

    print('\n以下真零件目前不在目录里，需要回官方目录考证后补：')
    for zh, en, grp in MISSING:
        print('  %-16s %-32s 图组：%s' % (zh, en, grp))


if __name__ == '__main__':
    main()
