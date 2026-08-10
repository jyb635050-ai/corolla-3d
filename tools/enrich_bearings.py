# -*- coding: utf-8 -*-
"""给 tags 含 bearing 的零件补两个专业字段：轴承角色 与 承载类型。

为什么要分角色：现在 29 条 bearing 里混着三种东西——
  · 真轴承本体（深沟球 / 角接触 / 圆锥滚子 / 滚针 / 推力滚针 / 轮毂单元）
  · 套圈与垫圈（内圈、外圈杯、推力垫圈）——它们是轴承的零件，本身不是轴承
  · 内含轴承的总成（张紧器、单向皮带轮、空调压缩机、离合器分泵）——带轴承但本体不是
把这三种混在一个标签下，任何按轴承做的统计都是错的。

承载类型按轴承结构定，不是猜：
  深沟球 → 径向为主，可承受小量双向轴向
  角接触 / 轮毂单元 → 径向 + 轴向（成对或双列）
  圆锥滚子 → 径向 + 单向轴向，必须成对预紧
  滚针 → 纯径向，小径向空间里排布密
  推力滚针 → 纯轴向

用法：uv run --no-project python tools/enrich_bearings.py [--write]
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'parts.json')

# 判定顺序即优先级：先认套圈和总成，再认本体类型。
# 「二挡轴承内圈」里也有"轴承"二字，不先摘出来就会被当成滚针本体。
ROLE_RULES = [
    (re.compile(r'内圈|外圈|滚道|垫圈|挡圈|\brace\b', re.I), 'race'),
    (re.compile(r'张紧器|皮带轮|压缩机|分泵|总成带|水泵|离合器分泵'), 'contains'),
]
KIND_RULES = [
    (re.compile(r'轮毂单元'), 'hub_unit',    '轮毂单元',   'Hub unit',            'radial_axial'),
    (re.compile(r'推力.*滚针|滚针.*推力'), 'thrust_needle', '推力滚针', 'Thrust needle roller', 'axial'),
    (re.compile(r'圆锥滚子'), 'taper',       '圆锥滚子',   'Tapered roller',      'radial_axial_paired'),
    (re.compile(r'角接触'),   'angular',     '角接触球',   'Angular contact ball', 'radial_axial'),
    (re.compile(r'滚针'),     'needle',      '滚针',       'Needle roller',       'radial'),
    (re.compile(r'深沟球'),   'deep_groove', '深沟球',     'Deep groove ball',    'radial'),
]
LOAD_TEXT = {
    'radial':              ('径向为主', 'Mainly radial'),
    'axial':               ('纯轴向', 'Axial only'),
    'radial_axial':        ('径向 + 轴向', 'Radial + axial'),
    'radial_axial_paired': ('径向 + 单向轴向，需成对预紧', 'Radial + one-way axial, must be preloaded in pairs'),
}


def classify(p):
    # 角色只看零件名，不看规格。规格里常写「与内圈 33356-12020 配对」，
    # 拿规格判角色，真滚针轴承就会因为提到了内圈而被判成套圈 —— 实测 4 条中招。
    # 名字是权威的：「二挡轴承内圈」和「二挡齿轮滚针轴承」说的是两个零件。
    nm = (p.get('name_zh') or '') + ' ' + (p.get('name_en') or '')
    txt = nm + ' ' + (p.get('spec') or '')
    role = 'bearing'
    for pat, r in ROLE_RULES:
        if pat.search(nm):
            role = r
            break
    kind = load = None
    for pat, k, zh, en, ld in KIND_RULES:
        if pat.search(txt):
            kind, load = k, ld
            break
    return role, kind, load


def main():
    write = '--write' in sys.argv
    doc = json.load(open(SRC, encoding='utf-8'))
    rows, stat = [], {}
    for p in doc['parts']:
        if 'bearing' not in (p.get('tags') or []):
            p.pop('bearing_role', None)
            p.pop('bearing_kind', None)
            p.pop('bearing_load', None)
            continue
        role, kind, load = classify(p)
        p['bearing_role'] = role
        p['bearing_kind'] = kind or ''
        p['bearing_load'] = load or ''
        stat[role] = stat.get(role, 0) + 1
        rows.append((role, kind or '?', p['oem_pn'] or '（空）', p['name_zh'][:20]))

    print('bearing 标签共 %d 条，按角色：%s' % (len(rows), stat))
    for r in ('bearing', 'race', 'contains'):
        sub = [x for x in rows if x[0] == r]
        if not sub:
            continue
        print('\n[%s] %d 条：' % (r, len(sub)))
        for _, k, pn, zh in sorted(sub, key=lambda x: (x[1], x[2])):
            print('    %-14s %-14s %s' % (k, pn, zh))

    if write:
        json.dump(doc, open(SRC, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('\n已写回 data/parts.json')
    else:
        print('\n（试跑，没写。加 --write 才落盘）')


if __name__ == '__main__':
    main()
