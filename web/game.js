import * as THREE from "https://unpkg.com/three@0.160.0/build/three.module.js";

const TICK_RATE = 60;
const DT = 1 / TICK_RATE;
const JUMP_VELOCITY = 7.0;
const GRAVITY = 20.0;
const CHARM_SPEED = 7.2;
const CHARM_DURATION_TICKS = 600;
const CHARM_RESPAWN_TICKS = 1200; // 20s in 3D Web mode (headless keeps 2700 ticks per Contract v1.1)
const DROPPED_MOTE_TTL_TICKS = 480;
const RESPAWN_WAIT_TICKS = 60;
const PULSE_PUSH_TICKS = 15;
const SHADE_RECOIL_TICKS = 60;
const SHADE_DETECT_R = 12.0;
const SHADE_LOSE_R = 18.0;
const DRIFTER_IDLE_SPEED = 2.0;
const DRIFTER_FAST_SPEED = 7.0;
const DRIFTER_DETECT_R = 15.0;
const DRIFTER_STEAL_R = 1.2;
const DRIFTER_FLEE_TICKS = 240;
const WIND_CYCLE_TICKS = 1800;
const WIND_ACTIVE_TICKS = 300;
const WIND_TELEGRAPH_TICKS = 120;
const WIND_SPEED = 2.0;

// Standardized Palette (Ticket-02)
const PALETTE = {
  sky: 0x0e1430,
  fog: 0x1b2350,
  grass: 0x2f5050,
  sand: 0xc9b48a,
  wood: 0x6b4a2f,
  clouds: 0x12384a,
  lanternLit: 0xffb347,
  lanternCore: 0xffe9b0,
  lanternUnlit: 0x5b5f6e,
  moteCore: 0xfff6c2,
  moteHalo: 0xffe58a,
  shadeBody: 0x120a1a,
  shadeRim: 0x7a3cff,
  shadeStunned: 0x3a3450,
  mayCloak: 0xe8e2d0,
  mayScarf: 0xc8102e,
  gold: 0xf2c14e,
  drifter: 0x8fa3b8,
};

const NIGHT_QUOTES = {
  1: {
    name: "Đêm 1 – Đảo Bến",
    quote: "Ông Đăng dặn: \"Sương đen đã phủ kín Đảo Bến rồi Mây ạ. Gom đom đóm thắp lại 5 Đèn Lồng Lớn, ánh sáng sẽ đẩy lùi Bóng Mực.\"",
  },
  2: {
    name: "Đêm 2 – Đảo Cau",
    quote: "Ông Đăng dặn: \"Hai bờ Đảo Cau nối bằng cầu tre mảnh và bục nhảy gió. Cẩn thận Gió Lạc — chúng sẽ cướp đom đóm nếu cháu mang quá nhiều!\"",
  },
  3: {
    name: "Đêm 3 – Đảo Chuông",
    quote: "Ông Đăng dặn: \"Đêm cuối trên Đảo Chuông ba tầng. Gió mạnh sẽ thổi từng cơn, hãy mượn Bùa Gió và thắp sáng ngọn đèn trên đỉnh tháp chuông!\"",
  },
};

function ringPoints(count, radius, startDeg = 0, stepDeg = null, cx = 0, cy = 0, cz = 0) {
  const step = stepDeg ?? 360 / count;
  const pts = [];
  for (let i = 0; i < count; i++) {
    const a = ((startDeg + i * step) * Math.PI) / 180;
    pts.push([cx + radius * Math.cos(a), cy, cz + radius * Math.sin(a)]);
  }
  return pts;
}

function getNightDef(night) {
  if (night === 1) {
    return {
      night: 1,
      duration: 300,
      shadeSpeed: 4.0,
      shadeInterval: 480,
      shadeMax: 6,
      hasDrifters: false,
      hasWind: false,
      lanterns: [
        { id: "L1", pos: [0, 0, 25] },
        { id: "L2", pos: [23.8, 0, 7.7] },
        { id: "L3", pos: [14.7, 0, -20.2] },
        { id: "L4", pos: [-14.7, 0, -20.2] },
        { id: "L5", pos: [-23.8, 0, 7.7] },
      ],
      moteSpawns: [...ringPoints(8, 12, 0, 45), ...ringPoints(16, 33, 0, 22.5)],
      shadeSpawns: ringPoints(12, 37, 15, 30),
      charms: [],
      jumpPads: [],
    };
  }
  if (night === 2) {
    const d1 = Math.hypot(50, -18);
    const d2 = Math.hypot(-50, 18);
    return {
      night: 2,
      duration: 330,
      shadeSpeed: 4.0,
      shadeInterval: 420,
      shadeMax: 8,
      hasDrifters: true,
      hasWind: false,
      lanterns: [
        { id: "L1", pos: [0, 0, 20] },
        { id: "L2", pos: [17, 0, -10] },
        { id: "L3", pos: [-17, 0, -10] },
        { id: "L4", pos: [70, 0, 20] },
        { id: "L5", pos: [87, 0, -10] },
        { id: "L6", pos: [53, 0, -10] },
      ],
      moteSpawns: [
        ...ringPoints(4, 10, 0, 90, 0),
        ...ringPoints(8, 22, 0, 45, 0),
        ...ringPoints(4, 10, 0, 90, 70),
        ...ringPoints(8, 22, 0, 45, 70),
      ],
      shadeSpawns: [...ringPoints(8, 26, 22.5, 45, 0), ...ringPoints(8, 26, 22.5, 45, 70)],
      charms: [{ id: "C1", pos: [35, 0, 0] }],
      jumpPads: [
        { pos: [20, 0, 18], r: 1.0, vy: 14, vh: 24, dx: 50 / d1, dz: -18 / d1 },
        { pos: [50, 0, -18], r: 1.0, vy: 14, vh: 24, dx: -50 / d2, dz: 18 / d2 },
      ],
    };
  }
  return {
    night: 3,
    duration: 360,
    shadeSpeed: 4.5,
    shadeInterval: 360,
    shadeMax: 10,
    hasDrifters: true,
    hasWind: true,
    lanterns: [
      { id: "L1", pos: [0, 6, 6] },
      { id: "L2", pos: [18, 3, 10] },
      { id: "L3", pos: [-18, 3, 10] },
      { id: "L4", pos: [35, 0, -10] },
      { id: "L5", pos: [-35, 0, -10] },
      { id: "L6", pos: [20, 0, -35] },
      { id: "L7", pos: [-20, 0, -35] },
    ],
    moteSpawns: [
      ...ringPoints(18, 34, 0, 20, 0, 0, 0),
      ...ringPoints(8, 18, 20, 20, 0, 3, 0),
      ...ringPoints(4, 5, 45, 90, 0, 6, 0),
    ],
    shadeSpawns: ringPoints(16, 43, 0, 22.5, 0, 0, 0),
    charms: [
      { id: "C1", pos: [30, 0, 25] },
      { id: "C2", pos: [-30, 0, 25] },
    ],
    jumpPads: [{ pos: [0, 3, 13], r: 1.0, vy: 12, vh: 8, dx: 0, dz: -1 }],
  };
}

function night3RampHeight(x, z) {
  for (const deg of [30, 150]) {
    const ang = (deg * Math.PI) / 180;
    const ux = Math.cos(ang);
    const uz = Math.sin(ang);
    const proj = x * ux + z * uz;
    const perp = Math.abs(-x * uz + z * ux);
    if (proj >= 24 && proj <= 30 && perp <= 1.5) {
      return (3.0 * (30.0 - proj)) / 6.0;
    }
  }
  return null;
}

