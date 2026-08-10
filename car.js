// car.js —— 纯代码程序化建模：用 Three.js 基本几何体拼一辆认得出的紧凑三厢轿车。
//
// 设计要点（改之前先读）：
// 1. 摆放表 PLACE 不按零件 id 索引，按「槽位 slot」索引。slot 是从 name_en 里认出来的
//    （hood / door.front + lh|rh 之类）。这样换成 A 的真数据、id 变了也还能对上，
//    只要英文件名还是行业通名。id 一变就散架的表是给自己挖坑。
// 2. 认不出的 has_mesh 零件不丢掉，落到 fallback：按 group 塞进车里对应的区域，
//    位置由 id 哈希决定（稳定、不随机跳）。宁可它是个小方块，也不能少一个可点的零件。
// 3. 一个零件 = 一个 Object3D，userData.id 就是它的 id。qty>1 的（比如 4 条轮胎）
//    是一个 Group 底下挂 4 个 Mesh，Group 才带 id —— 数 id 时仍然是 1 个零件。
//
// 坐标系：+X 车头，+Y 上，+Z 左侧（LH）。地面 y=0。单位米。

import * as THREE from 'three';

// ───────────────────────────────────────────────── 整车基准尺寸（E210 三厢，约数）
export const CAR = {
  len: 4.63, width: 1.78, height: 1.435,
  wheelbase: 2.70, track: 1.53,
  wheelR: 0.32, wheelW: 0.215,
  axleF: 1.35, axleR: -1.35,
  center: new THREE.Vector3(0, 0.72, 0),
};

// ───────────────────────────────────────────────── 材质（共用，控制 draw call 与内存）
function mats() {
  const M = (c, metalness, roughness, extra) => new THREE.MeshStandardMaterial(
    Object.assign({ color: new THREE.Color(c), metalness, roughness, side: THREE.DoubleSide }, extra || {}));
  // 车漆单独用 Physical：清漆层是「像车漆」和「像塑料」的分界，少了它再准的形状也发假
  const paint = new THREE.MeshPhysicalMaterial({
    color: new THREE.Color(0xb9c0c7), metalness: 0.62, roughness: 0.30,
    clearcoat: 1.0, clearcoatRoughness: 0.055, envMapIntensity: 1.15,
    side: THREE.DoubleSide,
  });
  return {
    paint,
    trim:    M(0x2c3036, 0.42, 0.46),
    dark:    M(0x1f2226, 0.12, 0.80),
    glass:   new THREE.MeshPhysicalMaterial({
      color: new THREE.Color(0x2d3c4a), metalness: 0.0, roughness: 0.045,
      transparent: true, opacity: 0.42, envMapIntensity: 2.0,
      clearcoat: 1.0, clearcoatRoughness: 0.02, side: THREE.DoubleSide,
    }),
    metal:   M(0x969ca3, 0.88, 0.34),
    alloy:   M(0xd2d7dc, 0.90, 0.18),
    chrome:  M(0xe8ecf0, 1.00, 0.06),
    engine:  M(0x7d848b, 0.70, 0.48),
    rubber:  M(0x17191c, 0.02, 0.96),
    lampw:   M(0xeef3f8, 0.30, 0.12, { emissive: new THREE.Color(0x8fa6bb), emissiveIntensity: 0.35 }),
    lampr:   M(0xb8342d, 0.25, 0.30, { emissive: new THREE.Color(0x8c1d17), emissiveIntensity: 0.45 }),
    copper:  M(0xb07a44, 0.80, 0.40),
    plastic: M(0xd6d9dc, 0.10, 0.72),
    fallback:M(0x8b9199, 0.35, 0.62),
  };
}

// ───────────────────────────────────────────────── 几何体工厂（带缓存，同规格只造一次）
const geoCache = new Map();
function cached(key, make) {
  let g = geoCache.get(key);
  if (!g) { g = make(); geoCache.set(key, g); }
  return g;
}

function boxGeo(sx, sy, sz) {
  return cached(`b|${sx}|${sy}|${sz}`, () => new THREE.BoxGeometry(sx, sy, sz));
}

// 圆角盒：外覆盖件用，避免一眼看去全是硬邦邦的方块
function rboxGeo(sx, sy, sz, r) {
  return cached(`r|${sx}|${sy}|${sz}|${r}`, () => {
    // 沿最薄的那根轴挤出，挤完把旋转烘进几何体
    const dims = [sx, sy, sz];
    const ax = dims.indexOf(Math.min(...dims));
    // 挤出后要绕轴转，转完哪条局部边落到哪条世界边是定死的，w/h 必须按结果反推：
    //   ax=0 转 Y90： 局部(x,y,z) -> 世界(z, y, -x)  => w 落到世界 Z，h 落到世界 Y
    //   ax=1 转 X90： 局部(x,y,z) -> 世界(x, -z, y)  => w 落到世界 X，h 落到世界 Z
    //   ax=2 不转：                                  => w 落到世界 X，h 落到世界 Y
    // 之前这里按 filter 顺序取 w/h，ax=0 时宽高正好反了，前保险杠被立成一堵墙。
    const d = dims[ax];
    const w = ax === 0 ? sz : sx;
    const h = ax === 1 ? sz : sy;
    const rr = Math.max(0.004, Math.min(r, w / 2 - 0.002, h / 2 - 0.002));
    const s = new THREE.Shape();
    const x = -w / 2, y = -h / 2;
    s.moveTo(x + rr, y);
    s.lineTo(x + w - rr, y); s.quadraticCurveTo(x + w, y, x + w, y + rr);
    s.lineTo(x + w, y + h - rr); s.quadraticCurveTo(x + w, y + h, x + w - rr, y + h);
    s.lineTo(x + rr, y + h); s.quadraticCurveTo(x, y + h, x, y + h - rr);
    s.lineTo(x, y + rr); s.quadraticCurveTo(x, y, x + rr, y);
    const bev = Math.min(rr * 0.6, d * 0.3);
    const g = new THREE.ExtrudeGeometry(s, {
      depth: Math.max(0.001, d - bev * 2), bevelEnabled: true,
      bevelThickness: bev, bevelSize: bev, bevelSegments: 1, curveSegments: 3, steps: 1,
    });
    g.translate(0, 0, -(d - bev * 2) / 2);
    // 挤出方向是 z；ax=0 需要绕 Y 转 90°，ax=1 需要绕 X 转 90°
    if (ax === 0) g.rotateY(Math.PI / 2);
    else if (ax === 1) g.rotateX(Math.PI / 2);
    g.computeVertexNormals();
    return g;
  });
}

function cylGeo(rt, rb, h, seg, axis) {
  return cached(`c|${rt}|${rb}|${h}|${seg}|${axis}`, () => {
    const g = new THREE.CylinderGeometry(rt, rb, h, seg);
    if (axis === 'x') g.rotateZ(Math.PI / 2);
    else if (axis === 'z') g.rotateX(Math.PI / 2);
    return g;
  });
}

function torusGeo(r, tube, seg, tseg) {
  return cached(`t|${r}|${tube}|${seg}|${tseg}`, () => new THREE.TorusGeometry(r, tube, tseg, seg));
}

function coilGeo(r, h, turns, tubeR) {
  return cached(`k|${r}|${h}|${turns}|${tubeR}`, () => {
    const N = turns * 10, pts = [];
    for (let i = 0; i <= N; i++) {
      const t = i / N, a = t * turns * Math.PI * 2;
      pts.push(new THREE.Vector3(Math.cos(a) * r, t * h - h / 2, Math.sin(a) * r));
    }
    return new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), N, tubeR, 5, false);
  });
}

function sphGeo(r) {
  return cached(`s|${r}`, () => new THREE.SphereGeometry(r, 12, 8));
}

// ═════════════════════════════════════════════════ 车身曲面
// 之前每块外覆盖件各画各的平板，拼出来是乐高。现在改成：先定义一条完整的车身外表面，
// 每块覆盖件从这条面上「切」自己那一片。这样翼子板和车门的边天然对齐、腰线连续、
// 轮拱是真的圆孔 —— 这是从积木变成示意图的关键一步，别再改回独立平板。
//
// 参数化：x 是纵向（+2.315 车头 ~ -2.315 车尾），v∈[0,1] 是从门槛底沿侧面绕到车顶中线。

// 单变量 Catmull-Rom：给一串 (x, y) 控制点，返回 f(x)
function spline1d(pts) {
  const n = pts.length;
  return (x) => {
    if (x <= pts[0][0]) return pts[0][1];
    if (x >= pts[n - 1][0]) return pts[n - 1][1];
    let i = 0;
    while (i < n - 2 && x > pts[i + 1][0]) i++;
    const [x1, y1] = pts[i], [x2, y2] = pts[i + 1];
    const y0 = pts[i - 1] ? pts[i - 1][1] : y1;
    const y3 = pts[i + 2] ? pts[i + 2][1] : y2;
    const t = (x - x1) / (x2 - x1), t2 = t * t, t3 = t2 * t;
    return 0.5 * ((2 * y1) + (-y0 + y2) * t
      + (2 * y0 - 5 * y1 + 4 * y2 - y3) * t2
      + (-y0 + 3 * y1 - 3 * y2 + y3) * t3);
  };
}

// 腰线处的最大半宽：车头车尾收进去
const halfWidthAt = spline1d([
  [-2.315, 0.60], [-2.05, 0.775], [-1.60, 0.868], [-0.60, 0.890],
  [0.60, 0.890], [1.55, 0.868], [2.02, 0.790], [2.315, 0.61],
]);
// 车顶/发动机盖/行李箱盖的中线高度：这条决定了侧面剪影，是「像不像卡罗拉」的主心骨
const topYAt = spline1d([
  [-2.315, 1.010], [-2.05, 1.088], [-1.72, 1.100], [-1.52, 1.132],
  [-1.02, 1.404], [-0.55, 1.437], [0.02, 1.435], [0.32, 1.421],
  [0.72, 1.268], [1.00, 1.062], [1.30, 1.020], [1.72, 0.988],
  [2.05, 0.945], [2.315, 0.880],
]);
// 车顶（或盖板）中线附近的半宽
const topHalfWAt = spline1d([
  [-2.315, 0.50], [-2.05, 0.660], [-1.52, 0.735], [-1.02, 0.700],
  [-0.55, 0.706], [0.32, 0.700], [1.00, 0.760], [1.72, 0.790],
  [2.05, 0.720], [2.315, 0.52],
]);
const BELT_Y = spline1d([[-2.315, 0.96], [-1.5, 1.045], [0.2, 1.012], [1.4, 0.985], [2.315, 0.94]]);
const SILL_Y = 0.335;

