#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
validate_data.py — data/parts.json 的判定脚本（A 的验收关）

跑法:  uv run --no-project python tools/validate_data.py

判定在任务 1 冻结，之后只许加新判定，不许放宽或删除已有判定。
每条判定独立打印 PASS/FAIL，任何一条 FAIL 则退出码为 1。
"""

import json
import os
import re
import sys
from collections import Counter, defaultdict, deque

# Windows 控制台默认 GBK，判定输出含中文与符号，强制 UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PARTS_PATH = os.path.join(ROOT, "data", "parts.json")

# ---- 冻结常量 --------------------------------------------------------------

GROUPS = {"body", "electrical", "engine_fuel_tool", "powertrain_chassis"}

TAGS = {
    "bearing", "motor", "gear", "seat", "door_window", "electrical",
    "audio", "wheel_hub", "tire", "brake", "steering", "suspension",
    "body_panel", "sensor",
}

# 领导点名的九类
CORE_TAGS = [
    "bearing", "motor", "gear", "seat", "door_window",
    "electrical", "audio", "wheel_hub", "tire",
]

BEARING_TYPES = ["深沟球", "角接触", "圆锥滚子", "滚针", "轮毂单元"]

# 2026-07-31 验收方裁决：允许第三段内饰色/纹理码。
# 出处是 BLOCKED_A.md 第 2.1 节 —— A 报告过真实零件号有 45100-0Z120-C0 这种三段形式，
# 原来的 5-5 两段正则装不下，A 当时只能把这类件的号留空。
# 这是把判定改对去贴合现实，不是放宽判定让数据蒙混：两段号依然必须是 5-5，
# 第三段是可选的两位码，其余判定和阈值一条没动。
OEM_RE = re.compile(r"^[0-9A-Z]{5}-[0-9A-Z]{5}(-[0-9A-Z]{2})?$")
ID_RE = re.compile(r"^[a-z0-9_]+$")
QTY_KINDS = {"exact", "approx"}
CONFIDENCES = {"confirmed", "typical", "guess"}

FIELDS = [
    "id", "group", "subgroup_en", "subgroup_zh", "name_en", "name_zh",
    "oem_pn", "parent", "connects_to", "role_zh", "role_en", "qty",
    "qty_kind", "tags", "has_mesh", "spec", "suppliers",
    # 2026-07-31 验收方授权扩展：补专业拆解基准的四个维度。
    # 只是把冻结字段表加长，原有 17 个字段的判定和阈值一条没动。
    # material / process 取受控词表里的枚举码，fastening 是 [{type,spec,count}]，
    # weight_g 按品类工程经验值，weight_basis 记明来路（category_typical / sum_of_children）。
    "material", "process", "fastening", "weight_g", "weight_basis", "weight_conf",
    # 2026-07-31 第二次扩展：参数化成本估算。cost_basis 记明是模型算的还是子件之和，
    # 界面上必须标出它不是采购价。系数表在 tools/enrich_parts.py。
    "cost_cny", "cost_basis",
    # 2026-08-04 第三次扩展：拆解工时与可拆性。
    # 工时 = Σ(紧固件单件拆卸耗时 × 数量) + 层级深度 × 通达系数；焊接件标 destructive 不给工时。
    "disassembly_min", "disassembly_kind", "tree_depth",
]

# 2026-08-04 第四次扩展：只挂在部分零件上的字段，允许存在但不强制每条都有。
# 轴承专业字段只对 tags 含 bearing 的零件有意义，给全表都塞一个空值反而是噪声。
OPTIONAL_FIELDS = ["bearing_role", "bearing_kind", "bearing_load"]

# ---- 判定框架 --------------------------------------------------------------

_results = []


def check(name, ok, detail=""):
    _results.append((name, bool(ok)))
    flag = "PASS" if ok else "FAIL"
    line = "[%s] %s" % (flag, name)
    if detail:
        line += "\n         " + str(detail).replace("\n", "\n         ")
    print(line)


def han_len(s):
    """中文字数：汉字按字计，其余按字符计。"""
    return len(s)


def word_len(s):
    return len([w for w in re.split(r"[\s,.;:()/-]+", s) if w])


# ---- 载入 ------------------------------------------------------------------

def main():
    print("=" * 74)
    print("validate_data.py  —  %s" % PARTS_PATH)
    print("=" * 74)

    if not os.path.exists(PARTS_PATH):
        check("data/parts.json 存在", False, "文件不存在: %s" % PARTS_PATH)
        return finish()

    with open(PARTS_PATH, "r", encoding="utf-8") as f:
        doc = json.load(f)

    check("顶层结构为 {vehicle, parts}",
          isinstance(doc, dict) and "vehicle" in doc and isinstance(doc.get("parts"), list),
          "keys=%s" % sorted(doc.keys()) if isinstance(doc, dict) else type(doc))

    parts = doc.get("parts", []) if isinstance(doc, dict) else []

    # ---- 字段完整性 ----
    bad_fields = []
    for p in parts:
        missing = [k for k in FIELDS if k not in p]
        extra = [k for k in p if k not in FIELDS and k not in OPTIONAL_FIELDS]
        if missing or extra:
            bad_fields.append((p.get("id", "?"), missing, extra))
    check("每条零件字段名与冻结格式完全一致（不多不少）",
          not bad_fields,
          "前 5 条异常: %s" % bad_fields[:5] if bad_fields else "共 %d 条，字段全对" % len(parts))

    # ---- 1. 条数 ----
    check("parts >= 350", len(parts) >= 350, "实际 parts = %d" % len(parts))

    # ---- 2. id 唯一 ----
    ids = [p.get("id") for p in parts]
    dup = [i for i, c in Counter(ids).items() if c > 1]
    check("id 唯一", not dup, "重复 id: %s" % dup[:10] if dup else "共 %d 个唯一 id" % len(set(ids)))

    bad_id = [i for i in ids if not (isinstance(i, str) and ID_RE.match(i))]
    check("id 为小写下划线格式", not bad_id, "非法 id: %s" % bad_id[:10] if bad_id else "全部合法")

    # ---- 3. group ----
    gs = Counter(p.get("group") for p in parts)
    unknown_g = set(gs) - GROUPS
    check("group 四个值都出现且无第五种",
          set(gs) == GROUPS,
          "分布 %s  非法值 %s" % (dict(gs), sorted(unknown_g) if unknown_g else "无"))

    # ---- 4. subgroup 去重 ----
    subs = set(p.get("subgroup_en") for p in parts if p.get("subgroup_en"))
    check("subgroup_en 去重 >= 60", len(subs) >= 60, "去重后 = %d" % len(subs))

    empty_sub = [p.get("id") for p in parts
                 if not p.get("subgroup_en") or not p.get("subgroup_zh")]
    check("subgroup_en / subgroup_zh 均非空",
          not empty_sub, "缺失: %s" % empty_sub[:10] if empty_sub else "全部有图组")

    # ---- 5. has_mesh ----
    mesh = [p for p in parts if p.get("has_mesh") is True]
    bad_mesh_type = [p.get("id") for p in parts if not isinstance(p.get("has_mesh"), bool)]
    check("has_mesh 为布尔", not bad_mesh_type,
          "非布尔: %s" % bad_mesh_type[:10] if bad_mesh_type else "全部为布尔")
    check("has_mesh=true 的 >= 110", len(mesh) >= 110, "实际 = %d" % len(mesh))

    # ---- 6. 核心件零件号 ----
    def is_core(p):
        if p.get("has_mesh") is True:
            return True
        return bool(set(p.get("tags") or []) & set(CORE_TAGS))

    core = [p for p in parts if is_core(p)]
    bad_pn = []
    for p in core:
        pn = p.get("oem_pn")
        if not pn or not (isinstance(pn, str) and OEM_RE.match(pn)):
            bad_pn.append((p.get("id"), pn))
    check("核心件 oem_pn 非空且合正则 ^[0-9A-Z]{5}-[0-9A-Z]{5}$",
          not bad_pn,
          "违规 %d 条，前 8: %s" % (len(bad_pn), bad_pn[:8]) if bad_pn
          else "核心件 %d 条，零件号全部合规" % len(core))

    # 非核心件若填了零件号，也必须合正则（不许填半截号糊弄）
    bad_pn2 = [(p.get("id"), p.get("oem_pn")) for p in parts
               if p.get("oem_pn") and not OEM_RE.match(str(p.get("oem_pn")))]
    check("非空 oem_pn 一律合正则", not bad_pn2,
          "违规: %s" % bad_pn2[:8] if bad_pn2 else "所有非空零件号格式正确")

    # ---- 7. 九类各 >=8 条，其中 has_mesh >=3 ----
    per_tag = defaultdict(list)
    for p in parts:
        for t in (p.get("tags") or []):
            per_tag[t].append(p)

    short = []
    short_mesh = []
    for t in CORE_TAGS:
        n = len(per_tag[t])
        nm = len([p for p in per_tag[t] if p.get("has_mesh") is True])
        if n < 8:
            short.append("%s=%d" % (t, n))
        if nm < 3:
            short_mesh.append("%s(mesh)=%d" % (t, nm))
    tally = "  ".join("%s:%d/mesh%d" % (t, len(per_tag[t]),
                      len([p for p in per_tag[t] if p.get("has_mesh") is True]))
                      for t in CORE_TAGS)
    check("九类每类 >= 8 条", not short, ("不足: %s" % short) if short else tally)
    check("九类每类中 has_mesh=true 的 >= 3 条", not short_mesh,
          ("不足: %s" % short_mesh) if short_mesh else tally)

    # ---- 8. tags 合法 + bearing ----
    bad_tags = []
    for p in parts:
        t = p.get("tags")
        if not isinstance(t, list) or not t:
            bad_tags.append((p.get("id"), t))
        else:
            ill = set(t) - TAGS
            if ill:
                bad_tags.append((p.get("id"), sorted(ill)))
    check("tags 非空且取值全在白名单内", not bad_tags,
          "违规: %s" % bad_tags[:8] if bad_tags else "全部合法")

    brg = per_tag["bearing"]
    check("tags 含 bearing 的 >= 18 条", len(brg) >= 18, "实际 = %d" % len(brg))

    no_type = [p.get("id") for p in brg
               if not any(k in (p.get("spec") or "") for k in BEARING_TYPES)]
    check("每个 bearing 件的 spec 含五种轴承类型之一",
          not no_type,
          "缺类型: %s" % no_type[:8] if no_type
          else "%d 条 bearing 件 spec 全部标明轴承类型" % len(brg))

    empty_spec = [p.get("id") for p in parts if not str(p.get("spec") or "").strip()]
    check("spec 非空", not empty_spec,
          "空 spec: %s" % empty_spec[:8] if empty_spec else "全部有 spec")

    # ---- 9. 连接与树 ----
    idset = set(ids)
    no_conn = [p.get("id") for p in parts
               if not isinstance(p.get("connects_to"), list) or len(p["connects_to"]) < 1]
    check("connects_to 每条 >= 1", not no_conn,
          "违规: %s" % no_conn[:8] if no_conn else "全部至少连 1 个")

    dangling = []
    for p in parts:
        for c in (p.get("connects_to") or []):
            if c not in idset:
                dangling.append((p.get("id"), c))
    check("connects_to 引用的 id 都存在", not dangling,
          "悬空引用 %d 个，前 8: %s" % (len(dangling), dangling[:8]) if dangling
          else "全部引用有效")

    self_conn = [p.get("id") for p in parts if p.get("id") in (p.get("connects_to") or [])]
    check("connects_to 不自连", not self_conn,
          "自连: %s" % self_conn[:8] if self_conn else "无自连")

    # parent 合法性
    pmap = {p.get("id"): p.get("parent") for p in parts}
    bad_parent = [(i, pa) for i, pa in pmap.items() if pa and pa not in idset]
    check("parent 引用的 id 都存在", not bad_parent,
          "悬空 parent: %s" % bad_parent[:8] if bad_parent else "全部有效")

    roots = [i for i, pa in pmap.items() if pa == ""]
    check("有且仅有一个顶层根（parent 为空串）", len(roots) == 1,
          "根 = %s" % roots[:10])

    # parent 链无环
    cyc = []
    for i in ids:
        seen, cur, steps = set(), i, 0
        while cur and steps < 10000:
            if cur in seen:
                cyc.append(i)
                break
            seen.add(cur)
            cur = pmap.get(cur, "")
            steps += 1
    check("parent 链无环", not cyc, "成环: %s" % sorted(set(cyc))[:8] if cyc else "无环")

    # 以车身为根可达所有节点
    if len(roots) == 1 and not cyc:
        children = defaultdict(list)
        for i, pa in pmap.items():
            if pa:
                children[pa].append(i)
        seen = set()
        q = deque([roots[0]])
        while q:
            cur = q.popleft()
            if cur in seen:
                continue
            seen.add(cur)
            q.extend(children[cur])
        orphan = sorted(idset - seen)
        check("以车身为根能走到所有节点，孤点 0",
              not orphan,
              "孤点 %d 个，前 8: %s" % (len(orphan), orphan[:8]) if orphan
              else "根 = %s，覆盖 %d/%d 节点" % (roots[0], len(seen), len(idset)))
    else:
        check("以车身为根能走到所有节点，孤点 0", False, "根不唯一或 parent 成环，无法判定")

    # ---- 10. suppliers ----
    few = [p.get("id") for p in parts
           if not isinstance(p.get("suppliers"), list) or len(p["suppliers"]) < 3]
    check("每条 suppliers >= 3", not few,
          "不足 3 条: %s" % few[:8] if few else "全部 >= 3")

    bad_conf, bad_src, bad_shape = [], [], []
    for p in parts:
        for s in (p.get("suppliers") or []):
            if not isinstance(s, dict) or set(s.keys()) != {"name", "note", "confidence", "source"}:
                bad_shape.append((p.get("id"), s if not isinstance(s, dict) else sorted(s.keys())))
                continue
            if s.get("confidence") not in CONFIDENCES:
                bad_conf.append((p.get("id"), s.get("confidence")))
            if s.get("confidence") == "confirmed" and not str(s.get("source") or "").strip():
                bad_src.append((p.get("id"), s.get("name")))
            if not str(s.get("name") or "").strip() or not str(s.get("note") or "").strip():
                bad_shape.append((p.get("id"), "name/note 为空"))
    check("suppliers 每条含 name/note/confidence/source 四个键", not bad_shape,
          "违规: %s" % bad_shape[:8] if bad_shape else "结构全对")
    check("suppliers.confidence 取值合法", not bad_conf,
          "非法: %s" % bad_conf[:8] if bad_conf else "全部为 confirmed/typical/guess")
    check("标 confirmed 的 suppliers 必须给 source", not bad_src,
          "缺 source: %s" % bad_src[:8] if bad_src else "confirmed 项全部有网址")

    # ---- 11. role 防灌水 ----
    pre = defaultdict(list)
    for p in parts:
        pre[str(p.get("role_zh") or "")[:20]].append(p.get("id"))
    clash = {k: v for k, v in pre.items() if len(v) > 1}
    check("role_zh 前 20 字在全表唯一",
          not clash,
          "撞车 %d 组，前 3: %s" % (len(clash), list(clash.items())[:3]) if clash
          else "%d 条 role_zh 开头互不相同" % len(parts))

    short_zh = [(p.get("id"), han_len(str(p.get("role_zh") or ""))) for p in parts
                if han_len(str(p.get("role_zh") or "")) < 40]
    check("role_zh >= 40 字", not short_zh,
          "过短: %s" % short_zh[:8] if short_zh else "全部 >= 40 字")

    short_en = [(p.get("id"), word_len(str(p.get("role_en") or ""))) for p in parts
                if word_len(str(p.get("role_en") or "")) < 40]
    check("role_en >= 40 词", not short_en,
          "过短: %s" % short_en[:8] if short_en else "全部 >= 40 词")

    # ---- 12. 杂项冻结字段 ----
    bad_qk = [(p.get("id"), p.get("qty_kind")) for p in parts
              if p.get("qty_kind") not in QTY_KINDS]
    check("qty_kind 取 exact / approx", not bad_qk,
          "非法: %s" % bad_qk[:8] if bad_qk else "全部合法")

    bad_qty = [(p.get("id"), p.get("qty")) for p in parts
               if not isinstance(p.get("qty"), (int, float)) or isinstance(p.get("qty"), bool)
               or p.get("qty") <= 0]
    check("qty 为正数", not bad_qty,
          "非法: %s" % bad_qty[:8] if bad_qty else "全部为正数")

    bad_name = [p.get("id") for p in parts
                if not str(p.get("name_en") or "").strip() or not str(p.get("name_zh") or "").strip()]
    check("name_en / name_zh 均非空", not bad_name,
          "缺失: %s" % bad_name[:8] if bad_name else "全部有中英文名")

    # ---- 摘要 ----
    print("-" * 74)
    print("摘要：parts=%d  has_mesh=%d  subgroup_en去重=%d  bearing=%d"
          % (len(parts), len(mesh), len(subs), len(brg)))
    print("      group 分布: %s" % dict(gs))
    print("      有零件号: %d / %d (%.1f%%)"
          % (sum(1 for p in parts if p.get("oem_pn")), len(parts),
             100.0 * sum(1 for p in parts if p.get("oem_pn")) / max(1, len(parts))))
    return finish()


def finish():
    print("-" * 74)
    failed = [n for n, ok in _results if not ok]
    if failed:
        print("结果：%d/%d 判定通过，FAIL %d 条：" % (len(_results) - len(failed), len(_results), len(failed)))
        for n in failed:
            print("   ✗ %s" % n)
        return 1
    print("结果：全绿 —— %d/%d 判定全部通过" % (len(_results), len(_results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
