import { useEffect, useRef } from "react";
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";

import { PALETTE } from "./palette";

/**
 * The landing page's 3D picture: a stack of alphabet blocks with a ball, pencil, apple, book and stars
 * floating around it, tilting towards the pointer. Loaded lazily; HeroFallback is shown until it is ready
 * and instead of it on devices that cannot run it well.
 */
export default function HeroScene({ brand, onReady }: { brand: string; onReady?: () => void }) {
  const holder = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = holder.current;
    if (!el) return;
    let disposed = false;
    let cleanup = () => {};
    // Wait for the display font so the letters on the blocks use it.
    document.fonts.load("700 100px Fredoka").catch(() => undefined).finally(() => {
      if (!disposed) {
        cleanup = build(el, brand);
        onReady?.();
      }
    });
    return () => {
      disposed = true;
      cleanup();
    };
  }, [brand, onReady]);

  return <div ref={holder} className="absolute inset-0" aria-hidden="true" />;
}

function build(el: HTMLElement, brand: string) {
  const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  el.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envTexture = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environment = envTexture;
  pmrem.dispose();

  const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
  const sun = new THREE.DirectionalLight(0xfff1dd, 1.6);
  sun.position.set(4, 8, 6);
  scene.add(sun, new THREE.AmbientLight(0xffffff, 0.35));

  const textures: THREE.Texture[] = [];
  const tex = (canvas: HTMLCanvasElement) => {
    const t = new THREE.CanvasTexture(canvas);
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = renderer.capabilities.getMaxAnisotropy();
    textures.push(t);
    return t;
  };
  const plastic = (color: THREE.ColorRepresentation, extra: THREE.MeshPhysicalMaterialParameters = {}) =>
    new THREE.MeshPhysicalMaterial({ color, roughness: 0.38, clearcoat: 0.7, clearcoatRoughness: 0.2, ...extra });

  const world = new THREE.Group();
  scene.add(world);

  // Alphabet blocks
  const blockGeometry = new RoundedBoxGeometry(1.4, 1.4, 1.4, 5, 0.2);
  const block = (colour: string, glyphs: string[]) =>
    new THREE.Mesh(blockGeometry, glyphs.map((g) => plastic(0xffffff, { map: tex(blockFace(colour, g)) })));
  const blocks = [
    // Faces: right, left, top, bottom, front, back. Fronts read A on top, then B and C.
    { mesh: block(PALETTE.coral, ["2", "1", "★", "♥", "B", "3"]), at: [-0.76, -2.0, 0], turn: 0.22 },
    { mesh: block(PALETTE.sky, ["3", "2", "★", "♥", "C", "1"]), at: [0.8, -2.0, 0.12], turn: -0.3 },
    { mesh: block(brand, ["1", "3", "★", "♥", "A", "2"]), at: [0.04, -0.6, 0.02], turn: 0.55 },
  ];
  for (const b of blocks) {
    b.mesh.position.set(b.at[0], b.at[1], b.at[2]);
    b.mesh.rotation.y = b.turn;
    world.add(b.mesh);
  }

  // Soft shadow under the stack
  const shadow = new THREE.Mesh(
    new THREE.PlaneGeometry(5, 2.2),
    new THREE.MeshBasicMaterial({ map: tex(softShadow()), transparent: true, depthWrite: false }),
  );
  shadow.rotation.x = -Math.PI / 2;
  shadow.position.set(0, -2.71, 0);
  world.add(shadow);

  // Things that float
  const floaters: { obj: THREE.Object3D; base: THREE.Vector3; spin: THREE.Vector3; phase: number; lift: number }[] = [];
  const float = (obj: THREE.Object3D, at: [number, number, number], spin: [number, number, number], lift = 0.18) => {
    obj.position.set(...at);
    world.add(obj);
    floaters.push({ obj, base: obj.position.clone(), spin: new THREE.Vector3(...spin), phase: Math.random() * 6, lift });
  };

  const ball = new THREE.Mesh(new THREE.SphereGeometry(0.7, 48, 32), plastic(0xffffff, { map: tex(beachBall()) }));
  ball.rotation.z = 0.4;
  float(ball, [-2.55, 1.35, -0.4], [0, 0.5, 0]);

  const pen = pencil(plastic);
  pen.rotation.set(0.2, 0, -0.85);
  float(pen, [2.45, 1.25, 0], [0, 0, 0], 0.22);

  float(apple(plastic), [2.65, -1.45, 0.7], [0, 0.4, 0], 0.14);
  const notebook = book(plastic);
  notebook.rotation.set(0.45, 0.6, -0.15);
  float(notebook, [-2.65, -1.15, 0.8], [0, 0.25, 0], 0.15);

  const starGeometry = starShape();
  const starMaterial = plastic(PALETTE.sun, { emissive: new THREE.Color(PALETTE.sun), emissiveIntensity: 0.18 });
  float(new THREE.Mesh(starGeometry, starMaterial), [0.1, 2.35, -0.8], [0, 0.9, 0], 0.22);
  float(scaled(new THREE.Mesh(starGeometry, starMaterial), 0.6), [-1.15, 2.95, 0.4], [0, -1.1, 0.2], 0.16);
  float(scaled(new THREE.Mesh(starGeometry, starMaterial), 0.45), [1.45, 3.05, -0.4], [0, 1.3, 0], 0.16);

  const dotGeometry = new THREE.SphereGeometry(0.11, 16, 12);
  const dotColours = [PALETTE.coral, PALETTE.mint, PALETTE.lilac, PALETTE.sun, PALETTE.sky, brand];
  const dotSpots: [number, number, number][] = [
    [-1.7, 0.2, 1.2], [1.6, 0.35, 1.0], [-3.3, -0.1, -1], [3.4, 0.2, -0.8], [-0.9, 3.4, -1.2],
    [2.0, -2.6, 1.1], [-2.0, -2.5, 1.3], [0.9, 1.9, 1.2], [-3.0, 2.6, -0.6], [3.1, 2.7, -1],
  ];
  dotSpots.forEach((spot, i) => float(new THREE.Mesh(dotGeometry, plastic(dotColours[i % dotColours.length])), spot, [0, 0, 0], 0.25));

  // Fit the camera to the box the picture is drawn in.
  const resize = () => {
    const { clientWidth: w, clientHeight: h } = el;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    camera.aspect = w / h;
    camera.position.set(0, 0.35, camera.aspect < 1 ? 13.5 / camera.aspect : 13.5);
    camera.lookAt(0, 0.1, 0);
    camera.updateProjectionMatrix();
    if (still) draw(0);
  };
  const observer = new ResizeObserver(resize);
  observer.observe(el);

  // Tilt towards the pointer.
  const target = new THREE.Vector2();
  const onPointer = (e: PointerEvent) => target.set(e.clientX / window.innerWidth - 0.5, e.clientY / window.innerHeight - 0.5);
  window.addEventListener("pointermove", onPointer, { passive: true });

  const clock = new THREE.Clock();
  function draw(t: number) {
    world.rotation.y += (target.x * 0.5 + Math.sin(t * 0.25) * 0.12 - world.rotation.y) * 0.05;
    world.rotation.x += (target.y * 0.18 - world.rotation.x) * 0.05;
    for (const f of floaters) {
      f.obj.position.y = f.base.y + Math.sin(t * 1.1 + f.phase) * f.lift;
      f.obj.rotation.x += f.spin.x * 0.01;
      f.obj.rotation.y += f.spin.y * 0.01;
      f.obj.rotation.z += f.spin.z * 0.01;
    }
    renderer.render(scene, camera);
  }

  // Only animate while the picture is on screen and the tab is visible.
  let frame = 0;
  let onScreen = true;
  const loop = () => {
    draw(clock.getElapsedTime());
    frame = requestAnimationFrame(loop);
  };
  const sync = () => {
    cancelAnimationFrame(frame);
    if (!still && onScreen && !document.hidden) frame = requestAnimationFrame(loop);
  };
  const visibility = new IntersectionObserver(([entry]) => {
    onScreen = entry.isIntersecting;
    sync();
  });
  visibility.observe(el);
  document.addEventListener("visibilitychange", sync);
  resize();
  sync();

  return () => {
    cancelAnimationFrame(frame);
    observer.disconnect();
    visibility.disconnect();
    document.removeEventListener("visibilitychange", sync);
    window.removeEventListener("pointermove", onPointer);
    scene.traverse((o) => {
      if (o instanceof THREE.Mesh) {
        o.geometry.dispose();
        for (const m of [o.material].flat()) m.dispose();
      }
    });
    textures.forEach((t) => t.dispose());
    envTexture.dispose();
    renderer.dispose();
    renderer.domElement.remove();
  };
}