function groundHeight(night, x, z, curY = 0) {
  if (night === 1) return Math.hypot(x, z) <= 40 ? 0 : null;
  if (night === 2) {
    const inA = Math.hypot(x, z) <= 28;
    const inB = Math.hypot(x - 70, z) <= 28;
    const bridge = x >= 26 && x <= 44 && z >= -2 && z <= 2;
    return inA || inB || bridge ? 0 : null;
  }
  const r = Math.hypot(x, z);
  if (r > 45) return null;
  const surfaces = [0];
  const rh = night3RampHeight(x, z);
  if (rh !== null) surfaces.push(rh);
  if (r >= 12 && r <= 24 && z > 0) surfaces.push(3);
  if (r <= 8) surfaces.push(6);
  const reachable = surfaces.filter((h) => h <= curY + 0.35);
  return reachable.length ? Math.max(...reachable) : 0;
}

function isBlockedNight3(oldX, oldZ, newX, newZ, curY) {
  const rNew = Math.hypot(newX, newZ);
  if (rNew < 2.0 && curY >= 5.5) return true;
  const rh = night3RampHeight(newX, newZ);
  if (rh !== null && rh <= curY + 0.55) return false;
  if (rNew <= 8.0 && curY < 5.65 && Math.hypot(oldX, oldZ) > 8.0) return true;
  if (rNew >= 12 && rNew <= 24 && newZ > 0 && curY < 2.65) {
    const rOld = Math.hypot(oldX, oldZ);
    if (!(rOld >= 12 && rOld <= 24 && oldZ > 0)) return true;
  }
  return false;
}

// Procedural Web Audio Engine (zero external audio files)
class SoundFX {
  constructor() {
    this.ctx = null;
    this.volume = 0.6;
    this.ambientGain = null;
  }
  ensure() {
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      this.ctx = new AC();
      const osc = this.ctx.createOscillator();
      this.ambientGain = this.ctx.createGain();
      osc.type = "sine";
      osc.frequency.value = 110;
      this.ambientGain.gain.value = this.volume * 0.03;
      osc.connect(this.ambientGain).connect(this.ctx.destination);
      osc.start();
    }
    if (this.ctx && this.ctx.state === "suspended") this.ctx.resume();
  }
  setVolume(v) {
    this.volume = v;
    if (this.ambientGain) this.ambientGain.gain.value = v * 0.03;
  }
  beep(freq, dur = 0.12, type = "sine", slideTo = null) {
    if (this.volume <= 0.01) return;
    this.ensure();
    if (!this.ctx) return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const g = this.ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, now);
    if (slideTo) osc.frequency.exponentialRampToValueAtTime(slideTo, now + dur);
    g.gain.setValueAtTime(this.volume * 0.18, now);
    g.gain.exponentialRampToValueAtTime(0.001, now + dur);
    osc.connect(g).connect(this.ctx.destination);
    osc.start(now);
    osc.stop(now + dur);
  }
  pickup() { this.beep(660, 0.1, "sine", 990); }
  lanternLit() { this.beep(440, 0.25, "triangle", 880); }
  pulse() { this.beep(320, 0.28, "sine", 140); }
  hit() { this.beep(150, 0.22, "sawtooth", 70); }
  jump() { this.beep(280, 0.1, "sine", 480); }
  dash() { this.beep(520, 0.12, "triangle", 260); }
  spawn() { this.beep(180, 0.3, "sawtooth", 120); }
  tick10s() { this.beep(880, 0.06, "square"); }
  win() { this.beep(523, 0.16, "triangle", 784); }
  lose() { this.beep(240, 0.35, "sawtooth", 110); }
}

function distXZ(a, b) {
  return Math.hypot(a[0] - b[0], a[2] - b[2]);
}

function dist3D(a, b) {
  return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
}

async function loadTuning() {
  try {
    const res = await fetch("/game.contract.json");
    if (res.ok) {
      const data = await res.json();
      if (data?.tuning) return data.tuning;
    }
  } catch { /* fallback */ }
  return {
    player_speed: 6.0, dash_speed: 14.0, dash_duration_s: 0.2, dash_cooldown_s: 1.5,
    carry_capacity: 10, lantern_cost: 10, pickup_radius: 1.0, interact_radius: 2.0,
    pulse_cost: 3, pulse_radius: 5.0, flames: 3, invuln_s: 1.5, hit_drop_ratio: 0.5,
    pulse_stun_s: 2.0, pulse_push_m: 4.0, pulse_cooldown_s: 3.0, safe_radius: 6.0,
    shade_hit_radius: 1.0, score: { per_mote: 10, per_lantern: 100, per_stun: 5, per_second_left: 2, per_flame_left: 50 },
  };
}

class DaoDenLongApp {
  constructor(tuning) {
    this.tuning = tuning;
    this.sfx = new SoundFX();
    this.settings = this.loadSettings();
    this.sfx.setVolume(this.settings.volume / 100);

    this.keys = {};
    this.prevKeys = {};
    this.camYaw = 0;
    this.dragging = false;
    this.lastMouseX = 0;
    this.mode = "menu"; // menu | intro | playing | paused | result
    this.settingsReturnMode = "menu";
    this.currentNight = 1;
    this.campaignTotalScore = 0;
    this.lastCountdownSec = 11;

    this.buildMoteBar();
    this.initScene();
    this.initUI();
    this.initInput();

    this.accumulator = 0;
    this.lastFrameTime = performance.now();
    this.animate(this.lastFrameTime);
  }

  loadSettings() {
    try {
      const saved = JSON.parse(localStorage.getItem("dao_den_long_settings") || "{}");
      return {
        volume: typeof saved.volume === "number" ? saved.volume : 60,
        sens: typeof saved.sens === "number" ? saved.sens : 100,
      };
    } catch {
      return { volume: 60, sens: 100 };
    }
  }

  saveSettings() {
    localStorage.setItem("dao_den_long_settings", JSON.stringify(this.settings));
  }

  buildMoteBar() {
    const bar = document.getElementById("mote-bar");
    bar.innerHTML = "";
    this.moteSlots = [];
    for (let i = 0; i < 10; i++) {
      const el = document.createElement("div");
      el.className = "mote-slot";
      bar.appendChild(el);
      this.moteSlots.push(el);
    }
  }

  initScene() {
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(PALETTE.sky);
    this.scene.fog = new THREE.FogExp2(PALETTE.fog, 0.011);

    this.camera = new THREE.PerspectiveCamera(58, window.innerWidth / window.innerHeight, 0.1, 320);
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    document.getElementById("canvas-container").appendChild(this.renderer.domElement);

    this.ambientLight = new THREE.AmbientLight(0xdce6ff, 0.15);
    this.scene.add(this.ambientLight);
    this.hemiLight = new THREE.HemisphereLight(0x8fa3d9, 0x12384a, 0.4);
    this.scene.add(this.hemiLight);
    this.moonLight = new THREE.DirectionalLight(0xffe9b0, 0.45);
    this.moonLight.position.set(30, 55, -25);
    this.scene.add(this.moonLight);

    // Stars
    const starGeo = new THREE.BufferGeometry();
    const verts = [];
    for (let i = 0; i < 400; i++) {
      const t = Math.random() * Math.PI * 2;
      const p = Math.random() * Math.PI * 0.45;
      verts.push(180 * Math.sin(p) * Math.cos(t), 180 * Math.cos(p) + 10, 180 * Math.sin(p) * Math.sin(t));
    }
    starGeo.setAttribute("position", new THREE.Float32BufferAttribute(verts, 3));
    this.scene.add(new THREE.Points(starGeo, new THREE.PointsMaterial({ color: PALETTE.moteCore, size: 0.7 })));

    // Cloud sea
    const clouds = new THREE.Mesh(
      new THREE.CircleGeometry(280, 32),
      new THREE.MeshBasicMaterial({ color: PALETTE.clouds, transparent: true, opacity: 0.8 })
    );
    clouds.rotation.x = -Math.PI / 2;
    clouds.position.y = -10.5;
    this.scene.add(clouds);

    this.worldGroup = new THREE.Group();
    this.lanternGroup = new THREE.Group();
    this.moteGroup = new THREE.Group();
    this.shadeGroup = new THREE.Group();
    this.drifterGroup = new THREE.Group();
    this.charmGroup = new THREE.Group();
    this.fxGroup = new THREE.Group();
    this.scene.add(
      this.worldGroup, this.lanternGroup, this.moteGroup,
      this.shadeGroup, this.drifterGroup, this.charmGroup, this.fxGroup
    );

    this.playerGroup = this.buildPlayerMesh();
    this.scene.add(this.playerGroup);

    window.addEventListener("resize", () => {
      this.camera.aspect = window.innerWidth / window.innerHeight;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(window.innerWidth, window.innerHeight);
    });
  }

