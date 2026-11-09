/* ==========================================================================
   ATOM 3D ENGINE — Apartamento 4A (The Big Bang Theory)
   Escena 3D interactiva en Three.js con los 7 personajes principales,
   pizarra científica en tiempo real, doble hélice de ADN y cámara orbital.
   ========================================================================== */

window.Atom3DScene = class Atom3DScene {
  constructor(stageContainerId, labelsContainerId, onSelectCharacter) {
    this.container = document.getElementById(stageContainerId);
    this.labelsContainer = document.getElementById(labelsContainerId);
    this.onSelectCharacter = onSelectCharacter;

    this.characters = {};
    this.interactiveMeshes = [];
    this.characterOrder = ["sheldon", "leonard", "penny", "howard", "raj", "bernadette", "amy"];
    this.activeCharId = "sheldon";
    this.teamData = [];
    this.liveData = null;

    this.clock = new THREE.Clock();
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();

    // Animación suave de cámara (Fly-To)
    this.camTargetPos = null;
    this.camTargetLook = null;
    this.backdropMesh = null;
    this.showPhotoBackdrop = true;
    this.dnaGroup = null;
    this.whiteboardCanvas = null;
    this.whiteboardTex = null;

    this.meetingTimer = null;
    this.meetingIndex = 0;

    if (this.container && window.THREE) {
      this._initThree();
      this._buildApartment4A();
      this._buildAllCharacters();
      this._setupInteractions();
      this._animate();
    }
  }

  // -------------------------------------------------------------------------
  // INICIALIZACIÓN DE THREE.JS, LUCES Y CONTROLES
  // -------------------------------------------------------------------------
  _initThree() {
    const w = this.container.clientWidth || 1100;
    const h = this.container.clientHeight || 620;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0d0e12);
    this.scene.fog = new THREE.FogExp2(0x0d0e12, 0.022);

    // Encuadre clásico de cámara de TV del Apartamento 4A
    this.camera = new THREE.PerspectiveCamera(42, w / h, 0.1, 120);
    this.defaultCamPos = new THREE.Vector3(0.4, 3.65, 8.35);
    this.defaultCamLook = new THREE.Vector3(0.1, 1.45, -1.1);
    this.camera.position.copy(this.defaultCamPos);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    this.renderer.setSize(w, h);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.outputEncoding = THREE.sRGBEncoding;
    this.container.appendChild(this.renderer.domElement);

    if (THREE.OrbitControls) {
      this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
      this.controls.target.copy(this.defaultCamLook);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.07;
      this.controls.maxPolarAngle = Math.PI / 2 - 0.03;
      this.controls.minPolarAngle = 0.22;
      this.controls.minDistance = 3.2;
      this.controls.maxDistance = 15.5;
      this.controls.update();
    }

    // Iluminación cálida de estudio de grabación (estilo sitcom multicámara + lámparas cálidas)
    const hemi = new THREE.HemisphereLight(0xffeacc, 0x2a2430, 0.68);
    this.scene.add(hemi);

    const keyLight = new THREE.DirectionalLight(0xfff1d6, 0.82);
    keyLight.position.set(4.5, 9.5, 6.5);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 2048;
    keyLight.shadow.mapSize.height = 2048;
    keyLight.shadow.camera.near = 1;
    keyLight.shadow.camera.far = 26;
    const d = 9.5;
    keyLight.shadow.camera.left = -d;
    keyLight.shadow.camera.right = d;
    keyLight.shadow.camera.top = d;
    keyLight.shadow.camera.bottom = -d;
    this.scene.add(keyLight);

    // Luz cálida de la lámpara de mesa junto al sofá y ADN
    this.lampLight = new THREE.PointLight(0xffaa44, 1.15, 9.5, 1.8);
    this.lampLight.position.set(0.85, 2.35, -2.1);
    this.lampLight.castShadow = true;
    this.scene.add(this.lampLight);

    // Luz azulada de los monitores de Howard y ventana nocturna de Pasadena
    const windowGlow = new THREE.PointLight(0x007acc, 0.65, 8.5);
    windowGlow.position.set(3.5, 3.2, -4.1);
    this.scene.add(windowGlow);

    const ro = new ResizeObserver(() => this.resize());
    ro.observe(this.container);
  }

  resize() {
    if (!this.container || !this.renderer || !this.camera) return;
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    if (!w || !h) return;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  }

  // -------------------------------------------------------------------------
  // TEXTURAS PROCEDURALES FIELES A LA FOTO DEL APARTAMENTO 4A
  // -------------------------------------------------------------------------
  _createWoodFloorTexture() {
    const c = document.createElement("canvas");
    c.width = 512;
    c.height = 512;
    const ctx = c.getContext("2d");
    ctx.fillStyle = "#6e4224";
    ctx.fillRect(0, 0, 512, 512);

    const rows = 16;
    const h = 512 / rows;
    for (let r = 0; r < rows; r++) {
      const y = r * h;
      ctx.fillStyle = r % 2 === 0 ? "#734627" : "#673d20";
      ctx.fillRect(0, y, 512, h - 1);
      ctx.strokeStyle = "#472813";
      ctx.lineWidth = 1.5;
      ctx.strokeRect(0, y, 512, h);
      const splitX = ((r * 137) % 380) + 60;
      ctx.beginPath();
      ctx.moveTo(splitX, y);
      ctx.lineTo(splitX, y + h);
      ctx.stroke();
    }
    const tex = new THREE.CanvasTexture(c);
    tex.wrapS = THREE.RepeatWrapping;
    tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(4, 4);
    return tex;
  }

  _createKilimRugTexture() {
    // Reproduce la alfombra geométrica naranja/azul/crema bajo la mesa de vidrio
    const c = document.createElement("canvas");
    c.width = 512;
    c.height = 320;
    const ctx = c.getContext("2d");

    ctx.fillStyle = "#e8d5bd";
    ctx.fillRect(0, 0, 512, 320);

    // Borde azul marino y grecas
    ctx.strokeStyle = "#23445e";
    ctx.lineWidth = 18;
    ctx.strokeRect(12, 12, 488, 296);

    ctx.strokeStyle = "#d46535";
    ctx.lineWidth = 8;
    ctx.strokeRect(28, 28, 456, 264);

    // Patrón de diamantes geométricos
    const cols = 6;
    const rows = 3;
    const cw = 420 / cols;
    const ch = 220 / rows;
    for (let r = 0; r < rows; r++) {
      for (let col = 0; col < cols; col++) {
        const cx = 46 + col * cw + cw / 2;
        const cy = 50 + r * ch + ch / 2;

        ctx.fillStyle = (r + col) % 2 === 0 ? "#d46535" : "#274b69";
        ctx.beginPath();
        ctx.moveTo(cx, cy - ch * 0.42);
        ctx.lineTo(cx + cw * 0.42, cy);
        ctx.lineTo(cx, cy + ch * 0.42);
        ctx.lineTo(cx - cw * 0.42, cy);
        ctx.closePath();
        ctx.fill();

        ctx.fillStyle = "#e8d5bd";
        ctx.beginPath();
        ctx.arc(cx, cy, 7, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    return new THREE.CanvasTexture(c);
  }

  _createStripedPillowTexture() {
    const c = document.createElement("canvas");
    c.width = 128;
    c.height = 128;
    const ctx = c.getContext("2d");
    const colors = ["#d46535", "#e3b341", "#2b5b84", "#c94a38", "#e8d5bd", "#3a7d5c"];
    const sh = 128 / colors.length;
    colors.forEach((col, i) => {
      ctx.fillStyle = col;
      ctx.fillRect(0, i * sh, 128, sh + 1);
    });
    return new THREE.CanvasTexture(c);
  }

  // -------------------------------------------------------------------------
  // CONSTRUCCIÓN ARQUITECTÓNICA DEL APARTAMENTO 4A
  // -------------------------------------------------------------------------
  _buildApartment4A() {
    // 1. Suelo de madera noble
    const floorGeo = new THREE.PlaneGeometry(24, 18);
    const floorMat = new THREE.MeshStandardMaterial({
      map: this._createWoodFloorTexture(),
      roughness: 0.72,
      metalness: 0.08,
    });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    this.scene.add(floor);

    // 2. Alfombra grande azul pizarra (base) + Alfombra geométrica Kilim (arriba)
    const blueRug = new THREE.Mesh(
      new THREE.BoxGeometry(8.8, 0.025, 5.4),
      new THREE.MeshStandardMaterial({ color: 0x203748, roughness: 0.92 })
    );
    blueRug.position.set(-0.15, 0.013, 0.55);
    blueRug.rotation.y = 0.14;
    blueRug.receiveShadow = true;
    this.scene.add(blueRug);

    const kilimRug = new THREE.Mesh(
      new THREE.BoxGeometry(5.6, 0.032, 3.4),
      new THREE.MeshStandardMaterial({ map: this._createKilimRugTexture(), roughness: 0.88 })
    );
    kilimRug.position.set(-0.1, 0.02, 0.85);
    kilimRug.rotation.y = 0.14;
    kilimRug.receiveShadow = true;
    this.scene.add(kilimRug);

    // 3. Paredes del set + Telón Fotográfico HD conmutable del Apartamento 4A
    const wallMat = new THREE.MeshStandardMaterial({ color: 0x9e8c72, roughness: 0.85 });

    // Pared trasera
    const backWall = new THREE.Mesh(new THREE.BoxGeometry(18, 7.2, 0.25), wallMat);
    backWall.position.set(0, 3.6, -5.6);
    backWall.receiveShadow = true;
    this.scene.add(backWall);

    // Pared izquierda angulada (nicho de la gran estantería de libros)
    const leftWall = new THREE.Mesh(new THREE.BoxGeometry(8.5, 7.2, 0.25), wallMat);
    leftWall.position.set(-6.2, 3.6, -2.5);
    leftWall.rotation.y = 0.42;
    leftWall.receiveShadow = true;
    this.scene.add(leftWall);

    // Escalón del pasillo derecho y pilar de madera icónico
    const stepPlatform = new THREE.Mesh(
      new THREE.BoxGeometry(5.5, 0.26, 6.5),
      new THREE.MeshStandardMaterial({ color: 0x734627, roughness: 0.75 })
    );
    stepPlatform.position.set(6.8, 0.13, -1.8);
    stepPlatform.receiveShadow = true;
    this.scene.add(stepPlatform);

    const woodPillar = new THREE.Mesh(
      new THREE.BoxGeometry(0.48, 7.2, 0.48),
      new THREE.MeshStandardMaterial({ color: 0x7d4e2d, roughness: 0.65 })
    );
    woodPillar.position.set(4.35, 3.6, -1.45);
    woodPillar.castShadow = true;
    this.scene.add(woodPillar);

    // Mural de referencia fotográfica sutil en el fondo (conmutable con botón)
    const texLoader = new THREE.TextureLoader();
    texLoader.load("/static/apt4a_ref.jpg", (tex) => {
      tex.encoding = THREE.sRGBEncoding;
      const bgPlane = new THREE.Mesh(
        new THREE.PlaneGeometry(16.8, 7.6),
        new THREE.MeshBasicMaterial({ map: tex, transparent: true, opacity: 0.28 })
      );
      bgPlane.position.set(0.2, 3.8, -5.42);
      this.scene.add(bgPlane);
      this.backdropMesh = bgPlane;
    });

    // 4. Puerta del pasillo con póster
    const doorGroup = new THREE.Group();
    const doorFrame = new THREE.Mesh(
      new THREE.BoxGeometry(1.55, 3.7, 0.12),
      new THREE.MeshStandardMaterial({ color: 0x8c5327, roughness: 0.7 })
    );
    const doorPanel = new THREE.Mesh(
      new THREE.BoxGeometry(1.38, 3.55, 0.14),
      new THREE.MeshStandardMaterial({ color: 0x9e5f2e, roughness: 0.65 })
    );
    const poster = new THREE.Mesh(
      new THREE.BoxGeometry(0.65, 0.52, 0.16),
      new THREE.MeshStandardMaterial({ color: 0x15355a, roughness: 0.5 })
    );
    poster.position.set(0, 0.45, 0.01);
    doorGroup.add(doorFrame, doorPanel, poster);
    doorGroup.position.set(-1.95, 1.85, -5.38);
    this.scene.add(doorGroup);

    // 5. Doble Estantería de Libros Izquierda (detrás del sofá)
    this._buildBookcase(-4.85, 0, -3.55, 0.16, 4.3, 2.75, 0.55, 0x9c6635);

    // 6. Pizarra Científica Interactiva de Sheldon (con Canvas en Vivo)
    this._buildLiveWhiteboard();

    // 7. Modelo 3D de la Doble Hélice de ADN (al lado de la pizarra)
    this._buildDnaHelix(0.48, 0.0, -4.45);

    // 8. Ventana de Pasadena con Cortinas Azules + Estación de Telescopio y PC de Howard
    this._buildWindowAndDesk();

    // 9. El Icónico Sofá de Cuero Marrón (con "My Spot" de Sheldon)
    this._buildBrownLeatherSofa();

    // 10. La Mesa de Centro Redonda de Cristal
    this._buildGlassCoffeeTable();

    // 11. El Sillón Individual Crema (Penny) y la Silla Caoba (Bernadette)
    this._buildArmchairs();
  }

  _buildBookcase(x, y, z, rotY, width, height, depth, woodHex) {
    const group = new THREE.Group();
    const woodMat = new THREE.MeshStandardMaterial({ color: woodHex, roughness: 0.68 });

    const body = new THREE.Mesh(new THREE.BoxGeometry(width, height, depth), woodMat);
    body.position.y = height / 2;
    body.castShadow = true;
    body.receiveShadow = true;
    group.add(body);

    const innerMat = new THREE.MeshStandardMaterial({ color: 0x3b2312, roughness: 0.9 });
    const inner = new THREE.Mesh(new THREE.BoxGeometry(width - 0.18, height - 0.18, depth - 0.06), innerMat);
    inner.position.set(0, height / 2, 0.05);
    group.add(inner);

    // Repisas y libros multicolores
    const bookColors = [0xb8332a, 0x1f5f8b, 0x2e7d32, 0xd4882a, 0x6a3d9a, 0xc9b458, 0x2b3a4a];
    const shelves = 4;
    for (let s = 0; s < shelves; s++) {
      const sy = 0.12 + s * ((height - 0.24) / shelves);
      const shelf = new THREE.Mesh(new THREE.BoxGeometry(width - 0.1, 0.06, depth + 0.02), woodMat);
      shelf.position.set(0, sy, 0.02);
      group.add(shelf);

      // Llenar de libros
      let bx = -width / 2 + 0.22;
      while (bx < width / 2 - 0.25) {
        const bw = 0.07 + ((Math.abs(Math.sin(bx * 19 + s * 7))) * 0.06);
        const bh = 0.34 + ((Math.abs(Math.cos(bx * 13 + s))) * 0.16);
        const bCol = bookColors[Math.floor(Math.abs(bx * 23 + s * 5)) % bookColors.length];
        const book = new THREE.Mesh(
          new THREE.BoxGeometry(bw, bh, depth * 0.65),
          new THREE.MeshStandardMaterial({ color: bCol, roughness: 0.6 })
        );
        book.position.set(bx, sy + bh / 2 + 0.03, 0.08);
        group.add(book);
        bx += bw + 0.015;
      }
    }

    // Esfera de plasma y coleccionables sobre el estante superior
    const globe = new THREE.Mesh(
      new THREE.SphereGeometry(0.22, 16, 16),
      new THREE.MeshStandardMaterial({ color: 0x007acc, emissive: 0x003366, roughness: 0.2, metalness: 0.3 })
    );
    globe.position.set(-0.9, height + 0.22, 0);
    group.add(globe);

    group.position.set(x, y, z);
    group.rotation.y = rotY;
    this.scene.add(group);
  }

  _buildLiveWhiteboard() {
    this.whiteboardCanvas = document.createElement("canvas");
    this.whiteboardCanvas.width = 512;
    this.whiteboardCanvas.height = 384;
    this.whiteboardTex = new THREE.CanvasTexture(this.whiteboardCanvas);
    this._renderWhiteboardContent();

    const wbGroup = new THREE.Group();
    const frame = new THREE.Mesh(
      new THREE.BoxGeometry(1.55, 1.25, 0.08),
      new THREE.MeshStandardMaterial({ color: 0x555555, metalness: 0.5, roughness: 0.4 })
    );
    const board = new THREE.Mesh(
      new THREE.PlaneGeometry(1.45, 1.15),
      new THREE.MeshBasicMaterial({ map: this.whiteboardTex })
    );
    board.position.z = 0.045;
    board.userData = { charId: "bernadette", isProp: true, propName: "Pizarra Científica XAU/USD" };
    this.interactiveMeshes.push(board);

    wbGroup.add(frame, board);
    wbGroup.position.set(-0.35, 2.75, -5.36);
    this.scene.add(wbGroup);
  }

  _renderWhiteboardContent() {
    if (!this.whiteboardCanvas) return;
    const ctx = this.whiteboardCanvas.getContext("2d");
    ctx.fillStyle = "#f4f6f8";
    ctx.fillRect(0, 0, 512, 384);

    ctx.strokeStyle = "#222";
    ctx.lineWidth = 4;
    ctx.strokeRect(6, 6, 500, 372);

    ctx.fillStyle = "#111";
    ctx.font = "bold 22px Consolas, monospace";
    ctx.fillText("ATOM LAB · ECUACIÓN XAU/USD", 22, 38);

    ctx.strokeStyle = "#007ACC";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(22, 48);
    ctx.lineTo(490, 48);
    ctx.stroke();

    const lv = (this.liveData && this.liveData.levels) || {};
    const px = lv.current_price ? `$${lv.current_price.toFixed(2)}` : "$4,074.90";
    const bias = lv.htf_bias || "ALCISTA";

    ctx.fillStyle = "#005a9e";
    ctx.font = "bold 28px Consolas, monospace";
    ctx.fillText(`XAU/USD: ${px} (${bias})`, 22, 88);

    ctx.fillStyle = "#222";
    ctx.font = "bold 18px Consolas, monospace";
    ctx.fillText(`• PDH: $${lv.pdh || "—"}   | PDL: $${lv.pdl || "—"}`, 22, 128);
    ctx.fillText(`• Asian H/L : $${lv.asian_high || "—"} / $${lv.asian_low || "—"}`, 22, 160);
    ctx.fillText(`• London H/L: $${lv.london_high || "—"} / $${lv.london_low || "—"}`, 22, 192);
    ctx.fillText(`• Lotaje(10K) = $50 / (ΔSL × 100)`, 22, 232);
    ctx.fillText(`• Ψ(CISD) = Body/Range ≥ 0.50 → FVG 50% CE`, 22, 265);

    // Dibujo esquemático de Sweep + CISD + FVG en la esquina de la pizarra
    ctx.strokeStyle = "#d93829";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(40, 340);
    ctx.lineTo(130, 290);
    ctx.lineTo(185, 350);
    ctx.lineTo(235, 315);
    ctx.lineTo(340, 365);
    ctx.stroke();

    ctx.fillStyle = "#2ea043";
    ctx.font = "bold 16px Consolas, monospace";
    ctx.fillText("[CLIC AQUÍ -> ABRIR GRÁFICO EN VIVO]", 80, 370);

    if (this.whiteboardTex) this.whiteboardTex.needsUpdate = true;
  }

  _buildDnaHelix(x, y, z) {
    this.dnaGroup = new THREE.Group();
    const stand = new THREE.Mesh(
      new THREE.CylinderGeometry(0.28, 0.34, 0.08, 18),
      new THREE.MeshStandardMaterial({ color: 0x222222, metalness: 0.6, roughness: 0.3 })
    );
    stand.position.y = 0.04;
    this.dnaGroup.add(stand);

    const rod = new THREE.Mesh(
      new THREE.CylinderGeometry(0.025, 0.025, 3.6, 10),
      new THREE.MeshStandardMaterial({ color: 0xaaaaaa, metalness: 0.8, roughness: 0.2 })
    );
    rod.position.y = 1.85;
    this.dnaGroup.add(rod);

    const atomColors = [0xe53935, 0x1e88e5, 0xfdd835, 0x43a047];
    const sphereGeo = new THREE.SphereGeometry(0.068, 12, 12);

    for (let i = 0; i < 34; i++) {
      const py = 0.35 + i * 0.095;
      const ang = i * 0.42;
      const r = 0.22;

      const s1 = new THREE.Mesh(
        sphereGeo,
        new THREE.MeshStandardMaterial({ color: atomColors[i % 4], roughness: 0.25, metalness: 0.2 })
      );
      s1.position.set(Math.cos(ang) * r, py, Math.sin(ang) * r);

      const s2 = new THREE.Mesh(
        sphereGeo,
        new THREE.MeshStandardMaterial({ color: atomColors[(i + 2) % 4], roughness: 0.25, metalness: 0.2 })
      );
      s2.position.set(Math.cos(ang + Math.PI) * r, py, Math.sin(ang + Math.PI) * r);

      const bond = new THREE.Mesh(
        new THREE.CylinderGeometry(0.015, 0.015, r * 2, 6),
        new THREE.MeshStandardMaterial({ color: 0xffffff })
      );
      bond.position.set(0, py, 0);
      bond.rotation.z = Math.PI / 2;
      bond.rotation.y = -ang;

      this.dnaGroup.add(s1, s2, bond);
    }

    this.dnaGroup.position.set(x, y, z);
    this.scene.add(this.dnaGroup);
  }

  _buildWindowAndDesk() {
    // Ventana al fondo derecha con cortinas azules
    const winGroup = new THREE.Group();
    const sky = new THREE.Mesh(
      new THREE.PlaneGeometry(2.6, 3.1),
      new THREE.MeshBasicMaterial({ color: 0x11243b })
    );
    const curtainMat = new THREE.MeshStandardMaterial({ color: 0x0b3954, roughness: 0.8 });
    const leftCurtain = new THREE.Mesh(new THREE.BoxGeometry(0.45, 3.4, 0.18), curtainMat);
    leftCurtain.position.set(-1.25, 0, 0.08);
    const rightCurtain = new THREE.Mesh(new THREE.BoxGeometry(0.45, 3.4, 0.18), curtainMat);
    rightCurtain.position.set(1.25, 0, 0.08);

    winGroup.add(sky, leftCurtain, rightCurtain);
    winGroup.position.set(3.55, 3.35, -5.35);
    this.scene.add(winGroup);

    // Escritorio de computadora y Telescopio
    const desk = new THREE.Mesh(
      new THREE.BoxGeometry(1.9, 0.85, 0.95),
      new THREE.MeshStandardMaterial({ color: 0x5c3419, roughness: 0.65 })
    );
    desk.position.set(2.85, 0.425, -3.55);
    desk.castShadow = true;
    this.scene.add(desk);

    // Monitor iMac brillante en el escritorio de Howard
    const monitor = new THREE.Mesh(
      new THREE.BoxGeometry(0.72, 0.48, 0.05),
      new THREE.MeshStandardMaterial({ color: 0xdadada, emissive: 0x004477, emissiveIntensity: 0.5 })
    );
    monitor.position.set(2.85, 1.15, -3.45);
    monitor.rotation.y = -0.25;
    this.scene.add(monitor);

    // Telescopio Astrofísico de Raj
    const teleGroup = new THREE.Group();
    const tube = new THREE.Mesh(
      new THREE.CylinderGeometry(0.07, 0.09, 1.15, 16),
      new THREE.MeshStandardMaterial({ color: 0x1c1c1c, metalness: 0.7, roughness: 0.3 })
    );
    tube.rotation.z = Math.PI / 3.2;
    tube.position.y = 1.38;
    const tripod = new THREE.Mesh(
      new THREE.ConeGeometry(0.38, 1.35, 3),
      new THREE.MeshStandardMaterial({ color: 0x734627 })
    );
    tripod.position.y = 0.68;
    teleGroup.add(tube, tripod);
    teleGroup.position.set(1.85, 0, -3.05);
    this.scene.add(teleGroup);

    // Mesa de lámpara junto al sofá
    const lampTable = new THREE.Mesh(
      new THREE.BoxGeometry(0.75, 0.72, 0.75),
      new THREE.MeshStandardMaterial({ color: 0x5c3419 })
    );
    lampTable.position.set(0.85, 0.36, -2.1);
    this.scene.add(lampTable);

    const lampShade = new THREE.Mesh(
      new THREE.ConeGeometry(0.28, 0.36, 18, 1, true),
      new THREE.MeshStandardMaterial({
        color: 0xfff0c4,
        emissive: 0xffaa33,
        emissiveIntensity: 0.7,
        side: THREE.DoubleSide,
      })
    );
    lampShade.position.set(0.85, 1.25, -2.1);
    this.scene.add(lampShade);
  }

  _buildBrownLeatherSofa() {
    const sofaGroup = new THREE.Group();
    const leatherMat = new THREE.MeshStandardMaterial({
      color: 0x7a371b,
      roughness: 0.42,
      metalness: 0.08,
    });
    const darkLeatherMat = new THREE.MeshStandardMaterial({
      color: 0x5e2812,
      roughness: 0.48,
    });

    // Base del sofá
    const base = new THREE.Mesh(new THREE.BoxGeometry(3.85, 0.42, 1.25), darkLeatherMat);
    base.position.y = 0.24;
    base.castShadow = true;
    base.receiveShadow = true;
    sofaGroup.add(base);

    // 3 Cojines de asiento (Izquierda = Sheldon's Spot!)
    for (let i = -1; i <= 1; i++) {
      const cushion = new THREE.Mesh(new THREE.BoxGeometry(1.12, 0.24, 1.08), leatherMat);
      cushion.position.set(i * 1.15, 0.54, 0.04);
      cushion.castShadow = true;
      cushion.receiveShadow = true;
      sofaGroup.add(cushion);

      const backCushion = new THREE.Mesh(new THREE.BoxGeometry(1.12, 0.76, 0.32), leatherMat);
      backCushion.position.set(i * 1.15, 0.98, -0.44);
      backCushion.rotation.x = -0.12;
      backCushion.castShadow = true;
      sofaGroup.add(backCushion);
    }

    // Manta crema sobre el respaldo
    const blanket = new THREE.Mesh(
      new THREE.BoxGeometry(2.2, 0.28, 0.36),
      new THREE.MeshStandardMaterial({ color: 0xd8be9e, roughness: 0.9 })
    );
    blanket.position.set(-0.5, 1.28, -0.46);
    sofaGroup.add(blanket);

    // Apoyabrazos redondeados
    const armGeo = new THREE.CylinderGeometry(0.24, 0.26, 1.24, 16);
    armGeo.rotateX(Math.PI / 2);
    const leftArm = new THREE.Mesh(armGeo, leatherMat);
    leftArm.position.set(-1.92, 0.68, 0.02);
    const rightArm = new THREE.Mesh(armGeo, leatherMat);
    rightArm.position.set(1.92, 0.68, 0.02);
    sofaGroup.add(leftArm, rightArm);

    // Cojín crema izquierdo y cojín rayado derecho
    const creamPillow = new THREE.Mesh(
      new THREE.BoxGeometry(0.44, 0.44, 0.16),
      new THREE.MeshStandardMaterial({ color: 0xe6d7be, roughness: 0.85 })
    );
    creamPillow.position.set(-1.55, 0.84, -0.12);
    creamPillow.rotation.z = 0.22;
    sofaGroup.add(creamPillow);

    const stripedPillow = new THREE.Mesh(
      new THREE.BoxGeometry(0.52, 0.52, 0.18),
      new THREE.MeshStandardMaterial({ map: this._createStripedPillowTexture(), roughness: 0.8 })
    );
    stripedPillow.position.set(1.48, 0.88, -0.12);
    stripedPillow.rotation.z = -0.18;
    sofaGroup.add(stripedPillow);

    // Baúl de madera antiguo a la izquierda del sofá
    const trunk = new THREE.Mesh(
      new THREE.BoxGeometry(0.68, 0.54, 0.92),
      new THREE.MeshStandardMaterial({ color: 0x4c2b14, roughness: 0.75 })
    );
    trunk.position.set(-2.48, 0.27, 0.15);
    trunk.castShadow = true;
    sofaGroup.add(trunk);

    sofaGroup.position.set(-1.75, 0, -0.95);
    sofaGroup.rotation.y = 0.14;
    this.scene.add(sofaGroup);
  }

  _buildGlassCoffeeTable() {
    const tblGroup = new THREE.Group();

    const base = new THREE.Mesh(
      new THREE.CylinderGeometry(0.45, 0.52, 0.06, 24),
      new THREE.MeshStandardMaterial({ color: 0x2b2623, metalness: 0.6, roughness: 0.4 })
    );
    base.position.y = 0.03;

    const pedestal = new THREE.Mesh(
      new THREE.CylinderGeometry(0.11, 0.14, 0.48, 16),
      new THREE.MeshStandardMaterial({ color: 0x3b2c20, metalness: 0.4, roughness: 0.5 })
    );
    pedestal.position.y = 0.26;

    const rim = new THREE.Mesh(
      new THREE.TorusGeometry(1.08, 0.045, 12, 36),
      new THREE.MeshStandardMaterial({ color: 0x4a321f, roughness: 0.5 })
    );
    rim.rotation.x = Math.PI / 2;
    rim.position.y = 0.52;

    const glass = new THREE.Mesh(
      new THREE.CylinderGeometry(1.06, 1.06, 0.03, 36),
      new THREE.MeshStandardMaterial({
        color: 0xaad8ec,
        transparent: true,
        opacity: 0.42,
        roughness: 0.1,
        metalness: 0.2,
      })
    );
    glass.position.y = 0.53;

    // Cómics y laptop sobre la mesa de vidrio
    const comic1 = new THREE.Mesh(
      new THREE.BoxGeometry(0.32, 0.02, 0.42),
      new THREE.MeshStandardMaterial({ color: 0xd93829 })
    );
    comic1.position.set(-0.35, 0.555, 0.22);
    comic1.rotation.y = 0.35;

    const comic2 = new THREE.Mesh(
      new THREE.BoxGeometry(0.32, 0.02, 0.42),
      new THREE.MeshStandardMaterial({ color: 0x007acc })
    );
    comic2.position.set(0.18, 0.555, 0.32);
    comic2.rotation.y = -0.25;

    tblGroup.add(base, pedestal, rim, glass, comic1, comic2);
    tblGroup.position.set(-0.08, 0, 1.25);
    this.scene.add(tblGroup);
  }

  _buildArmchairs() {
    // 1. Sillón Crema (Penny) con cojín naranja
    const creamGroup = new THREE.Group();
    const creamMat = new THREE.MeshStandardMaterial({ color: 0xd4c3a6, roughness: 0.82 });

    const seat = new THREE.Mesh(new THREE.BoxGeometry(1.28, 0.48, 1.18), creamMat);
    seat.position.y = 0.26;
    seat.castShadow = true;

    const back = new THREE.Mesh(new THREE.BoxGeometry(1.22, 0.78, 0.34), creamMat);
    back.position.set(0, 0.78, -0.4);
    back.rotation.x = -0.14;
    back.castShadow = true;

    const armL = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.42, 1.12), creamMat);
    armL.position.set(-0.56, 0.58, 0.02);
    const armR = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.42, 1.12), creamMat);
    armR.position.set(0.56, 0.58, 0.02);

    const orangePillow = new THREE.Mesh(
      new THREE.BoxGeometry(0.46, 0.42, 0.16),
      new THREE.MeshStandardMaterial({ color: 0xe05328, roughness: 0.75 })
    );
    orangePillow.position.set(0.08, 0.72, -0.14);
    orangePillow.rotation.x = -0.15;

    creamGroup.add(seat, back, armL, armR, orangePillow);
    creamGroup.position.set(2.55, 0, 0.15);
    creamGroup.rotation.y = -0.58;
    this.scene.add(creamGroup);

    // 2. Silla de Madera Caoba en primer plano derecho (Bernadette)
    const woodGroup = new THREE.Group();
    const mahogMat = new THREE.MeshStandardMaterial({ color: 0x4d2310, roughness: 0.45, metalness: 0.1 });

    const wSeat = new THREE.Mesh(new THREE.BoxGeometry(0.95, 0.08, 0.88), mahogMat);
    wSeat.position.y = 0.48;
    wSeat.castShadow = true;
    woodGroup.add(wSeat);

    const legGeo = new THREE.CylinderGeometry(0.04, 0.035, 0.48, 10);
    [[-0.42, -0.38], [0.42, -0.38], [-0.42, 0.38], [0.42, 0.38]].forEach(([lx, lz]) => {
      const leg = new THREE.Mesh(legGeo, mahogMat);
      leg.position.set(lx, 0.24, lz);
      woodGroup.add(leg);
    });

    const wBack = new THREE.Mesh(new THREE.BoxGeometry(0.95, 0.58, 0.07), mahogMat);
    wBack.position.set(0, 0.82, -0.4);
    woodGroup.add(wBack);

    const wArmL = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.06, 0.84), mahogMat);
    wArmL.position.set(-0.44, 0.74, 0);
    const wArmR = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.06, 0.84), mahogMat);
    wArmR.position.set(0.44, 0.74, 0);
    woodGroup.add(wArmL, wArmR);

    woodGroup.position.set(3.65, 0, 1.95);
    woodGroup.rotation.y = -0.95;
    this.scene.add(woodGroup);
  }

  // -------------------------------------------------------------------------
  // CONSTRUCCIÓN ARTICULADA DE LOS 7 PERSONAJES PRINCIPALES EN 3D
  // -------------------------------------------------------------------------
  _buildAllCharacters() {
    const configs = [
      {
        id: "sheldon",
        pos: new THREE.Vector3(-2.82, 0.56, -1.06),
        rotY: 0.22,
        pose: "seated",
        scaleY: 1.12, // Alto y delgado
        skin: 0xf5d0b5,
        hair: 0x3b2618,
        hairStyle: "short_part",
        shirt: 0x2e8b57, // Camiseta verde Linterna Verde / Atom
        sleeves: 0xc62828, // Manga larga roja clásica debajo
        pants: 0x8d6e4c,
        glasses: false,
        prop: "clipboard",
        accentHex: 0x007acc,
      },
      {
        id: "amy",
        pos: new THREE.Vector3(-1.72, 0.56, -0.92),
        rotY: 0.16,
        pose: "seated",
        scaleY: 0.96,
        skin: 0xf3cfb6,
        hair: 0x4a2f1d,
        hairStyle: "long_straight",
        shirt: 0x6d1b2b, // Cárdigan granate
        sleeves: 0x6d1b2b,
        pants: 0x37474f,
        glasses: true,
        prop: "tablet",
        accentHex: 0x3794ff,
      },
      {
        id: "leonard",
        pos: new THREE.Vector3(-0.62, 0.56, -0.78),
        rotY: 0.06,
        pose: "seated",
        scaleY: 0.94,
        skin: 0xf1c7a8,
        hair: 0x2b1d14,
        hairStyle: "curly_top",
        shirt: 0x4b5338, // Chaqueta oliva con capucha
        sleeves: 0x4b5338,
        pants: 0x4a3b2c,
        glasses: true,
        prop: "laptop",
        accentHex: 0x007acc,
      },
      {
        id: "penny",
        pos: new THREE.Vector3(2.48, 0.52, 0.22),
        rotY: -0.58,
        pose: "seated",
        scaleY: 0.98,
        skin: 0xf6ceaf,
        hair: 0xe6b84c, // Rubio
        hairStyle: "blonde_waves",
        shirt: 0xe05276, // Top rosa/coral
        sleeves: 0xf6ceaf,
        pants: 0x285584, // Jeans
        glasses: false,
        prop: "mug",
        accentHex: 0x3fb950,
      },
      {
        id: "bernadette",
        pos: new THREE.Vector3(3.58, 0.50, 1.92),
        rotY: -0.95,
        pose: "seated",
        scaleY: 0.88, // Bajita como en la serie
        skin: 0xf7d4bc,
        hair: 0xebbf52,
        hairStyle: "blonde_headband",
        shirt: 0x1e6b9e, // Cárdigan azul sobre vestido amarillo
        sleeves: 0x1e6b9e,
        pants: 0xe3b341,
        glasses: true,
        prop: "microscope_pad",
        accentHex: 0x3fb950,
      },
      {
        id: "raj",
        pos: new THREE.Vector3(1.12, 0.18, 1.75),
        rotY: -0.45,
        pose: "floor_cushion",
        scaleY: 0.96,
        skin: 0xb57c52, // Tono de piel de Raj
        hair: 0x1a1412,
        hairStyle: "curly_top",
        shirt: 0x7b2cbf, // Chaleco / chaqueta púrpura-vino
        sleeves: 0xc2185b,
        pants: 0x6e5a44,
        glasses: false,
        prop: "astro_radar",
        accentHex: 0xe3b341,
      },
      {
        id: "howard",
        pos: new THREE.Vector3(2.25, 0.0, -2.55),
        rotY: -0.35,
        pose: "standing",
        scaleY: 0.93,
        skin: 0xf2c9ac,
        hair: 0x332014,
        hairStyle: "bowl_cut", // Corte tazón icónico de Howard
        shirt: 0x8e24aa, // Cuello de tortuga morado + chaleco
        sleeves: 0x8e24aa,
        pants: 0x212121, // Jeans ajustados
        glasses: false,
        prop: "belt_and_pad",
        accentHex: 0xa371f7,
      },
    ];

    configs.forEach((cfg) => {
      const charGroup = this._createCharacterMesh(cfg);
      this.scene.add(charGroup);
      this.characters[cfg.id] = {
        id: cfg.id,
        cfg,
        group: charGroup,
        headMesh: charGroup.userData.headGroup,
        rightArm: charGroup.userData.rightArm,
        ringMesh: charGroup.userData.ringMesh,
      };
    });
  }

  _createCharacterMesh(cfg) {
    const root = new THREE.Group();
    root.position.copy(cfg.pos);
    root.rotation.y = cfg.rotY;

    const skinMat = new THREE.MeshStandardMaterial({ color: cfg.skin, roughness: 0.55 });
    const hairMat = new THREE.MeshStandardMaterial({ color: cfg.hair, roughness: 0.65 });
    const shirtMat = new THREE.MeshStandardMaterial({ color: cfg.shirt, roughness: 0.6 });
    const sleeveMat = new THREE.MeshStandardMaterial({ color: cfg.sleeves, roughness: 0.6 });
    const pantsMat = new THREE.MeshStandardMaterial({ color: cfg.pants, roughness: 0.7 });

    // Anillo luminoso de selección en la base
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(0.38, 0.46, 28),
      new THREE.MeshBasicMaterial({
        color: cfg.accentHex,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.75,
      })
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = cfg.pose === "standing" ? 0.03 : -0.48;
    root.add(ring);

    const bodyRoot = new THREE.Group();
    bodyRoot.scale.set(1, cfg.scaleY, 1);
    root.add(bodyRoot);

    const torsoY = cfg.pose === "standing" ? 0.98 : 0.42;

    // Torso
    const torso = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.54, 0.25), shirtMat);
    torso.position.y = torsoY;
    torso.castShadow = true;
    bodyRoot.add(torso);

    // Logo de Átomo / Flash en el pecho de Sheldon o hebilla de cinturón en Howard
    if (cfg.id === "sheldon") {
      const emblem = new THREE.Mesh(
        new THREE.CircleGeometry(0.085, 16),
        new THREE.MeshBasicMaterial({ color: 0xffeb3b })
      );
      emblem.position.set(0, torsoY + 0.05, 0.13);
      bodyRoot.add(emblem);
    } else if (cfg.id === "howard") {
      const buckle = new THREE.Mesh(
        new THREE.BoxGeometry(0.12, 0.08, 0.04),
        new THREE.MeshStandardMaterial({ color: 0xffd700, metalness: 0.9, roughness: 0.2 })
      );
      buckle.position.set(0, torsoY - 0.25, 0.13);
      bodyRoot.add(buckle);
    }

    // Cabeza y Rostro
    const headGroup = new THREE.Group();
    headGroup.position.set(0, torsoY + 0.46, 0.02);

    const head = new THREE.Mesh(new THREE.SphereGeometry(0.21, 20, 20), skinMat);
    head.castShadow = true;
    headGroup.add(head);

    // Ojos
    const eyeMat = new THREE.MeshBasicMaterial({ color: 0x151515 });
    const eyeL = new THREE.Mesh(new THREE.SphereGeometry(0.024, 8, 8), eyeMat);
    eyeL.position.set(-0.07, 0.02, 0.185);
    const eyeR = new THREE.Mesh(new THREE.SphereGeometry(0.024, 8, 8), eyeMat);
    eyeR.position.set(0.07, 0.02, 0.185);
    headGroup.add(eyeL, eyeR);

    // Gafas (Leonard, Amy, Bernadette)
    if (cfg.glasses) {
      const glassFrameMat = new THREE.MeshBasicMaterial({ color: 0x111111 });
      const gL = new THREE.Mesh(new THREE.TorusGeometry(0.048, 0.008, 8, 16), glassFrameMat);
      gL.position.set(-0.07, 0.02, 0.195);
      const gR = new THREE.Mesh(new THREE.TorusGeometry(0.048, 0.008, 8, 16), glassFrameMat);
      gR.position.set(0.07, 0.02, 0.195);
      const bridge = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.01, 0.01), glassFrameMat);
      bridge.position.set(0, 0.02, 0.195);
      headGroup.add(gL, gR, bridge);
    }

    // Cabello distintivo por personaje
    const hairCap = new THREE.Mesh(
      new THREE.SphereGeometry(0.222, 18, 14, 0, Math.PI * 2, 0, Math.PI * 0.58),
      hairMat
    );
    hairCap.position.y = 0.02;
    headGroup.add(hairCap);

    if (cfg.hairStyle === "long_straight" || cfg.hairStyle === "blonde_waves" || cfg.hairStyle === "blonde_headband") {
      const hairBack = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.34, 0.18), hairMat);
      hairBack.position.set(0, -0.08, -0.08);
      headGroup.add(hairBack);

      if (cfg.hairStyle === "blonde_headband") {
        const band = new THREE.Mesh(
          new THREE.TorusGeometry(0.215, 0.018, 8, 20, Math.PI),
          new THREE.MeshBasicMaterial({ color: 0xc2185b })
        );
        band.rotation.x = -0.3;
        band.position.y = 0.05;
        headGroup.add(band);
      }
    }

    bodyRoot.add(headGroup);

    // Brazos y accesorios de trabajo (Clipboard, Laptop, Taza, Tablet)
    const leftArm = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.05, 0.42, 10), sleeveMat);
    leftArm.position.set(-0.27, torsoY + 0.02, 0.12);
    leftArm.rotation.x = -0.65;
    leftArm.rotation.z = 0.18;

    const rightArm = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.05, 0.42, 10), sleeveMat);
    rightArm.position.set(0.27, torsoY + 0.02, 0.12);
    rightArm.rotation.x = -0.65;
    rightArm.rotation.z = -0.18;
    bodyRoot.add(leftArm, rightArm);

    // Prop en las manos
    const propMesh = new THREE.Mesh(
      new THREE.BoxGeometry(0.32, 0.03, 0.24),
      new THREE.MeshStandardMaterial({
        color: 0x1e293b,
        emissive: cfg.accentHex,
        emissiveIntensity: 0.35,
      })
    );
    propMesh.position.set(0, torsoY - 0.08, 0.29);
    propMesh.rotation.x = 0.3;
    bodyRoot.add(propMesh);

    // Piernas (Sentados vs De pie)
    if (cfg.pose === "standing") {
      const legL = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.065, 0.72, 10), pantsMat);
      legL.position.set(-0.11, 0.36, 0);
      const legR = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.065, 0.72, 10), pantsMat);
      legR.position.set(0.11, 0.36, 0);
      bodyRoot.add(legL, legR);
    } else {
      // Muslos horizontales + pantorrillas verticales
      const thighL = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.14, 0.42), pantsMat);
      thighL.position.set(-0.11, 0.12, 0.18);
      const thighR = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.14, 0.42), pantsMat);
      thighR.position.set(0.11, 0.12, 0.18);
      bodyRoot.add(thighL, thighR);

      if (cfg.pose === "seated") {
        const calfL = new THREE.Mesh(new THREE.CylinderGeometry(0.065, 0.055, 0.46, 10), pantsMat);
        calfL.position.set(-0.11, -0.14, 0.35);
        const calfR = new THREE.Mesh(new THREE.CylinderGeometry(0.065, 0.055, 0.46, 10), pantsMat);
        calfR.position.set(0.11, -0.14, 0.35);
        bodyRoot.add(calfL, calfR);
      } else if (cfg.pose === "floor_cushion") {
        // Cojín de suelo para Raj
        const cushion = new THREE.Mesh(
          new THREE.CylinderGeometry(0.42, 0.45, 0.14, 20),
          new THREE.MeshStandardMaterial({ color: 0x8c2d19, roughness: 0.85 })
        );
        cushion.position.set(0, -0.08, 0.05);
        bodyRoot.add(cushion);
      }
    }

    // Hitbox invisible amplio para clic cómodo con el mouse
    const hitbox = new THREE.Mesh(
      new THREE.CylinderGeometry(0.48, 0.48, 1.65, 12),
      new THREE.MeshBasicMaterial({ visible: false })
    );
    hitbox.position.y = torsoY + 0.15;
    hitbox.userData = { charId: cfg.id };
    root.add(hitbox);
    this.interactiveMeshes.push(hitbox);

    root.userData = { headGroup, rightArm, ringMesh: ring, charId: cfg.id };
    return root;
  }

  // -------------------------------------------------------------------------
  // INTERACCIONES DE MOUSE Y ACTUALIZACIÓN DE ETIQUETAS 3D PROYECTADAS
  // -------------------------------------------------------------------------
  _setupInteractions() {
    const dom = this.renderer.domElement;

    dom.addEventListener("pointermove", (e) => {
      const rect = dom.getBoundingClientRect();
      this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      this.raycaster.setFromCamera(this.mouse, this.camera);
      const hits = this.raycaster.intersectObjects(this.interactiveMeshes, false);
      dom.style.cursor = hits.length > 0 ? "pointer" : "grab";
    });

    let downPos = { x: 0, y: 0 };
    dom.addEventListener("pointerdown", (e) => {
      downPos = { x: e.clientX, y: e.clientY };
      // Si el usuario rota manualmente con el mouse, cancelar animación automática de cámara
      this.camTargetPos = null;
      this.camTargetLook = null;
    });

    dom.addEventListener("pointerup", (e) => {
      const dist = Math.hypot(e.clientX - downPos.x, e.clientY - downPos.y);
      if (dist > 6) return; // Fue arrastre de cámara, no clic

      const rect = dom.getBoundingClientRect();
      this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      this.raycaster.setFromCamera(this.mouse, this.camera);
      const hits = this.raycaster.intersectObjects(this.interactiveMeshes, false);
      if (hits.length > 0) {
        const cid = hits[0].object.userData.charId;
        if (cid) this.focusCharacter(cid, true);
      }
    });
  }

  updateLiveTelemetry(liveData) {
    this.liveData = liveData;
    this.teamData = (liveData && liveData.atom_team) || [];
    this._renderWhiteboardContent();
    this._rebuildHtmlLabels();
  }

  _rebuildHtmlLabels() {
    if (!this.labelsContainer) return;
    this.labelsContainer.innerHTML = "";

    this.teamData.forEach((member) => {
      const tag = document.createElement("div");
      tag.className = `char-3d-tag ${this.activeCharId === member.id ? "active" : ""}`;
      tag.id = `tag-3d-${member.id}`;
      tag.style.setProperty("--char-color", member.accent_color || "#007ACC");
      tag.innerHTML = `
        <div class="char-tag-header">
          <span class="char-tag-name">${member.short_name}</span>
          <span class="char-tag-badge" style="border-color:${member.accent_color};color:${member.accent_color};">${member.status_badge}</span>
        </div>
        <div class="char-tag-role">${member.role}</div>
      `;
      tag.addEventListener("click", (ev) => {
        ev.stopPropagation();
        this.focusCharacter(member.id, true);
      });
      this.labelsContainer.appendChild(tag);
    });
  }

  focusCharacter(charId, notifyCallback = true) {
    this.activeCharId = charId;
    const ch = this.characters[charId];
    if (!ch) return;

    // Actualizar estado activo de etiquetas
    if (this.labelsContainer) {
      this.labelsContainer.querySelectorAll(".char-3d-tag").forEach((el) => {
        el.classList.toggle("active", el.id === `tag-3d-${charId}`);
      });
    }

    // Calcular posición objetivo de cámara frente al personaje
    const worldPos = new THREE.Vector3();
    ch.group.getWorldPosition(worldPos);

    this.camTargetLook = new THREE.Vector3(worldPos.x, worldPos.y + 0.65, worldPos.z);
    this.camTargetPos = new THREE.Vector3(
      worldPos.x * 0.65,
      worldPos.y + 1.85,
      worldPos.z + 4.25
    );

    if (notifyCallback && this.onSelectCharacter) {
      const memberObj = this.teamData.find((m) => m.id === charId);
      this.onSelectCharacter(charId, memberObj);
    }
  }

  resetCameraView() {
    this.stopTeamMeeting();
    this.camTargetPos = this.defaultCamPos.clone();
    this.camTargetLook = this.defaultCamLook.clone();
  }

  toggleBackdropPhoto() {
    this.showPhotoBackdrop = !this.showPhotoBackdrop;
    if (this.backdropMesh) {
      this.backdropMesh.visible = this.showPhotoBackdrop;
    }
    return this.showPhotoBackdrop;
  }

  startTeamMeeting(onStepCallback) {
    this.stopTeamMeeting();
    this.meetingIndex = 0;
    const step = () => {
      const cid = this.characterOrder[this.meetingIndex % this.characterOrder.length];
      this.focusCharacter(cid, true);
      if (onStepCallback) onStepCallback(cid, this.meetingIndex + 1, this.characterOrder.length);
      this.meetingIndex++;
    };
    step();
    this.meetingTimer = setInterval(step, 5200);
  }

  stopTeamMeeting() {
    if (this.meetingTimer) {
      clearInterval(this.meetingTimer);
      this.meetingTimer = null;
    }
  }

  // -------------------------------------------------------------------------
  // LOOP DE RENDERIZADO 60 FPS
  // -------------------------------------------------------------------------
  _animate() {
    requestAnimationFrame(() => this._animate());

    const t = this.clock.getElapsedTime();

    // 1. Rotar suavemente la Doble Hélice de ADN
    if (this.dnaGroup) {
      this.dnaGroup.rotation.y = t * 0.45;
    }

    // 2. Animación viva de respiración y gestos sutiles de los 7 personajes
    Object.values(this.characters).forEach((ch, idx) => {
      const phase = t * 2.1 + idx * 1.1;
      if (ch.headMesh) {
        ch.headMesh.rotation.y = Math.sin(phase * 0.6) * 0.12;
        ch.headMesh.position.y =
          (ch.cfg.pose === "standing" ? 1.44 : 0.88) + Math.sin(phase) * 0.012;
      }
      if (ch.rightArm) {
        const isActive = ch.id === this.activeCharId;
        ch.rightArm.rotation.x = -0.65 + Math.sin(phase * (isActive ? 2.2 : 1.0)) * (isActive ? 0.18 : 0.05);
      }
      if (ch.ringMesh) {
        const isActive = ch.id === this.activeCharId;
        const s = isActive ? 1.08 + Math.sin(t * 4.5) * 0.08 : 0.92;
        ch.ringMesh.scale.set(s, s, 1);
      }
    });

    // 3. Interpolación suave de cámara (Fly-To)
    if (this.camTargetPos && this.camTargetLook && this.controls) {
      this.camera.position.lerp(this.camTargetPos, 0.065);
      this.controls.target.lerp(this.camTargetLook, 0.08);
      if (this.camera.position.distanceTo(this.camTargetPos) < 0.08) {
        this.camTargetPos = null;
        this.camTargetLook = null;
      }
    }

    if (this.controls) this.controls.update();
    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
      this._projectHtmlLabels();
    }
  }

  _projectHtmlLabels() {
    if (!this.labelsContainer || !this.container) return;
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    if (!w || !h) return;

    const projVec = new THREE.Vector3();
    Object.values(this.characters).forEach((ch) => {
      const el = document.getElementById(`tag-3d-${ch.id}`);
      if (!el || !ch.headMesh) return;

      ch.headMesh.getWorldPosition(projVec);
      projVec.y += 0.42;
      projVec.project(this.camera);

      if (projVec.z > 1.0) {
        el.style.display = "none";
        return;
      }
      const x = (projVec.x * 0.5 + 0.5) * w;
      const y = (-(projVec.y * 0.5) + 0.5) * h;

      el.style.display = "block";
      el.style.transform = `translate(-50%, -100%) translate(${Math.round(x)}px, ${Math.round(y)}px)`;
    });
  }
};
