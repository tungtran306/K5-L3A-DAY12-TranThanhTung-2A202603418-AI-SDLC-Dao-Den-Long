import * as THREE from "https://unpkg.com/three@0.160.0/build/three.module.js";

const TICK_RATE = 60;
const DT = 1 / TICK_RATE;
const ISLAND_RADIUS = 45.0;
const LANTERN_RING_RADIUS = 26.0;
const JUMP_VELOCITY = 7.5;
const GRAVITY = 20.0;
const INITIAL_MOTE_COUNT = 24;
const MOTE_RESPAWN_INTERVAL_TICKS = 300;
const MOTE_MAX_ACTIVE = 24;
const INITIAL_SHADE_COUNT = 2;
const SHADE_SPAWN_INTERVAL_TICKS = 1800;
const SHADE_MAX_ACTIVE = 5;

const DEFAULT_TUNING = {
  player_speed: 7.0,
  carry_capacity: 6,
  lantern_cost: 4,
  lantern_count_night1: 5,
  pickup_radius: 1.6,
  interact_radius: 2.5,
  pulse_cost: 2,
  pulse_radius: 8.0,
  night1_duration_s: 240,
  flames: 3,
  invuln_s: 1.5,
  hit_drop_ratio: 0.5,
  pulse_stun_s: 3.0,
  pulse_push_m: 6.0,
  pulse_cooldown_s: 2.5,
  safe_radius: 7.0,
  shade_speed: 4.2,
  shade_hit_radius: 1.2,
  fall_enabled: false,
  score: {
    per_mote: 10,
    per_lantern: 150,
    per_stun: 30,
    per_second_left: 2,
    per_flame_left: 100,
  },
};

function distXZ(a, b) {
  return Math.hypot(a[0] - b[0], a[2] - b[2]);
}

function clampToIsland(pos) {
  const d = Math.hypot(pos[0], pos[2]);
  if (d > ISLAND_RADIUS && d > 0) {
    const s = ISLAND_RADIUS / d;
    pos[0] *= s;
    pos[2] *= s;
  }
}

async function loadTuning() {
  try {
    const res = await fetch("/game.contract.json");
    if (res.ok) {
      const data = await res.json();
      if (data && data.tuning) return data.tuning;
    }
  } catch {
    // Fallback to DEFAULT_TUNING if opened offline
  }
  return DEFAULT_TUNING;
}

class DaoDenLongGame {
  constructor(tuning) {
    this.tuning = tuning;
    this.keys = {};
    this.prevKeys = {};
    this.camYaw = 0;
    this.dragging = false;
    this.lastMouseX = 0;
    this.pulseWave = null;

    this.initScene();
    this.initInput();
    this.resetGame();

    this.accumulator = 0;
    this.lastFrameTime = performance.now();
    this.animate(this.lastFrameTime);
  }

  initScene() {
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0b0f24);
    this.scene.fog = new THREE.FogExp2(0x0b0f24, 0.013);

    this.camera = new THREE.PerspectiveCamera(58, window.innerWidth / window.innerHeight, 0.1, 260);
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    document.getElementById("canvas-container").appendChild(this.renderer.domElement);

    // Lighting (brightens as lanterns are lit)
    this.hemiLight = new THREE.HemisphereLight(0x5264a8, 0x161b2e, 0.55);
    this.scene.add(this.hemiLight);

    this.moonLight = new THREE.DirectionalLight(0x9cb4ff, 0.45);
    this.moonLight.position.set(28, 48, -22);
    this.moonLight.castShadow = true;
    this.scene.add(this.moonLight);

    // Starfield
    const starGeo = new THREE.BufferGeometry();
    const starVerts = [];
    for (let i = 0; i < 450; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.random() * Math.PI * 0.45;
      const r = 140;
      starVerts.push(
        r * Math.sin(phi) * Math.cos(theta),
        r * Math.cos(phi) + 12,
        r * Math.sin(phi) * Math.sin(theta)
      );
    }
    starGeo.setAttribute("position", new THREE.Float32BufferAttribute(starVerts, 3));
    const starMat = new THREE.PointsMaterial({ color: 0xffe9c4, size: 0.7 });
    this.scene.add(new THREE.Points(starGeo, starMat));