  buildPlayerMesh() {
    const g = new THREE.Group();
    const cloak = new THREE.Mesh(
      new THREE.ConeGeometry(0.52, 1.32, 10),
      new THREE.MeshStandardMaterial({ color: PALETTE.mayCloak, roughness: 0.75 })
    );
    cloak.position.y = 0.66;
    const scarf = new THREE.Mesh(
      new THREE.TorusGeometry(0.32, 0.08, 8, 16),
      new THREE.MeshStandardMaterial({ color: PALETTE.mayScarf, roughness: 0.6 })
    );
    scarf.rotation.x = Math.PI / 2;
    scarf.position.y = 1.28;
    const head = new THREE.Mesh(
      new THREE.SphereGeometry(0.3, 12, 12),
      new THREE.MeshStandardMaterial({ color: 0xf7dfc4 })
    );
    head.position.y = 1.5;
    const hat = new THREE.Mesh(
      new THREE.ConeGeometry(0.86, 0.52, 16),
      new THREE.MeshStandardMaterial({ color: PALETTE.sand, roughness: 0.8 })
    );
    hat.position.y = 1.86;
    const miniLantern = new THREE.Mesh(
      new THREE.SphereGeometry(0.13, 10, 10),
      new THREE.MeshBasicMaterial({ color: PALETTE.lanternLit })
    );
    miniLantern.position.set(0.65, 1.48, 0.22);
    const pLight = new THREE.PointLight(PALETTE.lanternLit, 2.0, 11);
    pLight.position.set(0.65, 1.5, 0.22);

    // Translucent pale-gold shield aura around May (visible while shieldTicks > 0)
    this.shieldSphere = new THREE.Mesh(
      new THREE.SphereGeometry(1.35, 24, 18),
      new THREE.MeshStandardMaterial({
        color: 0xffe680,
        emissive: 0xffd166,
        emissiveIntensity: 0.45,
        transparent: true,
        opacity: 0.28,
        roughness: 0.2,
        depthWrite: false,
      })
    );
    this.shieldSphere.position.y = 1.05;
    this.shieldSphere.visible = false;

    g.add(cloak, scarf, head, hat, miniLantern, pLight, this.shieldSphere);
    return g;
  }

  buildWorldGeometry(night) {
    this.worldGroup.clear();
    const grassMat = new THREE.MeshStandardMaterial({ color: PALETTE.grass, roughness: 0.9 });
    const sandMat = new THREE.MeshStandardMaterial({ color: PALETTE.sand, roughness: 0.92 });
    const woodMat = new THREE.MeshStandardMaterial({ color: PALETTE.wood, roughness: 0.85 });

    if (night === 1) {
      const cyl = new THREE.Mesh(new THREE.CylinderGeometry(40, 36, 4, 48), grassMat);
      cyl.position.y = -2;
      this.worldGroup.add(cyl);
    } else if (night === 2) {
      const a = new THREE.Mesh(new THREE.CylinderGeometry(28, 25, 4, 40), grassMat);
      a.position.set(0, -2, 0);
      const b = new THREE.Mesh(new THREE.CylinderGeometry(28, 25, 4, 40), grassMat);
      b.position.set(70, -2, 0);
      const bridge = new THREE.Mesh(new THREE.BoxGeometry(18, 0.5, 4), woodMat);
      bridge.position.set(35, -0.25, 0);
      this.worldGroup.add(a, b, bridge);
    } else {
      const t0 = new THREE.Mesh(new THREE.CylinderGeometry(45, 40, 4, 48), grassMat);
      t0.position.y = -2;
      this.worldGroup.add(t0);

      // Tier 1 half-annulus (Y=3, r=12..24, z>0)
      const shape = new THREE.Shape();
      shape.absarc(0, 0, 24, 0, Math.PI, false);
      shape.absarc(0, 0, 12, Math.PI, 0, true);
      const t1Geo = new THREE.ExtrudeGeometry(shape, { depth: 3, bevelEnabled: false });
      t1Geo.rotateX(Math.PI / 2);
      const t1 = new THREE.Mesh(t1Geo, sandMat);
      t1.position.y = 3;
      this.worldGroup.add(t1);

      // Tier 2 center disk (Y=6, r=8)
      const t2 = new THREE.Mesh(new THREE.CylinderGeometry(8, 8, 6, 32), grassMat);
      t2.position.y = 3;
      this.worldGroup.add(t2);

      // Bell Tower (r=2, h=8 at center of Tier 2)
      const tower = new THREE.Mesh(new THREE.CylinderGeometry(2, 2, 8, 16), woodMat);
      tower.position.y = 10;
      const roof = new THREE.Mesh(new THREE.ConeGeometry(2.8, 2.2, 8), new THREE.MeshStandardMaterial({ color: PALETTE.mayScarf }));
      roof.position.y = 15.1;
      this.worldGroup.add(tower, roof);

      // 2 Ramps at 30 deg & 150 deg (r=30 Y=0 to r=24 Y=3)
      for (const deg of [30, 150]) {
        const ang = (deg * Math.PI) / 180;
        const ramp = new THREE.Mesh(new THREE.BoxGeometry(6.71, 0.3, 3.0), woodMat);
        ramp.position.set(27 * Math.cos(ang), 1.5, 27 * Math.sin(ang));
        ramp.rotation.y = -ang;
        ramp.rotation.z = -Math.atan2(3, 6);
        this.worldGroup.add(ramp);
      }
    }

    // Jump pads
    for (const pad of this.nightDef.jumpPads) {
      const m = new THREE.Mesh(
        new THREE.CylinderGeometry(pad.r, pad.r * 1.15, 0.22, 20),
        new THREE.MeshBasicMaterial({ color: PALETTE.gold })
      );
      m.position.set(pad.pos[0], pad.pos[1] + 0.11, pad.pos[2]);
      this.worldGroup.add(m);
    }
  }

  initUI() {
    const show = (id) => {
      for (const s of ["screen-menu", "screen-intro", "screen-pause", "screen-settings", "screen-result"]) {
        document.getElementById(s).classList.toggle("hidden", s !== id);
      }
      document.getElementById("hud").classList.toggle("hidden", id !== null);
    };
    this.showScreen = show;

    document.getElementById("btn-start-campaign").addEventListener("click", () => {
      this.campaignTotalScore = 0;
      this.startNightIntro(1);
    });
    document.querySelectorAll(".btn-night-pick").forEach((btn) => {
      btn.addEventListener("click", () => {
        this.campaignTotalScore = 0;
        this.startNightIntro(Number(btn.dataset.night));
      });
    });
    document.getElementById("btn-intro-go").addEventListener("click", () => {
      this.sfx.ensure();
      this.startNightPlay(this.currentNight);
    });
    document.getElementById("btn-resume").addEventListener("click", () => this.togglePause());
    document.getElementById("btn-pause-retry").addEventListener("click", () => this.startNightPlay(this.currentNight));
    document.getElementById("btn-pause-menu").addEventListener("click", () => {
      this.mode = "menu";
      this.showScreen("screen-menu");
    });

    const openSettings = (ret) => {
      this.settingsReturnMode = ret;
      document.getElementById("opt-volume").value = this.settings.volume;
      document.getElementById("opt-volume-val").textContent = `${this.settings.volume}%`;
      document.getElementById("opt-sens").value = this.settings.sens;
      document.getElementById("opt-sens-val").textContent = `${(this.settings.sens / 100).toFixed(1)}x`;
      this.showScreen("screen-settings");
    };
    document.getElementById("btn-menu-settings").addEventListener("click", () => openSettings("menu"));
    document.getElementById("btn-pause-settings").addEventListener("click", () => openSettings("paused"));
    document.getElementById("opt-volume").addEventListener("input", (e) => {
      this.settings.volume = Number(e.target.value);
      document.getElementById("opt-volume-val").textContent = `${this.settings.volume}%`;
      this.sfx.setVolume(this.settings.volume / 100);
    });
    document.getElementById("opt-sens").addEventListener("input", (e) => {
      this.settings.sens = Number(e.target.value);
      document.getElementById("opt-sens-val").textContent = `${(this.settings.sens / 100).toFixed(1)}x`;
    });
    document.getElementById("btn-settings-close").addEventListener("click", () => {
      this.saveSettings();
      this.showScreen(this.settingsReturnMode === "paused" ? "screen-pause" : "screen-menu");
    });

    document.getElementById("btn-next-night").addEventListener("click", () => this.startNightIntro(this.currentNight + 1));
    document.getElementById("btn-retry-night").addEventListener("click", () => this.startNightPlay(this.currentNight));
    document.getElementById("btn-result-menu").addEventListener("click", () => {
      this.mode = "menu";
      this.showScreen("screen-menu");
    });
  }

