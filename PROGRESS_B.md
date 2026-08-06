# PROGRESS_B — B（3D / 爆炸 / 面板 / 中英）

最后更新：2026-07-30 10:10 · 任务 0～4 全部完成 · `tools/verify.py` **27 条判定全绿**

## 目标 / 顺序 / 风险（任务 0 核完后写，≤10 行）

1. 目标：一辆认得出的程序化卡罗拉，110 个可点零件，炸开/合拢丝滑，点谁出谁的面板，一键中英。
2. 顺序：T1 假数据+`window.__car` 调试接口 → T2 3D 与爆炸 → T3 面板与中英 → T4 断网档+反向验证 → 收尾 verify.py 定版。
3. 顺序理由：`window.__car` 是 verify.py 唯一抓手，先立接口再堆几何，否则每做一步都无法自证。
4. 风险 A：headless 软渲染 frameP95<45ms 是最可能翻车的一条 → 低多边形预算，几何体尽量共用材质，控制 draw call。
5. 风险 B：110 个独立 Object3D 必然 110+ draw call，calls<600 有余量但不能滥用 Group 嵌套。
6. 风险 C：A 的 data/parts.json 未到（09:09 时 data/ 为空）→ 全程按 stub 开发，真数据到了再接。
7. 风险 D：爆炸态「互不穿插」无客观判据，只能按四大簇分离 + 簇内按图组聚拢，靠 bbox 倍数与目视兜底。

**风险回头看**：A、B 都没成为问题（三角形 11890 / draw call 139 / frameP95 17ms，余量极大）。
C 至今没解（A 未交，见 BLOCKED_B）。D 后来找到了客观判据 —— 四大簇的世界包围盒两两不相交，
已写成 verify.py 的一条硬判定，不再靠目视。

---

## 任务 0 核对结果（2026-07-30 09:05–09:12 实测）

| 项 | 结果 |
|---|---|
| python | 3.12.10 ✅ |
| uv | 0.11.23 ✅ |
| git | 2.54.0.windows.1 ✅ |
| node / npm | 均 `command not found` ✅（与任务书一致，不装） |
| Chrome | `C:\Program Files\Google\Chrome\Application\chrome.exe` ✅ |
| three.module.js | HTTP 200，1304820 B，REVISION='169' ✅ |
| OrbitControls.js | HTTP 200，32134 B，裸 `from 'three'` ✅（确认需 importmap） |
| RoomEnvironment.js | HTTP 200，3606 B，`new RoomEnvironment()` 无参 ✅ |
| 本地服务 | `python -m http.server 4399` 可用 ✅ |
| playwright | `channel="chrome"` headless 打开 localhost 页面并读到 DOM ✅ |

playwright 冒烟原始输出：

```
status: 200
text: smoke-ok
three.module.js status: 200 len: 1304820
T0_SMOKE_OK
```

**一处与任务书不符（不阻塞）**：`python -m http.server 4399 --directory D:\blender\corolla-3d`
经 Git Bash 传参时反斜杠被吞，服务起在错误目录、全站 404。改用「先 cd 到项目目录再 `--directory .`」后正常。
这是 shell 转义问题不是任务书错，记在这里免得下次再踩。
（verify.py 不受影响：它自己在代码里起 `ThreadingHTTPServer`，端口 0 自动选空闲口，不依赖外部服务。）

---

## 交付物与怎么跑

```bash
uv run --no-project --with playwright python tools/verify.py
```

verify.py 自带静态服务、自己收自己关，不需要先开 4399。人工看页面则：

```bash
python -m http.server 4399 --directory .
```

然后开 `http://localhost:4399/index.html`。

| 文件 | 干什么 |
|---|---|
| `index.html` | 骨架 + importmap（three 指向本地 vendor） |
| `style.css` | 高级简约：中性灰工作室、一处克制的红；面板独占一列，永远不压车 |
| `car.js` | 程序化建模：槽位识别 → 摆放表 → 110 个 Object3D；爆炸位置计算 |
| `app.js` | 场景/交互/面板/中英，以及冻结的 `window.__car` |
| `tools/make_stub.py` | 生成 558 条假数据（110 条 has_mesh），带自检 |
| `tools/verify.py` | 27 条硬判定 |
| `vendor/` | three r169 本地副本（3 个文件，1.34 MB） |

---

## 各任务完成情况

### 任务 1 · 假数据与调试接口 ✅

`tools/make_stub.py` → `stub/parts.stub.json`：

```
parts        = 558
has_mesh=true= 110
qty approx   = 57
subgroups    = 74
bytes        = 455306
SELFCHECK OK
```

自检不通过就不写文件（字段名与冻结格式逐字比对、id 唯一、parent/connects_to 不悬空）。
零件号、供应商、规格全是程序编的，`vehicle.data_kind="stub"`，页面挂「示例数据」角标。

