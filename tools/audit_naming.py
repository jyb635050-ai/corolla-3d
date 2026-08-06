# -*- coding: utf-8 -*-
"""id 与官方零件名的语义一致性审计。

背景：id 是 A 自己起的（front_coil_spring），name_en 是丰田官方零件名
（Support Sub-Assy, Front Suspension, RH）。两者对不上时，界面显示的名字是对的，
但 id 骗人 —— 更麻烦的是，任何按名字做的自动化（材料/工艺/重量规则、槽位识别）
都会被带偏，而且错得很隐蔽。

判据：把 id 拆成词，去掉方位词和总成后缀，剩下的「主体词」只要有一个能在
name_en 里找到（含同义词），就算对得上；一个都找不到就列出来人工过目。
本脚本只读不改。

用法：uv run --no-project python tools/audit_naming.py
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'parts.json')

# 方位、序号、总成后缀 —— 这些不承载「这是个什么零件」的信息
NOISE = {
    'lh', 'rh', 'left', 'right', 'front', 'rear', 'back', 'upper', 'lower', 'inner', 'outer',
    'no1', 'no2', 'no3', 'assy', 'assembly', 'sub', 'kit', 'set', 'main', 'center', 'centre',
    'side', 'in', 'of', 'for', 'and', 'the', 'w', 'with', 'a', 'b', 'c', 'f', 'r',
}

# id 里的词 → 官方名里可能的写法。只要命中一个就算对上。
SYN = {
    'disc': ['disc', 'rotor'],
    'caliper': ['caliper', 'cylinder'],
    'pad': ['pad'],
    'spring': ['spring'],
    'shock': ['shock', 'absorber'],
    'strut': ['strut', 'shock', 'absorber', 'support'],
    'hub': ['hub'],
    'knuckle': ['knuckle', 'steering knuckle'],
    'bearing': ['bearing'],
    'tank': ['tank'],
    'pump': ['pump'],
    'filter': ['filter', 'cleaner', 'element'],
    'hose': ['hose', 'tube', 'pipe'],
    'pipe': ['pipe', 'tube'],
    'glass': ['glass', 'windshield', 'window'],
    'windshield': ['windshield', 'glass'],
    'panel': ['panel', 'board'],
    'door': ['door'],
    'hood': ['hood'],
    'roof': ['roof', 'header'],
    'trunk': ['luggage', 'deck', 'back door'],
    'bumper': ['bumper'],
    'fender': ['fender'],
    'lamp': ['lamp', 'light'],
    'headlamp': ['headlamp', 'head lamp'],
    'taillamp': ['rear combination', 'tail lamp', 'lamp'],
    'mirror': ['mirror'],
    'seat': ['seat'],
    'belt': ['belt'],
    'wheel': ['wheel', 'disc wheel'],
    'tire': ['tire', 'tyre'],
    'rim': ['wheel', 'rim'],
    'battery': ['battery'],
    'alternator': ['alternator', 'generator'],
    'starter': ['starter'],
    'motor': ['motor'],
    'sensor': ['sensor'],
    'switch': ['switch'],
    'ecu': ['computer', 'control', 'ecu', 'module'],
    'compressor': ['compressor'],
    'condenser': ['condenser'],
    'radiator': ['radiator'],
    'muffler': ['muffler', 'exhaust'],
    'catalyst': ['catalytic', 'converter'],
    'converter': ['converter'],
    'manifold': ['manifold'],
    'block': ['block', 'cylinder block', 'engine'],
    'head': ['head'],
    'cover': ['cover'],
    'crankshaft': ['crankshaft'],
    'camshaft': ['camshaft', 'cam'],
    'piston': ['piston'],
    'valve': ['valve'],
    'injector': ['injector'],
    'plug': ['plug'],
    'coil': ['coil'],
    'clutch': ['clutch'],
    'flywheel': ['flywheel', 'drive plate'],
    'transaxle': ['transaxle', 'transmission'],
    'cvt': ['transaxle', 'transmission', 'continuously'],
    'diff': ['differential'],
    'gear': ['gear'],
    'shaft': ['shaft'],
    'steering': ['steering'],
    'column': ['column'],
    'rack': ['gear', 'rack'],
    'arm': ['arm'],
    'subframe': ['crossmember', 'frame', 'member'],
    'crossmember': ['crossmember', 'member'],
    'speaker': ['speaker'],
    'antenna': ['antenna'],
    'amplifier': ['amplifier'],
    'camera': ['camera'],
    'airbag': ['air bag', 'airbag', 'inflator'],
    'wiper': ['wiper'],
    'washer': ['washer'],
    'horn': ['horn'],
    'hvac': ['heater', 'blower', 'air conditioning', 'cooling unit'],
    'duct': ['duct'],
    'carpet': ['carpet', 'mat'],
    'console': ['console'],
    'dash': ['instrument panel', 'dash'],
    'instrument': ['instrument'],
    'meter': ['meter'],
    'pillar': ['pillar'],
    'rocker': ['rocker', 'sill', 'side member'],
    'floor': ['floor'],
    'quarter': ['quarter'],
    'fuel': ['fuel'],
    'oil': ['oil'],
    'water': ['water', 'coolant'],
    'brake': ['brake'],
    'exhaust': ['exhaust'],
    'intake': ['intake', 'inlet', 'air'],
    'engine': ['engine'],
    'body': ['body'],
    'bolt': ['bolt'],
    'nut': ['nut'],
    'lock': ['lock'],
    'hinge': ['hinge'],
    'handle': ['handle'],
    'regulator': ['regulator'],
    'weatherstrip': ['weatherstrip'],
    'moulding': ['moulding', 'molding'],
    'garnish': ['garnish'],
    'bracket': ['bracket', 'stay', 'support'],
    'mount': ['mounting', 'insulator', 'mount'],
    'boot': ['boot', 'cover'],
    'jack': ['jack'],
    'sunroof': ['sliding roof', 'sun roof', 'moon roof'],
    'spoiler': ['spoiler'],
    'grille': ['grille', 'radiator grille'],
    'trim': ['trim'],
    'stabilizer': ['stabilizer', 'bar'],
    'tensioner': ['tensioner'],
    'thermostat': ['thermostat', 'inlet'],
    'reservoir': ['reservoir', 'tank', 'jar'],
    'relay': ['relay', 'block'],
    'fuse': ['fuse', 'block'],
    'harness': ['wire', 'harness'],
    'cable': ['cable', 'wire'],
}


def main():
    doc = json.load(open(SRC, encoding='utf-8'))
    parts = doc['parts']
    bad = []
    for p in parts:
        # 丰田官方名是倒装的，零件类型写在第一个逗号之前：
        # 「Gasket, Cylinder Head Cover」是垫片，不是缸盖。所以只比主体词，
        # 在整串里找子串会把垫片认成缸盖 —— 这是这份审计的全部要点。
        raw = (p.get('name_en') or '')
        head = raw.split(',')[0].lower()
        head = re.sub(r'\b(sub-?assy|assy|assembly|kit|set)\b', ' ', head).strip()
        # id 的主体词：英文 id 一般把类型放最后（front_coil_spring → spring）
        # id 的类型词位置不固定：sensor_knock 在前、front_coil_spring 在后、
        # hood_panel 两个都是类型。所以任一实义词命中官方主体词就算对上。
        toks = [t for t in re.split(r'[_\d]+', p['id']) if t and t not in NOISE and len(t) > 1]
        if not toks or not head:
            continue
        ok = False
        for t in toks:
            for pr in SYN.get(t, [t]):
                if pr in head:
                    ok = True
                    break
            if ok:
                break
        if not ok:
            bad.append((p['id'], p.get('name_zh', ''), raw, p.get('oem_pn', '')))

    print('全表 %d 条，id 主体词与官方名主体词对不上的 %d 条：\n' % (len(parts), len(bad)))
    for pid, zh, en, pn in bad:
        print('  %-30s %-22s %-46s %s' % (pid, zh[:20], en[:44], pn))


if __name__ == '__main__':
    main()