  initInput() {
    window.addEventListener("keydown", (e) => {
      if ((e.code === "Escape" || e.code === "KeyP") && (this.mode === "playing" || this.mode === "paused")) {
        this.togglePause();
        return;
      }
      this.keys[e.code] = true;
    });
    window.addEventListener("keyup", (e) => {
      this.keys[e.code] = false;
    });
    window.addEventListener("mousedown", (e) => {
      this.dragging = true;
      this.lastMouseX = e.clientX;
    });
    window.addEventListener("mouseup", () => { this.dragging = false; });
    window.addEventListener("mousemove", (e) => {
      if (!this.dragging || this.mode !== "playing") return;
      const dx = e.clientX - this.lastMouseX;
      this.lastMouseX = e.clientX;
      this.camYaw -= dx * 0.006 * (this.settings.sens / 100);
    });
  }

  togglePause() {
    if (this.mode === "playing") {
      this.mode = "paused";
      this.showScreen("screen-pause");
    } else if (this.mode === "paused") {
      this.mode = "playing";
      this.showScreen(null);
      this.lastFrameTime = performance.now();
    }
  }

  startNightIntro(night) {
    this.currentNight = night;
    this.mode = "intro";
    const info = NIGHT_QUOTES[night];
    document.getElementById("intro-eyebrow").textContent = `ĐÊM ${night} / 3`;
    document.getElementById("intro-title").textContent = info.name;
    document.getElementById("intro-quote").textContent = info.quote;
    this.showScreen("screen-intro");
  }

  startNightPlay(night) {
    this.currentNight = night;
    this.nightDef = getNightDef(night);
    this.mode = "playing";
    this.showScreen(null);
    this.simTick = 0;
    this.score = 0;
    this.timeLeft = this.nightDef.duration;
    this.lastCountdownSec = 11;
    this.playerPos = [0, 0, 0];
    this.playerVel = [0, 0, 0];
    this.facingX = 0;
    this.facingZ = 1;
    this.grounded = true;
    this.flames = this.tuning.flames;
    this.carried = 0;
    this.invulnTicks = 0;
    this.dashCdTicks = 0;
    this.dashTicksLeft = 0;
    this.pulseCdTicks = 0;
    this.charmTicks = 0;
    this.magnetTicks = 0;
    this.shieldTicks = 0;
    this.respawnWaitTicks = 0;
    this.padLaunched = false;
    this.windActive = false;
    this.windDirDeg = 0;
    this.windTicksLeft = 0;
    this.camYaw = 0;
    this.pulseWave = null;

    this.buildWorldGeometry(night);
    this.lanternGroup.clear();
    this.moteGroup.clear();
    this.shadeGroup.clear();
    this.drifterGroup.clear();
    this.charmGroup.clear();
    this.fxGroup.clear();

    // Lanterns
    this.lanterns = this.nightDef.lanterns.map((l) => {
      const g = new THREE.Group();
      const post = new THREE.Mesh(
        new THREE.CylinderGeometry(0.28, 0.4, 3.6, 8),
        new THREE.MeshStandardMaterial({ color: PALETTE.wood })
      );
      post.position.y = 1.8;
      const orbMat = new THREE.MeshStandardMaterial({ color: PALETTE.lanternUnlit, emissive: 0x000000, emissiveIntensity: 0 });
      const orb = new THREE.Mesh(new THREE.OctahedronGeometry(0.85, 1), orbMat);
      orb.position.y = 4.1;
      const light = new THREE.PointLight(PALETTE.lanternLit, 0, 16);
      light.position.y = 4.1;
      const safeRing = new THREE.Mesh(
        new THREE.RingGeometry(5.85, 6.0, 36),
        new THREE.MeshBasicMaterial({ color: PALETTE.lanternLit, transparent: true, opacity: 0, side: THREE.DoubleSide })
      );
      safeRing.rotation.x = -Math.PI / 2;
      safeRing.position.y = 0.05;
      g.add(post, orb, light, safeRing);
      g.position.set(l.pos[0], l.pos[1], l.pos[2]);
      g.userData = { orbMat, light, safeRing };
      this.lanternGroup.add(g);
      return { id: l.id, pos: [...l.pos], lit: false, deposited: 0, mesh: g };
    });

    // Initial 20 motes
    this.motes = [];
    const pts = [...this.nightDef.moteSpawns].sort(() => Math.random() - 0.5);
    for (const p of pts.slice(0, 20)) this.addMote(p, "random", null);

    // Shades & Drifters (spawn on schedule)
    this.shades = [];
    this.drifters = [];

    // Charms (Standard Wind Charms)
    this.charms = this.nightDef.charms.map((c) => {
      const m = new THREE.Mesh(
        new THREE.OctahedronGeometry(0.45, 0),
        new THREE.MeshStandardMaterial({ color: PALETTE.mayScarf, emissive: PALETTE.gold, emissiveIntensity: 0.45 })
      );
      m.position.set(c.pos[0], c.pos[1] + 1.0, c.pos[2]);
      this.charmGroup.add(m);
      return { id: c.id, pos: [...c.pos], available: true, respawnTicks: 0, mesh: m };
    });

    // Creative 3D-only Bonus Charms (disabled in headless so Test Contract v1.1 is untouched)
    const bonusDefs =
      night === 1
        ? [
            { kind: "magnet", pos: [14, 0, 14] },
            { kind: "shield", pos: [-14, 0, -14] },
          ]
        : night === 2
          ? [
              { kind: "magnet", pos: [12, 0, -12] },
              { kind: "shield", pos: [58, 0, 12] },
            ]
          : [
              { kind: "magnet", pos: [26, 0, -18] },
              { kind: "shield", pos: [-26, 0, -18] },
            ];
    this.bonusCharms = bonusDefs.map((b) => {
      const col = b.kind === "magnet" ? 0x38e8c6 : 0xffd166;
      const m = new THREE.Mesh(
        new THREE.TorusKnotGeometry(0.32, 0.1, 32, 8),
        new THREE.MeshStandardMaterial({ color: col, emissive: col, emissiveIntensity: 0.65 })
      );
      m.position.set(b.pos[0], b.pos[1] + 1.05, b.pos[2]);
      this.charmGroup.add(m);
      return { kind: b.kind, pos: [...b.pos], available: true, respawnTicks: 0, mesh: m };
    });

    document.getElementById("hud-night-label").textContent = NIGHT_QUOTES[night].name;
    this.updateAtmosphere();
    this.updateHUD();
  }

