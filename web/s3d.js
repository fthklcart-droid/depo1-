/* SIRIUS 3D avatar engine: procedural meshes + a tiny additive-blend canvas renderer. No dependencies. */
(function () {
  const TAU = Math.PI * 2;
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const smooth = (a, b, x) => { x = clamp((x - a) / (b - a), 0, 1); return x * x * (3 - 2 * x); };
  const lerp = (a, b, t) => a + (b - a) * t;
  function rng(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

  /* ---------- meshes: a grid of N rows x M cols, wrap flag for columns ---------- */
  function makeGrid(N, M, wrap, fn) {
    const pos = new Float32Array(N * M * 3), aux = new Float32Array(N * M);
    for (let i = 0; i < N; i++) for (let j = 0; j < M; j++) {
      const v = fn(i / (N - 1), wrap ? j / M : j / (M - 1));
      const k = i * M + j; pos[k * 3] = v[0]; pos[k * 3 + 1] = v[1]; pos[k * 3 + 2] = v[2]; aux[k] = v[3] || 0;
    }
    const nrm = new Float32Array(N * M * 3);
    for (let i = 0; i < N; i++) for (let j = 0; j < M; j++) {
      const i0 = Math.max(0, i - 1), i1 = Math.min(N - 1, i + 1);
      const j0 = wrap ? (j + M - 1) % M : Math.max(0, j - 1), j1 = wrap ? (j + 1) % M : Math.min(M - 1, j + 1);
      const a = i0 * M + j, b = i1 * M + j, c = i * M + j0, d = i * M + j1;
      const ux = pos[b * 3] - pos[a * 3], uy = pos[b * 3 + 1] - pos[a * 3 + 1], uz = pos[b * 3 + 2] - pos[a * 3 + 2];
      const vx = pos[d * 3] - pos[c * 3], vy = pos[d * 3 + 1] - pos[c * 3 + 1], vz = pos[d * 3 + 2] - pos[c * 3 + 2];
      let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
      const l = Math.hypot(nx, ny, nz) || 1; nx /= l; ny /= l; nz /= l;
      const k = i * M + j;
      nrm[k * 3] = nx; nrm[k * 3 + 1] = ny; nrm[k * 3 + 2] = nz;
    }
    return { N, M, wrap, pos, nrm, aux, count: N * M };
  }
  function orientOutward(mesh, cx, cy, cz) {           // make normals point away from a centre
    const { pos, nrm, count } = mesh;
    for (let k = 0; k < count; k++) {
      const d = nrm[k * 3] * (pos[k * 3] - cx) + nrm[k * 3 + 1] * (pos[k * 3 + 1] - cy) + nrm[k * 3 + 2] * (pos[k * 3 + 2] - cz);
      if (d < 0) { nrm[k * 3] *= -1; nrm[k * 3 + 1] *= -1; nrm[k * 3 + 2] *= -1; }
    }
    return mesh;
  }

  // front features: [cx, cy, sx, sy, amplitude]  gaussians in the (x,y) plane, weighted by how much the surface faces +z
  const FACE = [
    [0, 0.20, 0.36, 0.055, 0.075],                                   // brow ridge
    [-0.30, 0.055, 0.115, 0.075, -0.105], [0.30, 0.055, 0.115, 0.075, -0.105],   // eye sockets
    [-0.30, 0.055, 0.075, 0.03, 0.040], [0.30, 0.055, 0.075, 0.03, 0.040],       // eyelids / lashes line
    [0, -0.03, 0.055, 0.20, 0.080],                                  // nose bridge
    [0, -0.27, 0.095, 0.085, 0.215],                                 // nose tip
    [-0.14, -0.30, 0.06, 0.06, 0.095], [0.14, -0.30, 0.06, 0.06, 0.095],         // nostril wings
    [0, -0.50, 0.17, 0.05, 0.070],                                   // upper lip
    [0, -0.585, 0.15, 0.022, -0.055],                                // mouth groove
    [0, -0.665, 0.15, 0.06, 0.085],                                  // lower lip
    [0, -0.77, 0.22, 0.09, -0.060],                                  // chin crease
    [0, -0.91, 0.19, 0.10, 0.110],                                   // chin
    [-0.47, -0.10, 0.17, 0.14, 0.085], [0.47, -0.10, 0.17, 0.14, 0.085],         // cheekbones
    [-0.40, -0.46, 0.16, 0.14, -0.065], [0.40, -0.46, 0.16, 0.14, -0.065],       // cheek hollows
    [-0.58, -0.66, 0.16, 0.16, 0.035], [0.58, -0.66, 0.16, 0.16, 0.035],         // jaw line
    [0, 0.44, 0.22, 0.10, -0.030],                                   // forehead dip above brows
  ];
  // side features (ears): [cx, cy, cz, sx, sy, sz, amplitude]
  const SIDE = [[-0.79, -0.10, -0.06, 0.09, 0.16, 0.14, 0.115], [0.79, -0.10, -0.06, 0.09, 0.16, 0.14, 0.115]];
  function headMesh(N, M) {
    const m = makeGrid(N, M, true, (t, u) => {
      const th = t * Math.PI, ph = u * TAU;
      const sx = Math.sin(th) * Math.sin(ph), cy = Math.cos(th), sz = Math.sin(th) * Math.cos(ph);
      const y = cy * 1.0;
      const wK = 0.70 + 0.30 * smooth(-0.95, 0.25, y), dK = 0.84 + 0.10 * smooth(-0.9, 0.3, y);
      let x = sx * 0.76 * wK, z = sz * dK * (sz > 0 ? 1 : 0.97), yy = y;
      if (yy < -0.55) { yy = -0.55 + (yy + 0.55) * 0.82; }                          // squarer chin
      const len = Math.hypot(x, yy - 0.05, z) || 1, dx = x / len, dy = (yy - 0.05) / len, dz = z / len;
      let disp = 0;
      const facing = smooth(0.12, 0.62, dz);
      for (let b = 0; b < FACE.length; b++) {
        const f = FACE[b], ex = (x - f[0]) / f[2], ey = (yy - f[1]) / f[3];
        disp += f[4] * Math.exp(-(ex * ex + ey * ey)) * facing;
      }
      for (let b = 0; b < SIDE.length; b++) {
        const f = SIDE[b], ex = (x - f[0]) / f[3], ey = (yy - f[1]) / f[4], ez = (z - f[2]) / f[5];
        disp += f[6] * Math.exp(-(ex * ex + ey * ey + ez * ez));
      }
      x += dx * disp; yy += dy * disp; z += dz * disp;
      const jaw = smooth(-0.62, -0.92, yy) * smooth(0.0, 0.5, z) * (1 - smooth(0.5, 0.85, Math.abs(x)));
      return [x, yy, z, jaw];
    });
    return orientOutward(m, 0, 0.05, 0);
  }
  function bustMesh(R, M) {
    const m = makeGrid(R, M, true, (t, u) => {
      const ph = u * TAU, s = Math.sin(ph), c = Math.cos(ph);
      const flare = smooth(0.38, 1, t);
      const rx = 0.31 + 1.60 * Math.pow(flare, 1.5), rz = 0.34 + 0.42 * Math.pow(flare, 1.3);
      let y = -0.70 - t * 1.30 - 0.30 * flare * Math.abs(s) * flare;
      return [s * rx, y, c * rz * (c > 0 ? 1 : 0.9) - 0.04 * flare, 0];
    });
    return orientOutward(m, 0, -1.4, 0);
  }
  function sphereMesh(N, M, r, fn) {
    return orientOutward(makeGrid(N, M, true, (t, u) => {
      const th = t * Math.PI, ph = u * TAU;
      let x = Math.sin(th) * Math.sin(ph), y = Math.cos(th), z = Math.sin(th) * Math.cos(ph);
      const k = fn ? fn(x, y, z) : 1;
      return [x * r * k, y * r * k, z * r * k, 0];
    }), 0, 0, 0);
  }
  function hemisphere(side, N, M) {
    const m = makeGrid(N, M, false, (t, u) => {
      const th = t * Math.PI, ph = u * Math.PI * (side > 0 ? 1 : -1);
      let x = Math.sin(th) * Math.sin(ph), y = Math.cos(th), z = Math.sin(th) * Math.cos(ph);
      let X = side * 0.05 + x * 0.50, Y = y * 0.56 + 0.02, Z = z * 0.80 + (z < 0 ? 0 : 0.02);
      Y -= 0.10 * smooth(0, 1, -y) * (z > 0 ? 0.6 : 0.2);                   // flatter underside
      // wide rounded gyri separated by narrow meandering grooves (sulci)
      const w1 = Math.abs(Math.sin(12.5 * Y + 2.4 * Math.sin(6.2 * Z + 1.0) + 1.7 * Math.sin(7.3 * X + 0.4)));
      const w2 = Math.abs(Math.sin(10.5 * Z + 2.0 * Math.sin(7.7 * Y + 2.0) + 1.2 * Math.sin(6.1 * X)));
      const groove = Math.min(1, Math.pow(1 - w1, 7) * 1.0 + Math.pow(1 - w2, 7) * 0.85);
      const k = 1 - 0.085 * groove * smooth(0.02, 0.22, Math.abs(x)) + 0.012 * (w1 + w2 - 1);
      const cx = side * 0.05, cy = 0.02;
      return [cx + (X - cx) * k, cy + (Y - cy) * k, Z * k, 0];
    });
    return orientOutward(m, side * 0.05, 0.02, 0);
  }
  function cerebellum() {
    return orientOutward(makeGrid(22, 36, true, (t, u) => {
      const th = t * Math.PI, ph = u * TAU;
      const x = Math.sin(th) * Math.sin(ph), y = Math.cos(th), z = Math.sin(th) * Math.cos(ph);
      const k = 1 + 0.07 * Math.sin(y * 26);
      return [x * 0.40 * k, -0.40 + y * 0.17 * k, -0.62 + z * 0.26 * k, 0];
    }), 0, -0.4, -0.62);
  }

  /* ---------- 3D helpers ---------- */
  function Cam(w, h, scale, cx, cy, cyDown) { this.w = w; this.h = h; this.s = scale; this.cx = cx; this.cy = cy; this.D = 4.6; }
  function project(mesh, cam, yaw, pitch, buf, ty) {
    const { pos, nrm, count } = mesh;
    const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
    for (let k = 0; k < count; k++) {
      let x = pos[k * 3], y = pos[k * 3 + 1] + (ty || 0), z = pos[k * 3 + 2];
      let x1 = x * cy + z * sy, z1 = -x * sy + z * cy;
      let y1 = y * cp - z1 * sp, z2 = y * sp + z1 * cp;
      const f = cam.D / (cam.D - z2);
      buf.sx[k] = cam.cx + x1 * cam.s * f; buf.sy[k] = cam.cy - y1 * cam.s * f; buf.z[k] = z2;
      let nx = nrm[k * 3], ny = nrm[k * 3 + 1], nz = nrm[k * 3 + 2];
      let nx1 = nx * cy + nz * sy, nz1 = -nx * sy + nz * cy;
      buf.nz[k] = (ny * sp + nz1 * cp);
      buf.ny[k] = ny * cp - nz1 * sp; buf.nx[k] = nx1;
    }
  }
  function Buf(n) { return { sx: new Float32Array(n), sy: new Float32Array(n), z: new Float32Array(n), nz: new Float32Array(n), ny: new Float32Array(n), nx: new Float32Array(n) }; }
  function projPoint(cam, x, y, z, yaw, pitch) {
    const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
    let x1 = x * cy + z * sy, z1 = -x * sy + z * cy, y1 = y * cp - z1 * sp, z2 = y * sp + z1 * cp;
    const f = cam.D / (cam.D - z2);
    return [cam.cx + x1 * cam.s * f, cam.cy - y1 * cam.s * f, z2];
  }

  /* ---------- shared drawing ---------- */
  const rgba = (c, a) => `rgba(${c[0]},${c[1]},${c[2]},${a.toFixed(3)})`;
  function glow(ctx, x, y, r, c, a, sx) {
    const g = ctx.createRadialGradient(0, 0, 0, 0, 0, r);
    g.addColorStop(0, rgba([255, 255, 255], a)); g.addColorStop(0.18, rgba(c, a * 0.7)); g.addColorStop(1, rgba(c, 0));
    ctx.save(); ctx.translate(x, y); ctx.scale(sx || 1, 1); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, r, 0, TAU); ctx.fill(); ctx.restore();
  }
  function binaryRain(ctx, w, h, t, c, a, st) {
    const cols = Math.floor(w / 17);
    ctx.font = '11px "IBM Plex Mono", monospace'; ctx.textAlign = 'center';
    for (let i = 0; i < cols; i++) {
      const r = st.r[i], speed = 22 + r * 46, len = 6 + Math.floor(r * 10), head = ((t * speed + r * 900) % (h + len * 14)) - len * 14 * 0.2;
      for (let k = 0; k < len; k++) {
        const y = head - k * 14; if (y < -10 || y > h + 10) continue;
        const ch = ((i * 31 + k * 7 + Math.floor(t * 3 + r * 10)) % 3) === 0 ? '1' : '0';
        ctx.fillStyle = rgba(c, a * (k === 0 ? 1 : (1 - k / len)) * (0.3 + r * 0.7));
        ctx.fillText(ch, 8 + i * 17, y);
      }
    }
  }
  function strokeBuckets(ctx, buckets, c, width) {
    ctx.lineWidth = width;
    for (let b = 0; b < buckets.length; b++) {
      const p = buckets[b]; if (!p.n) continue;
      ctx.strokeStyle = rgba(c, (b + 1) / buckets.length * p.max); ctx.stroke(p.path);
    }
  }
  function newBuckets(n) { const a = []; for (let i = 0; i < n; i++) a.push({ path: new Path2D(), n: 0, max: 1 }); return a; }

  /* ---------- mode targets ---------- */
  const MODES = {
    LISTENING: { spin: 0.30, glow: 0.80, flare: 0.55, jaw: 0, scan: 0.10, pulse: 0.5, think: 0 },
    THINKING:  { spin: 0.95, glow: 1.00, flare: 1.00, jaw: 0, scan: 0.55, pulse: 1.4, think: 1 },
    SPEAKING:  { spin: 0.34, glow: 1.00, flare: 0.80, jaw: 1, scan: 0.18, pulse: 2.2, think: 0 },
    SLEEPING:  { spin: 0.06, glow: 0.22, flare: 0.05, jaw: 0, scan: 0.03, pulse: 0.2, think: 0 },
  };

  /* ---------- avatar kinds ---------- */
  const KINDS = {};

  KINDS.holo = function (W, H) {                                 // wireframe half / particle half head with eye flare + binary rain
    const head = headMesh(60, 72), bust = bustMesh(12, 72);
    const hb = Buf(head.count), bb = Buf(bust.count), cam = new Cam(W, H, W * 0.325, W / 2, H * 0.43);
    const R = rng(7), st = { r: Array.from({ length: 64 }, R) };
    const C = [120, 205, 255], P = [225, 120, 255];
    const dust = Array.from({ length: 70 }, () => ({ a: R() * TAU, r: 0.9 + R() * 0.9, y: R() * 2.4 - 1.1, s: 0.2 + R() * 0.5 }));
    return function frame(ctx, t, S) {
      ctx.clearRect(0, 0, W, H);
      ctx.globalCompositeOperation = 'lighter';
      binaryRain(ctx, W, H, t, [60, 130, 255], 0.55 * (0.4 + S.glow * 0.6), st);
      const yaw = Math.sin(t * S.spin) * 0.55, pitch = -0.04 + Math.sin(t * 0.7) * 0.03 * (1 + S.think);
      const jawD = S.jaw * (0.5 + 0.5 * Math.sin(t * 13) * Math.sin(t * 5.3 + 1)) * 0.075;
      for (let k = 0; k < head.count; k++) { /* jaw drop is applied through ty per-vertex below */ }
      // project head with jaw offset per vertex
      const pos = head.pos, off = head.aux;
      const tmp = head._tmp || (head._tmp = new Float32Array(head.pos.length));
      for (let k = 0; k < head.count; k++) { tmp[k * 3] = pos[k * 3]; tmp[k * 3 + 1] = pos[k * 3 + 1] - off[k] * jawD; tmp[k * 3 + 2] = pos[k * 3 + 2]; }
      project({ pos: tmp, nrm: head.nrm, count: head.count }, cam, yaw, pitch, hb);
      project(bust, cam, yaw * 0.6, pitch, bb);
      const split = W / 2 + Math.sin(t * (0.35 + S.scan)) * W * 0.07 + W * 0.04;
      const b = newBuckets(5); const dots = [];
      const edge = (buf, i1, i2, boost, dimSide) => {
        const mx = (buf.sx[i1] + buf.sx[i2]) * 0.5; if (mx > split && dimSide) return;
        const f1 = 1 - Math.abs(buf.nz[i1]), f2 = 1 - Math.abs(buf.nz[i2]);
        const front = (buf.nz[i1] + buf.nz[i2]) > 0 ? 1 : 0.22;
        const lit = clamp(0.62 * (buf.nz[i1] + buf.nz[i2]) / 2 + 0.38 * (buf.ny[i1] + buf.ny[i2]) / 2 - 0.62 * (buf.nx[i1] + buf.nx[i2]) / 2, 0, 1);
        let a = (0.05 + 0.34 * Math.pow((f1 + f2) * 0.5, 1.4) + 0.95 * lit * lit) * front * boost * S.glow + (front === 1 ? 0.06 : 0.02);
        const bi = Math.min(4, Math.floor(clamp(a, 0, 0.999) * 5)); const B = b[bi];
        B.path.moveTo(buf.sx[i1], buf.sy[i1]); B.path.lineTo(buf.sx[i2], buf.sy[i2]); B.n++;
      };
      const gridEdges = (m, buf, boost, wrap) => {
        for (let i = 0; i < m.N - 1; i++) for (let j = 0; j < m.M; j++) {
          const j1 = (j + 1) % m.M, k = i * m.M + j;
          edge(buf, k, i * m.M + j1, boost, true); edge(buf, k, (i + 1) * m.M + j, boost, true); edge(buf, k, (i + 1) * m.M + j1, boost * 0.85, true);
        }
      };
      gridEdges(head, hb, 1, true); gridEdges(bust, bb, 0.55, true);
      strokeBuckets(ctx, b, C, 0.7);
      // particle half
      ctx.fillStyle = rgba([170, 225, 255], 1);
      const dotPass = (m, buf, boost) => {
        for (let k = 0; k < m.count; k++) {
          if (buf.sx[k] <= split - 6) continue;
          const f = 1 - Math.abs(buf.nz[k]), front = buf.nz[k] > 0 ? 1 : 0.2;
          const tw = 0.6 + 0.4 * Math.sin(t * 3 + k * 1.7);
          const a = (0.25 + 0.75 * f) * front * tw * boost * S.glow * smooth(split - 6, split + 14, buf.sx[k]);
          if (a < 0.05) continue;
          ctx.globalAlpha = Math.min(1, a); const s = 1.0 + f * 1.4 * front;
          ctx.fillRect(buf.sx[k] - s / 2, buf.sy[k] - s / 2, s, s);
        }
      };
      dotPass(head, hb, 1.15); dotPass(bust, bb, 0.7); ctx.globalAlpha = 1;
      // a second, denser particle skin on the dotted side (sparse samples between vertices)
      ctx.fillStyle = rgba([200, 240, 255], 1);
      for (let i = 0; i < head.N - 1; i += 1) for (let j = 0; j < head.M; j += 1) {
        const k = i * head.M + j, k2 = (i + 1) * head.M + (j + 1) % head.M;
        const mx = (hb.sx[k] + hb.sx[k2]) / 2; if (mx < split + 10) continue; if (hb.nz[k] < 0.05) continue;
        const f = 1 - hb.nz[k]; ctx.globalAlpha = 0.25 * S.glow * (0.3 + f);
        ctx.fillRect(mx - 0.5, (hb.sy[k] + hb.sy[k2]) / 2 - 0.5, 1, 1);
      }
      ctx.globalAlpha = 1;
      // eye flare
      const eye = projPoint(cam, 0, 0.215, 0.9, yaw, pitch);
      const pulse = 1 + 0.25 * Math.sin(t * S.pulse * 3);
      const fl = S.flare * pulse * (S.think ? (0.8 + 0.2 * Math.sin(t * 17)) : 1);
      glow(ctx, W / 2, eye[1], W * 0.65, P, 0.30 * fl, 1.0);
      ctx.save(); ctx.translate(W / 2, eye[1]); ctx.scale(1, 0.05);
      const g = ctx.createRadialGradient(0, 0, 0, 0, 0, W * 0.58); g.addColorStop(0, rgba([255, 235, 255], 0.9 * fl)); g.addColorStop(0.25, rgba(P, 0.55 * fl)); g.addColorStop(1, rgba(P, 0));
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, W * 0.58, 0, TAU); ctx.fill(); ctx.restore();
      glow(ctx, eye[0], eye[1], W * 0.11, [255, 190, 255], 0.9 * fl, 1.3);
      ctx.globalCompositeOperation = 'source-over';
    };
  };

  KINDS.neural = function (W, H) {                               // head as a living neural graph: scattered nodes, k-nearest links, travelling impulses
    const head = headMesh(70, 84), bust = bustMesh(14, 60), R = rng(21);
    const pts = [], layer = [];
    const add = (m, count, minNz, lay) => { for (let n = 0; n < count; n++) { const k = Math.floor(R() * m.count); if (m.nrm[k * 3 + 2] < minNz && R() < 0.5) continue; pts.push([m.pos[k * 3] + (R() - .5) * .02, m.pos[k * 3 + 1] + (R() - .5) * .02, m.pos[k * 3 + 2] + (R() - .5) * .02]); layer.push(lay); } };
    add(head, 430, -1, 0); add(bust, 90, -1, 0);
    for (let n = 0; n < 110; n++) { const a = R() * TAU, b = Math.acos(2 * R() - 1), r = 0.62 * Math.cbrt(R()); pts.push([Math.sin(b) * Math.sin(a) * r * 0.95, 0.30 + Math.cos(b) * r * 0.72, Math.sin(b) * Math.cos(a) * r * 0.9 - 0.06]); layer.push(1); }
    const edges = [], deg = new Array(pts.length).fill(0);
    for (let a = 0; a < pts.length; a++) {
      const near = [];
      for (let b = 0; b < pts.length; b++) if (a !== b && layer[a] === layer[b]) near.push([Math.hypot(pts[a][0] - pts[b][0], pts[a][1] - pts[b][1], pts[a][2] - pts[b][2]), b]);
      near.sort((p, q) => p[0] - q[0]);
      for (let k = 0; k < 4; k++) if (near[k] && near[k][0] < 0.34) { edges.push([a, near[k][1], layer[a]]); deg[a]++; deg[near[k][1]]++; }
    }
    const sig = Array.from({ length: 64 }, () => ({ e: Math.floor(R() * edges.length), p: R(), v: 0.3 + R() * 0.7, pink: R() < 0.28 }));
    const cam = new Cam(W, H, W * 0.285, W / 2, H * 0.40);
    const C = [110, 200, 255], P = [255, 110, 210];
    return function frame(ctx, t, S) {
      ctx.clearRect(0, 0, W, H); ctx.globalCompositeOperation = 'lighter';
      const yaw = Math.sin(t * S.spin * 0.8) * 0.8, pitch = -0.03;
      glow(ctx, W / 2, H * 0.40, W * 0.5, [40, 90, 255], 0.22 * S.glow, 1);
      const sp = pts.map(p => projPoint(cam, p[0], p[1], p[2], yaw, pitch));
      const b = [newBuckets(4), newBuckets(4)];
      for (const [i, j, l] of edges) {
        const z = (sp[i][2] + sp[j][2]) / 2, a = clamp(0.20 + z * 0.62, 0.04, 0.99) * S.glow * (l ? 1.2 : 1);
        const B = b[l][Math.min(3, Math.floor(clamp(a, 0, .999) * 4))]; B.path.moveTo(sp[i][0], sp[i][1]); B.path.lineTo(sp[j][0], sp[j][1]); B.n++;
      }
      strokeBuckets(ctx, b[0], C, 0.7); strokeBuckets(ctx, b[1], [200, 150, 255], 0.8);
      for (let n = 0; n < sp.length; n++) {
        const z = sp[n][2], a = clamp(0.25 + z * 0.7, 0.08, 1) * S.glow, hub = Math.min(1, deg[n] / 6);
        glow(ctx, sp[n][0], sp[n][1], (2.2 + hub * 2.8) * (0.8 + z * 0.4), layer[n] ? [200, 150, 255] : C, a * (0.55 + hub * 0.5), 1);
      }
      const speed = 0.5 + S.pulse * 0.9;
      for (const s of sig) {
        s.p += s.v * speed * 0.016; if (s.p > 1) { s.p = 0; s.e = Math.floor(Math.random() * edges.length); }
        const [i, j] = edges[s.e], x = lerp(sp[i][0], sp[j][0], s.p), y = lerp(sp[i][1], sp[j][1], s.p);
        glow(ctx, x, y, 8, s.pink ? P : [255, 255, 255], 0.95 * S.glow, 1);
      }
      ctx.globalCompositeOperation = 'source-over';
    };
  };

  KINDS.brain = function (W, H) {                                // rotating translucent brain, pink synapse flashes, HUD ring
    const L = hemisphere(-1, 58, 52), Rr = hemisphere(1, 58, 52), cb = cerebellum();
    const bufs = [Buf(L.count), Buf(Rr.count), Buf(cb.count)], meshes = [L, Rr, cb];
    const cam = new Cam(W, H, W * 0.40, W / 2, H * 0.50), R = rng(3);
    const syn = Array.from({ length: 26 }, () => ({ m: Math.floor(R() * 2), k: Math.floor(R() * L.count), ph: R() * 6, rate: 0.6 + R() * 1.6 }));
    const C = [90, 175, 255];
    return function frame(ctx, t, S) {
      ctx.clearRect(0, 0, W, H); ctx.globalCompositeOperation = 'lighter';
      // HUD ring
      ctx.save(); ctx.translate(W / 2, H / 2);
      for (let r = 0; r < 3; r++) {
        const rad = W * (0.46 - r * 0.045), n = 26 + r * 8;
        ctx.lineWidth = r === 0 ? 2.5 : 1; ctx.strokeStyle = rgba(C, (r === 0 ? 0.55 : 0.28) * S.glow);
        for (let i = 0; i < n; i++) { if ((i * 7 + r * 3) % 5 === 0) continue; const a0 = t * (0.15 + r * 0.1) * (r % 2 ? -1 : 1) + i / n * TAU; ctx.beginPath(); ctx.arc(0, 0, rad, a0, a0 + TAU / n * 0.62); ctx.stroke(); }
      }
      ctx.restore();
      glow(ctx, W / 2, H / 2, W * 0.45, [50, 110, 255], 0.30 * S.glow, 1);
      const yaw = -1.25 + Math.sin(t * (0.25 + S.spin * 0.5)) * 0.55, pitch = -0.22 + Math.sin(t * 0.6) * 0.06;
      const stripe = [];
      for (let m = 0; m < 3; m++) {
        const mesh = meshes[m], buf = bufs[m]; project(mesh, cam, yaw, pitch, buf);
        const b = newBuckets(5);
        for (let i = 0; i < mesh.N - 1; i++) for (let j = 0; j < mesh.M - (mesh.wrap ? 0 : 1); j++) {
          const j1 = (j + 1) % mesh.M, k = i * mesh.M + j, k2 = i * mesh.M + j1, k3 = (i + 1) * mesh.M + j;
          for (const q of [k2, k3]) {
            const f = 1 - Math.abs((buf.nz[k] + buf.nz[q]) / 2), front = (buf.nz[k] + buf.nz[q]) > 0 ? 1 : 0.3;
            const a = (0.18 + 0.8 * f * f) * front * S.glow + 0.05;
            const B = b[Math.min(4, Math.floor(clamp(a, 0, 0.999) * 5))]; B.path.moveTo(buf.sx[k], buf.sy[k]); B.path.lineTo(buf.sx[q], buf.sy[q]);B.n++;
          }
        }
        strokeBuckets(ctx, b, m === 2 ? [120, 200, 255] : C, 0.7);
        // lit surface (additive, order independent) for volume
        for (let i = 0; i < mesh.N - 1; i += 1) for (let j = 0; j < mesh.M - (mesh.wrap ? 0 : 1); j += 1) {
          const j1 = (j + 1) % mesh.M, k = i * mesh.M + j, k1 = i * mesh.M + j1, k2 = (i + 1) * mesh.M + j1, k3 = (i + 1) * mesh.M + j;
          const nz = (buf.nz[k] + buf.nz[k2]) / 2; if (nz <= 0) continue;
          const light = clamp(0.5 * buf.nz[k] + 0.4 * buf.ny[k] + 0.3, 0, 1);
          ctx.fillStyle = rgba([70, 140, 255], (0.05 + 0.40 * light * light) * S.glow);
          ctx.beginPath(); ctx.moveTo(buf.sx[k], buf.sy[k]); ctx.lineTo(buf.sx[k1], buf.sy[k1]); ctx.lineTo(buf.sx[k2], buf.sy[k2]); ctx.lineTo(buf.sx[k3], buf.sy[k3]); ctx.fill();
        }
      }
      for (const s of syn) {
        const buf = bufs[s.m], k = s.k, v = Math.max(0, Math.sin(t * s.rate * (1 + S.pulse * 0.5) + s.ph)); if (buf.nz[k] < -0.1 || v < 0.55) continue;
        glow(ctx, buf.sx[k], buf.sy[k], 15 * v, [255, 80, 170], 0.95 * v * S.glow, 1);
      }
      ctx.globalCompositeOperation = 'source-over';
    };
  };

  KINDS.sphere = function (W, H) {                                // quantum sphere: voice-reactive geodesic with segmented HUD rings
    const S1 = sphereMesh(20, 32, 1, null), buf = Buf(S1.count), cam = new Cam(W, H, W * 0.27, W / 2, H / 2);
    const inner = sphereMesh(12, 18, 0.55, null), ib = Buf(inner.count);
    const C = [110, 205, 255];
    return function frame(ctx, t, S) {
      ctx.clearRect(0, 0, W, H); ctx.globalCompositeOperation = 'lighter';
      glow(ctx, W / 2, H / 2, W * 0.5, [40, 110, 255], 0.3 * S.glow, 1);
      const amp = 0.02 + 0.10 * (S.jaw ? (0.6 + 0.4 * Math.sin(t * 11)) : S.think * 0.4 + 0.15);
      const wob = (m, kk) => { for (let k = 0; k < m.count; k++) { const x = m.pos[k * 3], y = m.pos[k * 3 + 1], z = m.pos[k * 3 + 2]; const d = 1 + amp * Math.sin(x * 5 + t * 4 * S.pulse) * Math.sin(y * 4 - t * 3) * Math.sin(z * 6 + t * 2); m._w = m._w || new Float32Array(m.pos.length); m._w[k * 3] = x * d; m._w[k * 3 + 1] = y * d; m._w[k * 3 + 2] = z * d; } return { pos: m._w, nrm: m.nrm, count: m.count }; };
      const yaw = t * (0.25 + S.spin * 0.6), pitch = 0.35;
      project(wob(S1), cam, yaw, pitch, buf); project(wob(inner), cam, -yaw * 1.4, pitch, ib);
      for (const [m, bf, col, al] of [[S1, buf, C, 1], [inner, ib, [190, 150, 255], 0.8]]) {
        const b = newBuckets(4);
        for (let i = 0; i < m.N - 1; i++) for (let j = 0; j < m.M; j++) {
          const j1 = (j + 1) % m.M, k = i * m.M + j;
          for (const q of [i * m.M + j1, (i + 1) * m.M + j]) {
            const front = (bf.nz[k] + bf.nz[q]) > 0 ? 1 : 0.28, f = 1 - Math.abs((bf.nz[k] + bf.nz[q]) / 2);
            const a = (0.2 + 0.8 * f) * front * S.glow * al; const B = b[Math.min(3, Math.floor(clamp(a, 0, .999) * 4))]; B.path.moveTo(bf.sx[k], bf.sy[k]); B.path.lineTo(bf.sx[q], bf.sy[q]); B.n++;
          }
        }
        strokeBuckets(ctx, b, col, 0.75);
        for (let k = 0; k < m.count; k += 1) { const f = bf.nz[k] > 0 ? 1 : 0.25; glow(ctx, bf.sx[k], bf.sy[k], 3.6, col, 0.55 * f * S.glow * al, 1); }
      }
      glow(ctx, W / 2, H / 2, W * 0.12, [255, 255, 255], (0.6 + 0.3 * Math.sin(t * S.pulse * 3)) * S.glow, 1);
      ctx.save(); ctx.translate(W / 2, H / 2);
      for (let r = 0; r < 3; r++) {
        const rad = W * (0.47 - r * 0.035), n = 18 + r * 10, dir = r % 2 ? -1 : 1;
        ctx.lineWidth = r === 1 ? 3 : 1.2; ctx.strokeStyle = rgba(r === 1 ? [255, 210, 130] : C, (r === 1 ? 0.7 : 0.45) * S.glow);
        for (let i = 0; i < n; i++) { if ((i + r) % 4 === 0) continue; const a0 = dir * t * (0.2 + r * 0.12 + S.think * 0.5) + i / n * TAU; ctx.beginPath(); ctx.arc(0, 0, rad, a0, a0 + TAU / n * 0.55); ctx.stroke(); }
        for (let i = 0; i < 48; i++) { const a = i / 48 * TAU; ctx.beginPath(); ctx.moveTo(Math.cos(a) * (W * 0.485), Math.sin(a) * (W * 0.485)); ctx.lineTo(Math.cos(a) * (W * (i % 4 ? 0.478 : 0.468)), Math.sin(a) * (W * (i % 4 ? 0.478 : 0.468))); ctx.strokeStyle = rgba(C, 0.3 * S.glow); ctx.lineWidth = 1; ctx.stroke(); }
      }
      ctx.restore(); ctx.globalCompositeOperation = 'source-over';
    };
  };

  KINDS.scan = function (W, H) {                                  // gold contour-slice bust with a sweeping scan plane
    const head = headMesh(64, 72), bust = bustMesh(18, 72);
    const hb = Buf(head.count), bb = Buf(bust.count), cam = new Cam(W, H, W * 0.285, W / 2, H * 0.40);
    const G = [255, 200, 120];
    return function frame(ctx, t, S) {
      ctx.clearRect(0, 0, W, H); ctx.globalCompositeOperation = 'lighter';
      glow(ctx, W / 2, H * 0.45, W * 0.55, [255, 150, 60], 0.18 * S.glow, 1);
      const yaw = Math.sin(t * S.spin * 0.9) * 0.7, pitch = -0.05;
      const scanY = 1.0 - ((t * (0.18 + S.scan * 0.5)) % 1) * 3.0;                // sweeps from the crown down through the bust
      const jawD = S.jaw * (0.5 + 0.5 * Math.sin(t * 12)) * 0.06;
      const tmp = head._tmp || (head._tmp = new Float32Array(head.pos.length));
      for (let k = 0; k < head.count; k++) { tmp[k * 3] = head.pos[k * 3]; tmp[k * 3 + 1] = head.pos[k * 3 + 1] - head.aux[k] * jawD; tmp[k * 3 + 2] = head.pos[k * 3 + 2]; }
      project({ pos: tmp, nrm: head.nrm, count: head.count }, cam, yaw, pitch, hb); project(bust, cam, yaw * 0.7, pitch, bb);
      const rows = (m, buf, pos, step) => {
        const bk = newBuckets(6), back = new Path2D(), hot = new Path2D();
        for (let i = 0; i < m.N; i += step) {
          const yv = pos[(i * m.M) * 3 + 1], near = Math.exp(-Math.pow((yv - scanY) / 0.10, 2));
          for (let j = 0; j < m.M; j++) {
            const k = i * m.M + j, q = i * m.M + (j + 1) % m.M, nzs = (buf.nz[k] + buf.nz[q]) / 2;
            if (nzs <= 0) { back.moveTo(buf.sx[k], buf.sy[k]); back.lineTo(buf.sx[q], buf.sy[q]); continue; }
            if (near > 0.3) { hot.moveTo(buf.sx[k], buf.sy[k]); hot.lineTo(buf.sx[q], buf.sy[q]); continue; }
            const lit = clamp(0.62 * nzs + 0.38 * (buf.ny[k] + buf.ny[q]) / 2 - 0.62 * (buf.nx[k] + buf.nx[q]) / 2, 0, 1), f = 1 - nzs;
            const a = clamp(0.07 + 0.95 * lit * lit + 0.35 * f * f, 0, 0.999) * S.glow;
            const B = bk[Math.floor(a * 6)]; B.path.moveTo(buf.sx[k], buf.sy[k]); B.path.lineTo(buf.sx[q], buf.sy[q]); B.n++;
          }
        }
        ctx.lineWidth = 0.9; strokeBuckets(ctx, bk, G, 0.9);
        ctx.lineWidth = 0.6; ctx.strokeStyle = rgba(G, 0.10 * S.glow); ctx.stroke(back);
        ctx.lineWidth = 1.8; ctx.strokeStyle = rgba([255, 245, 220], 0.95); ctx.stroke(hot);
      };
      rows(head, hb, tmp, 1); rows(bust, bb, bust.pos, 1);
      // meridian lines, faint
      ctx.lineWidth = 0.5; ctx.strokeStyle = rgba(G, 0.14 * S.glow);
      for (let j = 0; j < head.M; j += 6) { ctx.beginPath(); let st = false; for (let i = 0; i < head.N; i++) { const k = i * head.M + j; if (hb.nz[k] <= 0) { st = false; continue; } if (!st) { ctx.moveTo(hb.sx[k], hb.sy[k]); st = true; } else ctx.lineTo(hb.sx[k], hb.sy[k]); } ctx.stroke(); }
      // scan plane glow
      const sc = projPoint(cam, 0, scanY, 0, 0, pitch);
      ctx.save(); ctx.translate(W / 2, sc[1]); ctx.scale(1, 0.12);
      const g = ctx.createRadialGradient(0, 0, 0, 0, 0, W * 0.5); g.addColorStop(0, rgba([255, 240, 210], 0.55 * S.glow)); g.addColorStop(0.5, rgba(G, 0.18 * S.glow)); g.addColorStop(1, rgba(G, 0));
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, W * 0.5, 0, TAU); ctx.fill(); ctx.restore();
      const eye = projPoint(cam, 0, 0.215, 0.9, yaw, pitch);
      glow(ctx, eye[0], eye[1], W * 0.07, [255, 225, 170], 0.8 * S.flare, 2.2);
      ctx.globalCompositeOperation = 'source-over';
    };
  };

  /* ---------- mount ---------- */
  function mount(canvas, kind, getMode, size) {
    const W = Math.max(240, Math.min(900, Math.round(size || 360))), H = W, dpr = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = W * dpr; canvas.height = H * dpr; canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    const ctx = canvas.getContext('2d'); ctx.scale(dpr, dpr);
    const frame = KINDS[kind](W, H), S = Object.assign({}, MODES.LISTENING); let raf = 0, last = performance.now(), t0 = last, stopped = false, visible = true;
    if (window.IntersectionObserver) new IntersectionObserver(e => { visible = e[e.length - 1].isIntersecting; }).observe(canvas);
    function loop(now) {
      if (stopped) return;
      if (!visible) { last = now; raf = requestAnimationFrame(loop); return; }
      const target = MODES[getMode()] || MODES.LISTENING, dt = Math.min(0.05, (now - last) / 1000); last = now;
      for (const k in target) S[k] += (target[k] - S[k]) * Math.min(1, dt * 3.2);
      frame(ctx, window.S3D_FREEZE != null ? window.S3D_FREEZE : (now - t0) / 1000, S); raf = requestAnimationFrame(loop);
    }
    raf = requestAnimationFrame(loop);
    return () => { stopped = true; cancelAnimationFrame(raf); };
  }
  window.S3D = { mount, MODES };
})();
