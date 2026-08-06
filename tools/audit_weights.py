# -*- coding: utf-8 -*-
"""重量合理性审计：不靠调规则，靠物理上下界把离谱值挑出来。

三道独立于规则的检验：
  A 实心上界：有 3D 的零件，重量不能超过「包围盒体积 × 材料密度 × 0.6」。
    0.6 是形状填充率的宽松上限——再实心的零件也填不满自己的包围盒。
  B 品类常识上限：垫片/密封/O 圈/卡扣/螺栓/销 这类小五金不该超过 300 g。
  C 品类常识下限：名字里带 Assy/Assembly 的叶子件不该轻于 500 g。

用法：uv run --no-project --with playwright python tools/audit_weights.py
     （需要起页面量包围盒；只读，不改数据）
"""
import json, os, re, sys, threading, functools, http.server, socketserver

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from enrich_parts import MATERIALS  # noqa: E402

SMALL = re.compile(r'gasket|\bseal\b|o-?ring|packing|grommet|\bclip\b|\bbolt\b|\bnut\b|'
                   r'\bscrew\b|\bwasher\b|\bpin\b|\bkey\b|\bshim\b|\bplug\b|\bcap\b', re.I)
ASSY = re.compile(r'\bassy\b|\bassembly\b', re.I)


def bboxes():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)

    class Q(socketserver.ThreadingTCPServer):
        allow_reuse_address = True

        def handle_error(self, *a):
            pass

    srv = Q(('127.0.0.1', 0), h)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel='chrome')
        pg = b.new_page()
        pg.goto(f'http://127.0.0.1:{port}/index.html')
        pg.wait_for_function('window.__car && window.__car.ready === true', timeout=90000)
        pg.wait_for_timeout(500)
        out = pg.evaluate("""() => {
          const o = {};
          for (const id of window.__car.partIds) o[id] = window.__car.volumeOf(id);
          return o;
        }""")
        b.close()
    srv.shutdown()
    return out


def main():
    doc = json.load(open(os.path.join(ROOT, 'data', 'parts.json'), encoding='utf-8'))
    parts = doc['parts']
    byid = {p['id']: p for p in parts}
    kids = {}
    for p in parts:
        if p.get('parent') in byid:
            kids.setdefault(p['parent'], []).append(p['id'])

    vol = bboxes()
    bad = []
    for p in parts:
        w = p.get('weight_g') or 0
        nm = p['name_en'] or ''
        why = None
        if p['id'] in vol and vol[p['id']]:
            bb = vol[p['id']]['bbox']
            cap = bb[0] * bb[1] * bb[2] * MATERIALS[p['material']][2] * 1000 * 0.6
            if cap > 0 and w > cap:
                why = '超实心上界 %.0fg（包围盒 %.2f×%.2f×%.2f）' % (cap, *bb)
        if not why and SMALL.search(nm) and w > 300:
            why = '小五金却 %dg' % w
        if not why and ASSY.search(nm) and not kids.get(p['id']) and w < 500:
            why = '总成却只有 %dg' % w
        if why:
            bad.append((w, p['id'], p['name_zh'][:22], nm[:44], why))

    bad.sort(reverse=True)
    print('审计 %d 条，可疑 %d 条\n' % (len(parts), len(bad)))
    for w, pid, zh, en, why in bad:
        print('%8dg  %-26s %-22s %s' % (w, pid, zh, why))
    print('\n树结构可疑（总成下面挂了不该挂的）：')
    for pid, ks in kids.items():
        if len(ks) > 12:
            print('  %s(%s) 下挂 %d 个子件' % (byid[pid]['name_zh'], pid, len(ks)))


if __name__ == '__main__':
    main()
