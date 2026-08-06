# BLOCKED_B — B（3D / 爆炸 / 面板 / 中英）的卡点

写作日期：2026-07-30

**阻塞我干活的事：无。** 任务 0～4 全部做完，`tools/verify.py` 27 条判定全绿。

下面几条是「不归我处理、或者按任务书只能记下来不能自己动手」的事，留档给下一棒。

---

## 1. A 的 `data/parts.json` 到收工时仍未交付（不阻塞，已按预案走）

实测（2026-07-30 10:02）：`data/` 目录为空，`ls data/` 返回 `[]`。

按任务书预案：页面默认去读 `data/parts.json`，读不到就退回 `stub/parts.stub.json`，
并在标题旁挂「示例数据」角标。当前跑的就是这条降级路径，`__car.dataSource === 'stub'`。

**真数据到了之后不需要改任何代码**，页面自己会切过去。这一点不是嘴上说的，
verify.py 里第 26、27 条判定就是专门验它的 —— 用 playwright 在网络层把
`data/parts.json` 顶成一份合格文档 / 一份缺字段的文档，分别验到：

- 合格 → `dataSource=real`，角标消失，零 console error，110 个可点零件不变
- 不合格 → 退回 stub，角标出现，原因逐条记进 `__car.dataIssue`

真数据接上之后不合格式怎么办：按任务书，我不改 `data/`，只把 `__car.dataIssue`
里的报错原文抄到本文件，然后继续用 stub。目前没有可抄的内容。

## 2. 白名单里漏了 `tools/make_stub.py`（按任务书正文写了）

任务书【界限】列的可写文件里只有 `tools/verify.py`，但【任务 1】正文明确要求
「写 tools/make_stub.py 生成 stub/parts.stub.json」。判断为白名单笔误，按正文写了。
只此一个文件，`tools/` 下 A 的 `validate_data.py` 一个字节没动
（sha256 `e0eb7f26…`，mtime 09:11:36，早于我第一次写 tools/ 的时间）。

## 3. 「console 零 error」这条有一处明写豁免，不是放宽，请复核

浏览器对 404 的资源请求会在 console 打一条 error 级的
`Failed to load resource`，这是浏览器行为，`fetch` 的 catch 拦不住。
而任务书要求页面「默认读 data/parts.json，读不到再退 stub」——
A 的数据没交时，这条探测必然产生一条 404。

verify.py 的处理：**只在 `dataSource=='stub'` 时**，豁免「恰好 1 条、且 URL 以
`data/parts.json` 结尾」的资源加载失败，且每次运行都把这条原样打印出来
（`NOTE 已豁免的预期噪声：…`）。`dataSource=='real'` 时一条都不豁免，
其余任何 error / pageerror 一律判 FAIL。A 的数据一到，这个豁免自动不再触发。

我想不出既满足「必须先探真数据」又能让浏览器不打这条 404 的干净写法。
如果领导认为这仍算放宽，请直接把这条豁免删掉、并同意「A 交数据前 verify 就是 1 红」。

## 4. 英文模式下，`spec` / `suppliers[].note` 只能显示「Not available in English」

冻结格式里 `name`、`role`、`subgroup` 都有 `_zh` / `_en` 两份，
但 `spec` 和 `suppliers[].name / note / source` 只有一份，没有 `_en`。

所以英文模式碰到中文原文时，我既不能显示（「en 零汉字」会挂），
也不许自己编一个翻译（那是造数据）。统一显示 `Not available in English`，
原文是 ASCII 的照常显示。当前 stub 里两种都有，两条路径都验过。

**要真正解决，得给冻结格式加 `spec_en` / `suppliers[].note_en`。**
改冻结格式超出我这一批的授权，也会波及 A，所以只记在这里，没有擅自加字段。

## 5. 语言开关按钮在英文模式下写作 `ZH`，不是 `中文`

多数网站会一直把切换按钮写成「中文」，但那样英文模式下界面里就留了汉字，
硬指标那条「en 模式零汉字」直接挂。取舍结果：中文模式显示「中文 / EN」，
英文模式显示「ZH / EN」。如果领导更认可一直显示「中文」，那需要把
「document.body.innerText 零汉字」这条判定改成只查零件面板 —— 那是改判定，
我不能自己动，所以维持现状。

## 6. 没做（本批次不归我）

- 关系图、分类筛选：任务书写明下一批，本批没做。
- 部署：任务书写明「不部署」，没做。
- 根目录那堆 png、其他项目、权限：一律没碰。
