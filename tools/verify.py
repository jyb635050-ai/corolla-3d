# -*- coding: utf-8 -*-
"""
verify.py —— 卡罗拉分解页的验收脚本（B 的地界）

跑法：
    uv run --no-project --with playwright python tools/verify.py

自己起静态服务（不依赖外面已经开着的 4399），自己用 playwright + 本机 Chrome 跑，
每条判定打印 PASS / FAIL，有一条 FAIL 就 exit 1。

判定与阈值一经写下不再放宽、不再删除，只允许往后追加新判定。
不许出现 try/except pass、|| true 这类把红变绿的写法 —— 本文件里一处都没有，
唯一的 except 是打印错误后立刻判 FAIL。

关于「console 零 error」这条的一处明写豁免（不是放宽，是把噪声定死在一条上）：
页面按任务书要求先探 data/parts.json 再降级到 stub。A 的数据还没交时这个探测必然
产生一条浏览器级 404，它不是代码坏了。所以本脚本只在 dataSource=='stub' 时，
豁免「恰好 1 条、且 URL 以 data/parts.json 结尾」的资源加载失败，并且每次都原样打印
出来。dataSource=='real' 时一条都不豁免。除此之外任何 error / pageerror 一律判 FAIL。
"""

import functools
import hashlib
import http.server
import json
import os
import random
import re
import socket
import sys
import threading
import time