数据源三条支路都验过（verify.py 第 25/26/27 条）：读不到 → 退 stub；
合格式 → `dataSource=real` 且角标消失；不合格式 → 退 stub 且原因记进 `__car.dataIssue`。
后两支是用 playwright 在网络层顶掉 `data/parts.json` 验的，**没往 `data/` 写一个字节**。

`window.__car` 字段（冻结，只许加）：`ready / partIds / data / state / explode() / assemble() /
select(id) / panelText() / setLang() / lang / bbox() / stats() / dataSource`。
另外加了 `dataIssue / selected / coverage() / clusterBoxes() / countIdObjects() / meshCountFor(id) / resetView() / CAR`
—— 都是给验收当抓手用的，加的不是改的。

**`stats().frameP95` 的口径**（重要，别误读）：取的是 **requestAnimationFrame 相邻回调的间隔** 的 P95，
不是「我这段 JS 跑了多久」。软渲染下 GL 命令是排队的，真正的光栅化发生在 SwapBuffers，
只量自己那段 JS 会严重少算。另外还单独暴露了 `frameWorkP95`（帧内 JS 耗时）供参考。
实测 frameP95=17ms（≈60fps 上限），frameWorkP95≈2.4ms。

### 任务 2 · 3D 与爆炸 ✅

- **摆放表按「槽位」索引，不按 id。** 槽位从 `name_en` 用正则认出来（hood / door + front|rear + lh|rh …）。
  这样 A 的真数据 id 跟我 stub 不一样也能对上，只要英文件名还是行业通名。
  认不出的零件不丢，落 fallback：按 group 塞进车里对应区域，位置由 id 哈希决定（稳定不乱跳）。
  当前 stub 下 **matched=110 / fallback=0**。
- 一个零件 = 一个 Group，`userData.id` 挂在 Group 上，子网格不挂 —— 数 id 时永远是 1 个。
  qty>1 的件（4 条轮胎、4 个车门内饰板）在同一个 Group 下放多个 Mesh。
- 爆炸布局：整车按 1.72 倍从中心放大 → 四大部分各自平移到自己的簇 → 同图组再沿径向推开 0.42 m。
  均匀放大保证同簇内两两间距只增不减，簇内不会新增穿插。
- 相机阻尼 `dampingFactor=0.055`；爆炸/合拢与相机推拉都走 easeInOutCubic，1150 / 1000 ms。

**踩过的三个坑，记下来免得重犯：**

1. `rboxGeo` 在「最薄边是 X」时把宽高对调了 → 前保险杠被立成一堵墙、还插到地下。
   根因：挤出后要绕轴转，转完哪条局部边落到哪条世界边是定死的，不能按 `filter` 顺序取 w/h。
2. 四簇原本按 ±X / ±Z 摆，屏幕上只看到两坨。默认视角算出来「屏幕向右」是
   `U=(-0.669,0,0.743)`，也就是 **+Z 和 −X 在屏幕上都往右跑**。改成沿 ±U 加上下摆成菱形
   （车身抬起、底盘在下、发动机左、电气右）才真的分成四块。簇方向必须冲着相机定，不能想当然。
3. 相机原来用外接球算距离，球比车大一圈，车只占画面四成，60~75% 那条直接不达标。
   改成按包围盒 8 个角精确解距离，`fill=0.76` → 实测占比 0.682。

### 任务 3 · 零件面板与中英切换 ✅

面板内容：所属部分、中英名、作用、零件号、官方图组、整车数量（approx 显「≈」）、
规格、标签、连到哪些零件（可点跳转）、供应商表（厂商 / 说明 / 来源 / 把握度）。
页脚常驻口径声明。切语言不刷新、不丢选中。

**英文模式下的一条安全网**：冻结格式里 `spec` 和 `suppliers[].name/note/source` 没有 `_en` 版本。
英文模式碰到中文原文时，既不能原样显示（en 零汉字会挂），也不许自己编翻译（那是造数据），
统一显示 `Not available in English`；原文是 ASCII 的照常显示。详见 BLOCKED_B 第 4 条。

**语言开关按钮**：中文模式「中文 / EN」，英文模式「ZH / EN」。
一直写「中文」的话英文模式界面里就留了汉字。取舍理由见 BLOCKED_B 第 5 条。

**两处收尾打磨**（都不影响判定，verify sha256 未变）：
qty>1 的零件逐件描边 —— 选中「轮胎」时框住四个轮子，而不是套一个罩住整台车的大盒子；
英文模式下「另一种语言的名字」和供应商 `source` 若只有中文就直接不显示，
不再摆一行「Not available in English」当噪声（spec 和供应商说明仍明说没有，那两个字段有信息量）。

**两个 CSS/DOM 坑**：`#panelEmpty` 写了 `display:flex`，把 `hidden` 属性压掉了 →
空态和零件详情同时显示，而且 `document.body.innerText` 里混进本该藏起来的中文。
加了 `[hidden]{display:none!important}` 兜底。另外给了个空 favicon，
免得 `/favicon.ico` 在控制台留一条 404。

