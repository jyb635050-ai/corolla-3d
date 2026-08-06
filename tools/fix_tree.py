# -*- coding: utf-8 -*-
"""修装配树：把「小件当了大件父节点」的层级错误纠正过来。

病灶来历：A 当初给一批节点起的 id 是总成（cylinder_head_assy / transaxle_mtm_assy），
往下挂了整组零件；后来 audit_naming 查出这些 id 对应的官方零件其实是垫片、螺塞垫，
fix_ids 把 id 改对了，子件却还留在原地 —— 于是一个气缸盖罩垫成了 15 个零件的父节点。

判据（自动、可复算）：官方零件名的主体词是「小件类型」（Gasket / Support / Sensor /
Moulding / Pad …），却挂着子件 —— 这才是确凿的层级错误。处理是把子件提升到它的
父节点（祖父），它自己降为叶子。提升而不是删除，是为了不把子件变成孤点，
连通性判定还得过。

试过但推翻的判据：「自身品类经验重量 < 子件之和的 1/5」。规则表给的是单件重量，
而正当总成（前悬架总成、制动系统总成）的子件之和本来就该远大于任一单件，
用它会把一大批正确的总成误判掉，body_shell 甚至会自己判自己。别再往回改。

特例先处理：气缸盖罩垫下面那批本来就属于新补进来的真气缸盖，直接认领过去。

用法：uv run --no-project python tools/fix_tree.py [--write]
"""
import json, os, re, sys, importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'parts.json')

spec = importlib.util.spec_from_file_location('enrich', os.path.join(ROOT, 'tools', 'enrich_parts.py'))
enrich_mod = importlib.util.module_from_spec(spec)
_argv, sys.argv = sys.argv, ['x']
spec.loader.exec_module(enrich_mod)
sys.argv = _argv

# 明确知道该归谁的，先认领；剩下的交给通用判据
CLAIM = {
    'head_cover_gasket': 'cylinder_head',      # 缸盖内部件本来就属于新补的真气缸盖
}


def main():
    write = '--write' in sys.argv
    doc = json.load(open(SRC, encoding='utf-8'))
    parts = doc['parts']
    byid = {p['id']: p for p in parts}

    def children_of(pid):
        return [p for p in parts if p.get('parent') == pid]

    claimed = 0
    for bad, good in CLAIM.items():
        if bad not in byid or good not in byid:
            continue
        for c in children_of(bad):
            c['parent'] = good
            claimed += 1
    print('按名认领：%d 个子件改挂到真零件下' % claimed)

    # 判据只认一件事：官方名的主体词是「小件类型」却挂着子件。
    # 别拿「自身经验重量 vs 子件之和」当通用判据 —— 规则表给的是单件重量，
    # 而正当总成（前悬架总成、制动系统总成）的子件之和本来就该远大于任一单件，
    # 那样会把一大批正确的总成误判掉。实测踩过，body_shell 甚至会自己判自己。
    SMALL_HEAD = re.compile(
        r'^(gasket|seal|o-?ring|packing|grommet|plug|bolt|nut|screw|washer|stud|clip|clamp|'
        r'cap|retainer|pin|shim|spacer|bushing|bracket|stay|support|moulding|molding|garnish|'
        r'cover|sensor|camera|wire|pad|ring|race|band|hose|carrier|label|emblem|ornament)\b', re.I)

    promoted, rounds = [], 0
    while rounds < 6:
        rounds += 1
        changed = 0
        for p in parts:
            if p['id'] == 'body_shell':
                continue
            kids = children_of(p['id'])
            if not kids:
                continue
            head = (p.get('name_en') or '').split(',')[0].strip()
            head = re.sub(r'\b(sub-?assy|assy|assembly)\b', ' ', head, flags=re.I).strip()
            if not SMALL_HEAD.match(head):
                continue
            gp = p.get('parent') or 'body_shell'
            if gp == p['id']:
                gp = 'body_shell'
            for k in kids:
                k['parent'] = gp
            promoted.append((p['id'], p.get('name_zh', '')[:18], head[:22], len(kids), gp))
            changed += 1
        if not changed:
            break

    print('\n官方名是小件却挂着子件、已把子件提升的 %d 个（扫了 %d 轮）：' % (len(promoted), rounds))
    for pid, zh, head, n, gp in promoted:
        print('  %-26s %-18s 官方名主体「%s」 子件%2d → 提升到 %s' % (pid, zh, head, n, gp))

    if write:
        json.dump(doc, open(SRC, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('\n已写回。记得再跑 enrich_parts.py --write 重算滚加重量。')
    else:
        print('\n（试跑，没写。加 --write 才落盘）')


if __name__ == '__main__':
    main()