for _s in (sys.stdout, sys.stderr):          # Windows 控制台默认 GBK，中文判定名会变乱码
    if hasattr(_s, 'reconfigure'):
        _s.reconfigure(encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CJK = re.compile(r'[一-鿿]')

# ── 阈值（冻结）
MIN_MESH_PARTS = 110
EXPLODE_RATIO = 2.2
REASSEMBLE_TOL = 0.005          # 0.5%
MAX_TRIANGLES = 600000
MAX_CALLS = 600
MAX_FRAME_P95_MS = 45
COVERAGE_LO, COVERAGE_HI = 0.60, 0.75
SAMPLE_N = 10

results = []


def check(name, ok, detail=''):
    results.append((name, bool(ok), detail))
    print(('PASS  ' if ok else 'FAIL  ') + name + (('  |  ' + detail) if detail else ''))
    return bool(ok)


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
    handler.log_message = lambda *a, **k: None
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f'http://127.0.0.1:{port}/index.html'


def boxes_disjoint(a, b, eps=1e-6):
    for i in range(3):
        if a['max'][i] <= b['min'][i] + eps or b['max'][i] <= a['min'][i] + eps:
            return True
    return False


def main():
    from playwright.sync_api import sync_playwright

    httpd, url = serve()
    print(f'# 静态服务 {url}')
    print(f'# 站点根目录 {ROOT}')
    print()

    console_errors = []   # (text, url)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 900})

        def on_console(m):
            if m.type == 'error':
                loc = m.location or {}
                console_errors.append((m.text, loc.get('url', '')))

        page.on('console', on_console)
        page.on('pageerror', lambda e: console_errors.append(('pageerror: ' + str(e), '')))

        page.goto(url)
        page.wait_for_function('window.__car && window.__car.ready === true', timeout=90000)
        page.wait_for_timeout(3200)   # 攒够 frameP95 的样本

        car = lambda expr: page.evaluate('window.__car.' + expr)

        # ── 0. 数据源
        source = car('dataSource')
        issue = car('dataIssue')
        print(f'# dataSource = {source}')
        if issue:
            print('# data/parts.json 未采用，原因：' + json.dumps(issue, ensure_ascii=False)[:400])
        print()

        # ── 1. partIds 与数据里 has_mesh=true 的 id 集合完全相等，且 >= 110
        part_ids = car('partIds')
        data = car('data')
        mesh_ids = [p['id'] for p in data['parts'] if p.get('has_mesh') is True]
        set_p, set_m = set(part_ids), set(mesh_ids)
        check('partIds 数量 >= %d' % MIN_MESH_PARTS,
              len(part_ids) >= MIN_MESH_PARTS, f'partIds={len(part_ids)}')
        check('partIds 无重复',
              len(part_ids) == len(set_p), f'{len(part_ids)} 项 / {len(set_p)} 个不同')
        check('partIds 与 has_mesh=true 集合完全相等',
              set_p == set_m,
              f'has_mesh={len(set_m)} partIds={len(set_p)} '
              f'多出={sorted(set_p - set_m)[:5]} 缺少={sorted(set_m - set_p)[:5]}')

        # ── 2. 场景里带 id 的 Object3D 个数 == partIds 长度（防大网格冒充一堆零件）
        n_id_objs = car('countIdObjects()')
        check('场景中 userData.id 非空的 Object3D 个数 == partIds 长度',
              n_id_objs == len(part_ids), f'场景={n_id_objs} partIds={len(part_ids)}')

        empty = [i for i in part_ids if car(f'meshCountFor({json.dumps(i)})') == 0]
        check('每个 partId 底下至少挂着 1 个真实 Mesh',
              not empty, f'空壳零件={empty[:5]}')

        # ── 3. 默认视角构图
        cov = car('coverage()')
        check('默认视角整车占画面 %.0f%%~%.0f%%' % (COVERAGE_LO * 100, COVERAGE_HI * 100),
              COVERAGE_LO <= cov['max'] <= COVERAGE_HI,
              f'宽占比={cov["w"]} 高占比={cov["h"]}')

        # ── 4. 爆炸 / 合拢
        bbox0 = car('bbox()')
        t0 = time.time()
        page.evaluate('window.__car.explode()')
        dt_explode = time.time() - t0
        state1 = car('state')
        bbox1 = car('bbox()')
        ratio = bbox1['maxEdge'] / bbox0['maxEdge']
        check('explode() 后 bbox 最大边 >= 组装态 %.1f 倍' % EXPLODE_RATIO,
              ratio >= EXPLODE_RATIO,
              f'组装={bbox0["maxEdge"]:.3f} 爆炸={bbox1["maxEdge"]:.3f} 倍数={ratio:.3f}')
        check('explode() 的 Promise 等到动画结束才 resolve',
              state1 == 'exploded' and dt_explode > 0.6,
              f'state={state1} 耗时={dt_explode:.2f}s')

        clusters = car('clusterBoxes()')
        pairs, bad = [], []
        names = sorted(clusters.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                pairs.append((names[i], names[j]))
                if not boxes_disjoint(clusters[names[i]], clusters[names[j]]):
                    bad.append(f'{names[i]}×{names[j]}')
        check('爆炸态四大部分的包围盒两两不相交',
              len(names) >= 2 and not bad, f'{len(pairs)} 对，相交的={bad}')

        page.evaluate('window.__car.assemble()')
        bbox2 = car('bbox()')
        drift = max(abs(bbox2[k][i] - bbox0[k][i]) for k in ('min', 'max') for i in range(3))
        rel = drift / bbox0['maxEdge']
        check('assemble() 后与初始 bbox 误差 < %.1f%%' % (REASSEMBLE_TOL * 100),
              rel < REASSEMBLE_TOL and car('state') == 'assembled',
              f'最大偏差={drift:.5f}m 相对={rel * 100:.4f}%')

        # ── 5. 性能
        page.wait_for_timeout(2200)
        st = car('stats()')
        check('triangles < %d' % MAX_TRIANGLES, st['triangles'] < MAX_TRIANGLES, f'triangles={st["triangles"]}')
        check('draw calls < %d' % MAX_CALLS, st['calls'] < MAX_CALLS, f'calls={st["calls"]}')
        check('frameP95 < %d ms' % MAX_FRAME_P95_MS,
              st['frameP95'] < MAX_FRAME_P95_MS and st['frames'] >= 60,
              f'frameP95={st["frameP95"]}ms 帧内耗时P95={st["frameWorkP95"]}ms 样本={st["frames"]}')

        # ── 6. 面板：随机 10 个零件
        rnd = random.Random()
        sample = rnd.sample(part_ids, min(SAMPLE_N, len(part_ids)))
        print('# 抽中的 10 个零件：' + ', '.join(sample))
        by_id = {p['id']: p for p in data['parts']}
        miss_name, miss_pn, miss_sel = [], [], []
        for pid in sample:
            if not car(f'select({json.dumps(pid)})'):
                miss_sel.append(pid)
                continue
            txt = car('panelText()')
            pt = by_id[pid]
            if pt['name_zh'] not in txt:
                miss_name.append(pid)
            if pt['oem_pn'] and pt['oem_pn'] not in txt:
                miss_pn.append(pid)
        check('随机 10 个零件都能 select', not miss_sel, f'失败={miss_sel}')
        check('panelText() 含该零件的 name_zh', not miss_name, f'不含的={miss_name}')
        check('oem_pn 非空的零件，panelText() 含该零件号', not miss_pn, f'不含的={miss_pn}')

        # ── 7. 中英切换
        last_id = sample[-1]
        car(f'select({json.dumps(last_id)})')
        car('setLang("en")')
        page.wait_for_timeout(150)
        body_en = page.evaluate('document.body.innerText')
        panel_en = car('panelText()')
        hits_body = sorted(set(CJK.findall(body_en)))
        hits_panel = sorted(set(CJK.findall(panel_en)))
        check('setLang("en") 后 document.body.innerText 无汉字',
              not hits_body, '出现的汉字=' + ''.join(hits_body[:24]))
        check('setLang("en") 后 panelText() 无汉字',
              not hits_panel, '出现的汉字=' + ''.join(hits_panel[:24]))
        check('英文模式下面板确实有内容（不是靠清空蒙混）',
              by_id[last_id]['name_en'][:18] in panel_en,
              f'期望含 {by_id[last_id]["name_en"][:18]!r}，实际前 60 字={panel_en[:60]!r}')

        car('setLang("zh")')
        page.wait_for_timeout(120)
        check('切回中文后选中的零件没丢',
              car('selected') == last_id and by_id[last_id]['name_zh'] in car('panelText()'),
              f'selected={car("selected")} 期望={last_id}')
        check('切换语言不刷新页面（__car 实例没被重建）',
              car('ready') is True and car('partIds').__len__() == len(part_ids))

        # ── 8. console 零 error
        real, exempt = [], []
        for text, u in console_errors:
            if (source == 'stub' and u.endswith('data/parts.json')
                    and 'Failed to load resource' in text):
                exempt.append((text, u))
            else:
                real.append((text, u))
        for t, u in exempt:
            print(f'      NOTE 已豁免的预期噪声：{t}  <-  {u}')
        check('console 零 error（豁免仅限 data/parts.json 探测的 1 条 404）',
              not real and len(exempt) <= 1,
              f'真错误={len(real)} 豁免={len(exempt)} 头几条={real[:3]}')

        # ── 9. 断网档：掐掉所有非 localhost 请求后重开
        page2 = browser.new_page(viewport={'width': 1440, 'height': 900})
        blocked = []
        offline_errors = []

        def route_all(route, request):
            u = request.url
            if u.startswith('http://127.0.0.1') or u.startswith('http://localhost') or u.startswith('data:'):
                route.continue_()
            else:
                blocked.append(u)
                route.abort()

        page2.route('**/*', route_all)
        page2.on('pageerror', lambda e: offline_errors.append('pageerror: ' + str(e)))
        page2.on('console', lambda m: offline_errors.append(m.text) if m.type == 'error' else None)
        page2.goto(url)
        page2.wait_for_function('window.__car && window.__car.ready === true', timeout=90000)
        page2.wait_for_timeout(600)
        off_ids = page2.evaluate('window.__car.partIds')
        pick = rnd.sample(off_ids, min(5, len(off_ids)))
        off_ok = all(page2.evaluate(f'window.__car.select({json.dumps(i)})') for i in pick)
        off_txt = page2.evaluate('window.__car.panelText()')
        check('断掉所有非 localhost 请求后，__car.ready 仍为 true',
              page2.evaluate('window.__car.ready') is True,
              f'被拦下的外部请求={len(blocked)} 条 {blocked[:3]}')
        check('断网状态下随机 5 个零件仍能 select 且面板有内容',
              off_ok and len(off_txt) > 20, f'抽中={pick} 面板长度={len(off_txt)}')
        check('运行时零 CDN：整轮下来没有任何非 localhost 请求被发起',
              len(blocked) == 0, f'被拦下的外部请求={blocked[:5]}')

        # ── 10. 数据源降级的另外两支
        # A 的 data/parts.json 还没交时，上面只走到了「读不到 → 退 stub」。
        # 这里用 playwright 在网络层把 data/parts.json 顶掉，把另外两支也验了，
        # 全程不往 data/ 写一个字节（那是 A 的地界）。
        stub_doc = json.load(open(os.path.join(ROOT, 'stub', 'parts.stub.json'), encoding='utf-8'))

        good = json.loads(json.dumps(stub_doc))
        good['vehicle']['data_kind'] = 'real-shaped fixture (served in-memory by verify.py)'

        def serve_doc(doc):
            pg = browser.new_page(viewport={'width': 1280, 'height': 800})
            errs = []
            pg.on('pageerror', lambda e: errs.append('pageerror: ' + str(e)))
            pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
            pg.route('**/data/parts.json', lambda r: r.fulfill(
                status=200, content_type='application/json',
                body=json.dumps(doc, ensure_ascii=False)))
            pg.goto(url)
            pg.wait_for_function('window.__car && window.__car.ready === true', timeout=90000)
            pg.wait_for_timeout(400)
            out = {
                'source': pg.evaluate('window.__car.dataSource'),
                'issue': pg.evaluate('window.__car.dataIssue'),
                'n': len(pg.evaluate('window.__car.partIds')),
                'badge': pg.evaluate("document.getElementById('dataBadge').hidden"),
                'errs': errs,
            }
            pg.close()
            return out

        r_good = serve_doc(good)
        # 判定基线更正（2026-07-31，验收方授权）：原写法拿 len(part_ids)（主跑的真数据，216 条）
        # 去比这个 110 条的样本文档，A 的真数据一交付基线就变，判定必然红。
        # 正确的判据是「接进来多少个 has_mesh 件，就该建出多少个」——只改比较对象，判定本身没放宽。
        good_mesh = sum(1 for p in good['parts'] if p.get('has_mesh') is True)
        check('data/parts.json 合格式时接真数据（dataSource=real，示例数据角标消失，零 console error）',
              r_good['source'] == 'real' and r_good['badge'] is True
              and r_good['n'] == good_mesh and not r_good['errs'],
              f'source={r_good["source"]} 角标hidden={r_good["badge"]} '
              f'partIds={r_good["n"]} errors={r_good["errs"][:2]}')

        bad_doc = json.loads(json.dumps(stub_doc))
        del bad_doc['parts'][3]['qty_kind']            # 抽掉一个冻结字段
        bad_doc['parts'][7]['group'] = 'not_a_group'   # 再塞一个非法 group
        r_bad = serve_doc(bad_doc)
        check('data/parts.json 不合冻结格式时退回 stub，并把原因记在 __car.dataIssue 上',
              r_bad['source'] == 'stub' and r_bad['issue']
              and len(r_bad['issue'].get('errs', [])) >= 2 and r_bad['badge'] is False,
              f'source={r_bad["source"]} 角标hidden={r_bad["badge"]} '
              f'记下的原因={json.dumps(r_bad["issue"], ensure_ascii=False)[:200]}')

        browser.close()

    httpd.shutdown()

    bad = [n for n, ok, _ in results if not ok]
    print()
    print('=' * 64)
    print(f'共 {len(results)} 条判定，PASS {len(results) - len(bad)}，FAIL {len(bad)}')
    if bad:
        for n in bad:
            print('  FAIL: ' + n)
    else:
        print('全绿。')
    print('verify.py sha256 = ' + hashlib.sha256(
        open(os.path.abspath(__file__), 'rb').read()).hexdigest())
    print('=' * 64)
    return 1 if bad else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:                      # 不吞异常：打完就判失败退出
        import traceback
        traceback.print_exc()
        print('FAIL  verify.py 自身抛异常：' + repr(e))
        sys.exit(1)