  addMote(pos, kind, ttlTicks) {
    const mesh = new THREE.Mesh(
      new THREE.SphereGeometry(0.3, 10, 10),
      new THREE.MeshBasicMaterial({ color: kind === "dropped" ? PALETTE.lanternLit : PALETTE.moteCore })
    );
    mesh.position.set(pos[0], pos[1] + 0.85, pos[2]);
    this.moteGroup.add(mesh);
    this.motes.push({ pos: [...pos], kind, ttlTicks, spawnTick: this.simTick, phase: Math.random() * 6.28, mesh });
  }

  addShade(pos) {
    const g = new THREE.Group();
    const bodyMat = new THREE.MeshStandardMaterial({
      color: PALETTE.shadeBody,
      emissive: PALETTE.shadeRim,
      emissiveIntensity: 0.5,
    });
    const body = new THREE.Mesh(new THREE.DodecahedronGeometry(0.78, 0), bodyMat);
    body.position.y = 1.0;
    g.add(body);
    g.position.set(pos[0], pos[1], pos[2]);
    g.userData = { bodyMat };
    this.shadeGroup.add(g);
    this.shades.push({
      pos: [...pos], state: "wander", stateTicks: 0, pushTicks: 0,
      pushVx: 0, pushVz: 0, recoilVx: 0, recoilVz: 0, safePush: 0, mesh: g,
    });
    this.sfx.spawn();
  }

  addDrifter(pos) {
    const mesh = new THREE.Mesh(
      new THREE.ConeGeometry(0.45, 1.5, 6),
      new THREE.MeshStandardMaterial({ color: PALETTE.drifter, emissive: PALETTE.drifter, emissiveIntensity: 0.35 })
    );
    mesh.rotation.x = Math.PI / 2;
    mesh.position.set(pos[0], pos[1] + 1.5, pos[2]);
    this.drifterGroup.add(mesh);
    this.drifters.push({ pos: [...pos], state: "idle", stolen: 0, fleeTicks: 0, hasStolen: false, angle: 0, mesh });
  }

  updateAtmosphere() {
    const lit = this.lanterns.filter((l) => l.lit).length;
    const ratio = lit / this.lanterns.length;
    this.ambientLight.intensity = 0.15 + 0.55 * ratio;
    this.hemiLight.intensity = 0.35 + 0.5 * ratio;
  }