function scaled<T extends THREE.Object3D>(obj: T, s: number) {
  obj.scale.setScalar(s);
  return obj;
}

function canvas(w: number, h: number) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  return [c, c.getContext("2d")!] as const;
}

function blockFace(colour: string, glyph: string) {
  const [c, g] = canvas(256, 256);
  g.fillStyle = colour;
  g.fillRect(0, 0, 256, 256);
  g.strokeStyle = "rgba(255,255,255,0.6)";
  g.lineWidth = 9;
  g.beginPath();
  g.roundRect(30, 30, 196, 196, 30);
  g.stroke();
  g.fillStyle = "#ffffff";
  g.font = "700 150px Fredoka, 'Trebuchet MS', system-ui, sans-serif";
  g.textAlign = "center";
  g.textBaseline = "middle";
  g.shadowColor = "rgba(0,0,0,0.2)";
  g.shadowOffsetY = 6;
  g.shadowBlur = 6;
  g.fillText(glyph, 128, 138);
  return c;
}

function beachBall() {
  const [c, g] = canvas(512, 256);
  const stripes = [PALETTE.coral, "#ffffff", PALETTE.sun, "#ffffff", PALETTE.sky, "#ffffff", PALETTE.mint, "#ffffff"];
  stripes.forEach((s, i) => {
    g.fillStyle = s;
    g.fillRect((i * 512) / stripes.length, 0, 512 / stripes.length + 1, 256);
  });
  return c;
}

