// app.js —— 场景、交互、面板、中英切换，以及给 verify.py 用的 window.__car。
//
// window.__car 的字段名是冻结的（下一批还要往上加），只许加不许改。

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { buildCar, makeGroundShadow, CAR } from './car.js';

const CJK = /[一-鿿]/;
const GROUPS = ['body', 'electrical', 'engine_fuel_tool', 'powertrain_chassis'];
const FIELDS = ['id', 'group', 'subgroup_en', 'subgroup_zh', 'name_en', 'name_zh',
  'oem_pn', 'parent', 'connects_to', 'role_zh', 'role_en', 'qty', 'qty_kind',
  'tags', 'has_mesh', 'spec', 'suppliers'];

// ───────────────────────────────────────────────── 文案
const I18N = {
  zh: {
    title: '卡罗拉 整车分解',
    subtitle: '点开任意零件，看懂它叫什么、干什么',
    loading: '正在装配…',
    explode: '爆炸展开',
    assemble: '合拢复原',
    resetView: '回正视角',
    hint: '拖动旋转 · 滚轮缩放 · 单击零件',
    emptyTitle: '还没有选中零件',
    emptyHint: '在左边的车上单击任意一个零件，这里就会告诉你它是什么。',
    stub: '示例数据',
    langZh: '中文', langEn: 'EN',
    disclaimer: '口径：供应商是公开信息里该品类的主要厂商，不是官方 BOM；整车数量为估算，带「≈」的是约数。3D 为程序化示意模型，不是工程数模。',
    kGroup: '所属部分', kSub: '官方图组', kPn: '零件号', kQty: '整车数量',
    kSpec: '规格', kTags: '标签', kConn: '连到哪些零件', kSup: '供应商',
    kMaterial: '材料', kProcess: '成型工艺', kWeight: '单件重量', kFasten: '连接方式',
    kCost: '成本估算', kDisasm: '拆解工时', kDepth: '装配层级',
    disasmKind: { removable: '可无损拆卸', destructive: '焊接，不可无损拆卸' },
    aggDisasm: '可拆性', aggDisasmTotal: '可拆件工时合计',
    scopeParts: '零件数', scopeMass: '质量小计', scopeCost: '成本小计', scopeTime: '工时小计',
    scopeBack: '← 回到整车', scopeHint: '这一组的小计。点组里的零件看单件明细。',
    scopeHeaviest: '组里最重的 5 个',
    cmpAdd: '加入对比', cmpDrop: '移出对比', cmpOpen: '对比 {n} 件', cmpClear: '清空',
    cmpTitle: '零件横向对比', cmpHint: '同一口径下并排看。加号从零件面板或树里点。',
    cmpFull: '最多同时对比 3 件',
    aggDisasmNote: '工时 = Σ(每种紧固件的单件拆卸耗时 × 数量) + 装配层级 × 通达系数。层级代表要先拆掉几层才够得着它。焊接件按破坏性拆解处理，不计工时。',
    basis: { category_typical: '品类经验值', sum_of_children: '子件之和', official: '官方数据',
             parametric_model: '参数化模型' },
    aggCost: '按部分的成本估算', aggCostTotal: '成本估算合计',
    aggCostNote: '成本 = 重量 × (材料单价 + 工艺加工费率) + 紧固件数 × 0.6 元。这是透明的估算模型，系数可查可改，不是丰田的采购价——公开渠道拿不到那个数。',
    exportBtn: '导出 BOM',
    aggTitle: '整车构成', aggHint: '点开任意零件看它的明细；这里是整车层面的汇总。',
    aggMass: '按部分的质量分布', aggMat: '材料构成（前 6）', aggFas: '紧固件合计',
    treeBtn: '零件树', searchPh: '搜零件名或零件号', tagAll: '全部',
    treeCount: '显示 {n} / 共 {t} 条', treeNone: '没有匹配的零件',
    noMeshJump: '这个零件没有单独建 3D，已定位到它所属的总成',
    aggTotal: '目录合计', aggCurb: 'E210 整备质量约 1310–1405 kg，本目录为 {n} 条代表性零件，未覆盖上万个小件与油液',
    kRole: '它是干什么的', kNoPn: '（该零件无独立零件号）', kNone: '—',
    supName: '厂商', supNote: '说明', supConf: '把握',
    unit: '个', noMesh: '（此件未建模，仅在资料库中）',
    naEn: '—',
    tag: {
      exterior: '外观件', panel: '钣金', steel: '钢制', plastic: '塑料', glass: '玻璃',
      structure: '结构件', safety: '安全件', interior: '内饰', lighting: '灯具',
      led: 'LED', power: '电源', motor: '电机', sensor: '传感器', adas: '辅助驾驶',
      ecu: '电控单元', control: '控制', brake: '制动', suspension: '悬架',
      steering: '转向', wheel: '车轮', wear: '易损件', bearing: '轴承',
      engine: '发动机', cooling: '冷却', fuel: '燃油', exhaust: '排气', hot: '高温',
      emission: '排放', hvac: '空调', air: '进气', fluid: '油液', rubber: '橡胶',
      nvh: '隔音减振', bracket: '支架', fastener: '紧固件', seal: '密封',
      aluminium: '铝合金', cast: '铸件', driveline: '传动', belt: '皮带',
      audio: '音响', infotainment: '影音', display: '显示', switch: '开关',
      electric: '电气', filter: '滤清', trim: '饰件', door: '车门', hinge: '铰链',
      heat: '隔热', cover: '护盖', hose: '软管', assembly: '总成', aero: '空气动力',
      protection: '防护', precision: '精密件', chrome: '镀铬', heated: '电加热',
      gear: '齿轮传动', seat: '座椅', door_window: '门窗', wheel_hub: '轮毂', tire: '轮胎',
      electrical: '电气',
      body_panel: '车身钣金',
    },
  },
  en: {
    title: 'Corolla Exploded View',
    subtitle: 'Click any part to see what it is and what it does',
    loading: 'Assembling…',
    explode: 'Explode',
    assemble: 'Reassemble',
    resetView: 'Reset view',
    hint: 'Drag to orbit · Scroll to zoom · Click a part',
    emptyTitle: 'No part selected',
    emptyHint: 'Click any part on the car to the left and its details show up here.',
    stub: 'SAMPLE DATA',
    langZh: 'ZH', langEn: 'EN',
    disclaimer: 'Scope: suppliers are the makers publicly associated with each category, not an official BOM. Quantities are estimates; "≈" marks approximations. The 3D model is a procedural illustration, not engineering CAD.',
    kGroup: 'Group', kSub: 'Diagram group', kPn: 'Part number', kQty: 'Qty per car',
    kSpec: 'Spec', kTags: 'Tags', kConn: 'Connects to', kSup: 'Suppliers',
    kMaterial: 'Material', kProcess: 'Process', kWeight: 'Mass each', kFasten: 'Fastening',
    kCost: 'Cost estimate', kDisasm: 'Removal time', kDepth: 'Assembly level',
    disasmKind: { removable: 'Non-destructively removable', destructive: 'Welded, not removable without cutting' },
    aggDisasm: 'Removability', aggDisasmTotal: 'Removal time, removable parts',
    scopeParts: 'Parts', scopeMass: 'Mass subtotal', scopeCost: 'Cost subtotal', scopeTime: 'Time subtotal',
    scopeBack: '← Back to vehicle', scopeHint: 'Subtotals for this group. Click a part in it for the part detail.',
    scopeHeaviest: 'Heaviest 5 in this group',
    cmpAdd: 'Add to compare', cmpDrop: 'Remove', cmpOpen: 'Compare {n}', cmpClear: 'Clear',
    cmpTitle: 'Part comparison', cmpHint: 'Side by side on the same basis. Add from a part panel or the tree.',
    cmpFull: 'Up to 3 parts at a time',
    aggDisasmNote: 'Time = sum(per-fastener removal time x count) + assembly level x access factor. The level says how many layers must come off before you can reach it. Welded parts are destructive-removal only and carry no time.',
    basis: { category_typical: 'category typical', sum_of_children: 'sum of children', official: 'official',
             parametric_model: 'parametric model' },
    aggCost: 'Cost estimate by group', aggCostTotal: 'Cost estimate total',
    aggCostNote: 'Cost = mass x (material price + process rate) + fastener count x CNY 0.6. This is a transparent estimating model whose coefficients you can read and change. It is not what Toyota pays; that figure is not public.',
    exportBtn: 'Export BOM',
    aggTitle: 'Vehicle breakdown', aggHint: 'Click any part for its detail; this is the vehicle-level roll-up.',
    aggMass: 'Mass by group', aggMat: 'Material mix (top 6)', aggFas: 'Fastener count',
    treeBtn: 'Part tree', searchPh: 'Search name or part number', tagAll: 'All',
    treeCount: 'showing {n} of {t}', treeNone: 'No matching part',
    noMeshJump: 'This part has no separate 3D mesh; jumped to the assembly it belongs to',
    aggTotal: 'Catalogue total', aggCurb: 'E210 kerb mass is about 1310–1405 kg. This catalogue holds {n} representative parts and does not cover the thousands of small parts and fluids.',
    kRole: 'What it does', kNoPn: '(no separate part number)', kNone: '—',
    supName: 'Maker', supNote: 'Note', supConf: 'Confidence',
    unit: 'pcs', noMesh: '(not modelled in 3D; catalogue entry only)',
    naEn: 'Not available in English',
    tag: {
      bearing: 'Bearing', motor: 'Motor', gear: 'Gear', seat: 'Seat',
      door_window: 'Door & window', electrical: 'Electrical', audio: 'Audio',
      wheel_hub: 'Wheel hub', tire: 'Tire', brake: 'Brake', steering: 'Steering',
      suspension: 'Suspension', body_panel: 'Body panel', sensor: 'Sensor',
    },
  },
};