    // Circular Island (Y = 0 top surface)
    const islandGeo = new THREE.CylinderGeometry(ISLAND_RADIUS, ISLAND_RADIUS * 0.85, 4, 48);
    const islandMat = new THREE.MeshStandardMaterial({ color: 0x1d2b3a, roughness: 0.92 });
    const island = new THREE.Mesh(islandGeo, islandMat);
    island.position.y = -2.0;
    island.receiveShadow = true;
    this.scene.add(island);

    // Subtle stone path ring connecting lanterns
    const pathGeo = new THREE.RingGeometry(LANTERN_RING_RADIUS - 1.2, LANTERN_RING_RADIUS + 1.2, 48);
    const pathMat = new THREE.MeshStandardMaterial({
      color: 0x2c394d,
      roughness: 0.95,
      side: THREE.DoubleSide,
    });
    const pathRing = new THREE.Mesh(pathGeo, pathMat);
    pathRing.rotation.x = -Math.PI / 2;
    pathRing.position.y = 0.02;
    this.scene.add(pathRing);

    // Sea of clouds below island
    const cloudGeo = new THREE.CircleGeometry(210, 32);
    const cloudMat = new THREE.MeshBasicMaterial({ color: 0x151d38, transparent: true, opacity: 0.75 });
    const clouds = new THREE.Mesh(cloudGeo, cloudMat);
    clouds.rotation.x = -Math.PI / 2;
    clouds.position.y = -4.5;
    this.scene.add(clouds);

    // Decorative low-poly trees around outer rim
    for (let i = 0; i < 18; i++) {
      const a = (i / 18) * Math.PI * 2 + 0.15;
      const r = 36 + (i % 3) * 2.5;
      const tree = new THREE.Group();
      const trunk = new THREE.Mesh(
        new THREE.CylinderGeometry(0.25, 0.35, 2.2, 6),
        new THREE.MeshStandardMaterial({ color: 0x3b2a22 })
      );
      trunk.position.y = 1.1;
      const crown = new THREE.Mesh(
        new THREE.ConeGeometry(1.7, 4.2, 7),
        new THREE.MeshStandardMaterial({ color: 0x193836 })
      );
      crown.position.y = 3.6;
      tree.add(trunk, crown);
      tree.position.set(Math.sin(a) * r, 0, Math.cos(a) * r);
      this.scene.add(tree);
    }

    // Player (May wearing conical hat - non la - with hanging small lantern)
    this.playerGroup = this.buildPlayerMesh();
    this.scene.add(this.playerGroup);

    // Dynamic entity groups
    this.lanternGroup = new THREE.Group();
    this.moteGroup = new THREE.Group();
    this.shadeGroup = new THREE.Group();
    this.fxGroup = new THREE.Group();
    this.scene.add(this.lanternGroup, this.moteGroup, this.shadeGroup, this.fxGroup);