  stepSim() {
    if (this.mode !== "playing") return;
    this.simTick += 1;
    const st = this.simTick;

    if (this.keys["KeyQ"] || this.keys["ArrowLeft"]) this.camYaw += 2.0 * DT;
    if (this.keys["KeyR"] || this.keys["ArrowRight"]) this.camYaw -= 2.0 * DT;

    const jumpP = Boolean(this.keys["Space"]) && !Boolean(this.prevKeys["Space"]);
    const interactP = Boolean(this.keys["KeyE"]) && !Boolean(this.prevKeys["KeyE"]);
    const pulseP = Boolean(this.keys["KeyF"]) && !Boolean(this.prevKeys["KeyF"]);
    const dashP = (Boolean(this.keys["ShiftLeft"]) || Boolean(this.keys["ShiftRight"]))
      && !(Boolean(this.prevKeys["ShiftLeft"]) || Boolean(this.prevKeys["ShiftRight"]));
    this.prevKeys = { ...this.keys };

    // Timers
    this.timeLeft = Math.max(0, this.nightDef.duration - st / TICK_RATE);
    if (this.timeLeft <= 10 && Math.ceil(this.timeLeft) < this.lastCountdownSec && this.timeLeft > 0) {
      this.lastCountdownSec = Math.ceil(this.timeLeft);
      this.sfx.tick10s();
    }
    if (this.dashCdTicks > 0) this.dashCdTicks -= 1;
    if (this.pulseCdTicks > 0) this.pulseCdTicks -= 1;
    if (this.invulnTicks > 0) this.invulnTicks -= 1;
    if (this.charmTicks > 0) this.charmTicks -= 1;
    if (this.magnetTicks > 0) this.magnetTicks -= 1;
    if (this.shieldTicks > 0) this.shieldTicks -= 1;

    // Dropped mote TTL
    this.motes = this.motes.filter((m) => {
      if (m.ttlTicks !== null) {
        m.ttlTicks -= 1;
        if (m.ttlTicks <= 0) {
          this.moteGroup.remove(m.mesh);
          return false;
        }
      }
      return true;
    });

    // Charm respawn
    for (const c of this.charms) {
      if (!c.available) {
        c.respawnTicks -= 1;
        if (c.respawnTicks <= 0) {
          c.available = true;
          c.mesh.visible = true;
        }
      }
    }
    for (const b of this.bonusCharms) {
      if (!b.available) {
        b.respawnTicks -= 1;
        if (b.respawnTicks <= 0) {
          b.available = true;
          b.mesh.visible = true;
        }
      }
    }

    // Wind (Night 3)
    const windBadge = document.getElementById("hud-wind-badge");
    if (this.nightDef.hasWind) {
      const mod = st % WIND_CYCLE_TICKS;
      if (this.windActive) {
        this.windTicksLeft -= 1;
        if (this.windTicksLeft <= 0) this.windActive = false;
      } else if (st > 0 && mod === 0) {
        this.windActive = true;
        this.windTicksLeft = WIND_ACTIVE_TICKS;
        this.windDirDeg = Math.random() * 360;
      }
      const telegraph = !this.windActive && mod >= WIND_CYCLE_TICKS - WIND_TELEGRAPH_TICKS;
      windBadge.classList.toggle("hidden", !this.windActive && !telegraph);
      windBadge.textContent = this.windActive ? "🌬️ Gió mạnh đang thổi!" : "🍃 Sắp có gió mạnh...";
    } else {
      windBadge.classList.add("hidden");
    }

    // Respawn wait
    if (this.respawnWaitTicks > 0) {
      this.respawnWaitTicks -= 1;
      if (this.respawnWaitTicks <= 0) {
        this.playerPos = [0, 0, 0];
        this.playerVel = [0, 0, 0];
        this.grounded = true;
        this.padLaunched = false;
        this.invulnTicks = 90;
      }
    } else {
      // Movement
      let mx = 0, mz = 0;
      if (this.keys["KeyD"]) mx += 1;
      if (this.keys["KeyA"]) mx -= 1;
      if (this.keys["KeyW"]) mz -= 1;
      if (this.keys["KeyS"]) mz += 1;
      const mag = Math.hypot(mx, mz);
      if (mag > 1) { mx /= mag; mz /= mag; }
      const wx = mx * Math.cos(this.camYaw) + mz * Math.sin(this.camYaw);
      const wz = -mx * Math.sin(this.camYaw) + mz * Math.cos(this.camYaw);
      if (Math.hypot(wx, wz) > 1e-4) {
        const d = Math.hypot(wx, wz);
        this.facingX = wx / d;
        this.facingZ = wz / d;
        this.playerGroup.rotation.y = Math.atan2(wx, wz);
      }

      if (dashP && this.dashTicksLeft <= 0 && (this.charmTicks > 0 || this.dashCdTicks <= 0)) {
        this.dashTicksLeft = 12;
        this.dashCdTicks = this.charmTicks > 0 ? 0 : 90;
        this.dashDirX = this.facingX;
        this.dashDirZ = this.facingZ;
        this.padLaunched = false;
        this.sfx.dash();
      }

      let vx, vz, vy;
      if (this.dashTicksLeft > 0) {
        vx = this.dashDirX * this.tuning.dash_speed;
        vz = this.dashDirZ * this.tuning.dash_speed;
        vy = 0;
        this.dashTicksLeft -= 1;
      } else if (this.padLaunched) {
        vx = this.padVx;
        vz = this.padVz;
        vy = this.playerVel[1] - GRAVITY * DT;
      } else {
        const spd = this.charmTicks > 0 ? CHARM_SPEED : this.tuning.player_speed;
        vx = wx * spd;
        vz = wz * spd;
        if (jumpP && this.grounded) {
          vy = JUMP_VELOCITY;
          this.grounded = false;
          this.sfx.jump();
        } else {
          vy = this.grounded ? 0 : this.playerVel[1] - GRAVITY * DT;
        }
      }

      if (this.windActive) {
        const wr = (this.windDirDeg * Math.PI) / 180;
        vx += Math.cos(wr) * WIND_SPEED;
        vz += Math.sin(wr) * WIND_SPEED;
      }

      const [ox, oy, oz] = this.playerPos;
      let nx = ox + vx * DT;
      let nz = oz + vz * DT;
      if (this.currentNight === 3 && isBlockedNight3(ox, oz, nx, nz, oy)) {
        nx = ox; nz = oz; vx = 0; vz = 0;
      }
      let ny = oy + vy * DT;
      const gh = groundHeight(this.currentNight, nx, nz, oy);
      if (gh !== null && ny <= gh && vy <= 0) {
        ny = gh; vy = 0; this.grounded = true; this.padLaunched = false;
      } else if (gh !== null && ny <= gh && this.grounded) {
        ny = gh; vy = 0;
      } else {
        this.grounded = false;
      }
      this.playerPos = [nx, ny, nz];
      this.playerVel = [vx, vy, vz];

      // Jump pads
      for (const pad of this.nightDef.jumpPads) {
        if (distXZ(this.playerPos, pad.pos) <= pad.r && Math.abs(this.playerPos[1] - pad.pos[1]) <= 0.6) {
          this.padLaunched = true;
          this.grounded = false;
          this.padVx = pad.dx * pad.vh;
          this.padVz = pad.dz * pad.vh;
          this.playerVel = [this.padVx, pad.vy, this.padVz];
          this.sfx.jump();
          break;
        }
      }

      // Fall check
      if (this.playerPos[1] < -10) {
        this.flames = Math.max(0, this.flames - 1);
        this.carried = 0;
        this.sfx.hit();
        if (this.flames > 0) this.respawnWaitTicks = RESPAWN_WAIT_TICKS;
      }
    }

    // Pickup motes & charms
    if (this.respawnWaitTicks <= 0 && this.flames > 0) {
      this.motes = this.motes.filter((m) => {
        if (
          m.spawnTick < st &&
          this.carried < this.tuning.carry_capacity &&
          distXZ(this.playerPos, m.pos) <= this.tuning.pickup_radius &&
          Math.abs(this.playerPos[1] - m.pos[1]) <= 1.5
        ) {
          this.carried += 1;
          this.moteGroup.remove(m.mesh);
          this.sfx.pickup();
          return false;
        }
        return true;
      });

      for (const c of this.charms) {
        if (c.available && distXZ(this.playerPos, c.pos) <= 1.0 && Math.abs(this.playerPos[1] - c.pos[1]) <= 1.5) {
          c.available = false;
          c.respawnTicks = CHARM_RESPAWN_TICKS;
          c.mesh.visible = false;
          this.charmTicks = CHARM_DURATION_TICKS;
          this.sfx.lanternLit();
        }
      }

      // Bonus creative charms (Magnet & Light Shield)
      for (const b of this.bonusCharms) {
        if (b.available && distXZ(this.playerPos, b.pos) <= 1.2 && Math.abs(this.playerPos[1] - b.pos[1]) <= 1.5) {
          b.available = false;
          b.mesh.visible = false;
          if (b.kind === "magnet") {
            this.magnetTicks = 720; // 12s
            b.respawnTicks = 2100; // 35s
          } else {
            this.shieldTicks = 840; // 14s
            b.respawnTicks = 2400; // 40s
          }
          this.sfx.lanternLit();
        }
      }
      if (this.magnetTicks > 0 && this.carried < this.tuning.carry_capacity) {
        for (const m of this.motes) {
          const d = distXZ(this.playerPos, m.pos);
          if (d > 0.2 && d <= 20.0 && Math.abs(this.playerPos[1] - m.pos[1]) <= 4.0) {
            m.pos[0] += ((this.playerPos[0] - m.pos[0]) / d) * 11.0 * DT;
            m.pos[2] += ((this.playerPos[2] - m.pos[2]) / d) * 11.0 * DT;
          }
        }
      }

      // Lantern interact
      let nearL = null, bestD = Infinity;
      for (const lt of this.lanterns) {
        if (!lt.lit) {
          const d = distXZ(this.playerPos, lt.pos);
          if (d <= this.tuning.interact_radius && Math.abs(this.playerPos[1] - lt.pos[1]) <= 2.0 && d < bestD) {
            bestD = d;
            nearL = lt;
          }
        }
      }
      const hint = document.getElementById("interact-hint");
      if (nearL) {
        hint.textContent = `E — Nạp ánh sáng (${nearL.deposited}/10)`;
        hint.classList.remove("hidden");
      } else {
        hint.classList.add("hidden");
      }

      if (interactP && nearL && this.carried > 0) {
        const amt = Math.min(this.carried, 10 - nearL.deposited);
        if (amt > 0) {
          this.carried -= amt;
          nearL.deposited += amt;
          this.score += amt * this.tuning.score.per_mote;
          this.sfx.pickup();
          if (nearL.deposited >= 10) {
            nearL.lit = true;
            this.score += this.tuning.score.per_lantern;
            const ud = nearL.mesh.userData;
            ud.orbMat.color.setHex(PALETTE.lanternCore);
            ud.orbMat.emissive.setHex(PALETTE.lanternLit);
            ud.orbMat.emissiveIntensity = 1.6;
            ud.light.intensity = 4.5;
            ud.safeRing.material.opacity = 0.35;
            this.sfx.lanternLit();
            this.updateAtmosphere();
          }
        }
      }

      // Pulse
      if (pulseP && this.pulseCdTicks <= 0 && this.carried >= this.tuning.pulse_cost) {
        this.carried -= this.tuning.pulse_cost;
        this.pulseCdTicks = 180;
        this.sfx.pulse();
        this.spawnPulseRing();
        const center = [this.playerPos[0], this.playerPos[1] + 0.8, this.playerPos[2]];
        for (const s of this.shades) {
          if (dist3D(center, s.pos) <= this.tuning.pulse_radius) {
            s.state = "stunned";
            s.stateTicks = 120;
            s.pushTicks = PULSE_PUSH_TICKS;
            const dx = s.pos[0] - this.playerPos[0];
            const dz = s.pos[2] - this.playerPos[2];
            const d = Math.hypot(dx, dz);
            const nx = d > 1e-4 ? dx / d : 1;
            const nz = d > 1e-4 ? dz / d : 0;
            s.pushVx = nx * (4.0 / (PULSE_PUSH_TICKS * DT));
            s.pushVz = nz * (4.0 / (PULSE_PUSH_TICKS * DT));
            this.score += this.tuning.score.per_stun;
          }
        }
        for (const dr of this.drifters) {
          if (dr.state !== "removed" && dist3D(center, dr.pos) <= this.tuning.pulse_radius) {
            if (dr.state === "chase") {
              dr.state = "flee";
              dr.fleeTicks = DRIFTER_FLEE_TICKS;
            } else if (dr.state === "flee" && dr.stolen > 0) {
              for (let i = 0; i < dr.stolen; i++) this.addMote(dr.pos, "dropped", DROPPED_MOTE_TTL_TICKS);
              dr.stolen = 0;
              dr.fleeTicks = Math.min(dr.fleeTicks, 120);
            }
          }
        }
      }
    }

    // Move shades
    const litLanterns = this.lanterns.filter((l) => l.lit);
    for (const s of this.shades) {
      if (s.state === "stunned" || s.state === "recoil") {
        s.stateTicks -= 1;
        if (s.state === "stunned" && s.pushTicks > 0) {
          s.pos[0] += s.pushVx * DT;
          s.pos[2] += s.pushVz * DT;
          s.pushTicks -= 1;
        } else if (s.state === "recoil") {
          s.pos[0] += s.recoilVx * DT;
          s.pos[2] += s.recoilVz * DT;
        }
        if (s.stateTicks <= 0) s.state = "wander";
      } else {
        const d = distXZ(s.pos, this.playerPos);
        if (s.state === "wander" && d <= SHADE_DETECT_R) s.state = "chase";
        if (s.state === "chase" && d > SHADE_LOSE_R) s.state = "wander";
        if (s.state === "chase" && d > 1e-4) {
          const step = Math.min(d, this.nightDef.shadeSpeed * DT);
          s.pos[0] += ((this.playerPos[0] - s.pos[0]) / d) * step;
          s.pos[2] += ((this.playerPos[2] - s.pos[2]) / d) * step;
        }
      }
      for (const lt of litLanterns) {
        const lx = s.pos[0] - lt.pos[0];
        const lz = s.pos[2] - lt.pos[2];
        const ld = Math.hypot(lx, lz);
        if (ld < 6.0) {
          const nx = ld > 1e-4 ? lx / ld : 1;
          const nz = ld > 1e-4 ? lz / ld : 0;
          s.pos[0] = lt.pos[0] + nx * 6.01;
          s.pos[2] = lt.pos[2] + nz * 6.01;
        }
      }
      const gh = groundHeight(this.currentNight, s.pos[0], s.pos[2], s.pos[1]);
      if (gh !== null) s.pos[1] = gh;
      s.mesh.userData.bodyMat.color.setHex(s.state === "stunned" ? PALETTE.shadeStunned : PALETTE.shadeBody);
    }

    // Move drifters & steal
    for (const dr of this.drifters) {
      if (dr.state === "removed") continue;
      if (dr.state === "flee") {
        dr.fleeTicks -= 1;
        if (dr.fleeTicks <= 0) {
          dr.state = "removed";
          this.drifterGroup.remove(dr.mesh);
          continue;
        }
        const dx = dr.pos[0] - this.playerPos[0];
        const dz = dr.pos[2] - this.playerPos[2];
        const d = Math.hypot(dx, dz) || 1;
        dr.pos[0] += (dx / d) * DRIFTER_FAST_SPEED * DT;
        dr.pos[2] += (dz / d) * DRIFTER_FAST_SPEED * DT;
      } else {
        const d = distXZ(dr.pos, this.playerPos);
        dr.state = this.carried >= 5 && d <= DRIFTER_DETECT_R && !dr.hasStolen ? "chase" : "idle";
        if (dr.state === "chase" && d > 1e-4) {
          dr.pos[0] += ((this.playerPos[0] - dr.pos[0]) / d) * DRIFTER_FAST_SPEED * DT;
          dr.pos[2] += ((this.playerPos[2] - dr.pos[2]) / d) * DRIFTER_FAST_SPEED * DT;
        } else {
          dr.angle += 0.6 * DT;
          dr.pos[0] += Math.cos(dr.angle) * DRIFTER_IDLE_SPEED * DT;
          dr.pos[2] += Math.sin(dr.angle) * DRIFTER_IDLE_SPEED * DT;
        }
        if (this.respawnWaitTicks <= 0 && !dr.hasStolen && distXZ(this.playerPos, dr.pos) <= DRIFTER_STEAL_R && this.carried > 0) {
          const amt = Math.min(3, this.carried);
          this.carried -= amt;
          dr.stolen = amt;
          dr.hasStolen = true;
          dr.state = "flee";
          dr.fleeTicks = DRIFTER_FLEE_TICKS;
          this.sfx.hit();
        }
      }
    }

    // Shade hit
    if (this.respawnWaitTicks <= 0 && this.invulnTicks <= 0 && this.flames > 0) {
      for (const s of this.shades) {
        if (s.state !== "stunned" && s.state !== "recoil" && distXZ(this.playerPos, s.pos) <= 1.0 && Math.abs(this.playerPos[1] - s.pos[1]) <= 1.5) {
          const dx = s.pos[0] - this.playerPos[0];
          const dz = s.pos[2] - this.playerPos[2];
          const d = Math.hypot(dx, dz) || 1;
          s.state = "recoil";
          s.stateTicks = SHADE_RECOIL_TICKS;
          s.recoilVx = (dx / d) * (2.0 / (SHADE_RECOIL_TICKS * DT));
          s.recoilVz = (dz / d) * (2.0 / (SHADE_RECOIL_TICKS * DT));
          if (this.shieldTicks > 0) {
            // Light Shield absorbs 1 shade hit without losing Flame or motes
            this.shieldTicks = 0;
            this.invulnTicks = 60;
            this.sfx.pulse();
            break;
          }
          this.flames = Math.max(0, this.flames - 1);
          const dropped = Math.floor(this.carried * 0.5);
          this.carried -= dropped;
          this.invulnTicks = 90;
          for (let i = 0; i < dropped; i++) {
            const a = Math.random() * Math.PI * 2;
            const r = 1.5 + Math.random();
            this.addMote([this.playerPos[0] + r * Math.cos(a), this.playerPos[1], this.playerPos[2] + r * Math.sin(a)], "dropped", DROPPED_MOTE_TTL_TICKS);
          }
          this.sfx.hit();
          break;
        }
      }
    }

    // Scheduled spawns
    if (st % 240 === 0 && this.motes.length < 30) {
      const empty = this.nightDef.moteSpawns.filter((sp) => !this.motes.some((m) => distXZ(sp, m.pos) < 0.5));
      if (empty.length) this.addMote(empty[Math.floor(Math.random() * empty.length)], "random", null);
    }
    if (st === 300 || (st > 300 && (st - 300) % this.nightDef.shadeInterval === 0)) {
      const n = st === 300 ? 2 : 1;
      for (let i = 0; i < n && this.shades.length < this.nightDef.shadeMax; i++) {
        const valid = this.nightDef.shadeSpawns.filter((sp) => distXZ(sp, this.playerPos) >= 15);
        if (valid.length) this.addShade(valid[Math.floor(Math.random() * valid.length)]);
      }
    }
    if (this.nightDef.hasDrifters && st % 1200 === 0) {
      const active = this.drifters.filter((d) => d.state !== "removed");
      if (active.length < 2) {
        const sp = this.nightDef.shadeSpawns[Math.floor(Math.random() * this.nightDef.shadeSpawns.length)];
        this.addDrifter(sp);
      }
    }

    // Win/Lose priority
    if (this.flames <= 0) {
      this.finishNight("lost", "Ngọn lửa của Mây đã tắt.");
    } else if (this.lanterns.every((l) => l.lit)) {
      this.score += Math.floor(this.timeLeft) * 2 + this.flames * 50;
      this.campaignTotalScore += this.score;
      this.finishNight("won", `Hoàn thành ${NIGHT_QUOTES[this.currentNight].name}!`);
    } else if (this.timeLeft <= 0) {
      this.finishNight("lost", "Bình minh đã tới trước khi thắp hết đèn.");
    }

    this.updateHUD();
  }