// ───────────────────────────────────────────────── 受控词表的中英对照
// 数据里存的是枚举码（cast_iron / stamping / weld_spot），语言在这里落地。
// 这么设计是为了能聚合——「整车材料构成」「紧固件合计」靠的就是码而不是自由文本。
const VOCAB = {
  material: {
    steel_mild: ['低碳钢板', 'Mild steel sheet'], steel_hss: ['高强度钢', 'High-strength steel'],
    steel_spring: ['弹簧钢', 'Spring steel'], steel_bearing: ['轴承钢 GCr15', 'Bearing steel'],
    cast_iron: ['灰铸铁', 'Grey cast iron'], alu_cast: ['铸铝合金', 'Cast aluminium'],
    alu_sheet: ['铝板', 'Aluminium sheet'], copper: ['铜', 'Copper'],
    plastic_pp: ['聚丙烯 PP', 'Polypropylene'], plastic_pa66: ['玻纤增强尼龙 PA66-GF', 'Glass-filled PA66'],
    plastic_abs: ['ABS', 'ABS'], plastic_pc: ['聚碳酸酯 PC', 'Polycarbonate'],
    rubber_epdm: ['三元乙丙橡胶 EPDM', 'EPDM rubber'], rubber_nr: ['天然橡胶复合', 'Rubber compound'],
    glass_lam: ['夹层玻璃', 'Laminated glass'], glass_temp: ['钢化玻璃', 'Tempered glass'],
    foam_pu: ['聚氨酯发泡', 'PU foam'], textile: ['织物', 'Textile'],
    lead_acid: ['铅酸', 'Lead-acid'], ceramic: ['陶瓷载体', 'Ceramic substrate'],
    friction: ['摩擦材料', 'Friction material'], mixed: ['多材料总成', 'Multi-material'],
  },
  process: {
    stamping: ['冲压', 'Stamping'], casting_die: ['压铸', 'Die casting'],
    casting_sand: ['砂型铸造', 'Sand casting'], forging: ['锻造', 'Forging'],
    machining: ['机加工', 'Machining'], grinding: ['磨削', 'Grinding'],
    injection: ['注塑', 'Injection moulding'], blow_mold: ['吹塑', 'Blow moulding'],
    extrusion: ['挤出', 'Extrusion'], welding: ['焊接总成', 'Welded assembly'],
    winding: ['绕线 / 电机装配', 'Winding'], assembly: ['装配总成', 'Assembly'],
    float_glass: ['浮法+钢化/夹层', 'Float glass'], foaming: ['发泡成型', 'Foam moulding'],
    electronic: ['电子件装配', 'Electronics assembly'],
  },
  fasten: {
    bolt: ['螺栓', 'Bolt'], screw: ['螺钉', 'Screw'], nut: ['螺母', 'Nut'],
    clip: ['卡扣', 'Clip'], weld_spot: ['电阻点焊', 'Spot weld'], weld_seam: ['焊缝', 'Seam weld'],
    rivet: ['铆接', 'Rivet'], adhesive: ['结构胶粘接', 'Adhesive'], press_fit: ['过盈压装', 'Press fit'],
    snap: ['卡接', 'Snap fit'], hose_clamp: ['管夹', 'Hose clamp'],
    connector: ['电气插接件', 'Connector'], thread_in: ['螺纹旋入', 'Threaded in'],
  },
};

function fmtMass(g) {
  if (g == null) return '—';
  return g >= 1000 ? (g / 1000).toFixed(g >= 10000 ? 0 : 1) + ' kg' : Math.round(g) + ' g';
}

const GROUP_NAME = {
  zh: { body: '车身', electrical: '电气', engine_fuel_tool: '发动机 · 燃油 · 工具', powertrain_chassis: '传动 · 底盘' },
  en: { body: 'Body', electrical: 'Electrical', engine_fuel_tool: 'Engine / Fuel / Tool', powertrain_chassis: 'Power Train / Chassis' },
};

const GROUP_COLOR = {
  body: '#c0342c', electrical: '#2f6b8f',
  engine_fuel_tool: '#8a6a1f', powertrain_chassis: '#3f6b4a',
};

// ───────────────────────────────────────────────── 运行时状态
const S = {
  lang: 'zh',
  state: 'assembled',
  data: null,
  dataSource: 'stub',
  dataIssue: null,
  byId: new Map(),
  car: null,
  selected: null,
  scope: null,
  compare: [],       // 横向对比的零件 id，最多 3 个
  compareOpen: false,      // {group} 或 {group, subgroup}：树里点了某一组时的钻取范围
  anim: null,
  camAnim: null,
  frames: [],
  work: [],
  ready: false,
};

const el = (id) => document.getElementById(id);
const app = el('app');

// ───────────────────────────────────────────────── three 基础设施
const canvas = el('view');
const stage = el('stage');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.06;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 400);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.055;
controls.rotateSpeed = 0.62;
controls.zoomSpeed = 0.8;
controls.panSpeed = 0.6;
controls.minDistance = 2.2;
controls.maxDistance = 60;
controls.maxPolarAngle = Math.PI * 0.495;

const key = new THREE.DirectionalLight(0xffffff, 1.55);
key.position.set(5.2, 7.0, 4.4);
const fill = new THREE.DirectionalLight(0xdfe7f0, 0.5);
fill.position.set(-5.5, 3.0, -3.6);
scene.add(key, fill, new THREE.HemisphereLight(0xf3f5f7, 0xb9bcbe, 0.42));

{
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.55;
  pmrem.dispose();
}

const VIEW_DIR = new THREE.Vector3(1.0, 0.44, 0.90).normalize();
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();

const outline = [];   // 选中件的描边，可能不止一条（qty>1 的零件逐件框）
const emissiveBackup = new Map();

// ───────────────────────────────────────────────── 数据加载（真数据 → 不合格就退回 stub）
function validate(doc) {
  const errs = [];
  if (!doc || typeof doc !== 'object' || Array.isArray(doc)) { errs.push('顶层不是对象'); return errs; }
  if (!doc.vehicle || typeof doc.vehicle !== 'object') errs.push('缺少 vehicle 对象');
  if (!Array.isArray(doc.parts)) { errs.push('缺少 parts 数组'); return errs; }
  if (doc.parts.length === 0) { errs.push('parts 数组为空'); return errs; }

  const seen = new Set();
  let meshN = 0;
  for (let i = 0; i < doc.parts.length && errs.length < 8; i++) {
    const p = doc.parts[i];
    if (!p || typeof p !== 'object') { errs.push(`parts[${i}] 不是对象`); continue; }
    const missing = FIELDS.filter((k) => !(k in p));
    if (missing.length) { errs.push(`parts[${i}] (${p.id || '?'}) 缺字段: ${missing.join(', ')}`); continue; }
    if (typeof p.id !== 'string' || !p.id) { errs.push(`parts[${i}] id 不是非空字符串`); continue; }
    if (seen.has(p.id)) errs.push(`id 重复: ${p.id}`);
    seen.add(p.id);
    if (!GROUPS.includes(p.group)) errs.push(`${p.id} group 非法: ${JSON.stringify(p.group)}`);
    if (typeof p.has_mesh !== 'boolean') errs.push(`${p.id} has_mesh 不是布尔值`);
    if (p.qty_kind !== 'exact' && p.qty_kind !== 'approx') errs.push(`${p.id} qty_kind 非法: ${JSON.stringify(p.qty_kind)}`);
    if (!Array.isArray(p.connects_to)) errs.push(`${p.id} connects_to 不是数组`);
    if (!Array.isArray(p.tags)) errs.push(`${p.id} tags 不是数组`);
    if (!Array.isArray(p.suppliers)) errs.push(`${p.id} suppliers 不是数组`);
    if (p.has_mesh === true) meshN++;
  }
  if (meshN === 0 && errs.length < 8) errs.push('没有任何 has_mesh=true 的零件，3D 无从建起');
  return errs;
}

