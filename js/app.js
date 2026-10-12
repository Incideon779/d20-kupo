/* One or two d20s on a table. Click a die to roll it. */
(function () {
  const UP = new THREE.Vector3(0, 1, 0);
  const params = new URLSearchParams(location.search);
  const force = params.get("force");
  const settleArg = params.get("settle");
  let count = params.get("dice") === "2" ? 2 : 1;

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  renderer.setSize(innerWidth, innerHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.08;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  document.body.prepend(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x120c09);
  scene.fog = new THREE.FogExp2(0x120c09, 0.055);

  const camera = new THREE.PerspectiveCamera(34, innerWidth / innerHeight, 0.1, 40);
  // High enough that the face lying on top is the one you read. y-up, camera on +z.
  const camOne = { y: 5.5, z: 5.6 };
  const camTwo = { y: 6.6, z: 7.4 };
  let cam = count === 1 ? camOne : camTwo;
  camera.position.set(0, cam.y, cam.z);
  camera.lookAt(0, 0.85, 0);

  const key = new THREE.DirectionalLight(0xfff1dc, 2.6);
  key.position.set(-3.4, 7.2, 4.2);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.camera.near = 1;
  key.shadow.camera.far = 22;
  key.shadow.camera.left = -6;
  key.shadow.camera.right = 6;
  key.shadow.camera.top = 6;
  key.shadow.camera.bottom = -6;
  key.shadow.bias = -0.0008;
  scene.add(key);
  scene.add(new THREE.DirectionalLight(0xc9d6ff, 0.55).translateX(6).translateY(3).translateZ(-2));
  const rimLight = new THREE.DirectionalLight(0xffc98a, 0.85);
  rimLight.position.set(1.5, 4.2, -6);
  scene.add(rimLight);
  scene.add(new THREE.AmbientLight(0x3a291f, 0.55));
  scene.add(new THREE.HemisphereLight(0xffe6c4, 0x2a140e, 0.4));

  function environment() {
    const room = new THREE.Scene();
    room.background = new THREE.Color(0x1a100c);
    function blob(color, x, y, z, s) {
      const mesh = new THREE.Mesh(
        new THREE.SphereGeometry(s, 16, 12),
        new THREE.MeshBasicMaterial({ color: color })
      );
      mesh.position.set(x, y, z);
      room.add(mesh);
    }
    blob(0xfff3dd, -7, 8, 5, 2.4);
    blob(0xd5e2ff, 8, 3, -3, 1.5);
    blob(0xffb46a, 0, 2, -9, 1.8);
    const baked = new THREE.PMREMGenerator(renderer).fromScene(room, 0.04);
    scene.environment = baked.texture;
  }
  environment();

  const woodImg = new Image();
  woodImg.src = "assets/wood.jpg";
  const faceImgs = {};
  for (let n = 1; n <= 20; n++) {
    const img = new Image();
    img.src = "assets/faces/" + String(n).padStart(2, "0") + ".jpg";
    faceImgs[n] = img;
    const preload = document.createElement("img");
    preload.src = img.src;
    preload.alt = "";
    document.getElementById("preload").appendChild(preload);
  }

  const byN = {};
  DIE.faces.forEach(function (f) { byN[f.n] = f; });

  function quatOf(n) {
    const q = byN[n].quat;
    return new THREE.Quaternion(q[0], q[1], q[2], q[3]);
  }

  function faceUp(q) {
    let best = -2;
    let n = 0;
    for (let i = 0; i < DIE.faces.length; i++) {
      const f = DIE.faces[i];
      const v = new THREE.Vector3(f.normal[0], f.normal[1], f.normal[2]).applyQuaternion(q);
      if (v.y > best) {
        best = v.y;
        n = f.n;
      }
    }
    return n;
  }

  function lift(q) {
    const v = new THREE.Vector3();
    let minY = Infinity;
    for (let i = 0; i < DIE.positions.length; i++) {
      const p = DIE.positions[i];
      v.set(p[0], p[1], p[2]).applyQuaternion(q);
      if (v.y < minY) minY = v.y;
    }
    return -minY + 0.012;
  }

  let bodyGeo = null;
  let bodyMats = null;
  let rimGeo = null;
  let dice = [];

  function buildGeometry() {
    const pos = [];
    const nrm = [];
    const uv = [];
    bodyMats = [];
    DIE.faces.forEach(function (f) {
      for (let k = 0; k < 3; k++) {
        pos.push(DIE.positions[f.idx[k]][0], DIE.positions[f.idx[k]][1], DIE.positions[f.idx[k]][2]);
        nrm.push(f.normal[0], f.normal[1], f.normal[2]);
        uv.push(f.uv[k][0], f.uv[k][1]);
      }
      const tex = new THREE.Texture(faceImgs[f.n]);
      tex.needsUpdate = true;
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
      bodyMats.push(new THREE.MeshPhysicalMaterial({
        map: tex,
        roughness: 0.55,
        metalness: 0.08,
        clearcoat: 0.28,
        clearcoatRoughness: 0.4,
      }));
    });
    bodyGeo = new THREE.BufferGeometry();
    bodyGeo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    bodyGeo.setAttribute("normal", new THREE.Float32BufferAttribute(nrm, 3));
    bodyGeo.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
    for (let i = 0; i < 20; i++) bodyGeo.addGroup(i * 3, 3, i);
    rimGeo = new THREE.BoxGeometry(0.028, 0.028, 1);
  }

  function makeRim() {
    const mat = new THREE.MeshPhysicalMaterial({
      color: 0xf3efe4,
      metalness: 0.72,
      roughness: 0.32,
      clearcoat: 0.2,
    });
    const group = new THREE.Group();
    DIE.edges.forEach(function (e) {
      const a = new THREE.Vector3().fromArray(DIE.positions[e[0]]);
      const b = new THREE.Vector3().fromArray(DIE.positions[e[1]]);
      const len = a.distanceTo(b);
      const mesh = new THREE.Mesh(rimGeo, mat);
      mesh.scale.set(1, 1, len);
      mesh.position.copy(a).add(b).multiplyScalar(0.5);
      mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), b.clone().sub(a).normalize());
      mesh.castShadow = true;
      group.add(mesh);
    });
    return group;
  }

  function place(die, q) {
    die.group.quaternion.copy(q);
    die.group.position.set(die.homeX, lift(q), die.homeZ);
  }

  function spawn() {
    dice.forEach(function (d) { scene.remove(d.group); });
    dice = [];
    const homes = count === 1 ? [0] : [-1.7, 1.7];
    homes.forEach(function (x, i) {
      const group = new THREE.Group();
      group.userData.dieIndex = i;
      const body = new THREE.Mesh(bodyGeo, bodyMats);
      body.castShadow = true;
      body.receiveShadow = true;
      body.userData.dieIndex = i;
      const rim = makeRim();
      rim.userData.dieIndex = i;
      group.add(body, rim);
      scene.add(group);
      const die = {
        group: group,
        homeX: x,
        homeZ: 0,
        result: null,
        rolling: false,
        t0: 0,
        dur: 1,
        qStart: quatOf(20),
        qTarget: quatOf(20),
        axis: new THREE.Vector3(1, 0, 0),
        turns: 2,
        hop: 0.4,
        slide: 0,
        slideZ: 0,
      };
      place(die, quatOf(20));
      dice.push(die);
    });
  }

  const tableMat = new THREE.MeshStandardMaterial({ roughness: 0.78, metalness: 0.04 });
  const table = new THREE.Mesh(new THREE.BoxGeometry(28, 0.45, 28), [
    new THREE.MeshStandardMaterial({ color: 0x1a100c, roughness: 0.9 }),
    new THREE.MeshStandardMaterial({ color: 0x1a100c, roughness: 0.9 }),
    tableMat,
    new THREE.MeshStandardMaterial({ color: 0x100a08, roughness: 0.9 }),
    new THREE.MeshStandardMaterial({ color: 0x1a100c, roughness: 0.9 }),
    new THREE.MeshStandardMaterial({ color: 0x1a100c, roughness: 0.9 }),
  ]);
  table.position.y = -0.225;
  table.receiveShadow = true;
  scene.add(table);

  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  function rollValue() {
    if (force) {
      const n = parseInt(force, 10);
      if (n >= 1 && n <= 20) return n;
    }
    const buf = new Uint32Array(1);
    const limit = Math.floor(0x100000000 / 20) * 20;
    do {
      crypto.getRandomValues(buf);
    } while (buf[0] >= limit);
    return (buf[0] % 20) + 1;
  }

  function smooth(a, b, t) {
    if (t <= a) return 0;
    if (t >= b) return 1;
    const x = (t - a) / (b - a);
    return x * x * (3 - 2 * x);
  }

  function poseAt(die, t) {
    const ang = die.turns * Math.PI * 2 * (1 - t);
    const spin = new THREE.Quaternion().setFromAxisAngle(die.axis, ang);
    const spinning = die.qStart.clone().multiply(spin);
    const u = smooth(0.55, 1, t);
    spinning.slerp(die.qTarget, u);
    const hop = Math.sin(Math.PI * t) * die.hop;
    die.group.quaternion.copy(spinning);
    die.group.position.set(
      die.homeX + Math.sin(Math.PI * t) * die.slide,
      lift(spinning) + hop,
      die.homeZ + Math.sin(Math.PI * t) * die.slideZ
    );
    return spinning;
  }

  const mog = document.getElementById("mog");
  const prompt = document.getElementById("prompt");
  const nums = document.getElementById("nums");
  const total = document.getElementById("total");
  const warn = document.getElementById("warn");
  const MOOD = {
    idle: "assets/mog-idle.jpg",
    cheer: "assets/mog-cheer.jpg",
    sad: "assets/mog-sad.jpg",
  };

  function setMood(n) {
    const src = n === 20 ? MOOD.cheer : n === 1 ? MOOD.sad : MOOD.idle;
    if (mog.getAttribute("src") !== src) mog.src = src;
  }

  function paintReadout() {
    const rolling = dice.some(function (d) { return d.rolling; });
    const shown = dice.map(function (d) { return d.result; });
    const any = shown.some(function (n) { return n; });
    prompt.hidden = any || rolling;
    nums.replaceChildren();
    if (!any) {
      total.textContent = "";
      return;
    }
    shown.forEach(function (n, i) {
      if (i > 0 && count === 2) {
        const plus = document.createElement("span");
        plus.className = "plus";
        plus.textContent = "+";
        nums.appendChild(plus);
      }
      const el = document.createElement("span");
      el.className = "num" + (n === 20 ? " crit" : n === 1 ? " fail" : "");
      el.textContent = n && !dice[i].rolling ? String(n) : "·";
      nums.appendChild(el);
    });
    const both = count === 2 && shown[0] && shown[1] && !rolling;
    total.textContent = both ? String(shown[0] + shown[1]) : "";
  }

  function startRoll(index, value) {
    const die = dice[index];
    if (!die || die.rolling) return;
    const n = value || rollValue();
    die.qStart = die.group.quaternion.clone();
    die.qTarget = quatOf(n);
    die.axis = new THREE.Vector3(Math.random() - 0.5, Math.random() * 0.35, Math.random() - 0.5).normalize();
    die.turns = Math.random() < 0.5 ? 2 : 3;
    die.hop = 0.28 + Math.random() * 0.22;
    die.slide = (Math.random() - 0.5) * 0.35;
    die.slideZ = (Math.random() - 0.5) * 0.28;
    die.dur = 1.15;
    die.t0 = performance.now();
    die.rolling = true;
    die.pending = n;
    prompt.hidden = true;
    paintReadout();
  }

  function applySettle() {
    if (!settleArg) return;
    const parts = settleArg.split(",").map(function (s) { return parseInt(s, 10); });
    if (parts.length > 1) count = 2;
    document.getElementById("one").setAttribute("aria-pressed", count === 1 ? "true" : "false");
    document.getElementById("two").setAttribute("aria-pressed", count === 2 ? "true" : "false");
    spawn();
    parts.forEach(function (n, i) {
      if (!dice[i] || n < 1 || n > 20) return;
      dice[i].qTarget = quatOf(n);
      place(dice[i], dice[i].qTarget);
      dice[i].result = faceUp(dice[i].group.quaternion);
      warn.hidden = warn.hidden && dice[i].result === n;
    });
    const last = dice[Math.min(parts.length, dice.length) - 1];
    if (last && last.result) setMood(last.result);
    paintReadout();
  }

  function onPointer(e) {
    const rect = renderer.domElement.getBoundingClientRect();
    pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const hits = raycaster.intersectObjects(dice.map(function (d) { return d.group; }), true);
    if (!hits.length) {
      renderer.domElement.style.cursor = "default";
      return null;
    }
    let o = hits[0].object;
    while (o && o.userData.dieIndex === undefined) o = o.parent;
    renderer.domElement.style.cursor = "pointer";
    return o ? o.userData.dieIndex : null;
  }

  renderer.domElement.addEventListener("pointermove", onPointer);
  renderer.domElement.addEventListener("pointerdown", function (e) {
    const index = onPointer(e);
    if (index === null || index === undefined) return;
    if (dice.some(function (d) { return d.rolling; })) return;
    hideSave();
    if (count === 2) dice.forEach(function (_, i) { startRoll(i); });
    else startRoll(index);
  });

  const saveCard = document.getElementById("save-card");
  const saveRoll = document.getElementById("save-roll");
  const saveName = document.getElementById("save-name");
  const logPanel = document.getElementById("log-panel");
  const logBtn = document.getElementById("log");
  let saveTimer = 0;
  let pendingSave = null;

  function hideSave() {
    clearTimeout(saveTimer);
    saveTimer = 0;
    pendingSave = null;
    saveCard.hidden = true;
    saveName.value = "";
  }

  function rollLine(faces) {
    if (faces.length >= 2) return faces[0] + " + " + faces[1];
    return String(faces[0]);
  }

  function showSave(snap) {
    pendingSave = snap;
    saveRoll.textContent = rollLine(snap.dice);
    saveName.value = "";
    saveCard.hidden = false;
    saveName.focus();
  }

  function armSave() {
    if (dice.some(function (d) { return d.rolling || !d.result; })) return;
    clearTimeout(saveTimer);
    const faces = dice.map(function (d) { return d.result; });
    const rolledAt = new Date().toISOString();
    saveTimer = setTimeout(function () {
      saveTimer = 0;
      showSave({ dice: faces, rolledAt: rolledAt });
    }, 2500);
  }

  function renderLog() {
    const list = document.getElementById("log-list");
    const empty = document.getElementById("log-empty");
    const rows = window.RollLog.list();
    list.replaceChildren();
    empty.hidden = rows.length > 0;
    rows.forEach(function (row) {
      const li = document.createElement("li");
      li.textContent = window.RollLog.label(row);
      list.appendChild(li);
    });
  }

  function setLogOpen(open) {
    logPanel.hidden = !open;
    logBtn.setAttribute("aria-pressed", open ? "true" : "false");
    if (open) renderLog();
  }

  saveCard.addEventListener("submit", function (e) {
    e.preventDefault();
    if (!pendingSave) return;
    const row = window.RollLog.save(saveName.value, pendingSave.dice, pendingSave.rolledAt);
    if (!row) return;
    hideSave();
    if (!logPanel.hidden) renderLog();
  });
  document.getElementById("save-close").addEventListener("click", hideSave);
  logBtn.addEventListener("click", function () { setLogOpen(logPanel.hidden); });
  document.getElementById("log-close").addEventListener("click", function () { setLogOpen(false); });

  document.getElementById("one").addEventListener("click", function () { setCount(1); });
  document.getElementById("two").addEventListener("click", function () { setCount(2); });

  function setCount(n) {
    count = n;
    document.getElementById("one").setAttribute("aria-pressed", n === 1 ? "true" : "false");
    document.getElementById("two").setAttribute("aria-pressed", n === 2 ? "true" : "false");
    hideSave();
    spawn();
    setMood(0);
    prompt.hidden = false;
    warn.hidden = true;
    paintReadout();
  }

  addEventListener("resize", function () {
    camera.aspect = innerWidth / innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight);
  });

  let ready = false;
  function boot() {
    if (ready) return;
    const pending = [woodImg].concat(Object.keys(faceImgs).map(function (k) { return faceImgs[k]; }));
    if (pending.some(function (img) { return !img.complete || !img.naturalWidth; })) return;
    ready = true;
    const woodTex = new THREE.Texture(woodImg);
    woodTex.needsUpdate = true;
    woodTex.colorSpace = THREE.SRGBColorSpace;
    woodTex.wrapS = woodTex.wrapT = THREE.RepeatWrapping;
    woodTex.repeat.set(1, 1);
    woodTex.anisotropy = renderer.capabilities.getMaxAnisotropy();
    tableMat.map = woodTex;
    tableMat.needsUpdate = true;
    buildGeometry();
    if (settleArg) applySettle();
    else {
      setCount(count);
    }
    document.body.dataset.ready = "1";
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }

  function frame(now) {
    let settledNow = false;
    const want = count === 1 ? camOne : camTwo;
    camera.position.y += (want.y - camera.position.y) * 0.08;
    camera.position.z += (want.z - camera.position.z) * 0.08;
    camera.lookAt(0, 0.85, 0);
    dice.forEach(function (die) {
      if (!die.rolling) return;
      const t = Math.min(1, (now - die.t0) / (die.dur * 1000));
      const q = poseAt(die, t);
      if (t >= 1) {
        die.rolling = false;
        place(die, die.qTarget);
        const landed = faceUp(die.group.quaternion);
        die.result = landed;
        warn.hidden = landed === die.pending;
        settledNow = true;
        paintReadout();
        if (landed !== die.pending) warn.hidden = false;
      } else {
        void q;
      }
    });
    if (settledNow && dice.every(function (d) { return !d.rolling && d.result; })) {
      const faces = dice.map(function (d) { return d.result; });
      if (faces.indexOf(20) !== -1) setMood(20);
      else if (faces.indexOf(1) !== -1) setMood(1);
      else setMood(faces[faces.length - 1]);
      armSave();
    }
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }

  addEventListener("load", boot);
  boot();
})();