  spawnPulseRing() {
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(0.4, 0.85, 32),
      new THREE.MeshBasicMaterial({ color: PALETTE.lanternLit, transparent: true, opacity: 0.9, side: THREE.DoubleSide })
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.set(this.playerPos[0], this.playerPos[1] + 0.4, this.playerPos[2]);
    this.fxGroup.add(ring);
    this.pulseWave = { mesh: ring, age: 0 };
  }

  finishNight(result, msg) {
    this.mode = "result";
    if (result === "won") this.sfx.win();
    else this.sfx.lose();
    const isFinalWin = result === "won" && this.currentNight === 3;
    document.getElementById("result-eyebrow").textContent = isFinalWin ? "BÌNH MINH ĐÃ LÊN" : `ĐÊM ${this.currentNight}`;
    document.getElementById("result-title").textContent = isFinalWin ? "Bình Minh Rực Rỡ!" : result === "won" ? "Chiến Thắng!" : "Thất Bại";
    document.getElementById("result-subtitle").textContent = isFinalWin
      ? "Cả ba hòn đảo đều đã ngập tràn ánh sáng đèn lồng!"
      : msg;
    document.getElementById("result-stats").innerHTML =
      `Điểm Đêm ${this.currentNight}: <b>${this.score}</b><br>` +
      `Tổng điểm hành trình: <b>${this.campaignTotalScore}</b>`;
    document.getElementById("btn-next-night").classList.toggle("hidden", !(result === "won" && this.currentNight < 3));
    this.showScreen("screen-result");
  }