### 任务 4 · 断网也能跑 + 反向验证 ✅

verify.py 第 23~25 条：playwright 把所有非 localhost 请求 `route → abort` 后重开页面，
`__car.ready` 仍为 true，随机 5 个零件仍能 select，面板仍有内容。
整轮下来**被拦下的外部请求 = 0 条** —— 运行时根本没发过任何非 localhost 请求。
`grep -rn "http://\|https://\|cdn\|unpkg\|jsdelivr" index.html app.js car.js style.css` 也是空。

反向验证见下面「红转绿证据」。

---

## verify.py 定版

```
verify.py sha256 = ce63a9e01bc7166945f52ede3b5b8485e25cca4ba4bb094223d455c992aaf08b
共 27 条判定，PASS 27，FAIL 0
```

阈值（冻结，之后只许加新判定，不许放宽或删除）：
`MIN_MESH_PARTS=110 / EXPLODE_RATIO=2.2 / REASSEMBLE_TOL=0.5% /
MAX_TRIANGLES=600000 / MAX_CALLS=600 / MAX_FRAME_P95_MS=45 /
COVERAGE 60%~75% / SAMPLE_N=10`

实测余量：三角形 11890（阈值 60 万）、draw call 139（阈值 600）、frameP95 17ms（阈值 45）、
爆炸倍数 3.926（阈值 2.2）、合拢偏差 0.00000 m、默认视角占比 0.682（区间 0.60~0.75）。

有一条明写豁免（`console 零 error`），理由和范围写在 BLOCKED_B 第 3 条，
每次运行都会把被豁免的那条原样打印出来。

---

## 红转绿证据（反向验证）

手法：脚本把 `app.js` 打坏 → 跑 verify → 还原 → 用 sha256 校验还原一致。

```
app.js 原始 sha256 = 11292469cd7c560b386427129a067aefea88dd85000e6dbfd5c230892797e549

### 故障一：从场景里删掉 body-hood 这个 Object3D
FAIL  场景中 userData.id 非空的 Object3D 个数 == partIds 长度  |  场景=109 partIds=110
共 25 条判定，PASS 24，FAIL 1
--> exit code = 1

### 故障二：往英文语言包里塞一个中文名
FAIL  setLang("en") 后 document.body.innerText 无汉字  |  出现的汉字=中文
共 25 条判定，PASS 24，FAIL 1
--> exit code = 1

还原后 app.js sha256 = 11292469cd7c560b386427129a067aefea88dd85000e6dbfd5c230892797e549
还原一致：是
```

（当时是 25 条；之后追加了 2 条数据源判定，现为 27 条。追加不影响这两条报警。）

---

## 只动了自己的地界

A 的文件到收工时的状态：

```
tools/validate_data.py
  sha256 = e0eb7f2696532d32f3d0411b6fc341fcde0abf36e58ea8d04412e13120b8fc1b
  bytes  = 14992
  mtime  = 2026-07-30 09:11:36        ← 早于我第一次写 tools/ 的时间
data/ 目录内容 = []                    ← 空的，A 还没交
```

我建/改过的，全部在白名单内：
`index.html`、`style.css`、`app.js`、`car.js`、`vendor/`（3 个文件）、
`stub/parts.stub.json`、`tools/make_stub.py`、`tools/verify.py`、`PROGRESS_B.md`、`BLOCKED_B.md`。

任务 0 期间在项目根建过 `_smoke.html` 做探针，用完当场删除（我自己 3 分钟前建的文件，非他人资产）。
`data/`、`tools/validate_data.py`、`BLOCKED_A.md`、`PROGRESS_A.md` 一个字节没动。
没装任何依赖，没 git init，没推远端，没部署，根目录那堆 png 没碰。

---

## 进度台账

- [x] 任务 0 环境核对 —— 2026-07-30 09:12 全绿
- [x] 任务 1 假数据 + `window.__car` 调试接口
- [x] 任务 2 3D 与爆炸
- [x] 任务 3 零件面板与中英切换
- [x] 任务 4 断网档 + 反向验证
- [x] 收尾 verify.py 定版（27 条，sha256 已记）

## 下一批接手的人需要知道的

1. 关系图和分类筛选是下一批的活，本批一行没写。往 `window.__car` 上加字段就行，别改现有的。
2. 要加新零件形状：改 `car.js` 的 `SLOT_RULES`（加识别规则）和 `PLACE`（加摆放条目）。
   `PLACE` 的 `t` 里 z 一律按左侧写，右侧会自动镜像。
3. 改完必须重跑 verify.py。可以往里加判定，不许放宽已有的。
4. `data/parts.json` 一到就自动接上，不用改代码；不合格式会自动退回 stub 并把原因放在 `__car.dataIssue`。