async function loadJSON(url) {
  const r = await fetch(url, { cache: 'no-store' });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

async function loadData() {
  try {
    const doc = await loadJSON('data/parts.json');
    const errs = validate(doc);
    if (errs.length === 0) return { doc, source: 'real', issue: null };
    return { doc: await loadJSON('stub/parts.stub.json'), source: 'stub', issue: { where: 'data/parts.json', errs } };
  } catch (e) {
    const doc = await loadJSON('stub/parts.stub.json');
    return { doc, source: 'stub', issue: { where: 'data/parts.json', errs: [String(e && e.message || e)] } };
  }
}

// ───────────────────────────────────────────────── 中英安全网
// 冻结格式里 spec / suppliers[].note / suppliers[].name 没有 _en 对应字段。
// 英文模式下如果原文是中文，只能如实说「英文里没有」，不许硬凑一个翻译出来。
function enSafe(text) {
  const t = (text == null ? '' : String(text)).trim();
  if (!t) return '';
  if (S.lang === 'en' && CJK.test(t)) return I18N.en.naEn;
  return t;
}

function t() { return I18N[S.lang]; }

function tagLabel(tag) {
  const d = t().tag || {};
  const v = d[tag];
  if (v) return v;
  return CJK.test(tag) && S.lang === 'en' ? I18N.en.naEn : tag;
}

// ───────────────────────────────────────────────── 面板
function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function partName(p) {
  const raw = S.lang === 'zh' ? p.name_zh : p.name_en;
  const alt = S.lang === 'zh' ? p.name_en : p.name_zh;
  // 副标题只是「另一种语言的名字」，没有就不显示 —— 摆一行「Not available in English」
  // 在大标题底下纯属噪声。spec 和供应商说明那种带信息量的字段才值得明说没有。
  const altSafe = enSafe(alt);
  return { main: enSafe(raw) || p.id, alt: altSafe === I18N.en.naEn ? '' : altSafe };
}

// ───────────────────────────────────────────────── 零件树
// 为什么要有它：434 条零件里只有 225 条建了 3D，其余 209 条（火花塞、气门油封、
// 各种传感器和垫片）在画布上根本点不到，考证出来的零件号和作用说明等于看不见。
// 树按官方三层走：四大部分 → 官方图组 → 零件。没建 3D 的照样能点开看资料。
const NINE = ['bearing', 'motor', 'gear', 'seat', 'door_window', 'electrical', 'audio', 'wheel_hub', 'tire'];
const TREE = { open: new Set(), q: '', tag: null };

function treeData() {
  const parts = (S.data && S.data.parts) || [];
  const groups = new Map();
  for (const p of parts) {
    if (TREE.tag && !(p.tags || []).includes(TREE.tag)) continue;
    if (TREE.q) {
      const hay = [p.name_zh, p.name_en, p.oem_pn, p.subgroup_zh, p.subgroup_en, p.id]
        .join(' ').toLowerCase();
      if (!hay.includes(TREE.q)) continue;
    }
    if (!groups.has(p.group)) groups.set(p.group, new Map());
    const sg = groups.get(p.group);
    const key = p.subgroup_en || p.subgroup_zh || '—';
    if (!sg.has(key)) sg.set(key, []);
    sg.get(key).push(p);
  }
  return groups;
}

function renderTree() {
  const box = el('treeBody');
  if (!box) return;
  const L = t();
  const groups = treeData();
  let shown = 0, h = '';
  for (const g of GROUPS) {
    const sgs = groups.get(g);
    if (!sgs) continue;
    let n = 0;
    for (const arr of sgs.values()) n += arr.length;
    shown += n;
    const gOpen = TREE.open.has(g) || !!TREE.q || !!TREE.tag;
    h += `<div class="tn tn-g" data-tg="${esc(g)}">`
      + `<span class="tn-caret">${gOpen ? '▾' : '▸'}</span>`
      + `<span class="tn-dot" style="background:${GROUP_COLOR[g]}"></span>`
      + `<span class="tn-n">${esc(GROUP_NAME[S.lang][g] || g)}</span>`
      + `<span class="tn-k">${n}</span></div>`;
    if (!gOpen) continue;
    for (const [key, arr] of sgs) {
      const sk = g + '::' + key;
      const sOpen = TREE.open.has(sk) || !!TREE.q || !!TREE.tag;
      const label = S.lang === 'zh' ? (arr[0].subgroup_zh || key) : (arr[0].subgroup_en || key);
      h += `<div class="tn tn-s" data-tg="${esc(sk)}">`
        + `<span class="tn-caret">${sOpen ? '▾' : '▸'}</span>`
        + `<span class="tn-n">${esc(label)}</span>`
        + `<span class="tn-k">${arr.length}</span></div>`;
      if (!sOpen) continue;
      for (const p of arr) {
        const cls = 'tn tn-p' + (p.id === S.selected ? ' sel' : '') + (p.has_mesh ? '' : ' nomesh');
        h += `<div class="${cls}" data-tp="${esc(p.id)}">`
          + `<span class="tn-n">${esc(partName(p).main)}</span>`
          + `<span class="tn-k mono">${esc(p.oem_pn || '')}</span></div>`;
      }
    }
  }
  box.innerHTML = h || `<div class="tn tn-p">${esc(L.treeNone)}</div>`;
  const total = ((S.data && S.data.parts) || []).length;
  el('treeCount').textContent = L.treeCount.replace('{n}', shown).replace('{t}', total);
}

function renderTreeTags() {
  const box = el('treeTags');
  if (!box) return;
  let h = `<span class="chip flat${TREE.tag ? '' : ' on'}" data-tag="">${esc(t().tagAll)}</span>`;
  for (const tg of NINE) {
    h += `<span class="chip flat${TREE.tag === tg ? ' on' : ''}" data-tag="${tg}">${esc(tagLabel(tg))}</span>`;
  }
  box.innerHTML = h;
}

// 导出 BOM：专业基准工具都能把整表拿走。带 UTF-8 BOM 头，Excel 打开不乱码。
function exportBOM() {
  const parts = (S.data && S.data.parts) || [];
  const head = ['id', 'group', 'subgroup_en', 'subgroup_zh', 'name_en', 'name_zh',
    'oem_pn', 'parent', 'qty', 'qty_kind', 'material', 'process',
    'weight_g', 'weight_basis', 'cost_cny', 'cost_basis', 'disassembly_min', 'disassembly_kind', 'tree_depth', 'fastening', 'tags',
    'has_mesh', 'spec', 'suppliers'];
  const cell = (v) => {
    let x;
    if (Array.isArray(v)) {
      x = v.map((i) => (typeof i === 'object' && i
        ? [i.type, i.spec, i.count, i.name, i.confidence].filter(Boolean).join(' ')
        : i)).join(' | ');
    } else x = v == null ? '' : String(v);
    // 含逗号、引号或换行的字段要按 CSV 规矩用双引号包起来，内部引号翻倍
    const needQuote = x.indexOf(',') >= 0 || x.indexOf('"') >= 0
      || x.indexOf('\n') >= 0 || x.indexOf('\r') >= 0;
    return needQuote ? '"' + x.replace(/"/g, '""') + '"' : x;
  };
  const rows = [head.join(',')];
  for (const p of parts) rows.push(head.map((k) => cell(p[k])).join(','));
  // 开头那个 ﻿ 是 UTF-8 BOM 头，没有它 Excel 打开中文会乱码
  const blob = new Blob(['﻿' + rows.join('\r\n')], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'corolla-e210-bom.csv';
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  return parts.length;
}

function bindTree() {
  el('btnTree').addEventListener('click', () => {
    const tr = el('tree');
    tr.hidden = !tr.hidden;
    el('btnTree').classList.toggle('primary', !tr.hidden);
    if (!tr.hidden) { renderTreeTags(); renderTree(); }
  });
  el('btnExport').addEventListener('click', exportBOM);
  el('treeSearch').addEventListener('input', (e) => {
    TREE.q = (e.target.value || '').trim().toLowerCase();
    renderTree();
  });
  el('treeTags').addEventListener('click', (e) => {
    const c = e.target.closest('[data-tag]');
    if (!c) return;
    TREE.tag = c.getAttribute('data-tag') || null;
    renderTreeTags(); renderTree();
  });
  el('treeBody').addEventListener('click', (e) => {
    const pn = e.target.closest('[data-tp]');
    if (pn) { selectPart(pn.getAttribute('data-tp'), true); return; }
    const gn = e.target.closest('[data-tg]');
    if (!gn) return;
    const k = gn.getAttribute('data-tg');
    if (TREE.open.has(k)) TREE.open.delete(k); else TREE.open.add(k);
    // 展开的同时把右栏切到这一组的小计 —— 这就是「钻取」
    const seg = k.split('::');
    S.selected = null;
    S.scope = seg.length > 1 ? { group: seg[0], subgroup: seg[1] } : { group: seg[0] };
    clearHighlight();
    renderTree(); renderPanel();
  });
}

// 整车汇总：只统计叶子零件，总成的重量是子件之和，进统计会重复计
function aggregate() {
  const parts = (S.data && S.data.parts) || [];
  const byid = new Map(parts.map((p) => [p.id, p]));
  const hasKid = new Set();
  for (const p of parts) if (p.parent && byid.has(p.parent)) hasKid.add(p.parent);

  let total = 0;
  let cost = 0, disasm = 0, nRemov = 0, nDestr = 0;
  const byGroup = new Map(), byMat = new Map(), byFas = new Map(), byCost = new Map();
  for (const p of parts) {
    if (hasKid.has(p.id)) continue;
    const q = p.qty || 1, w = (p.weight_g || 0) * q;
    total += w;
    byGroup.set(p.group, (byGroup.get(p.group) || 0) + w);
    if (p.material) byMat.set(p.material, (byMat.get(p.material) || 0) + w);
    for (const f of p.fastening || []) byFas.set(f.type, (byFas.get(f.type) || 0) + (f.count || 0) * q);
    cost += (p.cost_cny || 0) * q;
    if (p.disassembly_kind === 'destructive') nDestr++;
    else { nRemov++; disasm += (p.disassembly_min || 0); }
    byCost.set(p.group, (byCost.get(p.group) || 0) + (p.cost_cny || 0) * q);
  }
  const srt = (m) => Array.from(m.entries()).sort((a, b) => b[1] - a[1]);
  return { total, cost, disasm, nRemov, nDestr,
           byGroup: srt(byGroup), byMat: srt(byMat), byFas: srt(byFas), byCost: srt(byCost) };
}

function renderAggregate() {
  const L = t(), a = aggregate();
  if (!a.total) return '';
  const bar = (label, val, max, color) => {
    const pct = Math.max(1.5, (val / max) * 100);
    return `<div class="agg-row"><span class="agg-lb">${esc(label)}</span>`
      + `<span class="agg-bar"><i style="width:${pct.toFixed(1)}%;background:${color}"></i></span>`
      + `<span class="agg-val mono">${esc(fmtMass(val))}</span></div>`;
  };
  let h = `<div class="agg">`;
  h += `<h2 class="p-name">${esc(L.aggTitle)}</h2>`;
  h += `<p class="p-alt">${esc(L.aggHint)}</p>`;
  h += `<div class="agg-total mono">${esc(L.aggTotal)} <b>${esc(fmtMass(a.total))}</b></div>`;
  h += `<p class="agg-note">${esc(L.aggCurb.replace('{n}', ((S.data && S.data.parts) || []).length))}</p>`;

  const gmax = a.byGroup[0][1];
  h += `<div class="p-sec"><h4>${esc(L.aggMass)}</h4>`;
  for (const [g, v] of a.byGroup) h += bar(GROUP_NAME[S.lang][g] || g, v, gmax, GROUP_COLOR[g] || '#888');
  h += `</div>`;

  const mtop = a.byMat.slice(0, 6), mmax = mtop[0][1];
  h += `<div class="p-sec"><h4>${esc(L.aggMat)}</h4>`;
  for (const [m, v] of mtop) {
    const nm = VOCAB.material[m] ? VOCAB.material[m][S.lang === 'zh' ? 0 : 1] : m;
    h += bar(nm, v, mmax, '#6b7280');
  }
  h += `</div>`;

  if (a.cost) {
    const cmax = a.byCost[0][1];
    h += `<div class="p-sec"><h4>${esc(L.aggCost)}</h4>`;
    h += `<div class="agg-total mono">${esc(L.aggCostTotal)} <b>¥${Math.round(a.cost).toLocaleString()}</b></div>`;
    for (const [g, v] of a.byCost) {
      const pct = Math.max(1.5, (v / cmax) * 100);
      h += `<div class="agg-row"><span class="agg-lb">${esc(GROUP_NAME[S.lang][g] || g)}</span>`
        + `<span class="agg-bar"><i style="width:${pct.toFixed(1)}%;background:${GROUP_COLOR[g] || '#888'}"></i></span>`
        + `<span class="agg-val mono">¥${Math.round(v).toLocaleString()}</span></div>`;
    }
    h += `<p class="agg-note">${esc(L.aggCostNote)}</p></div>`;
  }
  if (a.nRemov || a.nDestr) {
    h += `<div class="p-sec"><h4>${esc(L.aggDisasm)}</h4>`;
    h += `<div class="agg-total mono">${esc(L.aggDisasmTotal)} <b>${(a.disasm / 60).toFixed(1)} h</b></div>`;
    const mx = Math.max(a.nRemov, a.nDestr);
    for (const [lb, n, c] of [[L.disasmKind.removable, a.nRemov, '#3f6b4a'],
                              [L.disasmKind.destructive, a.nDestr, '#c0342c']]) {
      const pct = Math.max(1.5, (n / mx) * 100);
      h += `<div class="agg-row"><span class="agg-lb">${esc(lb)}</span>`
        + `<span class="agg-bar"><i style="width:${pct.toFixed(1)}%;background:${c}"></i></span>`
        + `<span class="agg-val mono">${n}</span></div>`;
    }
    h += `<p class="agg-note">${esc(L.aggDisasmNote)}</p></div>`;
  }
  h += `<div class="p-sec"><h4>${esc(L.aggFas)}</h4><div class="chips">`;
  for (const [f, n] of a.byFas) {
    const nm = VOCAB.fasten[f] ? VOCAB.fasten[f][S.lang === 'zh' ? 0 : 1] : f;
    h += `<span class="chip flat">${esc(nm)} <b class="mono">${n}</b></span>`;
  }
  h += `</div></div></div>`;
  return h;
}

// 钻取：某个部分或某个官方图组的小计。基准工具的系统级对比就是从这儿开始的。
function scopeAgg(scope) {
  const parts = ((S.data && S.data.parts) || []).filter((p) => {
    if (p.group !== scope.group) return false;
    if (!scope.subgroup) return true;
    return (p.subgroup_en || p.subgroup_zh || '—') === scope.subgroup;
  });
  let mass = 0, cost = 0, time = 0, removable = 0, destructive = 0;
  const byMat = new Map();
  // 组内也只统计叶子件：这一组里若某件是别件的父，它的重量已经是子件之和
  const ids = new Set(parts.map((p) => p.id));
  const hasKidInScope = new Set(parts.filter((p) => ids.has(p.parent)).map((p) => p.parent));
  for (const p of parts) {
    if (hasKidInScope.has(p.id)) continue;
    const q = p.qty || 1;
    mass += (p.weight_g || 0) * q;
    cost += (p.cost_cny || 0) * q;
    if (p.disassembly_kind === 'destructive') destructive++;
    else { removable++; time += p.disassembly_min || 0; }
    if (p.material) byMat.set(p.material, (byMat.get(p.material) || 0) + (p.weight_g || 0) * q);
  }
  const heavy = parts.slice().sort((a, b) =>
    (b.weight_g || 0) * (b.qty || 1) - (a.weight_g || 0) * (a.qty || 1)).slice(0, 5);
  return { parts, mass, cost, time, removable, destructive, heavy,
           byMat: Array.from(byMat.entries()).sort((a, b) => b[1] - a[1]).slice(0, 5) };
}

function renderScope() {
  const L = t(), sc = S.scope, a = scopeAgg(sc);
  if (!a.parts.length) return '';
  const title = sc.subgroup
    ? (S.lang === 'zh' ? (a.parts[0].subgroup_zh || sc.subgroup) : (a.parts[0].subgroup_en || sc.subgroup))
    : (GROUP_NAME[S.lang][sc.group] || sc.group);
  const kicker = sc.subgroup ? (GROUP_NAME[S.lang][sc.group] || sc.group) : '';
  let h = `<div class="agg">`;
  h += `<button type="button" class="pill mini" id="scopeBack">${esc(L.scopeBack)}</button>`;
  if (kicker) h += `<div class="p-kicker" style="color:${GROUP_COLOR[sc.group]}">${esc(kicker)}</div>`;
  h += `<h2 class="p-name">${esc(title)}</h2>`;
  h += `<p class="p-alt">${esc(L.scopeHint)}</p>`;
  h += `<div class="p-sec"><dl class="kv">`;
  h += `<dt>${esc(L.scopeParts)}</dt><dd class="mono">${a.parts.length}</dd>`;
  h += `<dt>${esc(L.scopeMass)}</dt><dd class="mono">${esc(fmtMass(a.mass))}</dd>`;
  h += `<dt>${esc(L.scopeCost)}</dt><dd class="mono">¥${Math.round(a.cost).toLocaleString()}</dd>`;
  h += `<dt>${esc(L.scopeTime)}</dt><dd class="mono">${a.time.toFixed(1)} min</dd>`;
  h += `<dt>${esc(L.aggDisasm)}</dt><dd class="mono">${a.removable} / ${a.destructive}</dd>`;
  h += `</dl></div>`;
  if (a.byMat.length) {
    const mx = a.byMat[0][1];
    h += `<div class="p-sec"><h4>${esc(L.aggMat)}</h4>`;
    for (const [m, v] of a.byMat) {
      const nm = VOCAB.material[m] ? VOCAB.material[m][S.lang === 'zh' ? 0 : 1] : m;
      const pct = Math.max(1.5, (v / mx) * 100);
      h += `<div class="agg-row"><span class="agg-lb">${esc(nm)}</span>`
        + `<span class="agg-bar"><i style="width:${pct.toFixed(1)}%;background:#6b7280"></i></span>`
        + `<span class="agg-val mono">${esc(fmtMass(v))}</span></div>`;
    }
    h += `</div>`;
  }
  h += `<div class="p-sec"><h4>${esc(L.scopeHeaviest)}</h4><div class="chips">`;
  for (const p of a.heavy) {
    h += `<span class="chip flat" data-goto="${esc(p.id)}">${esc(partName(p).main)}`
      + ` <b class="mono">${esc(fmtMass((p.weight_g || 0) * (p.qty || 1)))}</b></span>`;
  }
  h += `</div></div></div>`;
  return h;
}

// 零件横向对比：基准工具最核心的动作。所有值都用和单件面板完全相同的口径，
// 不另算一套 —— 两处对不上是最容易失去信任的地方。
const CMP_ROWS = [
  ['kPn',       (p) => p.oem_pn || '—'],
  ['kSub',      (p, L) => (S.lang === 'zh' ? p.subgroup_zh : p.subgroup_en) || '—'],
  ['kQty',      (p, L) => (p.qty_kind === 'approx' ? '≈ ' : '') + p.qty + ' ' + L.unit],
  ['kMaterial', (p) => (VOCAB.material[p.material] || ['—', '—'])[S.lang === 'zh' ? 0 : 1]],
  ['kProcess',  (p) => (VOCAB.process[p.process] || ['—', '—'])[S.lang === 'zh' ? 0 : 1]],
  ['kWeight',   (p) => fmtMass(p.weight_g)],
  ['kCost',     (p) => '¥' + (p.cost_cny || 0).toFixed(2)],
  ['kDisasm',   (p, L) => (p.disassembly_kind === 'destructive'
                   ? L.disasmKind.destructive : (p.disassembly_min || 0).toFixed(1) + ' min')],
  ['kDepth',    (p) => String(p.tree_depth == null ? '—' : p.tree_depth)],
  ['kFasten',   (p, L) => (p.fastening || []).map((f) =>
                   ((VOCAB.fasten[f.type] || [f.type, f.type])[S.lang === 'zh' ? 0 : 1])
                   + (f.count > 1 ? '×' + f.count : '')).join('，') || '—'],
  ['kSup',      (p) => String((p.suppliers || []).length)],
];

function renderCompare() {
  const L = t();
  const list = S.compare.map((id) => S.byId.get(id)).filter(Boolean);
  if (!list.length) return '';
  let h = `<div class="agg">`;
  h += `<button type="button" class="pill mini" id="cmpBack">${esc(L.scopeBack)}</button>`;
  h += `<h2 class="p-name">${esc(L.cmpTitle)}</h2>`;
  h += `<p class="p-alt">${esc(L.cmpHint)}</p>`;
  h += `<div class="cmp-wrap"><table class="cmp"><thead><tr><th></th>`;
  for (const p of list) {
    h += `<th><span class="cmp-h" data-goto="${esc(p.id)}">${esc(partName(p).main)}</span>`
      + `<button type="button" class="cmp-x" data-drop="${esc(p.id)}">×</button></th>`;
  }
  h += `</tr></thead><tbody>`;
  for (const [key, fn] of CMP_ROWS) {
    h += `<tr><th>${esc(L[key])}</th>`;
    for (const p of list) h += `<td class="mono">${esc(String(fn(p, L)))}</td>`;
    h += `</tr>`;
  }
  h += `</tbody></table></div>`;
  h += `<button type="button" class="pill mini" id="cmpClear">${esc(L.cmpClear)}</button></div>`;
  return h;
}

function renderCompareTray() {
  const L = t();
  if (!S.compare.length) return '';
  let h = `<div class="cmp-tray">`;
  for (const id of S.compare) {
    const p = S.byId.get(id);
    if (p) h += `<span class="chip flat">${esc(partName(p).main)}<button type="button" class="cmp-x" data-drop="${esc(id)}">×</button></span>`;
  }
  if (S.compare.length >= 2) {
    h += `<button type="button" class="pill mini primary" id="cmpOpen">`
      + esc(L.cmpOpen.replace('{n}', S.compare.length)) + `</button>`;
  }
  h += `</div>`;
  return h;
}

function bindCompare(root) {
  root.querySelectorAll('[data-drop]').forEach((n) => n.addEventListener('click', (e) => {
    e.stopPropagation();
    S.compare = S.compare.filter((x) => x !== n.getAttribute('data-drop'));
    if (S.compare.length < 2) S.compareOpen = false;
    renderPanel();
  }));
  const o = root.querySelector('#cmpOpen');
  if (o) o.addEventListener('click', () => { S.compareOpen = true; S.selected = null; S.scope = null; clearHighlight(); renderPanel(); });
  const c = root.querySelector('#cmpClear');
  if (c) c.addEventListener('click', () => { S.compare = []; S.compareOpen = false; renderPanel(); });
  const bk = root.querySelector('#cmpBack');
  if (bk) bk.addEventListener('click', () => { S.compareOpen = false; renderPanel(); });
  root.querySelectorAll('[data-goto]').forEach((n) => {
    n.style.cursor = 'pointer';
    n.addEventListener('click', () => selectPart(n.getAttribute('data-goto'), true));
  });
}

function renderPanel() {
  const body = el('panelBody');
  const empty = el('panelEmpty');
  const p = S.selected ? S.byId.get(S.selected) : null;
  if (!p) {
    // 没选中零件时，右栏给整车层面的汇总，而不是一句「还没有选中零件」。
    // 质量分布 / 材料构成 / 紧固件合计 —— 这是拆解基准工具真正的看点。
    body.hidden = true; empty.hidden = false; body.innerHTML = '';
    empty.innerHTML = (S.compareOpen && S.compare.length >= 2)
      ? renderCompare()
      : (S.scope ? renderScope() : renderAggregate()) + renderCompareTray();
    bindCompare(empty);
    const bk = el('scopeBack');
    if (bk) bk.addEventListener('click', () => { S.scope = null; renderPanel(); });
    empty.querySelectorAll('[data-goto]').forEach((n) => {
      n.style.cursor = 'pointer';
      n.addEventListener('click', () => selectPart(n.getAttribute('data-goto'), true));
    });
    return;
  }
  empty.hidden = true; body.hidden = false;

  const L = t();
  const nm = partName(p);
  const qty = (p.qty_kind === 'approx' ? '≈ ' : '') + p.qty + ' ' + L.unit;
  const sub = S.lang === 'zh' ? (p.subgroup_zh || p.subgroup_en) : (p.subgroup_en || p.subgroup_zh);
  const role = enSafe(S.lang === 'zh' ? p.role_zh : p.role_en);
  const gname = GROUP_NAME[S.lang][p.group] || p.group;
  const gcolor = GROUP_COLOR[p.group] || '#666';

  let h = '';
  h += `<div class="p-kicker" style="color:${gcolor}">${esc(gname)}</div>`;
  h += `<h2 class="p-name">${esc(nm.main)}</h2>`;
  h += `<p class="p-alt">${esc(nm.alt || '')}${p.has_mesh ? '' : ' ' + esc(L.noMesh)}</p>`;
  if (role) h += `<div class="p-role">${esc(role)}</div>`;

  h += `<div class="p-sec"><dl class="kv">`;
  h += `<dt>${esc(L.kPn)}</dt><dd class="mono">${p.oem_pn ? esc(p.oem_pn) : esc(L.kNoPn)}</dd>`;
  h += `<dt>${esc(L.kSub)}</dt><dd>${esc(sub || L.kNone)}</dd>`;
  h += `<dt>${esc(L.kQty)}</dt><dd class="mono">${esc(qty)}</dd>`;
  // 专业拆解基准的四个维度：材料 / 成型工艺 / 连接方式 / 重量
  if (p.material && VOCAB.material[p.material]) {
    h += `<dt>${esc(L.kMaterial)}</dt><dd>${esc(VOCAB.material[p.material][S.lang === 'zh' ? 0 : 1])}</dd>`;
  }
  if (p.process && VOCAB.process[p.process]) {
    h += `<dt>${esc(L.kProcess)}</dt><dd>${esc(VOCAB.process[p.process][S.lang === 'zh' ? 0 : 1])}</dd>`;
  }
  if (typeof p.weight_g === 'number') {
    h += `<dt>${esc(L.kWeight)}</dt><dd class="mono">${esc(fmtMass(p.weight_g))}`
      + `<span class="conf">${esc(L.basis[p.weight_basis] || p.weight_basis)}</span></dd>`;
  }
  if (typeof p.cost_cny === 'number') {
    h += `<dt>${esc(L.kCost)}</dt><dd class="mono">¥${esc(p.cost_cny.toFixed(2))}`
      + `<span class="conf">${esc(L.basis[p.cost_basis] || p.cost_basis)}</span></dd>`;
  }
  if (typeof p.disassembly_min === 'number') {
    const dk = L.disasmKind[p.disassembly_kind] || p.disassembly_kind;
    const val = p.disassembly_kind === 'destructive'
      ? esc(dk)
      : esc(p.disassembly_min.toFixed(1)) + ' min<span class="conf">' + esc(dk) + '</span>';
    h += `<dt>${esc(L.kDisasm)}</dt><dd class="mono">${val}</dd>`;
    h += `<dt>${esc(L.kDepth)}</dt><dd class="mono">${esc(String(p.tree_depth))}</dd>`;
  }
  if (Array.isArray(p.fastening) && p.fastening.length) {
    const fs = p.fastening.map((f) => {
      const nm2 = VOCAB.fasten[f.type] ? VOCAB.fasten[f.type][S.lang === 'zh' ? 0 : 1] : f.type;
      return nm2 + (f.spec ? ' ' + f.spec : '') + (f.count > 1 ? ' ×' + f.count : '');
    }).join('，');
    h += `<dt>${esc(L.kFasten)}</dt><dd>${esc(fs)}</dd>`;
  }
  const spec = enSafe(p.spec);
  if (spec) h += `<dt>${esc(L.kSpec)}</dt><dd>${esc(spec)}</dd>`;
  h += `</dl></div>`;

  if (Array.isArray(p.tags) && p.tags.length) {
    h += `<div class="p-sec"><h4>${esc(L.kTags)}</h4><div class="chips">`;
    for (const tg of p.tags) h += `<span class="chip flat">${esc(tagLabel(tg))}</span>`;
    h += `</div></div>`;
  }

  {
    const inCmp = S.compare.includes(p.id);
    h += `<div class="p-sec"><button type="button" class="pill mini${inCmp ? '' : ' primary'}" `
      + `id="cmpToggle">${esc(inCmp ? L.cmpDrop : L.cmpAdd)}</button></div>`;
  }
  const conn = (p.connects_to || []).filter((c) => S.byId.has(c));
  if (conn.length) {
    h += `<div class="p-sec"><h4>${esc(L.kConn)}</h4><div class="chips">`;
    for (const c of conn) {
      const cp = S.byId.get(c);
      h += `<button type="button" class="chip" data-goto="${esc(c)}">${esc(partName(cp).main)}</button>`;
    }
    h += `</div></div>`;
  }

  if (Array.isArray(p.suppliers) && p.suppliers.length) {
    h += `<div class="p-sec"><h4>${esc(L.kSup)}</h4><table class="sup"><thead><tr>`;
    h += `<th>${esc(L.supName)}</th><th>${esc(L.supConf)}</th></tr></thead><tbody>`;
    for (const s of p.suppliers) {
      const conf = String(s.confidence || 'low').toLowerCase();
      const cls = ['high', 'medium', 'low'].includes(conf) ? conf : 'low';
      h += `<tr><td><b>${esc(enSafe(s.name) || L.kNone)}</b>`;
      const note = enSafe(s.note);
      if (note) h += `<div class="sup-note">${esc(note)}</div>`;
      const src = enSafe(s.source);
      if (src && src !== I18N.en.naEn) h += `<div class="sup-src">${esc(src)}</div>`;
      h += `</td><td><span class="conf ${cls}">${esc(cls)}</span></td></tr>`;
    }
    h += `</tbody></table></div>`;
  }

  body.innerHTML = h;
  {
    const tg = el('cmpToggle');
    if (tg) tg.addEventListener('click', () => {
      const id = S.selected;
      if (S.compare.includes(id)) S.compare = S.compare.filter((x) => x !== id);
      else if (S.compare.length >= 3) { toast(t().cmpFull); return; }
      else S.compare.push(id);
      renderPanel();
    });
    const tray = document.createElement('div');
    tray.innerHTML = renderCompareTray();
    if (tray.firstChild) { body.appendChild(tray.firstChild); bindCompare(body); }
  }
  body.querySelectorAll('[data-goto]').forEach((b) => {
    b.addEventListener('click', () => selectPart(b.getAttribute('data-goto'), true));
  });
  el('panel').scrollTop = 0;
}

// ───────────────────────────────────────────────── 选中高亮
function clearHighlight() {
  for (const o of outline) {
    scene.remove(o);
    o.geometry.dispose(); o.material.dispose();
  }
  outline.length = 0;
  for (const [mesh, mat] of emissiveBackup) {
    if (mesh.material !== mat) mesh.material.dispose();  // 丢掉高亮用的克隆材质，别攒着
    mesh.material = mat;
  }
  emissiveBackup.clear();
}

function applyHighlight(id) {
  const obj = S.car && S.car.objects.get(id);
  if (!obj) return;
  obj.traverse((n) => {
    if (!n.isMesh) return;
    emissiveBackup.set(n, n.material);
    const m = n.material.clone();
    m.emissive = new THREE.Color(0xc0342c);
    m.emissiveIntensity = 0.42;
    n.material = m;
  });
  // qty>1 的零件（4 条轮胎、4 块门内饰板）逐件描边。整组套一个大盒的话，
  // 选中轮胎会框住整台车，看着像选错了。
  const targets = obj.children.length > 1 ? obj.children : [obj];
  for (const t of targets) {
    const h = new THREE.BoxHelper(t, 0xc0342c);
    h.material.depthTest = false;
    h.material.transparent = true;
    h.material.opacity = 0.95;
    h.renderOrder = 999;
    scene.add(h);
    outline.push(h);
  }
}

function selectPart(id, focus) {
  if (!S.byId.has(id)) return false;
  S.scope = null;
  clearHighlight();
  S.selected = id;
  applyHighlight(id);
  renderPanel();
  if (!el('tree').hidden) renderTree();
  if (focus) {
    let obj = S.car.objects.get(id);
    if (!obj) {
      // 这一条没建 3D。往上找最近一个建了 3D 的祖先，把镜头带过去并说明原因，
      // 否则用户在树里点了半天没反应，会以为是坏的。
      let cur = p.parent, guard = 0;
      while (cur && !S.car.objects.has(cur) && guard++ < 12) {
        const up = S.byId.get(cur);
        cur = up && up.parent;
      }
      obj = cur ? S.car.objects.get(cur) : null;
      toast(t().noMeshJump);
    }
    if (obj) {
      const c = new THREE.Box3().setFromObject(obj).getCenter(new THREE.Vector3());
      tweenCamera(c, null, 620);
    }
  }
  return true;
}

// ───────────────────────────────────────────────── 相机
// 按包围盒 8 个角精确解相机距离：fillRatio=0.7 就是「盒子在画面里占 70%」。
// 之前用外接球算，球比车大一大圈，车只能占到画面四成，领导那条 60~75% 直接不达标。
function fitDistance(box, fillRatio, dirIn) {
  const center = box.getCenter(new THREE.Vector3());
  const dir = (dirIn || camera.position.clone().sub(controls.target)).clone();
  if (dir.lengthSq() < 1e-8) dir.copy(VIEW_DIR);
  dir.normalize();
  const right = new THREE.Vector3().crossVectors(dir, new THREE.Vector3(0, 1, 0));
  if (right.lengthSq() < 1e-8) right.set(1, 0, 0);
  right.normalize();
  const up = new THREE.Vector3().crossVectors(right, dir).normalize();
  const vT = Math.tan((camera.fov * Math.PI) / 360) * fillRatio;
  const hT = vT * camera.aspect;
  const v = new THREE.Vector3();
  let d = 0;
  for (let i = 0; i < 8; i++) {
    v.set(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z).sub(center);
    const along = v.dot(dir);
    d = Math.max(d, along + Math.abs(v.dot(right)) / hT, along + Math.abs(v.dot(up)) / vT);
  }
  return { center, dist: Math.max(d, 0.6) };
}

const FILL = { assembled: 0.76, exploded: 0.78 };

const easeInOut = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);

function tweenCamera(target, dist, ms) {
  const fromT = controls.target.clone();
  const fromD = camera.position.distanceTo(controls.target);
  const toT = target ? target.clone() : fromT.clone();
  const toD = dist == null ? fromD : dist;
  S.camAnim = { t0: performance.now(), ms, fromT, toT, fromD, toD };
}

function resetView(ms) {
  S.car.root.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(S.car.root);
  const { center, dist } = fitDistance(box, FILL[S.state], VIEW_DIR);
  const pos = center.clone().add(VIEW_DIR.clone().multiplyScalar(dist));
  if (ms === 0) {
    controls.target.copy(center);
    camera.position.copy(pos);
    controls.update();
    S.camAnim = null;
    return;
  }
  S.camAnim = {
    t0: performance.now(), ms,
    fromT: controls.target.clone(), toT: center.clone(),
    fromP: camera.position.clone(), toP: pos,
  };
}

// ───────────────────────────────────────────────── 爆炸 / 合拢
function animateTo(stateName, ms) {
  if (!S.car) return Promise.resolve();
  const targets = stateName === 'exploded' ? S.car.exploded : S.car.assembled;
  const from = new Map();
  for (const [id, obj] of S.car.objects) from.set(id, obj.position.clone());
  S.state = stateName;
  syncStateUI();
  return new Promise((resolve) => {
    S.anim = { t0: performance.now(), ms, from, targets, resolve };
    // 相机同步跟着走一段，避免展开后车飞出画面
    S.car.root.updateMatrixWorld(true);
    const box = new THREE.Box3();
    const b = new THREE.Box3();
    for (const [id, obj] of S.car.objects) {
      const p = targets.get(id) || obj.position;
      b.setFromObject(obj).translate(p.clone().sub(obj.position));
      box.union(b);
    }
    const { center, dist } = fitDistance(box, FILL[stateName]);
    tweenCamera(center, dist, ms);
  });
}

function explode() { return S.state === 'exploded' ? Promise.resolve() : animateTo('exploded', 1150); }
function assemble() { return S.state === 'assembled' ? Promise.resolve() : animateTo('assembled', 1000); }

function syncStateUI() {
  const b = el('btnExplode');
  b.textContent = S.state === 'exploded' ? t().assemble : t().explode;
  b.classList.toggle('primary', S.state === 'assembled');
  const g = S.car && S.car.ground;
  if (g) g.userData.want = S.state === 'assembled' ? 1 : 0;
}

// ───────────────────────────────────────────────── 语言
function setLang(l) {
  if (l !== 'zh' && l !== 'en') return false;
  S.lang = l;
  app.setAttribute('data-lang', l);
  document.documentElement.lang = l === 'zh' ? 'zh-CN' : 'en';
  const L = t();
  document.querySelectorAll('[data-i18n]').forEach((n) => {
    const k = n.getAttribute('data-i18n');
    if (L[k] != null) n.textContent = L[k];
  });
  document.querySelectorAll('[data-lang-btn]').forEach((b) => {
    b.classList.toggle('on', b.getAttribute('data-lang-btn') === l);
  });
  document.querySelectorAll('[data-i18n-ph]').forEach((n) => {
    const k = n.getAttribute('data-i18n-ph');
    if (L[k] != null) n.placeholder = L[k];
  });
  const badge = el('dataBadge');
  if (!badge.hidden) badge.textContent = L.stub;
  const tip = el('tip');
  tip.hidden = true; tip.textContent = '';
  syncStateUI();
  renderPanel();
  if (!el('tree').hidden) { renderTreeTags(); renderTree(); }
  return true;
}

let toastTimer = null;
function toast(msg) {
  const n = el('tip');
  if (!n) return;
  n.textContent = msg;
  n.classList.add('toast');
  n.style.left = '50%'; n.style.top = '18px';
  n.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { n.hidden = true; n.classList.remove('toast'); }, 2600);
}

// ───────────────────────────────────────────────── 拾取
function pickAt(cx, cy) {
  const r = canvas.getBoundingClientRect();
  pointer.x = ((cx - r.left) / r.width) * 2 - 1;
  pointer.y = -((cy - r.top) / r.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObject(S.car.root, true);
  for (const h of hits) {
    let o = h.object;
    while (o && !o.userData.id) o = o.parent;
    if (o && o.userData.id) return o.userData.id;
  }
  return null;
}

function bindEvents() {
  let downAt = null;
  canvas.addEventListener('pointerdown', (e) => { downAt = { x: e.clientX, y: e.clientY, t: performance.now() }; });
  canvas.addEventListener('pointerup', (e) => {
    if (!downAt) return;
    const moved = Math.hypot(e.clientX - downAt.x, e.clientY - downAt.y);
    const dt = performance.now() - downAt.t;
    downAt = null;
    if (moved > 5 || dt > 600) return;      // 拖动过就不算点击
    const id = pickAt(e.clientX, e.clientY);
    if (id) selectPart(id, false);
  });

  let hoverTick = 0;
  canvas.addEventListener('pointermove', (e) => {
    const now = performance.now();
    if (now - hoverTick < 60) return;
    hoverTick = now;
    const id = pickAt(e.clientX, e.clientY);
    const tip = el('tip');
    if (id && S.byId.has(id)) {
      const r = stage.getBoundingClientRect();
      tip.textContent = partName(S.byId.get(id)).main;
      tip.style.left = (e.clientX - r.left) + 'px';
      tip.style.top = (e.clientY - r.top) + 'px';
      tip.hidden = false;
      canvas.style.cursor = 'pointer';
    } else {
      tip.hidden = true; tip.textContent = '';
      canvas.style.cursor = '';
    }
  });
  canvas.addEventListener('pointerleave', () => {
    const tip = el('tip'); tip.hidden = true; tip.textContent = '';
  });

  el('btnExplode').addEventListener('click', () => {
    (S.state === 'assembled' ? explode() : assemble());
  });
  el('btnReset').addEventListener('click', () => resetView(700));
  bindTree();
  document.querySelectorAll('[data-lang-btn]').forEach((b) => {
    b.addEventListener('click', () => setLang(b.getAttribute('data-lang-btn')));
  });

  const ro = new ResizeObserver(resize);
  ro.observe(stage);
  window.addEventListener('resize', resize);
}

function resize() {
  const w = Math.max(1, stage.clientWidth), h = Math.max(1, stage.clientHeight);
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}

// ───────────────────────────────────────────────── 主循环
let last = performance.now();
function tick(now) {
  requestAnimationFrame(tick);
  const dt = now - last; last = now;
  if (S.ready) {
    S.frames.push(dt);
    if (S.frames.length > 180) S.frames.shift();
  }
  const w0 = performance.now();

  if (S.anim) {
    const a = S.anim;
    const k = Math.min(1, (now - a.t0) / a.ms);
    const e = easeInOut(k);
    for (const [id, obj] of S.car.objects) {
      const f = a.from.get(id), tg = a.targets.get(id);
      if (!f || !tg) continue;
      obj.position.lerpVectors(f, tg, e);
    }
    for (const o of outline) o.update();
    if (k >= 1) { const r = a.resolve; S.anim = null; if (r) r(); }
  }

  if (S.camAnim) {
    const c = S.camAnim;
    const k = Math.min(1, (now - c.t0) / c.ms);
    const e = easeInOut(k);
    controls.target.lerpVectors(c.fromT, c.toT, e);
    if (c.toP) {
      camera.position.lerpVectors(c.fromP, c.toP, e);
    } else {
      const dir = camera.position.clone().sub(controls.target);
      if (dir.lengthSq() < 1e-8) dir.copy(VIEW_DIR);
      dir.normalize().multiplyScalar(c.fromD + (c.toD - c.fromD) * e);
      camera.position.copy(controls.target).add(dir);
    }
    if (k >= 1) S.camAnim = null;
  }

  const g = S.car && S.car.ground;
  if (g) {
    const want = g.userData.want == null ? 1 : g.userData.want;
    g.material.opacity += (want - g.material.opacity) * Math.min(1, dt / 240);
  }

  controls.update();
  renderer.render(scene, camera);

  if (S.ready) {
    S.work.push(performance.now() - w0);
    if (S.work.length > 180) S.work.shift();
  }
}

function p95(arr) {
  if (!arr.length) return 0;
  const a = arr.slice().sort((x, y) => x - y);
  return a[Math.min(a.length - 1, Math.floor(a.length * 0.95))];
}

// ───────────────────────────────────────────────── 启动
async function boot() {
  const { doc, source, issue } = await loadData();
  S.data = doc; S.dataSource = source; S.dataIssue = issue;
  for (const p of doc.parts) S.byId.set(p.id, p);

  if (source === 'stub') {
    const b = el('dataBadge');
    b.hidden = false;
    b.textContent = I18N[S.lang].stub;
  }
  if (issue) console.warn('[corolla] data/parts.json 不可用或不合冻结格式，已退回 stub：', issue);

  S.car = buildCar(doc.parts);
  S.car.ground = makeGroundShadow();
  S.car.ground.userData.want = 1;
  scene.add(S.car.root, S.car.ground);

  resize();
  setLang('zh');
  resetView(0);
  bindEvents();

  renderer.render(scene, camera);
  requestAnimationFrame(tick);

  const lo = el('loading');
  lo.classList.add('gone');
  setTimeout(() => { lo.style.display = 'none'; }, 520);

  S.ready = true;
  console.info(`[corolla] ready · source=${source} · meshParts=${S.car.objects.size} · matched=${S.car.buildStats.matched} · fallback=${S.car.buildStats.fallback}`);
}

// ───────────────────────────────────────────────── 冻结调试接口
const api = {
  get ready() { return S.ready; },
  get partIds() { return S.car ? Array.from(S.car.objects.keys()) : []; },
  get data() { return S.data; },
  get state() { return S.state; },
  get lang() { return S.lang; },
  get dataSource() { return S.dataSource; },
  get dataIssue() { return S.dataIssue; },
  explode, assemble,
  select: (id) => selectPart(id, false),
  get selected() { return S.selected; },
  setLang,
  panelText() {
    const b = el('panelBody');
    if (!b || b.hidden) return el('panelEmpty').innerText || '';
    return b.innerText || '';
  },
  bbox() {
    if (!S.car) return null;
    const b = new THREE.Box3().setFromObject(S.car.root);
    const s = b.getSize(new THREE.Vector3());
    return {
      min: b.min.toArray(), max: b.max.toArray(), size: s.toArray(),
      maxEdge: Math.max(s.x, s.y, s.z),
      center: b.getCenter(new THREE.Vector3()).toArray(),
    };
  },
  // 整车包围盒投影到画布上占多大：领导那条「默认视角车身占画面 60~75%」的客观量法
  coverage() {
    if (!S.car) return null;
    S.car.root.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(S.car.root);
    camera.updateMatrixWorld(true);
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    const v = new THREE.Vector3();
    for (let i = 0; i < 8; i++) {
      v.set(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z);
      v.project(camera);
      x0 = Math.min(x0, v.x); x1 = Math.max(x1, v.x);
      y0 = Math.min(y0, v.y); y1 = Math.max(y1, v.y);
    }
    const w = (x1 - x0) / 2, h = (y1 - y0) / 2;
    return { w: Math.round(w * 1000) / 1000, h: Math.round(h * 1000) / 1000, max: Math.round(Math.max(w, h) * 1000) / 1000 };
  },
  // 四大簇各自的世界包围盒。「爆炸后四簇互不穿插」这句话要能验，就得给得出盒子。
  clusterBoxes() {
    if (!S.car) return null;
    S.car.root.updateMatrixWorld(true);
    const acc = new Map();
    const b = new THREE.Box3();
    for (const obj of S.car.objects.values()) {
      const g = obj.userData.group || 'unknown';
      b.setFromObject(obj);
      let e = acc.get(g);
      if (!e) { e = { box: new THREE.Box3(), n: 0 }; acc.set(g, e); }
      e.box.union(b);
      e.n++;
    }
    const out = {};
    for (const [g, e] of acc) out[g] = { min: e.box.min.toArray(), max: e.box.max.toArray(), n: e.n };
    return out;
  },
  stats() {
    const r = renderer.info.render;
    return {
      triangles: r.triangles,
      calls: r.calls,
      frameP95: Math.round(p95(S.frames) * 100) / 100,
      frameWorkP95: Math.round(p95(S.work) * 100) / 100,
      frames: S.frames.length,
      objects: S.car ? S.car.objects.size : 0,
      geometries: renderer.info.memory.geometries,
      materials: renderer.info.programs ? renderer.info.programs.length : -1,
    };
  },
  // 给 verify.py 数「场景里带 id 的 Object3D」用，防止拿一个大网格冒充一堆零件
  countIdObjects() {
    let n = 0;
    scene.traverse((o) => { if (o.userData && typeof o.userData.id === 'string' && o.userData.id) n++; });
    return n;
  },
  meshCountFor(id) {
    const o = S.car && S.car.objects.get(id);
    if (!o) return 0;
    let n = 0;
    o.traverse((c) => { if (c.isMesh) n++; });
    return n;
  },
  // 零件的几何实体体积（立方米，含世界缩放）。重量估算靠它，比上网抄「运输重量」诚实得多。
  volumeOf(id) {
    const o = S.car && S.car.objects.get(id);
    if (!o) return null;
    const s = new THREE.Vector3();
    let vol = 0;
    o.updateMatrixWorld(true);
    o.traverse((m) => {
      if (!m.isMesh || !m.geometry) return;
      const g = m.geometry, p = g.attributes.position.array, ix = g.index ? g.index.array : null;
      const n = ix ? ix.length : g.attributes.position.count;
      let v = 0;
      for (let i = 0; i < n; i += 3) {
        const a = (ix ? ix[i] : i) * 3, b = (ix ? ix[i + 1] : i + 1) * 3, c = (ix ? ix[i + 2] : i + 2) * 3;
        v += (p[a] * (p[b + 1] * p[c + 2] - p[b + 2] * p[c + 1])
            - p[a + 1] * (p[b] * p[c + 2] - p[b + 2] * p[c])
            + p[a + 2] * (p[b] * p[c + 1] - p[b + 1] * p[c])) / 6;
      }
      m.getWorldScale(s);
      vol += Math.abs(v) * Math.abs(s.x * s.y * s.z);
    });
    const bb = new THREE.Box3().setFromObject(o), sz = bb.getSize(new THREE.Vector3());
    return { vol_m3: vol, bbox: [sz.x, sz.y, sz.z] };
  },
  // 零件树的规模：节点 = 四大部分 + 官方图组 + 零件；孤点 = 挂不到任何图组上的
  graphStats() {
    const parts = (S.data && S.data.parts) || [];
    const sgs = new Set(), orphan = [];
    for (const p of parts) {
      const k = p.group + '::' + (p.subgroup_en || p.subgroup_zh || '');
      if (!GROUPS.includes(p.group) || !(p.subgroup_en || p.subgroup_zh)) orphan.push(p.id);
      else sgs.add(k);
    }
    return { nodes: GROUPS.length + sgs.size + parts.length, groups: GROUPS.length,
             subgroups: sgs.size, parts: parts.length, edges: parts.length + sgs.size,
             orphans: orphan.length };
  },
  filterCount(tag) {
    const box = document.getElementById('treeBody');
    if (!box || document.getElementById('tree').hidden) return null;
    return box.querySelectorAll('[data-tp]').length;
  },
  setTreeTag(tag) { TREE.tag = tag || null; renderTreeTags(); renderTree(); return true; },
  setTreeOpen(on) {
    const tr = el('tree');
    tr.hidden = !on;
    el('btnTree').classList.toggle('primary', on);
    if (on) { renderTreeTags(); renderTree(); }
    return !tr.hidden;
  },
  scopeStats(group, subgroup) {
    const keep = S.scope;
    S.scope = subgroup ? { group, subgroup } : { group };
    const a = scopeAgg(S.scope);
    S.scope = keep;
    return { parts: a.parts.length, mass_g: a.mass, cost_cny: Math.round(a.cost),
             disasm_min: Math.round(a.time * 10) / 10, removable: a.removable, destructive: a.destructive };
  },
  exportBOM,
  resetView,
  CAR,
};

window.__car = api;

boot().catch((e) => {
  console.error('[corolla] boot failed', e);
  const lo = el('loading');
  if (lo) lo.querySelector('em').textContent = String(e && e.message || e);
});