function softShadow() {
  const [c, g] = canvas(256, 128);
  const grad = g.createRadialGradient(128, 64, 4, 128, 64, 120);
  grad.addColorStop(0, "rgba(40,30,60,0.28)");
  grad.addColorStop(1, "rgba(40,30,60,0)");
  g.setTransform(1, 0, 0, 0.5, 0, 32);
  g.fillStyle = grad;
  g.fillRect(0, 0, 256, 256);
  return c;
}

type Plastic = (color: THREE.ColorRepresentation, extra?: THREE.MeshPhysicalMaterialParameters) => THREE.Material;

function pencil(plastic: Plastic) {
  const g = new THREE.Group();
  const part = (geometry: THREE.BufferGeometry, material: THREE.Material, y: number, pointDown = false) => {
    const m = new THREE.Mesh(geometry, material);
    m.position.y = y;
    if (pointDown) m.rotation.x = Math.PI;
    g.add(m);
  };
  part(new THREE.CylinderGeometry(0.17, 0.17, 2.2, 6), plastic(PALETTE.sun), 0);
  part(new THREE.CylinderGeometry(0.175, 0.175, 0.22, 24), plastic(0xc9ccd6, { metalness: 1, roughness: 0.3 }), 1.21);
  part(new THREE.CylinderGeometry(0.17, 0.17, 0.26, 24), plastic(PALETTE.pink), 1.44);
  part(new THREE.ConeGeometry(0.17, 0.5, 6), plastic(0xf2cf9c, { clearcoat: 0, roughness: 0.8 }), -1.35, true);
  part(new THREE.ConeGeometry(0.06, 0.18, 12), plastic(0x2b2b35), -1.51, true);
  return g;
}

function apple(plastic: Plastic) {
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.SphereGeometry(0.6, 40, 28), plastic(PALETTE.coral));
  body.scale.set(1, 0.9, 1);
  const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.05, 0.3, 8), plastic(0x6b4a2b, { clearcoat: 0 }));
  stem.position.y = 0.62;
  const leaf = new THREE.Mesh(new THREE.SphereGeometry(0.2, 20, 12), plastic(PALETTE.mint));
  leaf.scale.set(1, 0.25, 0.5);
  leaf.position.set(0.2, 0.7, 0);
  leaf.rotation.z = 0.5;
  g.add(body, stem, leaf);
  return g;
}

function book(plastic: Plastic) {
  const g = new THREE.Group();
  const cover = new THREE.Mesh(new RoundedBoxGeometry(1.3, 0.24, 1.0, 2, 0.05), plastic(PALETTE.lilac));
  const pages = new THREE.Mesh(new THREE.BoxGeometry(1.22, 0.17, 0.94), plastic(0xfffaf0, { clearcoat: 0, roughness: 0.9 }));
  pages.position.x = 0.06;
  g.add(cover, pages);
  return g;
}

function starShape() {
  const shape = new THREE.Shape();
  for (let i = 0; i < 10; i++) {
    const r = i % 2 ? 0.22 : 0.5;
    const a = (i / 10) * Math.PI * 2 + Math.PI / 2;
    if (i) shape.lineTo(Math.cos(a) * r, Math.sin(a) * r);
    else shape.moveTo(Math.cos(a) * r, Math.sin(a) * r);
  }
  const geometry = new THREE.ExtrudeGeometry(shape, { depth: 0.14, bevelEnabled: true, bevelThickness: 0.06, bevelSize: 0.05, bevelSegments: 3 });
  geometry.center();
  return geometry;
}