    window.addEventListener("resize", () => {
      this.camera.aspect = window.innerWidth / window.innerHeight;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(window.innerWidth, window.innerHeight);
    });
  }

  buildPlayerMesh() {
    const g = new THREE.Group();
    // Cloak body
    const body = new THREE.Mesh(
      new THREE.ConeGeometry(0.55, 1.35, 10),
      new THREE.MeshStandardMaterial({ color: 0x3a6b8c, roughness: 0.7 })
    );
    body.position.y = 0.68;
    body.castShadow = true;
    g.add(body);

    // Head
    const head = new THREE.Mesh(
      new THREE.SphereGeometry(0.32, 12, 12),
      new THREE.MeshStandardMaterial({ color: 0xf7dfc4 })
    );
    head.position.y = 1.5;
    g.add(head);

    // Non la (Vietnamese conical hat)
    const hat = new THREE.Mesh(
      new THREE.ConeGeometry(0.88, 0.55, 16),
      new THREE.MeshStandardMaterial({ color: 0xd9b36c, roughness: 0.8 })
    );
    hat.position.y = 1.88;
    hat.castShadow = true;
    g.add(hat);

    // Small lantern hanging from hat brim
    const miniLantern = new THREE.Mesh(
      new THREE.SphereGeometry(0.14, 10, 10),
      new THREE.MeshBasicMaterial({ color: 0xffc14d })
    );
    miniLantern.position.set(0.68, 1.48, 0.25);
    g.add(miniLantern);

    const playerLight = new THREE.PointLight(0xffb84d, 2.2, 12);
    playerLight.position.set(0.68, 1.5, 0.25);
    g.add(playerLight);

    return g;
  }

  buildLanternMesh(lantern) {
    const g = new THREE.Group();
    const post = new THREE.Mesh(
      new THREE.CylinderGeometry(0.28, 0.42, 3.6, 8),
      new THREE.MeshStandardMaterial({ color: 0x453b4f, roughness: 0.85 })
    );
    post.position.y = 1.8;
    g.add(post);

    const orbMat = new THREE.MeshStandardMaterial({
      color: 0x332c3d,
      emissive: 0x000000,
      emissiveIntensity: 0,
      roughness: 0.4,
    });
    const orb = new THREE.Mesh(new THREE.OctahedronGeometry(0.85, 1), orbMat);
    orb.position.y = 4.1;
    g.add(orb);

    const roof = new THREE.Mesh(
      new THREE.ConeGeometry(1.3, 0.7, 6),
      new THREE.MeshStandardMaterial({ color: 0x2d2438 })
    );
    roof.position.y = 5.0;
    g.add(roof);

    const light = new THREE.PointLight(0xffa73b, 0, this.tuning.safe_radius * 2.4);
    light.position.y = 4.1;
    g.add(light);

    const safeRing = new THREE.Mesh(
      new THREE.RingGeometry(this.tuning.safe_radius - 0.15, this.tuning.safe_radius, 36),
      new THREE.MeshBasicMaterial({
        color: 0xffb84d,
        transparent: true,
        opacity: 0.0,
        side: THREE.DoubleSide,
      })
    );
    safeRing.rotation.x = -Math.PI / 2;
    safeRing.position.y = 0.05;
    g.add(safeRing);

    g.position.set(lantern.pos[0], 0, lantern.pos[2]);
    g.userData = { orbMat, light, safeRing };
    return g;
  }

  buildMoteMesh(mote) {
    const mesh = new THREE.Mesh(
      new THREE.SphereGeometry(0.32, 10, 10),
      new THREE.MeshBasicMaterial({ color: 0xffd56b })
    );
    mesh.position.set(mote.pos[0], 0.9, mote.pos[2]);
    return mesh;
  }

  buildShadeMesh(shade) {
    const g = new THREE.Group();
    const bodyMat = new THREE.MeshStandardMaterial({
      color: 0x1b0d29,
      emissive: 0x2b0a45,
      emissiveIntensity: 0.6,
      roughness: 0.5,
    });
    const body = new THREE.Mesh(new THREE.DodecahedronGeometry(0.82, 0), bodyMat);
    body.position.y = 1.1;
    g.add(body);

    const eyeMat = new THREE.MeshBasicMaterial({ color: 0xc86bff });
    const leftEye = new THREE.Mesh(new THREE.SphereGeometry(0.12, 8, 8), eyeMat);
    leftEye.position.set(-0.26, 1.25, 0.65);
    const rightEye = new THREE.Mesh(new THREE.SphereGeometry(0.12, 8, 8), eyeMat);
    rightEye.position.set(0.26, 1.25, 0.65);
    g.add(leftEye, rightEye);

    g.position.set(shade.pos[0], 0, shade.pos[2]);
    g.userData = { bodyMat, eyeMat };
    return g;
  }

  initInput() {
    window.addEventListener("keydown", (e) => {
      this.keys[e.code] = true;
    });
    window.addEventListener("keyup", (e) => {
      this.keys[e.code] = false;
    });
    window.addEventListener("mousedown", (e) => {
      this.dragging = true;
      this.lastMouseX = e.clientX;
    });
    window.addEventListener("mouseup", () => {
      this.dragging = false;
    });
    window.addEventListener("mousemove", (e) => {
      if (!this.dragging) return;
      const dx = e.clientX - this.lastMouseX;
      this.lastMouseX = e.clientX;
      this.camYaw -= dx * 0.006;
    });

    document.getElementById("btn-restart").addEventListener("click", () => {
      this.resetGame();
    });
  }

  resetGame() {
    this.tick = 0;
    this.state = "playing";
    this.score = 0;
    this.timeLeft = this.tuning.night1_duration_s;
    this.playerPos = [0, 0, 0];
    this.playerVy = 0;
    this.flames = this.tuning.flames;
    this.carried = 0;
    this.invulnTimer = 0;
    this.pulseCd = 0;
    this.camYaw = 0;

    // Clear 3D groups
    this.lanternGroup.clear();
    this.moteGroup.clear();
    this.shadeGroup.clear();
    this.fxGroup.clear();
    this.pulseWave = null;

    // 5 Great Lanterns
    this.lanterns = [];
    const count = this.tuning.lantern_count_night1;
    for (let i = 0; i < count; i++) {
      const a = (2 * Math.PI * i) / count;
      const lt = {
        id: `L${i + 1}`,
        pos: [LANTERN_RING_RADIUS * Math.sin(a), 0, LANTERN_RING_RADIUS * Math.cos(a)],
        lit: false,
        deposited: 0,
      };
      lt.mesh = this.buildLanternMesh(lt);
      this.lanternGroup.add(lt.mesh);
      this.lanterns.push(lt);
    }

    // Motes
    this.motes = [];
    for (let i = 0; i < INITIAL_MOTE_COUNT; i++) {
      this.spawnMote();
    }

    // Shades
    this.shades = [];
    for (let i = 0; i < INITIAL_SHADE_COUNT; i++) {
      this.spawnShade();
    }

    document.getElementById("overlay").classList.add("hidden");
    this.updateAtmosphere();
    this.updateHUD();
  }

  spawnMote() {
    const a = Math.random() * Math.PI * 2;
    const r = Math.sqrt(0.05 + Math.random() * 0.8) * ISLAND_RADIUS;
    const m = { pos: [r * Math.sin(a), 0, r * Math.cos(a)], phase: Math.random() * Math.PI * 2 };
    m.mesh = this.buildMoteMesh(m);
    this.moteGroup.add(m.mesh);
    this.motes.push(m);
  }

  spawnShade() {
    const a = Math.random() * Math.PI * 2;
    const r = 33 + Math.random() * 9;
    const s = { pos: [r * Math.sin(a), 0, r * Math.cos(a)], state: "chase", stunTimer: 0 };
    s.mesh = this.buildShadeMesh(s);
    this.shadeGroup.add(s.mesh);
    this.shades.push(s);
  }

  triggerPulseFX() {
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(0.4, 0.9, 36),
      new THREE.MeshBasicMaterial({
        color: 0xffcc66,
        transparent: true,
        opacity: 0.9,
        side: THREE.DoubleSide,
      })
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.set(this.playerPos[0], 0.3, this.playerPos[2]);
    this.fxGroup.add(ring);
    this.pulseWave = { mesh: ring, age: 0 };
  }

  updateAtmosphere() {
    const litCount = this.lanterns.filter((l) => l.lit).length;
    const ratio = litCount / this.lanterns.length;
    this.hemiLight.intensity = 0.55 + ratio * 0.95;
    this.moonLight.intensity = 0.45 + ratio * 0.6;
    const bg = new THREE.Color(0x0b0f24).lerp(new THREE.Color(0x2b2438), ratio);
    this.scene.background = bg;
    this.scene.fog.color.copy(bg);
    this.scene.fog.density = 0.013 - ratio * 0.006;
  }

  stepSim() {
    if (this.state !== "playing") return;

    this.tick += 1;
    if (this.keys["KeyQ"] || this.keys["ArrowLeft"]) this.camYaw += 1.9 * DT;
    if (this.keys["KeyR"] || this.keys["ArrowRight"]) this.camYaw -= 1.9 * DT;

    const jumpPressed = Boolean(this.keys["Space"]) && !Boolean(this.prevKeys["Space"]);
    const interactPressed = Boolean(this.keys["KeyF"]) && !Boolean(this.prevKeys["KeyF"]);
    const pulsePressed = Boolean(this.keys["KeyE"]) && !Boolean(this.prevKeys["KeyE"]);
    this.prevKeys = { ...this.keys };

    if (this.invulnTimer > 0) this.invulnTimer = Math.max(0, this.invulnTimer - DT);
    if (this.pulseCd > 0) this.pulseCd = Math.max(0, this.pulseCd - DT);

    // Move input (WASD)
    let mx = 0;
    let mz = 0;
    if (this.keys["KeyD"]) mx += 1;
    if (this.keys["KeyA"]) mx -= 1;
    if (this.keys["KeyW"]) mz -= 1;
    if (this.keys["KeyS"]) mz += 1;
    const mag = Math.hypot(mx, mz);
    if (mag > 1) {
      mx /= mag;
      mz /= mag;
    }
    const cosT = Math.cos(this.camYaw);
    const sinT = Math.sin(this.camYaw);
    const wx = mx * cosT + mz * sinT;
    const wz = -mx * sinT + mz * cosT;
    this.playerPos[0] += wx * this.tuning.player_speed * DT;
    this.playerPos[2] += wz * this.tuning.player_speed * DT;
    clampToIsland(this.playerPos);

    if (mag > 0.01) {
      this.playerGroup.rotation.y = Math.atan2(wx, wz);
    }

    // Jump
    if (jumpPressed && this.playerPos[1] <= 0) {
      this.playerVy = JUMP_VELOCITY;
    }
    if (this.playerPos[1] > 0 || this.playerVy > 0) {
      this.playerPos[1] += this.playerVy * DT;
      this.playerVy -= GRAVITY * DT;
      if (this.playerPos[1] <= 0) {
        this.playerPos[1] = 0;
        this.playerVy = 0;
      }
    }

    // Pickup motes
    const keepMotes = [];
    for (const m of this.motes) {
      if (this.carried < this.tuning.carry_capacity && distXZ(this.playerPos, m.pos) <= this.tuning.pickup_radius) {
        this.carried += 1;
        this.score += this.tuning.score.per_mote;
        this.moteGroup.remove(m.mesh);
      } else {
        keepMotes.push(m);
      }
    }
    this.motes = keepMotes;

    // Deposit into nearest unlit lantern
    let nearUnlit = false;
    let targetLantern = null;
    let bestDist = Infinity;
    for (const lt of this.lanterns) {
      if (!lt.lit) {
        const d = distXZ(this.playerPos, lt.pos);
        if (d <= this.tuning.interact_radius) {
          nearUnlit = true;
          if (d < bestDist) {
            bestDist = d;
            targetLantern = lt;
          }
        }
      }
    }
    document.getElementById("interact-hint").classList.toggle("hidden", !(nearUnlit && this.carried > 0));

    if (interactPressed && targetLantern && this.carried > 0) {
      const needed = Math.max(0, this.tuning.lantern_cost - targetLantern.deposited);
      const amt = Math.min(this.carried, needed);
      if (amt > 0) {
        this.carried -= amt;
        targetLantern.deposited += amt;
        if (targetLantern.deposited >= this.tuning.lantern_cost && !targetLantern.lit) {
          targetLantern.lit = true;
          this.score += this.tuning.score.per_lantern;
          const ud = targetLantern.mesh.userData;
          ud.orbMat.color.setHex(0xffd27d);
          ud.orbMat.emissive.setHex(0xff9922);
          ud.orbMat.emissiveIntensity = 1.6;
          ud.light.intensity = 4.2;
          ud.safeRing.material.opacity = 0.35;
          this.updateAtmosphere();
        }
      }
    }

    // Pulse
    if (pulsePressed && this.pulseCd <= 0 && this.carried >= this.tuning.pulse_cost) {
      this.carried -= this.tuning.pulse_cost;
      this.pulseCd = this.tuning.pulse_cooldown_s;
      this.triggerPulseFX();
      for (const s of this.shades) {
        const d = distXZ(this.playerPos, s.pos);
        if (d <= this.tuning.pulse_radius) {
          s.state = "stunned";
          s.stunTimer = this.tuning.pulse_stun_s;
          const nx = d > 1e-6 ? (s.pos[0] - this.playerPos[0]) / d : 1;
          const nz = d > 1e-6 ? (s.pos[2] - this.playerPos[2]) / d : 0;
          s.pos[0] += nx * this.tuning.pulse_push_m;
          s.pos[2] += nz * this.tuning.pulse_push_m;
          clampToIsland(s.pos);
          this.score += this.tuning.score.per_stun;
        }
      }
    }

    // Update shades
    const litLanterns = this.lanterns.filter((l) => l.lit);
    for (const s of this.shades) {
      if (s.state === "stunned") {
        s.stunTimer = Math.max(0, s.stunTimer - DT);
        if (s.stunTimer <= 0) s.state = "chase";
      } else {
        const dx = this.playerPos[0] - s.pos[0];
        const dz = this.playerPos[2] - s.pos[2];
        const d = Math.hypot(dx, dz);
        if (d > 1e-6) {
          const stepD = Math.min(d, this.tuning.shade_speed * DT);
          s.pos[0] += (dx / d) * stepD;
          s.pos[2] += (dz / d) * stepD;
        }
      }

      for (const lt of litLanterns) {
        const lx = s.pos[0] - lt.pos[0];
        const lz = s.pos[2] - lt.pos[2];
        const ld = Math.hypot(lx, lz);
        if (ld < this.tuning.safe_radius) {
          const nx = ld > 1e-6 ? lx / ld : 1;
          const nz = ld > 1e-6 ? lz / ld : 0;
          s.pos[0] = lt.pos[0] + nx * (this.tuning.safe_radius + 0.01);
          s.pos[2] = lt.pos[2] + nz * (this.tuning.safe_radius + 0.01);
        }
      }
      clampToIsland(s.pos);

      const ud = s.mesh.userData;
      if (s.state === "stunned") {
        ud.bodyMat.emissive.setHex(0x4a90d9);
        ud.eyeMat.color.setHex(0xa8e0ff);
      } else {
        ud.bodyMat.emissive.setHex(0x2b0a45);
        ud.eyeMat.color.setHex(0xc86bff);
      }
    }

    // Shade hit
    if (this.invulnTimer <= 0) {
      for (const s of this.shades) {
        if (s.state !== "stunned" && distXZ(this.playerPos, s.pos) <= this.tuning.shade_hit_radius) {
          this.flames = Math.max(0, this.flames - 1);
          const dropped = Math.floor(this.carried * this.tuning.hit_drop_ratio);
          this.carried -= dropped;
          this.invulnTimer = this.tuning.invuln_s;
          break;
        }
      }
    }

    // Periodic spawns
    if (this.tick % MOTE_RESPAWN_INTERVAL_TICKS === 0 && this.motes.length < MOTE_MAX_ACTIVE) {
      this.spawnMote();
    }
    if (this.tick % SHADE_SPAWN_INTERVAL_TICKS === 0 && this.shades.length < SHADE_MAX_ACTIVE) {
      this.spawnShade();
    }

    // Clock & Win/Lose
    this.timeLeft = Math.max(0, this.tuning.night1_duration_s - this.tick / TICK_RATE);
    if (this.lanterns.every((l) => l.lit)) {
      this.score += Math.floor(this.timeLeft) * this.tuning.score.per_second_left;
      this.score += this.flames * this.tuning.score.per_flame_left;
      this.endGame("won", "Đảo Bến đã rực sáng! Tất cả 5 Đèn Lồng Lớn đã được thắp lại.");
    } else if (this.flames <= 0) {
      this.endGame("lost", "Ngọn lửa của Mây đã tắt vì Bóng Mực.");
    } else if (this.timeLeft <= 0) {
      this.endGame("lost", "Bình minh đã tới trước khi thắp hết các Đèn Lồng Lớn.");
    }

    this.updateHUD();
  }

  endGame(result, message) {
    this.state = result;
    const overlay = document.getElementById("overlay");
    document.getElementById("overlay-title").textContent = result === "won" ? "Chiến Thắng!" : "Thất Bại";
    document.getElementById("overlay-subtitle").textContent = message;
    const lit = this.lanterns.filter((l) => l.lit).length;
    document.getElementById("overlay-stats").innerHTML =
      `Điểm số: <b>${this.score}</b><br>` +
      `Đèn đã thắp: <b>${lit} / ${this.lanterns.length}</b><br>` +
      `Ngọn lửa còn lại: <b>${this.flames}</b> · Thời gian còn: <b>${Math.ceil(this.timeLeft)}s</b>`;
    overlay.classList.remove("hidden");
  }

  updateHUD() {
    document.getElementById("hud-flames").textContent = this.flames > 0 ? "🔥".repeat(this.flames) : "0";
    document.getElementById("hud-carried").textContent = `${this.carried} / ${this.tuning.carry_capacity}`;
    const lit = this.lanterns.filter((l) => l.lit).length;
    document.getElementById("hud-lanterns").textContent = `${lit} / ${this.lanterns.length}`;
    const secs = Math.ceil(this.timeLeft);
    const mm = String(Math.floor(secs / 60)).padStart(2, "0");
    const ss = String(secs % 60).padStart(2, "0");
    document.getElementById("hud-time").textContent = `${mm}:${ss}`;
    document.getElementById("hud-score").textContent = String(this.score);
    const pulseEl = document.getElementById("hud-pulse");
    if (this.pulseCd > 0) {
      pulseEl.textContent = `${this.pulseCd.toFixed(1)}s`;
    } else if (this.carried < this.tuning.pulse_cost) {
      pulseEl.textContent = `Cần ${this.tuning.pulse_cost} đom đóm`;
    } else {
      pulseEl.textContent = "Sẵn sàng";
    }
  }

  syncVisuals(nowSec) {
    this.playerGroup.position.set(this.playerPos[0], this.playerPos[1], this.playerPos[2]);
    this.playerGroup.visible = this.invulnTimer <= 0 || Math.floor(nowSec * 14) % 2 === 0;

    for (const m of this.motes) {
      m.mesh.position.set(m.pos[0], 0.85 + Math.sin(nowSec * 3.0 + m.phase) * 0.25, m.pos[2]);
    }
    for (const s of this.shades) {
      const bob = s.state === "stunned" ? 0 : Math.sin(nowSec * 4.5) * 0.15;
      s.mesh.position.set(s.pos[0], bob, s.pos[2]);
      s.mesh.lookAt(this.playerPos[0], 1.0, this.playerPos[2]);
    }
    if (this.pulseWave) {
      this.pulseWave.age += DT;
      const t = this.pulseWave.age / 0.45;
      if (t >= 1) {
        this.fxGroup.remove(this.pulseWave.mesh);
        this.pulseWave = null;
      } else {
        const scale = 1 + t * this.tuning.pulse_radius;
        this.pulseWave.mesh.scale.set(scale, scale, 1);
        this.pulseWave.mesh.material.opacity = 0.9 * (1 - t);
      }
    }

    // Third-person camera behind May
    const camDist = 11.5;
    const camHeight = 6.2;
    const targetX = this.playerPos[0] + Math.sin(this.camYaw) * camDist;
    const targetZ = this.playerPos[2] + Math.cos(this.camYaw) * camDist;
    this.camera.position.lerp(new THREE.Vector3(targetX, this.playerPos[1] + camHeight, targetZ), 0.15);
    this.camera.lookAt(this.playerPos[0], this.playerPos[1] + 1.4, this.playerPos[2]);
  }

  animate(nowMs) {
    requestAnimationFrame((t) => this.animate(t));
    const dt = Math.min(0.1, (nowMs - this.lastFrameTime) / 1000);
    this.lastFrameTime = nowMs;
    this.accumulator += dt;
    while (this.accumulator >= DT) {
      this.stepSim();
      this.accumulator -= DT;
    }
    this.syncVisuals(nowMs / 1000);
    this.renderer.render(this.scene, this.camera);
  }
}

loadTuning().then((tuning) => {
  new DaoDenLongGame(tuning);
});
