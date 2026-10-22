import React, { useCallback, useEffect, useRef } from "react";
import {
  DRAG_SENSITIVITY,
  FRAME_MS,
  generateLandPoints,
  IDLE_VELOCITY,
  TILT_X,
  VELOCITY_RECOVERY,
} from "./globeMath";

// Accent color: #d97757
const ACCENT_R = 0xd9;
const ACCENT_G = 0x77;
const ACCENT_B = 0x57;

// Pre-compute land points once (module-level, shared across instances)
const LAND_PTS = generateLandPoints(1400, 3);
const PT_COUNT = LAND_PTS.length / 3;

// ~18 alpha buckets
const BUCKET_COUNT = 18;

interface GlobeProps {
  className?: string;
  onUnsupported?: () => void;
}

const Globe: React.FC<GlobeProps> = ({ className, onUnsupported }) => {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // All mutable frame state lives in refs — never React state
  const rotRef = useRef(0);
  const velRef = useRef(IDLE_VELOCITY);
  const rafRef = useRef<number>(0);
  const lastTsRef = useRef<number>(-1);
  const sizeRef = useRef({ w: 300, h: 300 });
  const draggingRef = useRef(false);
  const lastPtrXRef = useRef(0);
  const lastMoveTimeRef = useRef(0);
  const reducedMotionRef = useRef(false);

  // Projected point cache (reused each frame)
  const projCache = useRef<Float64Array>(new Float64Array(PT_COUNT * 3)); // x2, y2, z2

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const { w, h } = sizeRef.current;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const pw = w * dpr;
    const ph = h * dpr;

    if (canvas.width !== pw || canvas.height !== ph) {
      canvas.width = pw;
      canvas.height = ph;
      ctx.scale(dpr, dpr);
    }

    ctx.clearRect(0, 0, w, h);

    const R = Math.min(w, h) * 0.4;
    const cx = w / 2;
    const cy = h / 2;
    const BASE_R = Math.max(0.8, R * 0.0072);

    const rot = rotRef.current;
    const sinY = Math.sin(rot);
    const cosY = Math.cos(rot);
    const sinX = Math.sin(TILT_X);
    const cosX = Math.cos(TILT_X);

    const proj = projCache.current;

    // Project all points
    for (let i = 0; i < PT_COUNT; i++) {
      const ox = LAND_PTS[i * 3];
      const oy = LAND_PTS[i * 3 + 1];
      const oz = LAND_PTS[i * 3 + 2];

      // Rotate Y
      const x1 = ox * cosY + oz * sinY;
      const z1 = -ox * sinY + oz * cosY;

      // Rotate X
      const y2 = oy * cosX - z1 * sinX;
      const z2 = oy * sinX + z1 * cosX;

      proj[i * 3] = x1;
      proj[i * 3 + 1] = y2;
      proj[i * 3 + 2] = z2;
    }

    // Bucket sorting: 0..BUCKET_COUNT-1, based on depth
    // Separate far (z2 < 0) and near (z2 >= 0) passes
    // Far: one set of buckets; Near: another set — draw far first
    type BucketEntry = { x: number; y: number; radius: number };
    const farBuckets: BucketEntry[][] = Array.from({ length: BUCKET_COUNT }, () => []);
    const nearBuckets: BucketEntry[][] = Array.from({ length: BUCKET_COUNT }, () => []);

    for (let i = 0; i < PT_COUNT; i++) {
      const x2 = proj[i * 3];
      const y2 = proj[i * 3 + 1];
      const z2 = proj[i * 3 + 2];

      const depth = (z2 + 1) / 2; // 0..1
      const persp = 0.86 + depth * 0.28;
      const px = cx + x2 * R * persp;
      const py = cy - y2 * R * persp;
      const pr = BASE_R * (0.45 + depth * 0.85);

      const bucketIdx = Math.min(
        BUCKET_COUNT - 1,
        Math.floor(depth * BUCKET_COUNT),
      );

      if (z2 < 0) {
        farBuckets[bucketIdx].push({ x: px, y: py, radius: pr });
      } else {
        nearBuckets[bucketIdx].push({ x: px, y: py, radius: pr });
      }
    }

    // Draw far hemisphere (rgb(186,206,255))
    for (let b = 0; b < BUCKET_COUNT; b++) {
      const pts = farBuckets[b];
      if (pts.length === 0) continue;
      const depth = (b + 0.5) / BUCKET_COUNT;
      const alpha = 0.06 + depth * 0.30;
      ctx.fillStyle = `rgba(186,206,255,${alpha.toFixed(3)})`;
      ctx.beginPath();
      for (const p of pts) {
        ctx.moveTo(p.x + p.radius, p.y);
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      }
      ctx.fill();
    }

    // Draw near hemisphere (accent color #d97757)
    for (let b = 0; b < BUCKET_COUNT; b++) {
      const pts = nearBuckets[b];
      if (pts.length === 0) continue;
      const depth = (b + 0.5) / BUCKET_COUNT;
      const alpha = 0.18 + depth * 0.72;
      ctx.fillStyle = `rgba(${ACCENT_R},${ACCENT_G},${ACCENT_B},${alpha.toFixed(3)})`;
      ctx.beginPath();
      for (const p of pts) {
        ctx.moveTo(p.x + p.radius, p.y);
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      }
      ctx.fill();
    }
  }, []);

  const animate = useCallback(
    (ts: number) => {
      if (lastTsRef.current < 0) lastTsRef.current = ts;
      const elapsed = Math.min(ts - lastTsRef.current, 64); // cap to avoid jumps
      lastTsRef.current = ts;

      if (!draggingRef.current && !reducedMotionRef.current) {
        // f = elapsed / FRAME_MS (refresh-rate-normalized)
        const f = elapsed / FRAME_MS;
        const vel = velRef.current;
        const recovery = 1 - Math.pow(1 - VELOCITY_RECOVERY, f);
        velRef.current = vel + (IDLE_VELOCITY - vel) * recovery;
        rotRef.current += velRef.current * f;
      }

      draw();
      rafRef.current = requestAnimationFrame(animate);
    },
    [draw],
  );

  // Start / stop loop based on visibility
  const startLoop = useCallback(() => {
    if (rafRef.current) return;
    lastTsRef.current = -1;
    rafRef.current = requestAnimationFrame(animate);
  }, [animate]);

  const stopLoop = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = 0;
    }
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Check for Canvas 2D support
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      onUnsupported?.();
      return;
    }

    // Reduced motion check
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    reducedMotionRef.current = mq.matches;
    const onMQChange = (e: MediaQueryListEvent) => {
      reducedMotionRef.current = e.matches;
      if (e.matches) velRef.current = 0;
    };
    mq.addEventListener("change", onMQChange);

    // ResizeObserver on wrapper
    const wrapper = wrapperRef.current;
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const { width, height } = entry.contentRect;
      sizeRef.current = { w: width, h: height };
    });
    if (wrapper) ro.observe(wrapper);

    // Visibility change
    const onVisChange = () => {
      if (document.hidden) stopLoop();
      else startLoop();
    };
    document.addEventListener("visibilitychange", onVisChange);

    // Pointer events
    const onPointerDown = (e: PointerEvent) => {
      draggingRef.current = true;
      velRef.current = 0;
      lastPtrXRef.current = e.clientX;
      lastMoveTimeRef.current = performance.now();
      canvas.setPointerCapture(e.pointerId);
    };

    const onPointerMove = (e: PointerEvent) => {
      if (!draggingRef.current) return;
      e.preventDefault();
      const dx = e.clientX - lastPtrXRef.current;
      const step = dx * DRAG_SENSITIVITY;
      rotRef.current += step;
      // Clamp velocity from this step to ±0.12
      velRef.current = Math.max(-0.12, Math.min(0.12, step));
      lastPtrXRef.current = e.clientX;
      lastMoveTimeRef.current = performance.now();
    };

    const onPointerUp = (e: PointerEvent) => {
      if (!draggingRef.current) return;
      draggingRef.current = false;
      canvas.releasePointerCapture(e.pointerId);
      // If pointer was still for > 80ms, clear velocity so idle recovery starts from 0
      const idleTime = performance.now() - lastMoveTimeRef.current;
      if (idleTime > 80) {
        velRef.current = 0;
      }
    };

    canvas.addEventListener("pointerdown", onPointerDown);
    canvas.addEventListener("pointermove", onPointerMove, { passive: false });
    canvas.addEventListener("pointerup", onPointerUp);
    canvas.addEventListener("pointercancel", onPointerUp);

    startLoop();

    return () => {
      stopLoop();
      ro.disconnect();
      mq.removeEventListener("change", onMQChange);
      document.removeEventListener("visibilitychange", onVisChange);
      canvas.removeEventListener("pointerdown", onPointerDown);
      canvas.removeEventListener("pointermove", onPointerMove);
      canvas.removeEventListener("pointerup", onPointerUp);
      canvas.removeEventListener("pointercancel", onPointerUp);
    };
  }, [onUnsupported, startLoop, stopLoop]);

  return (
    <div
      ref={wrapperRef}
      className={className}
      style={{ width: "100%", height: "100%", position: "relative" }}
    >
      <canvas
        ref={canvasRef}
        style={{
          display: "block",
          width: "100%",
          height: "100%",
          touchAction: "none",
          cursor: "grab",
        }}
      />
    </div>
  );
};

export default Globe;