// 某个纵向站位上的横截面：v 从 0（门槛底）到 1（车顶中线）
function sectionAt(x, v) {
  const hw = halfWidthAt(x), rhw = Math.min(topHalfWAt(x), hw), ty = topYAt(x), by = Math.min(BELT_Y(x), ty - 0.01);
  // 控制点：门槛 → 侧面 → 腰线最外点 → 侧窗内收 → 肩线 → 顶中线
  const P = [
    [hw * 0.815, SILL_Y],
    [hw * 0.965, by - 0.30],
    [hw, by - 0.06],
    [rhw * 1.035, by + Math.min(0.16, (ty - by) * 0.42)],
    [rhw, ty - 0.055],
    [rhw * 0.60, ty],
    [0, ty + 0.010],
  ];
  const s = v * (P.length - 1), i = Math.min(P.length - 2, Math.floor(s)), t = s - i;
  const p0 = P[Math.max(0, i - 1)], p1 = P[i], p2 = P[i + 1], p3 = P[Math.min(P.length - 1, i + 2)];
  const cr = (a, b, c, d) => {
    const t2 = t * t, t3 = t2 * t;
    return 0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3);
  };
  return [cr(p0[0], p1[0], p2[0], p3[0]), cr(p0[1], p1[1], p2[1], p3[1])];
}

// 轮拱：判断点是否落在轮口里（挖圆孔用）
const ARCH = [{ x: 1.35, r: 0.415 }, { x: -1.35, r: 0.415 }];
function inArch(x, y) {
  for (const a of ARCH) {
    const dy = y - 0.325;
    if (dy > -0.02 && Math.hypot(x - a.x, dy) < a.r) return true;
    if (dy <= -0.02 && Math.abs(x - a.x) < a.r) return true;
  }
  return false;
}

