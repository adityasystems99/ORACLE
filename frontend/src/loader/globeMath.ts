// Pure math — no DOM. Deterministic Fibonacci lattice land-point generator.

export const TILT_X = -0.32;
export const IDLE_VELOCITY = 0.0035;
export const DRAG_SENSITIVITY = 0.006;
export const VELOCITY_RECOVERY = 0.02;
export const FRAME_MS = 1000 / 60;

/**
 * Walk the full Fibonacci lattice of target * oversample candidates.
 * Keep points where the land mask s > 0.25.
 * If survivors > target, decimate evenly so both hemispheres stay covered.
 * Returns a Float32Array of x,y,z triples (unit sphere).
 */
export function generateLandPoints(
  target = 1400,
  oversample = 3,
): Float32Array {
  const n = target * oversample;
  const candidates: number[] = [];

  for (let i = 0; i < n; i++) {
    const y = 1 - (i / n) * 2;
    const r = Math.sqrt(Math.max(0, 1 - y * y));
    const theta = i * 2.399963;
    const x = Math.cos(theta) * r;
    const z = Math.sin(theta) * r;

    const lat = Math.asin(y);
    const lon = Math.atan2(z, x);

    const s =
      Math.sin(lat * 3.1) * Math.cos(lon * 2.2) +
      Math.sin(lon * 1.3 + 1.1) * Math.cos(lat * 1.7) +
      0.6 * Math.sin((lat + lon) * 4.3);

    if (s > 0.25) {
      candidates.push(x, y, z);
    }
  }

  const count = candidates.length / 3;

  if (count <= target) {
    return new Float32Array(candidates);
  }

  // Decimate: keep every (count/target)-th point by index to cover both hemispheres
  const step = count / target;
  const out = new Float32Array(target * 3);
  for (let k = 0; k < target; k++) {
    const srcIdx = Math.round(k * step);
    const base = srcIdx * 3;
    out[k * 3] = candidates[base];
    out[k * 3 + 1] = candidates[base + 1];
    out[k * 3 + 2] = candidates[base + 2];
  }
  return out;
}