  updateHUD() {
    document.getElementById("hud-flames").textContent = this.flames > 0 ? "🔥".repeat(this.flames) : "0";
    const lit = this.lanterns.filter((l) => l.lit).length;
    document.getElementById("hud-lanterns").textContent = `${lit} / ${this.lanterns.length}`;
    document.getElementById("hud-score").textContent = String(this.score);
    const secs = Math.ceil(this.timeLeft);
    const clock = document.getElementById("hud-time");
    clock.textContent = `${String(Math.floor(secs / 60)).padStart(2, "0")}:${String(secs % 60).padStart(2, "0")}`;
    clock.classList.toggle("danger", this.timeLeft <= 30);

    document.getElementById("hud-mote-count").textContent = String(this.carried);
    this.moteSlots.forEach((el, i) => el.classList.toggle("filled", i < this.carried));

    const charmBadge = document.getElementById("hud-charm-badge");
    charmBadge.classList.toggle("hidden", this.charmTicks <= 0);
    if (this.charmTicks > 0) charmBadge.textContent = `🧧 Bùa Gió: ${(this.charmTicks / 60).toFixed(1)}s`;

    const magBadge = document.getElementById("hud-magnet-badge");
    magBadge.classList.toggle("hidden", this.magnetTicks <= 0);
    if (this.magnetTicks > 0) magBadge.textContent = `🧲 Hút Đom Đóm: ${(this.magnetTicks / 60).toFixed(1)}s`;

    const shBadge = document.getElementById("hud-shield-badge");
    shBadge.classList.toggle("hidden", this.shieldTicks <= 0);
    if (this.shieldTicks > 0) shBadge.textContent = `🛡️ Khiên Ánh Sáng: ${(this.shieldTicks / 60).toFixed(1)}s`;

    const dashBox = document.getElementById("cd-dash");
    const dashVal = document.getElementById("cd-dash-val");
    if (this.charmTicks > 0) {
      dashBox.classList.remove("cooldown");
      dashVal.textContent = "0s (Bùa)";
    } else if (this.dashCdTicks > 0) {
      dashBox.classList.add("cooldown");
      dashVal.textContent = `${(this.dashCdTicks / 60).toFixed(1)}s`;
    } else {
      dashBox.classList.remove("cooldown");
      dashVal.textContent = "Sẵn sàng";
    }

    const pulseBox = document.getElementById("cd-pulse");
    const pulseVal = document.getElementById("cd-pulse-val");
    if (this.pulseCdTicks > 0) {
      pulseBox.classList.add("cooldown");
      pulseVal.textContent = `${(this.pulseCdTicks / 60).toFixed(1)}s`;
    } else if (this.carried < 3) {
      pulseBox.classList.add("cooldown");
      pulseVal.textContent = "Cần 3";
    } else {
      pulseBox.classList.remove("cooldown");
      pulseVal.textContent = "Sẵn sàng";
    }
  }

  updateOffscreenArrow() {
    const arrow = document.getElementById("offscreen-arrow");
    if (this.mode !== "playing") {
      arrow.classList.add("hidden");
      return;
    }
    const unlit = this.lanterns.filter((l) => !l.lit);
    if (!unlit.length) {
      arrow.classList.add("hidden");
      return;
    }
    unlit.sort((a, b) => distXZ(this.playerPos, a.pos) - distXZ(this.playerPos, b.pos));
    const target = new THREE.Vector3(unlit[0].pos[0], unlit[0].pos[1] + 4, unlit[0].pos[2]);
    const proj = target.clone().project(this.camera);
    const inFront = proj.z < 1;
    const onScreen = inFront && Math.abs(proj.x) <= 0.92 && Math.abs(proj.y) <= 0.88;
    if (onScreen) {
      arrow.classList.add("hidden");
      return;
    }
    let sx = proj.x;
    let sy = proj.y;
    if (!inFront) { sx = -sx; sy = -sy; }
    const ang = Math.atan2(sy, sx);
    const cx = window.innerWidth / 2 + Math.cos(ang) * (window.innerWidth * 0.42);
    const cy = window.innerHeight / 2 - Math.sin(ang) * (window.innerHeight * 0.38);
    arrow.style.left = `${cx - 17}px`;
    arrow.style.top = `${cy - 17}px`;
    arrow.style.transform = `rotate(${90 - (ang * 180) / Math.PI}deg)`;
    arrow.classList.remove("hidden");
  }

  syncVisuals(nowSec) {
    if (!this.playerPos) return;
    this.playerGroup.position.set(this.playerPos[0], this.playerPos[1], this.playerPos[2]);
    this.playerGroup.visible = this.respawnWaitTicks <= 0 && (this.invulnTicks <= 0 || Math.floor(nowSec * 14) % 2 === 0);
    if (this.shieldSphere) {
      this.shieldSphere.visible = this.shieldTicks > 0;
      if (this.shieldTicks > 0) {
        const pulse = 1.0 + Math.sin(nowSec * 5.0) * 0.04;
        this.shieldSphere.scale.set(pulse, pulse, pulse);
      }
    }

    for (const m of this.motes) {
      m.mesh.position.set(m.pos[0], m.pos[1] + 0.8 + Math.sin(nowSec * 3 + m.phase) * 0.2, m.pos[2]);
    }
    for (const s of this.shades) {
      s.mesh.position.set(s.pos[0], s.pos[1] + 0.1, s.pos[2]);
    }
    for (const dr of this.drifters) {
      if (dr.state !== "removed") {
        dr.mesh.position.set(dr.pos[0], dr.pos[1] + 1.5 + Math.sin(nowSec * 5) * 0.25, dr.pos[2]);
      }
    }
    for (const c of this.charms) {
      if (c.available) c.mesh.rotation.y = nowSec * 2.2;
    }
    for (const b of this.bonusCharms) {
      if (b.available) {
        b.mesh.rotation.y = nowSec * 2.5;
        b.mesh.rotation.x = nowSec * 1.4;
      }
    }
    if (this.pulseWave) {
      this.pulseWave.age += DT;
      const t = this.pulseWave.age / 0.35;
      if (t >= 1) {
        this.fxGroup.remove(this.pulseWave.mesh);
        this.pulseWave = null;
      } else {
        const sc = 1 + t * 5.0;
        this.pulseWave.mesh.scale.set(sc, sc, 1);
        this.pulseWave.mesh.material.opacity = 0.9 * (1 - t);
      }
    }

    const camDist = 11.5;
    const camHeight = 6.5;
    const tx = this.playerPos[0] + Math.sin(this.camYaw) * camDist;
    const tz = this.playerPos[2] + Math.cos(this.camYaw) * camDist;
    this.camera.position.lerp(new THREE.Vector3(tx, this.playerPos[1] + camHeight, tz), 0.15);
    this.camera.lookAt(this.playerPos[0], this.playerPos[1] + 1.5, this.playerPos[2]);
    this.updateOffscreenArrow();
  }

  animate(nowMs) {
    requestAnimationFrame((t) => this.animate(t));
    const dt = Math.min(0.1, (nowMs - this.lastFrameTime) / 1000);
    this.lastFrameTime = nowMs;
    if (this.mode === "playing") {
      this.accumulator += dt;
      while (this.accumulator >= DT) {
        this.stepSim();
        this.accumulator -= DT;
      }
      this.syncVisuals(nowMs / 1000);
    }
    this.renderer.render(this.scene, this.camera);
  }
}

loadTuning().then((tuning) => new DaoDenLongApp(tuning));