// 从车身曲面上切一片：x∈[x0,x1]、v∈[v0,v1]。side='lh'|'rh'|'both'
// arch=true 时挖掉轮拱。返回单层壳（DoubleSide 渲染），覆盖件本来就是薄钣金。
function shellGeo(key, x0, x1, v0, v1, side, opt) {
  const o = opt || {};
  return cached(`sh|${key}|${side}`, () => {
    const NX = o.nx || 26, NV = o.nv || 10;
    const sides = side === 'both' ? [1, -1] : [side === 'rh' ? -1 : 1];
    const pos = [], idx = [];
    for (const sg of sides) {
      const base = pos.length / 3;
      for (let i = 0; i <= NX; i++) {
        const x = x0 + (x1 - x0) * (i / NX);
        for (let j = 0; j <= NV; j++) {
          const v = v0 + (v1 - v0) * (j / NV);
          const [z, y] = sectionAt(x, v);
          pos.push(x, y, z * sg);
        }
      }
      for (let i = 0; i < NX; i++) {
        for (let j = 0; j < NV; j++) {
          const a = base + i * (NV + 1) + j, b = a + NV + 1;
          if (o.arch) {
            const xc = x0 + (x1 - x0) * ((i + 0.5) / NX);
            const [, yc] = sectionAt(xc, v0 + (v1 - v0) * ((j + 0.5) / NV));
            if (inArch(xc, yc)) continue;
          }
          if (sg > 0) idx.push(a, b, a + 1, b, b + 1, a + 1);
          else idx.push(a, a + 1, b, b, a + 1, b + 1);
        }
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setIndex(idx);
    g.computeVertexNormals();
    // 几何体按整车坐标生成，摆放表里一律给 T(0,0,0)
    return g;
  });
}

// 轮胎：旋转成型，带圆肩和胎壁弧度，不再是圆柱
function tireGeo() {
  return cached('tire2', () => {
    const R = CAR.wheelR, w = CAR.wheelW / 2, rimR = 0.203;
    const p = [];
    p.push(new THREE.Vector2(rimR, -w));
    p.push(new THREE.Vector2(R * 0.80, -w * 1.02));
    p.push(new THREE.Vector2(R * 0.965, -w * 0.80));
    p.push(new THREE.Vector2(R, -w * 0.52));
    p.push(new THREE.Vector2(R, w * 0.52));
    p.push(new THREE.Vector2(R * 0.965, w * 0.80));
    p.push(new THREE.Vector2(R * 0.80, w * 1.02));
    p.push(new THREE.Vector2(rimR, w));
    const g = new THREE.LatheGeometry(p, 34);
    g.rotateX(Math.PI / 2);
    g.computeVertexNormals();
    return g;
  });
}

// 轮辋：轮辐 + 轮缘，示意即可但要有辐条
function rimGeo2() {
  return cached('rim2', () => {
    const parts = [];
    const rimR = 0.203, w = CAR.wheelW;
    const lip = new THREE.TorusGeometry(rimR, 0.022, 8, 30);
    lip.rotateY(Math.PI / 2); lip.translate(0, 0, 0);
    parts.push(lip);
    const dish = new THREE.CylinderGeometry(rimR * 0.97, rimR * 0.90, 0.030, 30);
    dish.rotateZ(Math.PI / 2); dish.translate(-w * 0.16, 0, 0);
    parts.push(dish);
    const hub = new THREE.CylinderGeometry(0.055, 0.055, 0.060, 16);
    hub.rotateZ(Math.PI / 2); parts.push(hub);
    for (let i = 0; i < 5; i++) {
      const a = (i / 5) * Math.PI * 2;
      const sp = new THREE.BoxGeometry(0.026, 0.150, 0.052);
      sp.translate(0, 0.108, 0); sp.rotateX(a); sp.translate(-w * 0.15, 0, 0);
      parts.push(sp);
    }
    const g = mergeGeos(parts);
    g.computeVertexNormals();
    return g;
  });
}

// ───────────────────────────────────────────────── 槽位识别：从 name_en 认出这是什么件
// 顺序即优先级，具体的必须排在笼统的前面（"Windshield Wiper Arm" 不能被 windshield 抢走）
const SLOT_RULES = [
  [/wiper\s+arm|wiper\s+blade/i, 'wiperarm'],
  [/wiper\s+motor/i, 'wipermotor'],
  [/washer\s+tank/i, 'washertank'],
  [/wind\s*shield\s+glass|windscreen/i, 'windshield'],
  [/back\s+window|rear\s+window\s+glass/i, 'backwindow'],
  [/door\s+glass/i, 'doorglass'],
  [/door\s+trim/i, 'doortrim'],
  [/door\s+panel|door\s+shell|door\s+sub-?assembly/i, 'door'],
  [/hood/i, 'hood'],
  [/front\s+fender|fender/i, 'fender'],
  [/bumper\s+cover|bumper\s+assembly/i, 'bumpercover'],
  [/bumper\s+reinforcement|bumper\s+stay|bumper\s+beam/i, 'bumperreinf'],
  [/grille\s+upper|upper\s+grille/i, 'grilleupper'],
  [/grille/i, 'grillelower'],
  [/radiator\s+support/i, 'radsupport'],
  [/roof\s+panel/i, 'roof'],
  [/luggage\s+compartment\s+door|trunk\s+lid|deck\s+lid|back\s+door/i, 'trunklid'],
  [/quarter\s+panel/i, 'quarter'],
  [/rocker\s+panel|side\s+member|sill/i, 'rocker'],
  [/a-?pillar|front\s+body\s+pillar/i, 'pillara'],
  [/b-?pillar|center\s+body\s+pillar/i, 'pillarb'],
  [/c-?pillar|rear\s+body\s+pillar/i, 'pillarc'],
  [/mirror/i, 'mirror'],
  [/spoiler/i, 'spoiler'],
  [/floor\s+panel|floor\s+pan/i, 'floor'],
  [/dash\s+panel|fire\s*wall|cowl/i, 'firewall'],
  [/instrument\s+panel/i, 'instrpanel'],
  [/console/i, 'console'],
  [/seat\s+cushion/i, 'seatcushion'],
  [/seat\s+back/i, 'seatback'],
  [/seat/i, 'seat'],
  [/head\s*lin(ing|er)/i, 'headliner'],
  [/carpet/i, 'carpet'],

  [/head\s*lamp|head\s*light/i, 'headlamp'],
  [/rear\s+combination\s+lamp|tail\s*lamp|tail\s*light/i, 'taillamp'],
  [/fog\s+lamp/i, 'foglamp'],
  [/high\s+mounted\s+stop\s+lamp|third\s+brake/i, 'stoplamp'],
  [/license\s+plate\s+lamp/i, 'licenselamp'],
  [/battery/i, 'battery'],
  [/relay\s+block|fuse\s+box|junction\s+block/i, 'fusebox'],
  [/alternator|generator/i, 'alternator'],
  [/starter/i, 'starter'],
  [/horn/i, 'horn'],
  [/cooling\s+fan|radiator\s+fan|fan\s+assembly/i, 'coolingfan'],
  [/radio\s+receiver|display\s+audio|head\s+unit|multimedia/i, 'headunit'],
  [/speaker/i, 'speaker'],
  [/combination\s+meter|meter\s+assembly|instrument\s+cluster/i, 'meter'],
  [/recognition\s+camera|front\s+camera/i, 'camera'],
  [/radar/i, 'radar'],
  [/skid\s+control|abs/i, 'absunit'],
  [/computer|control\s+module|\becu\b/i, 'ecu'],

  [/cylinder\s+block|engine\s+block|short\s+block/i, 'block'],
  [/cylinder\s+head\s+cover|head\s+cover|valve\s+cover/i, 'headcover'],
  [/cylinder\s+head/i, 'cylhead'],
  [/oil\s+pan/i, 'oilpan'],
  [/intake\s+manifold/i, 'intakemani'],
  [/exhaust\s+manifold/i, 'exhmani'],
  [/throttle/i, 'throttle'],
  [/air\s+cleaner\s+case|air\s+cleaner\s+assembly|air\s+cleaner$/i, 'aircleaner'],
  [/air\s+cleaner|inlet\s+duct|intake\s+duct/i, 'intakeduct'],
  [/condenser/i, 'condenser'],
  [/radiator/i, 'radiator'],
  [/upper\s+hose/i, 'hoseup'],
  [/lower\s+hose/i, 'hoselo'],
  [/reservoir/i, 'reservoir'],
  [/water\s+pump/i, 'waterpump'],
  [/fuel\s+tank(?!\s+protector)/i, 'fueltank'],
  [/fuel\s+pump/i, 'fuelpump'],
  [/front\s+pipe|exhaust\s+front/i, 'exhfront'],
  [/catalytic/i, 'catalytic'],
  [/muffler|tail\s+pipe/i, 'muffler'],
  [/compressor/i, 'accomp'],
  [/heater\s*&?\s*cool|hvac|evaporator/i, 'hvac'],
  [/mounting\s+insulator|engine\s+mount|transmission\s+mount/i, 'engmount'],

  [/transaxle|transmission\s+case|gearbox\s+case/i, 'transaxle'],
  [/drive\s+shaft|half\s+shaft|axle\s+shaft/i, 'driveshaft'],
  [/strut|shock\s+absorber\s+strut/i, 'strut'],
  [/rear\s+shock|shock\s+absorber/i, 'rearshock'],
  [/coil\s+spring/i, 'coilspring'],
  [/lower\s+suspension\s+arm|control\s+arm|suspension\s+arm/i, 'lowerarm'],
  [/steering\s+knuckle|knuckle/i, 'knuckle'],
  [/axle\s+hub|wheel\s+hub|hub\s*&?\s*bearing/i, 'hub'],
  [/brake\s+disc|disc\s+rotor|brake\s+rotor/i, 'brakedisc'],
  [/brake\s+caliper|disc\s+brake\s+caliper/i, 'caliper'],
  [/master\s+cylinder|brake\s+booster/i, 'brakemaster'],
  [/brake\s+pedal|pedal/i, 'pedal'],
  [/steering\s+gear|steering\s+rack/i, 'steergear'],
  [/steering\s+column/i, 'steercolumn'],
  [/steering\s+wheel/i, 'steerwheel'],
  [/\btire\b|\btyre\b/i, 'tire'],
  [/disc\s+wheel|\bwheel\b|\brim\b/i, 'rim'],
  [/torsion\s+beam|rear\s+axle\s+beam/i, 'torsionbeam'],
  [/crossmember|sub\s*frame/i, 'subframe'],
  [/stabilizer\s+bar/i, 'stabar'],
  [/under\s*cover|under\s*shield|engine\s+under/i, 'undercover'],
  [/mudguard|mud\s*flap/i, 'mudguard'],

  // ── 丰田官方目录（EPC）的倒装写法专用规则。
  // 官方名是「主体在前、定语在后」：Panel Sub-Assy, Front Door, RH。
  // slotOf 会先拿原名试上面的自然语序规则，不中再拿逗号倒装后的名字试一遍，
  // 仍不中才落到下面这批按官方写法直接写的规则。全部只指向 PLACE 里已有的槽位。
  [/disc\s+brake\s+cylinder|cylinder\s+assy.*disc\s+brake|disc\s+brake.*cylinder/i, 'caliper'],
  [/pad\s+kit|disc\s+brake\s+pad|brake\s+pad/i, 'caliper'],
  [/flexible\s+hose|brake\s+hose|hose,?\s*flexible/i, 'caliper'],
  [/^\s*(front|rear)\s+disc\b|\bdisc,\s*(front|rear)/i, 'brakedisc'],
  [/hub\s+bolt|bolt,?\s*hub|hub\s+nut|nut,?\s*hub|hub\s+sub-?assy/i, 'hub'],
  [/wheel\s+speed\s+sensor|speed\s+sensor|sensor,?\s*speed/i, 'knuckle'],
  [/tie\s+rod/i, 'steergear'],
  [/steering\s+intermediate|intermediate\s+shaft/i, 'steercolumn'],
  [/shift\s+lever|lever\s+assy,?\s*shift/i, 'console'],
  [/parking\s+brake\s+cable|cable\s+assy,?\s*parking/i, 'torsionbeam'],
  [/trailing\s+arm|arm\s+assy,?\s*trailing/i, 'lowerarm'],
  [/ball\s+joint/i, 'lowerarm'],
  [/suspension\s+support|support\s+sub-?assy,?\s*front\s+suspension/i, 'strut'],
  [/rear\s+suspension\s+member|suspension\s+member/i, 'subframe'],
  [/differential|drive\s+pinion|ring\s+gear|planetary|torque\s+converter|transmission\s+valve|valve\s+body|input\s+shaft|output\s+shaft|counter\s+gear|shift\s+fork|shift\s*&?\s*select|synchronizer|gear\s+sub-?assy,?\s*\d|front\s+oil\s+pump/i, 'transaxle'],
  [/clutch|flywheel/i, 'transaxle'],
  [/crankshaft|piston|connecting\s+rod|\bcamshaft\b|valve,\s*(intake|exhaust)|timing\s+chain|timing\s+belt|camshaft\s+timing|oil\s+pump|oil\s+filter|balance\s+shaft|engine\s+assy|partial\s+engine|vacuum\s+pump/i, 'block'],
  [/spark|ignition\s+coil/i, 'cylhead'],
  [/injector|fuel\s+delivery|fuel\s+rail|\begr\b/i, 'intakemani'],
  [/v-?ribbed\s+belt|tensioner|idler\s+pulley/i, 'alternator'],
  [/water\s+inlet|inlet,?\s*water|thermostat/i, 'waterpump'],
  [/fan\s+shroud|shroud,?\s*fan/i, 'coolingfan'],
  [/manifold\s+stay|stay,?\s*manifold/i, 'exhmani'],
  [/air\s+fuel\s+ratio|oxygen\s+sensor|\bo2\s+sensor/i, 'exhfront'],
  [/exhaust,?\s*tail|tail\s+pipe/i, 'muffler'],
  [/pipe\s+assy,?\s*exhaust|exhaust\s+pipe/i, 'exhfront'],
  [/radio|display\s+audio|receiver\s+assy/i, 'headunit'],
  [/amplifier|stereo/i, 'speaker'],
  [/wiper\s+link|link\s+assy,?\s*wiper/i, 'wiperarm'],
  [/washer.*(motor|pump|jar)|jar\s+assy,?\s*windshield/i, 'washertank'],
  [/blower/i, 'hvac'],
  [/clean\s+air|cabin\s+air|filter,?\s*clean/i, 'hvac'],
  [/heater\s+to\s+register|duct\s+sub-?assy/i, 'hvac'],
  [/power\s+window|window\s+regulator|regulator\s+sub-?assy.*window/i, 'doortrim'],
  [/door\s+lock|lock\s+assy.*door/i, 'doortrim'],
  [/weatherstrip/i, 'door'],
  [/door\s+hinge|hinge\s+assy.*door/i, 'door'],
  [/outside\s+handle|handle\s+assy.*door/i, 'door'],
  [/belt\s+moulding|moulding\s+assy.*belt/i, 'door'],
  [/moulding.*windshield|windshield.*moulding/i, 'windshield'],
  [/windshield\s+header|header.*windshield/i, 'roof'],
  [/sliding\s+roof|sun\s*roof|moon\s*roof/i, 'roof'],
  [/led\s+illumination|daytime\s+running|\bdrl\b/i, 'headlamp'],
  [/lamp\s+assy,?\s*rear|rear\s+lamp/i, 'taillamp'],
  [/television|rear\s+view\s+camera|camera\s+assy.*rear/i, 'trunklid'],
  [/belt\s+anchor|seat\s+belt|belt\s+outer/i, 'pillarb'],
  [/pillar\s+garnish|garnish,?\s*center\s+pillar/i, 'pillarb'],
  [/floor\s+cross|cross\s+member/i, 'floor'],
  [/upper\s+back\s+panel|panel\s+sub-?assy,?\s*upper\s+back/i, 'quarter'],
  [/package\s+tray|tray\s+trim/i, 'quarter'],
  [/\bjack\b|wrench|tool\s+box/i, 'quarter'],
  [/check\s+valve/i, 'brakemaster'],
];

// 丰田官方零件名是逗号倒装的：把逗号段前后翻过来，自然语序的规则就能认。
// 「Panel Sub-Assy, Front Door, RH」→「RH Front Door Panel Sub-Assy」
function invertedName(n) {
  const segs = n.split(',').map((s) => s.trim()).filter(Boolean);
  return segs.length > 1 ? segs.reverse().join(' ') : n;
}

function slotOf(part) {
  const n = part.name_en || '';
  let base = null;
  for (const [re, s] of SLOT_RULES) { if (re.test(n)) { base = s; break; } }
  if (!base) {
    const inv = invertedName(n);
    if (inv !== n) for (const [re, s] of SLOT_RULES) { if (re.test(inv)) { base = s; break; } }
  }
  let side = null;
  if (/\blh\b|\bleft\b/i.test(n)) side = 'lh';
  else if (/\brh\b|\bright\b/i.test(n)) side = 'rh';
  let pos = null;
  if (/\bfront\b/i.test(n)) pos = 'front';
  else if (/\brear\b|\bback\b/i.test(n)) pos = 'rear';
  return { base, side, pos };
}

// ───────────────────────────────────────────────── 摆放表
// t: [x, y, z, rx, ry, rz]，z 一律按左侧（LH）写，右侧自动镜像
// f(ctx) 形式的条目会拿到 {pos, side, qty}，用来区分前后门这种同槽位不同位置的件
const T = (x, y, z, rx, ry, rz) => [x, y, z, rx || 0, ry || 0, rz || 0];

const PLACE = {
  // ── 车身外覆盖件：全部从统一车身曲面 shellGeo 上切片，几何体已在整车坐标里，t 一律给 0
  hood:        { g: (c) => shellGeo('hood', 1.02, 2.08, 0.615, 1.0, 'both', { nx: 24, nv: 9 }), m: 'paint', t: [T(0, 0, 0)] },
  fender:      { g: (c) => shellGeo('fender', 1.05, 2.04, 0.02, 0.515, c.side || 'lh', { nx: 30, nv: 8, arch: true }), m: 'paint', t: [T(0, 0, 0)] },
  // 端面不封口：试过给壳的端头做扇形封口，结果更糟 —— 截面在 v=1 处两侧汇到同一点、
  // 底部又是敞开的，扇形必然折成帐篷，前脸出现一道 V 形折痕。这是几何上的死路不是参数问题。
  // 要真正封住得改成闭合截面（把 v 绕一整圈回到底），那是重写车身曲面，不在这一轮范围内。
  bumpercover: { g: (c) => (c.pos === 'rear'
                   ? shellGeo('bmpR', -2.315, -1.99, 0.0, 1.0, 'both', { nx: 14, nv: 14 })
                   : shellGeo('bmpF', 1.99, 2.315, 0.0, 1.0, 'both', { nx: 14, nv: 14 })), m: 'paint', t: [T(0, 0, 0)] },
  bumperreinf: { g: () => boxGeo(0.07, 0.14, 1.36), m: 'metal',
                 f: (c) => [T(c.pos === 'rear' ? -2.02 : 1.99, 0.62, 0)] },
  grilleupper: { g: () => rboxGeo(0.05, 0.085, 0.80, 0.025), m: 'chrome', t: [T(2.175, 0.860, 0)] },
  grillelower: { g: () => rboxGeo(0.05, 0.20, 0.88, 0.04), m: 'dark', t: [T(2.185, 0.480, 0)] },
  radsupport:  { g: () => boxGeo(0.06, 0.60, 1.20), m: 'metal', t: [T(1.90, 0.68, 0)] },
  door:        { g: (c) => (c.pos === 'rear'
                   ? shellGeo('doorR', -0.96, 0.045, 0.02, 0.515, c.side || 'lh', { nx: 26, nv: 8 })
                   : shellGeo('doorF', 0.055, 1.04, 0.02, 0.515, c.side || 'lh', { nx: 26, nv: 8 })), m: 'paint', t: [T(0, 0, 0)] },
  doorglass:   { g: (c) => (c.pos === 'rear'
                   ? shellGeo('dglsR', -0.94, 0.02, 0.545, 0.722, c.side || 'lh', { nx: 20, nv: 5 })
                   : shellGeo('dglsF', 0.06, 1.00, 0.545, 0.722, c.side || 'lh', { nx: 20, nv: 5 })), m: 'glass', t: [T(0, 0, 0)] },
  doortrim:    { g: () => rboxGeo(0.90, 0.44, 0.025, 0.05), m: 'trim',
                 f: () => [T(0.55, 0.74, 0.66), T(-0.46, 0.74, 0.66), T(0.55, 0.74, -0.66), T(-0.46, 0.74, -0.66)] },
  windshield:  { g: () => shellGeo('wsh', 0.60, 1.02, 0.505, 1.0, 'both', { nx: 14, nv: 10 }), m: 'glass', t: [T(0, 0, 0)] },
  backwindow:  { g: () => shellGeo('bwin', -1.53, -1.02, 0.505, 1.0, 'both', { nx: 14, nv: 10 }), m: 'glass', t: [T(0, 0, 0)] },
  roof:        { g: () => shellGeo('roof', -1.03, 0.62, 0.715, 1.0, 'both', { nx: 24, nv: 8 }), m: 'paint', t: [T(0, 0, 0)] },
  trunklid:    { g: () => shellGeo('trunk', -2.06, -1.51, 0.615, 1.0, 'both', { nx: 14, nv: 9 }), m: 'paint', t: [T(0, 0, 0)] },
  quarter:     { g: (c) => shellGeo('qtr', -2.02, -0.94, 0.02, 0.515, c.side || 'lh', { nx: 30, nv: 8, arch: true }), m: 'paint', t: [T(0, 0, 0)] },
  rocker:      { g: (c) => shellGeo('rock', -1.58, 1.58, 0.0, 0.085, c.side || 'lh', { nx: 26, nv: 3 }), m: 'paint', t: [T(0, 0, 0)] },
  pillara:     { g: (c) => shellGeo('pA', 0.30, 1.03, 0.500, 0.575, c.side || 'lh', { nx: 14, nv: 3 }), m: 'trim', t: [T(0, 0, 0)] },
  pillarb:     { g: (c) => shellGeo('pB', -0.04, 0.09, 0.500, 0.900, c.side || 'lh', { nx: 4, nv: 8 }), m: 'trim', t: [T(0, 0, 0)] },
  pillarc:     { g: (c) => shellGeo('pC', -1.54, -0.93, 0.500, 0.590, c.side || 'lh', { nx: 14, nv: 3 }), m: 'trim', t: [T(0, 0, 0)] },
  mirror:      { g: () => rboxGeo(0.11, 0.09, 0.20, 0.04), m: 'trim', t: [T(0.99, 1.055, 0.925)] },
  spoiler:     { g: () => boxGeo(0.16, 0.035, 1.30), m: 'paint', t: [T(-1.98, 1.075, 0, 0, 0, 0.16)] },
  mudguard:    { g: () => boxGeo(0.03, 0.18, 0.16), m: 'dark',
                 f: () => [T(1.00, 0.235, 0.66), T(-1.68, 0.235, 0.66), T(1.00, 0.235, -0.66), T(-1.68, 0.235, -0.66)] },
  floor:       { g: () => boxGeo(1.34, 0.035, 1.38), m: 'metal',
                 f: (c) => [T(c.pos === 'rear' ? -1.10 : 0.56, 0.350, 0)] },
  firewall:    { g: () => boxGeo(0.05, 0.62, 1.50), m: 'metal', t: [T(1.03, 0.70, 0)] },
  instrpanel:  { build: buildInstrPanel, t: [T(0.84, 0.98, 0)] },
  console:     { g: () => rboxGeo(0.70, 0.26, 0.30, 0.05), m: 'trim', t: [T(0.42, 0.55, 0)] },
  seat:        { g: () => null, build: buildSeat, m: 'trim',
                 f: (c) => [T(0.30, 0.42, c.side === 'rh' ? -0.37 : 0.37)] },
  seatcushion: { g: () => rboxGeo(0.48, 0.16, 1.32, 0.06), m: 'trim', t: [T(-0.60, 0.50, 0)] },
  seatback:    { g: () => rboxGeo(0.14, 0.58, 1.32, 0.06), m: 'trim', t: [T(-0.86, 0.82, 0, 0, 0, 0.14)] },
  headliner:   { g: () => rboxGeo(1.56, 0.02, 1.34, 0.12), m: 'plastic', t: [T(0.02, 1.385, 0)] },
  carpet:      { g: () => boxGeo(2.30, 0.02, 1.50), m: 'dark', t: [T(-0.20, 0.375, 0)] },

  // ── 电气
  headlamp:    { build: buildHeadlampGeo, t: [T(1.985, 0.905, 0.545)] },
  taillamp:    { g: () => rboxGeo(0.10, 0.135, 0.30, 0.035), m: 'lampr', t: [T(-2.00, 0.945, 0.585)] },
  foglamp:     { g: () => cylGeo(0.055, 0.055, 0.07, 12, 'x'), m: 'lampw',
                 f: () => [T(2.30, 0.42, 0.60), T(2.30, 0.42, -0.60)] },
  stoplamp:    { g: () => boxGeo(0.05, 0.03, 0.66), m: 'lampr', t: [T(-1.19, 1.375, 0)] },
  licenselamp: { g: () => boxGeo(0.03, 0.025, 0.07), m: 'lampw',
                 f: () => [T(-2.33, 0.72, 0.09), T(-2.33, 0.72, -0.09)] },
  battery:     { build: buildBattery, t: [T(1.84, 0.78, 0.50)] },
  fusebox:     { g: () => boxGeo(0.20, 0.14, 0.15), m: 'dark', t: [T(1.82, 0.80, -0.48)] },
  alternator:  { build: buildAlternator, t: [T(1.60, 0.56, -0.20)] },
  starter:     { g: () => cylGeo(0.055, 0.055, 0.17, 12, 'x'), m: 'metal', t: [T(1.14, 0.46, 0.26)] },
  horn:        { g: () => cylGeo(0.045, 0.045, 0.04, 12, 'x'), m: 'dark',
                 f: () => [T(2.02, 0.55, 0.34), T(2.02, 0.55, -0.34)] },
  coolingfan:  { g: () => buildFanGeo(), m: 'dark', t: [T(1.74, 0.66, 0)] },
  headunit:    { g: () => boxGeo(0.06, 0.17, 0.28), m: 'dark', t: [T(0.74, 0.96, 0)] },
  speaker:     { g: () => cylGeo(0.075, 0.055, 0.05, 14, 'z'), m: 'dark',
                 f: (c) => (c.pos === 'rear'
                   ? [T(-0.50, 0.56, 0.83), T(-0.50, 0.56, -0.83)]
                   : [T(0.42, 0.56, 0.83), T(0.42, 0.56, -0.83)]) },
  meter:       { g: () => rboxGeo(0.07, 0.14, 0.30, 0.03), m: 'dark', t: [T(0.80, 1.06, 0.36)] },
  camera:      { g: () => boxGeo(0.07, 0.05, 0.09), m: 'dark', t: [T(0.74, 1.31, 0)] },
  radar:       { g: () => boxGeo(0.05, 0.10, 0.11), m: 'dark', t: [T(2.19, 0.47, 0)] },
  absunit:     { g: () => boxGeo(0.13, 0.13, 0.11), m: 'metal', t: [T(1.72, 0.72, 0.42)] },
  ecu:         { g: () => boxGeo(0.15, 0.05, 0.13), m: 'metal', t: [T(1.70, 0.74, -0.32)] },
  wipermotor:  { g: () => cylGeo(0.05, 0.05, 0.09, 12, 'z'), m: 'dark', t: [T(1.00, 1.02, 0.46)] },
  wiperarm:    { g: () => boxGeo(0.30, 0.010, 0.020), m: 'dark',
                 f: () => [T(1.03, 0.995, 0.28, 0, 0.18, -0.30), T(1.03, 0.995, -0.20, 0, -0.18, -0.30)] },
  washertank:  { g: () => boxGeo(0.16, 0.24, 0.12), m: 'plastic', t: [T(1.76, 0.62, -0.56)] },

  // ── 发动机 / 燃油
  // 机舱天花板 = 机盖下表面 ≈ y 0.95，下面这些的顶都必须低于它，不然会戳出机盖
  block:       { build: buildEngineBlock, t: [T(1.36, 0.52, 0)] },
  cylhead:     { build: buildCylHead, t: [T(1.36, 0.765, 0)] },
  headcover:   { build: buildHeadCover, t: [T(1.36, 0.875, 0)] },
  oilpan:      { g: () => rboxGeo(0.36, 0.13, 0.40, 0.04), m: 'metal', t: [T(1.34, 0.28, 0)] },
  intakemani:  { build: buildIntakeMani, t: [T(1.12, 0.78, 0)] },
  exhmani:     { build: buildExhMani, t: [T(1.62, 0.58, 0)] },
  throttle:    { g: () => cylGeo(0.045, 0.045, 0.08, 12, 'x'), m: 'metal', t: [T(0.98, 0.80, 0)] },
  aircleaner:  { g: () => rboxGeo(0.26, 0.16, 0.30, 0.04), m: 'dark', t: [T(1.06, 0.84, 0.42)] },
  intakeduct:  { g: () => cylGeo(0.05, 0.05, 0.34, 10, 'x'), m: 'dark', t: [T(1.36, 0.86, 0.45)] },
  radiator:    { build: buildRadiator, t: [T(1.90, 0.66, 0)] },
  condenser:   { g: () => boxGeo(0.03, 0.40, 0.62), m: 'metal', t: [T(1.96, 0.64, 0)] },
  hoseup:      { g: () => cylGeo(0.026, 0.026, 0.36, 10, 'x'), m: 'rubber', t: [T(1.68, 0.80, 0.22)] },
  hoselo:      { g: () => cylGeo(0.026, 0.026, 0.40, 10, 'x'), m: 'rubber', t: [T(1.66, 0.44, -0.20)] },
  reservoir:   { g: () => cylGeo(0.055, 0.055, 0.20, 12, 'y'), m: 'plastic', t: [T(1.80, 0.72, 0.34)] },
  waterpump:   { g: () => cylGeo(0.06, 0.06, 0.07, 12, 'x'), m: 'metal', t: [T(1.58, 0.66, 0.12)] },
  engmount:    { g: () => boxGeo(0.11, 0.10, 0.12), m: 'rubber',
                 f: (c) => [T(1.36, 0.80, c.side === 'rh' ? -0.44 : 0.44)] },
  fueltank:    { g: () => rboxGeo(0.72, 0.24, 1.00, 0.07), m: 'plastic', t: [T(-0.78, 0.42, 0)] },
  fuelpump:    { g: () => cylGeo(0.055, 0.055, 0.10, 12, 'y'), m: 'dark', t: [T(-0.72, 0.58, 0.16)] },
  exhfront:    { g: () => cylGeo(0.032, 0.032, 0.70, 10, 'x'), m: 'metal', t: [T(1.05, 0.30, 0.06)] },
  catalytic:   { g: () => cylGeo(0.055, 0.055, 0.30, 12, 'x'), m: 'metal', t: [T(0.30, 0.28, 0.02)] },
  muffler:     { g: () => buildMufflerGeo(), m: 'metal', t: [T(-1.88, 0.32, -0.30)] },
  accomp:      { g: () => cylGeo(0.065, 0.065, 0.14, 12, 'x'), m: 'metal', t: [T(1.50, 0.40, 0.22)] },
  hvac:        { g: () => rboxGeo(0.34, 0.32, 0.50, 0.05), m: 'dark', t: [T(0.92, 0.72, 0)] },

  // ── 传动 / 底盘
  transaxle:   { build: buildTransaxle, t: [T(1.36, 0.55, 0.42)] },
  driveshaft:  { g: () => cylGeo(0.024, 0.024, 0.42, 10, 'z'), m: 'metal',
                 f: (c) => [T(1.35, 0.335, c.side === 'rh' ? -0.55 : 0.55)] },
  strut:       { build: buildStrut, t: [T(1.35, 0.66, 0.66, 0, 0, 0.10)] },
  coilspring:  { g: () => coilGeo(0.072, 0.30, 6, 0.013), m: 'metal',
                 f: (c) => (c.pos === 'rear'
                   ? [T(-1.33, 0.46, 0.62), T(-1.33, 0.46, -0.62)]
                   : [T(1.35, 0.68, 0.66), T(1.35, 0.68, -0.66)]) },
  rearshock:   { g: () => cylGeo(0.028, 0.028, 0.36, 10, 'y'), m: 'metal',
                 f: () => [T(-1.30, 0.52, 0.70, 0, 0, 0.14), T(-1.30, 0.52, -0.70, 0, 0, -0.14)] },
  lowerarm:    { build: buildLowerArm, t: [T(1.24, 0.30, 0.56, 0, -0.30, 0)] },
  knuckle:     { g: () => boxGeo(0.10, 0.22, 0.09), m: 'metal', t: [T(1.35, 0.36, 0.68)] },
  hub:         { g: () => cylGeo(0.055, 0.055, 0.07, 14, 'z'), m: 'metal',
                 f: (c) => (c.pos === 'rear'
                   ? [T(-1.35, 0.32, 0.70), T(-1.35, 0.32, -0.70)]
                   : [T(1.35, 0.32, 0.70), T(1.35, 0.32, -0.70)]) },
  brakedisc:   { build: buildBrakeDisc,
                 f: (c) => (c.pos === 'rear'
                   ? [T(-1.35, 0.32, 0.735), T(-1.35, 0.32, -0.735)]
                   : [T(1.35, 0.32, 0.735), T(1.35, 0.32, -0.735)]) },
  caliper:     { build: buildCaliper,
                 f: (c) => (c.pos === 'rear'
                   ? [T(-1.47, 0.42, 0.735), T(-1.47, 0.42, -0.735)]
                   : [T(1.23, 0.42, 0.735), T(1.23, 0.42, -0.735)]) },
  brakemaster: { g: () => cylGeo(0.055, 0.055, 0.18, 12, 'x'), m: 'metal', t: [T(1.20, 0.80, 0.40)] },
  pedal:       { g: () => boxGeo(0.06, 0.14, 0.05), m: 'dark', t: [T(0.86, 0.48, 0.30, 0, 0, 0.25)] },
  steergear:   { g: () => cylGeo(0.028, 0.028, 1.06, 10, 'z'), m: 'metal', t: [T(1.05, 0.40, 0)] },
  steercolumn: { g: () => cylGeo(0.024, 0.024, 0.44, 10, 'x'), m: 'metal', t: [T(0.66, 0.90, 0.36, 0, 0, 0.58)] },
  steerwheel:  { build: buildSteerWheel, t: [T(0.46, 1.05, 0.36, 0, Math.PI / 2, 1.02)] },
  rim:         { g: () => rimGeo2(), m: 'alloy',
                 f: () => [T(1.35, 0.32, 0.755), T(1.35, 0.32, -0.755), T(-1.35, 0.32, 0.755), T(-1.35, 0.32, -0.755)] },
  tire:        { g: () => tireGeo(), m: 'rubber',
                 f: () => [T(1.35, 0.32, 0.755), T(1.35, 0.32, -0.755), T(-1.35, 0.32, 0.755), T(-1.35, 0.32, -0.755)] },
  torsionbeam: { g: () => boxGeo(0.16, 0.11, 1.30), m: 'metal', t: [T(-1.36, 0.34, 0)] },
  subframe:    { g: () => buildFrameGeo(0.80, 1.20, 0.06), m: 'metal', t: [T(1.24, 0.28, 0)] },
  stabar:      { g: () => cylGeo(0.014, 0.014, 1.16, 8, 'z'), m: 'metal', t: [T(1.12, 0.29, 0)] },
  undercover:  { g: () => boxGeo(1.00, 0.02, 1.30), m: 'dark', t: [T(1.40, 0.22, 0)] },
};

// ── 几个需要多块几何体的件，单独造
function buildSeat(matmap) {
  const g = new THREE.Group();
  const m = matmap.trim;
  const cushion = new THREE.Mesh(rboxGeo(0.48, 0.12, 0.50, 0.05), m); cushion.position.set(0, 0.10, 0);
  const back = new THREE.Mesh(rboxGeo(0.13, 0.56, 0.48, 0.05), m); back.position.set(-0.22, 0.42, 0); back.rotation.z = 0.14;
  const rest = new THREE.Mesh(rboxGeo(0.11, 0.16, 0.24, 0.04), m); rest.position.set(-0.26, 0.76, 0);
  g.add(cushion, back, rest);
  return g;
}

function buildFanGeo() {
  return cached('fan', () => {
    const shroud = new THREE.CylinderGeometry(0.21, 0.21, 0.07, 16, 1, true).rotateZ(Math.PI / 2);
    const hub = new THREE.CylinderGeometry(0.05, 0.05, 0.09, 10).rotateZ(Math.PI / 2);
    return mergeGeos([shroud, hub]);
  });
}

// 保险杠皮：中间一块 + 两侧向后折的翼子，包住车头/车尾。
// 用一块平板的话，车头看着就是「前面立了块牌子」，不像车。
// d 进深 / h 高 / w 中段宽 / lx 翼子往后包多长 / lz 翼子往外张多少 / back=+1 车头(往 -X 包) -1 车尾
function buildBumperGeo(d, h, w, lx, lz, back) {
  return cached(`bump|${d}|${h}|${w}|${lx}|${lz}|${back}`, () => {
    const parts = [new THREE.BoxGeometry(d, h, w)];
    const L = Math.hypot(lx, lz);
    for (const s of [1, -1]) {
      const th = Math.atan2(-s * lz, -back * lx);   // 让盒子的 +X 轴落在 A→B 这条线上
      const g = new THREE.BoxGeometry(L, h, d * 0.85);
      g.rotateY(th);
      g.translate(-back * lx / 2, 0, s * (w / 2 + lz / 2));
      parts.push(g);
    }
    return mergeGeos(parts);
  });
}

function buildMufflerGeo() {
  return cached('muff', () => {
    const can = new THREE.CylinderGeometry(0.115, 0.115, 0.46, 14).rotateZ(Math.PI / 2);
    const tip = new THREE.CylinderGeometry(0.032, 0.032, 0.26, 10).rotateZ(Math.PI / 2).translate(-0.34, 0.03, 0);
    return mergeGeos([can, tip]);
  });
}

function buildRimGeo() {
  return cached('rim', () => {
    const parts = [new THREE.CylinderGeometry(0.085, 0.085, 0.12, 14).rotateX(Math.PI / 2)];
    for (let i = 0; i < 5; i++) {
      const a = (i / 5) * Math.PI * 2;
      parts.push(new THREE.BoxGeometry(0.042, 0.20, 0.05)
        .translate(0, 0.115, 0).rotateZ(a).translate(0, 0, 0.028));
    }
    parts.push(new THREE.CylinderGeometry(0.215, 0.215, 0.16, 20, 1, true).rotateX(Math.PI / 2));
    return mergeGeos(parts);
  });
}

// 轮胎做成「胎面环 + 两侧胎壁圆环」，中间空着，这样轮辋才看得见。
// 实心圆柱当轮胎的话轮辋等于白建。
function buildTireGeo() {
  return cached('tire', () => {
    const R = CAR.wheelR, r = 0.215, w = CAR.wheelW;
    const tread = new THREE.CylinderGeometry(R, R, w, 22, 1, true).rotateX(Math.PI / 2);
    const sideA = new THREE.RingGeometry(r, R, 22, 1).translate(0, 0, w / 2);
    const sideB = new THREE.RingGeometry(r, R, 22, 1).rotateY(Math.PI).translate(0, 0, -w / 2);
    return mergeGeos([tread, sideA, sideB]);
  });
}

function buildFrameGeo(lx, lz, th) {
  return cached(`frame|${lx}|${lz}|${th}`, () => mergeGeos([
    new THREE.BoxGeometry(th, th, lz).translate(lx / 2, 0, 0),
    new THREE.BoxGeometry(th, th, lz).translate(-lx / 2, 0, 0),
    new THREE.BoxGeometry(lx, th, th).translate(0, 0, lz / 2),
    new THREE.BoxGeometry(lx, th, th).translate(0, 0, -lz / 2),
  ]));
}

// 手写的小合并器：只需要 position/normal，避免为了 mergeGeometries 再拉一个 addon 进 vendor
function mergeGeos(list) {
  // 注意：ExtrudeGeometry（圆角盒）是非索引几何，index 为 null。
  // 这里给它现编一份顺序索引，否则一混进来就 Cannot read properties of null。
  let vc = 0, ic = 0;
  for (const g of list) {
    vc += g.attributes.position.count;
    ic += g.index ? g.index.count : g.attributes.position.count;
  }
  const pos = new Float32Array(vc * 3), nor = new Float32Array(vc * 3);
  const idx = new Uint32Array(ic);
  let vo = 0, io = 0;
  for (const g of list) {
    const p = g.attributes.position.array, n = g.attributes.normal.array;
    pos.set(p, vo * 3); nor.set(n, vo * 3);
    const gi = g.index ? g.index.array
      : Uint32Array.from({ length: g.attributes.position.count }, (_, i) => i);
    for (let i = 0; i < gi.length; i++) idx[io + i] = gi[i] + vo;
    vo += g.attributes.position.count; io += gi.length;
    g.dispose();
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  out.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
  out.setIndex(new THREE.BufferAttribute(idx, 1));
  return out;
}

// ═════════════════════════════════════════════════ 精细零件
// 零件本身才是这个站的主角。之前它们全是圆角盒子和圆柱，炸开一看就是一堆灰疙瘩。
// 下面这些按真实结构拼：缸体有缸孔和皮带轮，进气歧管有四根弯管，制动盘是通风盘，
// 变速箱有钟形罩。都按材质合并，一个零件通常只占 1~2 个 draw call。
//
// 约定：几何体围绕零件自身原点建（+X 车头方向），摆放交给 PLACE 的 t。

// 一堆 {g, m} 按材质合并成 Group，g 必须是新建的（会被 translate/rotate 就地改写）
const builtCache = new Map();
function multi(key, M, make) {
  let pieces = builtCache.get(key);
  if (!pieces) {
    const byMat = new Map();
    for (const p of make()) {
      if (!byMat.has(p.m)) byMat.set(p.m, []);
      byMat.get(p.m).push(p.g);
    }
    pieces = [];
    for (const [mk, gs] of byMat) pieces.push({ m: mk, g: gs.length === 1 ? gs[0] : mergeGeos(gs) });
    for (const p of pieces) p.g.computeVertexNormals();
    builtCache.set(key, pieces);
  }
  const grp = new THREE.Group();
  for (const p of pieces) grp.add(new THREE.Mesh(p.g, M[p.m] || M.fallback));
  return grp;
}

// rboxGeo 是带缓存的，这里要就地平移，所以必须 clone 一份，否则会污染缓存里的共享几何体
const rbox = (sx, sy, sz, r) => rboxGeo(sx, sy, sz, r).clone();
const box = (sx, sy, sz, x, y, z) => { const g = new THREE.BoxGeometry(sx, sy, sz); g.translate(x || 0, y || 0, z || 0); return g; };
const cyl = (r1, r2, h, seg, axis, x, y, z) => {
  const g = new THREE.CylinderGeometry(r1, r2, h, seg);
  if (axis === 'x') g.rotateZ(Math.PI / 2); else if (axis === 'z') g.rotateX(Math.PI / 2);
  g.translate(x || 0, y || 0, z || 0); return g;
};
const sph = (r, x, y, z) => { const g = new THREE.SphereGeometry(r, 14, 10); g.translate(x || 0, y || 0, z || 0); return g; };
const tor = (r, t, x, y, z, axis) => {
  const g = new THREE.TorusGeometry(r, t, 8, 22);
  if (axis === 'x') g.rotateY(Math.PI / 2); else if (axis === 'y') g.rotateX(Math.PI / 2);
  g.translate(x || 0, y || 0, z || 0); return g;
};
// 一段圆弧管，用来做进排气歧管的弯管
function bend(pts, r) {
  const c = new THREE.CatmullRomCurve3(pts.map((p) => new THREE.Vector3(p[0], p[1], p[2])));
  return new THREE.TubeGeometry(c, 14, r, 8, false);
}

function buildEngineBlock(M) {
  return multi('block', M, () => {
    const a = [{ g: rbox(0.42, 0.34, 0.50, 0.03), m: 'engine' }];
    for (let i = 0; i < 4; i++) {                       // 四个缸孔凸台
      const z = -0.165 + i * 0.11;
      a.push({ g: cyl(0.043, 0.043, 0.07, 14, 'y', 0, 0.185, z), m: 'engine' });
    }
    a.push({ g: box(0.44, 0.03, 0.52, 0, -0.16, 0), m: 'metal' });   // 主轴承盖面
    a.push({ g: cyl(0.075, 0.075, 0.032, 16, 'x', 0.225, -0.05, 0), m: 'metal' });  // 曲轴皮带轮
    a.push({ g: cyl(0.020, 0.020, 0.05, 10, 'x', 0.245, -0.05, 0), m: 'metal' });
    for (const s of [-1, 1]) a.push({ g: box(0.30, 0.20, 0.012, 0, 0.02, s * 0.255), m: 'engine' });
    return a;
  });
}

function buildCylHead(M) {
  return multi('cylhead', M, () => {
    const a = [{ g: rbox(0.40, 0.13, 0.48, 0.025), m: 'engine' }];
    for (const s of [-1, 1]) a.push({ g: cyl(0.030, 0.030, 0.44, 12, 'z', s * 0.085, 0.075, 0), m: 'metal' });
    for (let i = 0; i < 4; i++) a.push({ g: cyl(0.014, 0.014, 0.05, 8, 'y', 0, 0.085, -0.165 + i * 0.11), m: 'metal' });
    a.push({ g: box(0.42, 0.012, 0.50, 0, -0.068, 0), m: 'metal' });  // 缸垫面
    return a;
  });
}

function buildHeadCover(M) {
  return multi('headcover', M, () => ([
    { g: rbox(0.38, 0.085, 0.44, 0.025), m: 'dark' },
    { g: cyl(0.038, 0.038, 0.035, 14, 'y', -0.10, 0.055, 0.13), m: 'dark' },   // 加机油口盖
    { g: box(0.34, 0.010, 0.40, 0, -0.046, 0), m: 'metal' },
  ]));
}

function buildIntakeMani(M) {
  return multi('intakemani', M, () => {
    const a = [{ g: rbox(0.15, 0.13, 0.42, 0.04), m: 'plastic' }];      // 稳压腔
    for (let i = 0; i < 4; i++) {                                       // 四根弯管
      const z = -0.155 + i * 0.105;
      a.push({ g: bend([[0.06, 0.02, z], [0.14, 0.00, z], [0.19, -0.06, z], [0.19, -0.12, z]], 0.021), m: 'plastic' });
    }
    a.push({ g: box(0.02, 0.16, 0.46, 0.20, -0.11, 0), m: 'plastic' }); // 法兰
    return a;
  });
}

function buildExhMani(M) {
  return multi('exhmani', M, () => {
    const a = [{ g: box(0.022, 0.20, 0.46, -0.075, 0.02, 0), m: 'metal' }];  // 法兰
    for (let i = 0; i < 4; i++) {
      const z = -0.165 + i * 0.11;
      a.push({ g: bend([[-0.06, 0.06, z], [0.01, 0.03, z], [0.05, -0.03, z * 0.35], [0.06, -0.10, 0]], 0.019), m: 'metal' });
    }
    a.push({ g: cyl(0.042, 0.042, 0.10, 14, 'y', 0.06, -0.16, 0), m: 'metal' });
    return a;
  });
}

function buildTransaxle(M) {
  return multi('transaxle', M, () => {
    const p = [];
    for (let i = 0; i <= 8; i++) { const t = i / 8; p.push(new THREE.Vector2(0.075 + 0.115 * Math.sin(t * Math.PI * 0.5), -0.17 + t * 0.20)); }
    const bell = new THREE.LatheGeometry(p, 20); bell.rotateZ(Math.PI / 2); bell.translate(0.09, 0, 0);
    return [
      { g: bell, m: 'metal' },                                        // 钟形罩
      { g: rbox(0.26, 0.30, 0.30, 0.05), m: 'metal' },                // 主壳
      { g: sph(0.115, -0.05, -0.05, 0), m: 'metal' },                 // 差速器凸包
      { g: cyl(0.032, 0.032, 0.12, 12, 'z', -0.05, -0.05, 0.17), m: 'metal' },
      { g: cyl(0.05, 0.05, 0.06, 12, 'y', 0.02, 0.17, 0), m: 'alloy' },
    ];
  });
}

function buildBrakeDisc(M) {
  return multi('brakedisc', M, () => {
    const a = [];
    a.push({ g: cyl(0.140, 0.140, 0.010, 30, 'z', 0, 0, 0.010), m: 'metal' });   // 摩擦面 外
    a.push({ g: cyl(0.140, 0.140, 0.010, 30, 'z', 0, 0, -0.010), m: 'metal' });  // 摩擦面 内
    for (let i = 0; i < 16; i++) {                                              // 通风筋
      const ang = (i / 16) * Math.PI * 2;
      const g = box(0.055, 0.010, 0.010, 0.10, 0, 0); g.rotateZ(ang);
      a.push({ g, m: 'metal' });
    }
    a.push({ g: cyl(0.062, 0.062, 0.045, 20, 'z', 0, 0, -0.014), m: 'metal' });  // 制动盘帽
    for (let i = 0; i < 5; i++) {
      const ang = (i / 5) * Math.PI * 2;
      a.push({ g: cyl(0.008, 0.008, 0.05, 8, 'z', Math.cos(ang) * 0.045, Math.sin(ang) * 0.045, -0.014), m: 'alloy' });
    }
    return a;
  });
}

function buildCaliper(M) {
  return multi('caliper', M, () => ([
    { g: rbox(0.075, 0.115, 0.035, 0.012), m: 'trim' },                  // 钳体外侧
    { g: rbox(0.075, 0.115, 0.030, 0.012), m: 'trim' },
    { g: box(0.075, 0.030, 0.070, 0, 0.058, 0), m: 'trim' },             // 跨过盘的桥
    { g: cyl(0.026, 0.026, 0.030, 14, 'z', 0, -0.01, 0.030), m: 'metal' }, // 活塞
    { g: cyl(0.009, 0.009, 0.09, 8, 'z', 0.028, 0.045, 0), m: 'metal' },   // 滑动销
    { g: cyl(0.009, 0.009, 0.09, 8, 'z', -0.028, 0.045, 0), m: 'metal' },
  ]));
}

function buildRadiator(M) {
  return multi('radiator', M, () => {
    const a = [{ g: box(0.028, 0.34, 0.62, 0, 0, 0), m: 'metal' }];       // 芯体
    for (let i = 0; i < 14; i++) a.push({ g: box(0.034, 0.006, 0.60, 0, -0.16 + i * 0.0245, 0), m: 'alloy' });
    const top = rbox(0.045, 0.055, 0.66, 0.02); top.translate(0, 0.195, 0);
    const bot = rbox(0.045, 0.055, 0.66, 0.02); bot.translate(0, -0.195, 0);
    a.push({ g: top, m: 'plastic' }, { g: bot, m: 'plastic' });           // 上下水室
    a.push({ g: cyl(0.020, 0.020, 0.05, 10, 'x', 0.045, 0.195, 0.24), m: 'plastic' });
    return a;
  });
}

function buildAlternator(M) {
  return multi('alternator', M, () => {
    const p = [];
    for (let i = 0; i <= 6; i++) { const t = i / 6; p.push(new THREE.Vector2(0.052 + 0.012 * Math.sin(t * Math.PI), -0.055 + t * 0.11)); }
    const shell = new THREE.LatheGeometry(p, 18); shell.rotateZ(Math.PI / 2);
    return [
      { g: shell, m: 'metal' },
      { g: cyl(0.034, 0.034, 0.028, 16, 'x', 0.072, 0, 0), m: 'metal' },   // 皮带轮
      { g: tor(0.034, 0.005, 0.072, 0, 0, 'x'), m: 'metal' },
      { g: box(0.03, 0.05, 0.016, -0.05, -0.05, 0), m: 'metal' },          // 支架耳
      { g: cyl(0.010, 0.010, 0.03, 8, 'z', -0.05, 0.045, 0), m: 'copper' },
    ];
  });
}

function buildBattery(M) {
  return multi('battery', M, () => ([
    { g: rbox(0.24, 0.17, 0.17, 0.012), m: 'dark' },
    { g: rbox(0.235, 0.022, 0.165, 0.008), m: 'trim', },
    { g: cyl(0.011, 0.013, 0.022, 12, 'y', 0.085, 0.098, 0.055), m: 'copper' },
    { g: cyl(0.011, 0.013, 0.022, 12, 'y', 0.085, 0.098, -0.055), m: 'copper' },
    { g: box(0.10, 0.010, 0.020, -0.05, 0.098, 0), m: 'trim' },
  ]));
}

function buildSteerWheel(M) {
  return multi('steerwheel', M, () => {
    const a = [{ g: tor(0.175, 0.018, 0, 0, 0, 'x'), m: 'dark' }];
    for (const ang of [Math.PI * 0.5, Math.PI * 1.17, Math.PI * 1.83]) {
      const g = box(0.014, 0.155, 0.030, 0, 0.082, 0); g.rotateX(ang); a.push({ g, m: 'dark' });
    }
    a.push({ g: rbox(0.030, 0.115, 0.115, 0.03), m: 'trim' });
    return a;
  });
}

function buildStrut(M) {
  return multi('strut', M, () => ([
    { g: cyl(0.032, 0.032, 0.26, 16, 'y', 0, -0.10, 0), m: 'metal' },      // 减振器筒
    { g: cyl(0.013, 0.013, 0.22, 10, 'y', 0, 0.13, 0), m: 'chrome' },      // 活塞杆
    { g: cyl(0.070, 0.070, 0.016, 18, 'y', 0, 0.235, 0), m: 'metal' },     // 上支座
    { g: cyl(0.062, 0.062, 0.012, 18, 'y', 0, -0.02, 0), m: 'metal' },     // 下弹簧盘
    { g: box(0.05, 0.07, 0.030, 0, -0.235, 0), m: 'metal' },               // 与转向节的连接叉
  ]));
}

function buildHeadlampGeo(M) {
  return multi('headlamp', M, () => {
    const a = [{ g: rbox(0.17, 0.115, 0.34, 0.035), m: 'trim' }];
    const lens = rbox(0.020, 0.100, 0.32, 0.030); lens.translate(0.078, 0, 0);
    a.push({ g: lens, m: 'glass' });
    for (const z of [-0.09, 0.02]) a.push({ g: sph(0.040, 0.030, 0, z), m: 'lampw' });
    a.push({ g: box(0.012, 0.022, 0.26, 0.060, -0.040, 0.02), m: 'lampw' });  // 日行灯条
    return a;
  });
}

function buildLowerArm(M) {
  return multi('lowerarm', M, () => ([
    { g: box(0.30, 0.026, 0.075, 0, 0, 0), m: 'metal' },
    { g: box(0.075, 0.026, 0.20, -0.10, 0, 0.09), m: 'metal' },
    { g: cyl(0.028, 0.028, 0.070, 12, 'z', -0.135, 0, 0.16), m: 'rubber' },  // 前衬套
    { g: cyl(0.030, 0.030, 0.060, 12, 'y', -0.10, 0, -0.02), m: 'rubber' },  // 后衬套
    { g: cyl(0.026, 0.020, 0.045, 12, 'y', 0.145, 0.02, 0), m: 'metal' },    // 球头
  ]));
}

function buildInstrPanel(M) {
  return multi('instrpanel', M, () => {
    const a = [{ g: rbox(0.30, 0.16, 1.42, 0.05), m: 'trim' }];
    a.push({ g: box(0.24, 0.030, 1.40, -0.02, 0.095, 0), m: 'trim' });        // 台面
    for (const z of [-0.52, -0.18, 0.18, 0.52]) {                             // 四个出风口
      const v = rbox(0.020, 0.055, 0.13, 0.02); v.translate(-0.145, 0.02, z);
      a.push({ g: v, m: 'dark' });
    }
    const scr = rbox(0.030, 0.16, 0.30, 0.02); scr.translate(-0.135, 0.05, 0);
    a.push({ g: scr, m: 'dark' });                                            // 中控屏
    return a;
  });
}

// ───────────────────────────────────────────────── 认不出的零件：按 group 塞进车里
const ZONE = {
  body:               { c: [-0.30, 0.80, 0.00], s: [2.00, 0.50, 1.20] },
  electrical:         { c: [1.30, 0.72, 0.00], s: [1.00, 0.40, 1.20] },
  engine_fuel_tool:   { c: [1.45, 0.62, 0.00], s: [0.90, 0.45, 0.95] },
  powertrain_chassis: { c: [-0.20, 0.32, 0.00], s: [2.20, 0.20, 1.10] },
};

// 外覆盖件：合拢态如果显示真实车壳，这批要让位（否则和车壳穿模）。
// 藏在里面的件不用管，本来就被壳挡住，也不会打架。
export const EXTERIOR_SLOTS = new Set([
  'roof', 'hood', 'trunklid', 'door', 'doorglass', 'windshield', 'backwindow',
  'fender', 'quarter', 'bumpercover', 'bumperreinf', 'rocker',
  'pillara', 'pillarb', 'pillarc', 'rim', 'tire', 'headlamp', 'taillamp',
  'mirror', 'grilleupper', 'grillelower', 'spoiler', 'mudguard', 'licenselamp',
  'stoplamp', 'foglamp', 'wiperarm',
]);

// 这些槽位决定整车外形，多个零件落进同一个也必须原位重叠，不许错开
const NO_JITTER = new Set([
  'roof', 'hood', 'trunklid', 'door', 'doorglass', 'windshield', 'backwindow',
  'fender', 'quarter', 'bumpercover', 'bumperreinf', 'rocker', 'floor',
  'pillara', 'pillarb', 'pillarc', 'rim', 'tire', 'headlamp', 'taillamp',
  'mirror', 'grilleupper', 'grillelower', 'spoiler', 'seat', 'seatback', 'seatcushion',
]);

function hash32(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}

function fallbackTransform(part) {
  const z = ZONE[part.group] || ZONE.body;
  const h = hash32(part.id);
  const u = ((h & 0x3ff) / 1023) - 0.5;
  const v = (((h >>> 10) & 0x3ff) / 1023) - 0.5;
  const w = (((h >>> 20) & 0x3ff) / 1023) - 0.5;
  return T(z.c[0] + u * z.s[0], z.c[1] + v * z.s[1], z.c[2] + w * z.s[2]);
}

// ───────────────────────────────────────────────── 主入口
export function buildCar(parts) {
  const M = mats();
  const root = new THREE.Group();
  root.name = 'car';
  const objects = new Map();   // id -> Object3D
  const assembled = new Map(); // id -> Vector3
  const halfY = new Map();     // id -> 半高，爆炸态抬离地面时要用
  const meshParts = parts.filter((p) => p.has_mesh === true);
  const stats = { matched: 0, fallback: 0, shared: 0 };
  const exteriorIds = new Set();   // 合拢态显示真实车壳时，这批要隐藏
  // 真实零件目录里，同一个槽位会落进好几个零件（变速箱内部就有十几个）。
  // 第一个占位的用原始坐标，后面的按 id 哈希在小范围内错开，
  // 否则它们会精确重叠成一坨，爆炸时也分不开。
  const slotUse = new Map();

  for (const part of meshParts) {
    const { base, side, pos } = slotOf(part);
    const spec = base ? PLACE[base] : null;
    let transforms, material, geoFn, custom = null;

    if (spec) {
      stats.matched++;
      if (EXTERIOR_SLOTS.has(base)) exteriorIds.add(part.id);
      transforms = spec.f ? spec.f({ pos, side, qty: part.qty }) : spec.t;
      // 单边件：表里按左侧写，右侧整体镜像
      if (side === 'rh' && !spec.f) {
        transforms = transforms.map((t) => T(t[0], t[1], -t[2], -t[3], -t[4], t[5]));
      }
      const key = `${base}|${side || ''}|${pos || ''}`;
      const nth = slotUse.get(key) || 0;
      slotUse.set(key, nth + 1);
      // 外观件的位置是「这辆车看起来对不对」的全部来源，宁可重叠也不许错开；
      // 只有藏在里面的件（变速箱内部、门板内、发动机内）才允许抖开。
      if (nth > 0 && !NO_JITTER.has(base)) {
        stats.shared++;
        const h = hash32(part.id);
        const dx = (((h & 0x3ff) / 1023) - 0.5) * 0.34;
        const dy = ((((h >>> 10) & 0x3ff) / 1023) - 0.5) * 0.20;
        const dz = ((((h >>> 20) & 0x3ff) / 1023) - 0.5) * 0.34;
        transforms = transforms.map((t) => T(t[0] + dx, t[1] + dy, t[2] + dz, t[3], t[4], t[5]));
      }
      material = M[spec.m] || M.fallback;
      geoFn = spec.g;
      custom = spec.build || null;
    } else {
      stats.fallback++;
      transforms = [fallbackTransform(part)];
      material = M.fallback;
      geoFn = () => boxGeo(0.11, 0.09, 0.13);
    }

    // 一个零件一个容器；容器带 id，子网格不带 —— 数 id 的时候它就是 1 个
    const holder = new THREE.Group();
    holder.name = part.id;
    holder.userData.id = part.id;
    holder.userData.group = part.group;
    holder.userData.subgroup_en = part.subgroup_en;

    for (const t of transforms) {
      let node;
      if (custom) {
        node = custom(M);
      } else {
        const geo = geoFn({ pos, side, qty: part.qty });
        if (!geo) continue;
        node = new THREE.Mesh(geo, material);
      }
      node.position.set(t[0], t[1], t[2]);
      node.rotation.set(t[3], t[4], t[5]);
      if (side === 'rh' && custom) node.position.z = -Math.abs(node.position.z);
      holder.add(node);
    }
    if (holder.children.length === 0) {
      const t = fallbackTransform(part);
      const n = new THREE.Mesh(boxGeo(0.11, 0.09, 0.13), M.fallback);
      n.position.set(t[0], t[1], t[2]);
      holder.add(n);
    }

    // 容器自身放在它所有子件的几何中心上，这样爆炸时整组一起平移不会散
    const box = new THREE.Box3().setFromObject(holder);
    const c = box.getCenter(new THREE.Vector3());
    holder.children.forEach((ch) => ch.position.sub(c));
    holder.position.copy(c);

    assembled.set(part.id, c.clone());
    halfY.set(part.id, (box.max.y - box.min.y) / 2);
    objects.set(part.id, holder);
    root.add(holder);
  }

  const exploded = computeExploded(meshParts, assembled);
  // 整体抬到地面以上：簇的 y 偏移是手写的，谁最低不好心算，这里量完再统一顶上去
  let minY = Infinity;
  for (const [id, v] of exploded) minY = Math.min(minY, v.y - (halfY.get(id) || 0));
  if (minY < 0.12) for (const v of exploded.values()) v.y += 0.12 - minY;
  return { root, objects, assembled, exploded, materials: M, buildStats: stats, exteriorIds };
}

// ───────────────────────────────────────────────── 爆炸位置
// 规则：整车按 SCALE 从中心放大 → 四个 group 各自平移到自己的簇 → 同图组再沿径向推开一点。
// 均匀放大保证同一簇内两两间距只增不减（零件尺寸不变），所以簇内不会新增穿插。
const SCALE = 1.72;
// 簇的方向必须冲着默认相机来定，不能想当然按 ±X / ±Z 摆。
// 默认视角 dir≈(0.706,0.311,0.636)，算出来「屏幕向右」这条轴是 U=(-0.669,0,0.743)，
// 也就是 +Z 和 -X 在屏幕上都往右跑 —— 按 ±X/±Z 摆四簇，屏幕上只会看到两坨。
// 所以：车身整体抬起、底盘留在下面、发动机与电气各沿 ±U 分到左右，摆成一个菱形。
// 顺带这也是最好读的一种分解图：壳子掀起来，动力总成和电气各拉一边。
const U = new THREE.Vector3(-0.669, 0, 0.743);
const CLUSTER = {
  body:               new THREE.Vector3(0, 4.15, 0),
  powertrain_chassis: new THREE.Vector3(0, 0.55, 0),
  engine_fuel_tool:   U.clone().multiplyScalar(7.4).setY(1.90),
  electrical:         U.clone().multiplyScalar(-7.4).setY(1.90),
};
const SUBGROUP_PUSH = 0.42;

function computeExploded(meshParts, assembled) {
  const C = CAR.center;
  const subCentroid = new Map();
  const subCount = new Map();
  for (const p of meshParts) {
    const key = p.group + '|' + p.subgroup_en;
    const a = assembled.get(p.id);
    if (!a) continue;
    const acc = subCentroid.get(key) || new THREE.Vector3();
    acc.add(a); subCentroid.set(key, acc);
    subCount.set(key, (subCount.get(key) || 0) + 1);
  }
  for (const [k, v] of subCentroid) v.divideScalar(subCount.get(k));

  const out = new Map();
  for (const p of meshParts) {
    const a = assembled.get(p.id);
    if (!a) continue;
    const off = CLUSTER[p.group] || new THREE.Vector3();
    const v = a.clone().sub(C).multiplyScalar(SCALE).add(C).add(off);
    const sc = subCentroid.get(p.group + '|' + p.subgroup_en);
    if (sc) {
      const dir = sc.clone().sub(C);
      dir.y *= 0.5;
      if (dir.lengthSq() > 1e-6) v.add(dir.normalize().multiplyScalar(SUBGROUP_PUSH));
    }
    out.set(p.id, v);
  }
  return out;
}

// ───────────────────────────────────────────────── 地面接触阴影（假的，够用且便宜）
export function makeGroundShadow() {
  const cv = document.createElement('canvas');
  cv.width = cv.height = 256;
  const ctx = cv.getContext('2d');
  const g = ctx.createRadialGradient(128, 128, 8, 128, 128, 126);
  g.addColorStop(0, 'rgba(20,24,30,0.46)');
  g.addColorStop(0.45, 'rgba(20,24,30,0.20)');
  g.addColorStop(1, 'rgba(20,24,30,0)');
  ctx.fillStyle = g; ctx.fillRect(0, 0, 256, 256);
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(6.6, 3.0),
    new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false }),
  );
  mesh.rotation.x = -Math.PI / 2;
  mesh.position.y = 0.004;
  mesh.renderOrder = -1;
  return mesh;
}
