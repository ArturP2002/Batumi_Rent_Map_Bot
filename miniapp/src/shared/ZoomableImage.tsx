import { useEffect, useRef } from "react";

type Point = { x: number; y: number };

function distance(a: Point, b: Point) {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.hypot(dx, dy);
}

function midpoint(a: Point, b: Point): Point {
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
}

const MIN_SCALE = 1;
const MAX_SCALE = 4;

type Props = {
  src: string;
  resetKey: string | number;
  /** Called on vertical swipe when image is not zoomed (e.g. close lightbox). */
  onSwipeDown?: () => void;
};

/**
 * Two-finger pinch zoom + one-finger pan only while zoomed.
 * At scale 1 we do not capture touches, so the page / lightbox can scroll.
 */
export function ZoomableImage({ src, resetKey, onSwipeDown }: Props) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const scaleRef = useRef(1);
  const xRef = useRef(0);
  const yRef = useRef(0);
  const pointers = useRef(new Map<number, Point>());
  const pinchStart = useRef<{
    dist: number;
    scale: number;
    mid: Point;
    x: number;
    y: number;
  } | null>(null);
  const panStart = useRef<{ x: number; y: number; ox: number; oy: number } | null>(null);
  const swipeStart = useRef<{ y: number } | null>(null);
  const onSwipeDownRef = useRef(onSwipeDown);
  onSwipeDownRef.current = onSwipeDown;

  function setTouchAction(zoomed: boolean) {
    const el = viewportRef.current;
    if (!el) return;
    el.style.touchAction = zoomed ? "none" : "pan-y";
    el.dataset.zoomed = zoomed ? "1" : "0";
  }

  function apply() {
    const img = imageRef.current;
    if (!img) return;
    img.style.transform = `translate3d(${xRef.current}px, ${yRef.current}px, 0) scale(${scaleRef.current})`;
    setTouchAction(scaleRef.current > 1.01);
  }

  function clampPan() {
    const viewport = viewportRef.current;
    const img = imageRef.current;
    if (!viewport || !img) return;
    const scale = scaleRef.current;
    if (scale <= 1.01) {
      xRef.current = 0;
      yRef.current = 0;
      return;
    }
    const rect = viewport.getBoundingClientRect();
    const iw = img.offsetWidth * scale;
    const ih = img.offsetHeight * scale;
    const maxX = Math.max(0, (iw - rect.width) / 2);
    const maxY = Math.max(0, (ih - rect.height) / 2);
    xRef.current = Math.min(maxX, Math.max(-maxX, xRef.current));
    yRef.current = Math.min(maxY, Math.max(-maxY, yRef.current));
  }

  function reset() {
    scaleRef.current = 1;
    xRef.current = 0;
    yRef.current = 0;
    pinchStart.current = null;
    panStart.current = null;
    swipeStart.current = null;
    pointers.current.clear();
    apply();
  }

  useEffect(() => {
    reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resetKey, src]);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    setTouchAction(false);

    const onTouchStart = (e: TouchEvent) => {
      if (e.touches.length >= 2) {
        // Pinch starts — block scroll for this gesture
        e.preventDefault();
        swipeStart.current = null;
        panStart.current = null;
        const a = e.touches[0];
        const b = e.touches[1];
        const p0 = { x: a.clientX, y: a.clientY };
        const p1 = { x: b.clientX, y: b.clientY };
        pointers.current.clear();
        pointers.current.set(a.identifier, p0);
        pointers.current.set(b.identifier, p1);
        pinchStart.current = {
          dist: distance(p0, p1),
          scale: scaleRef.current,
          mid: midpoint(p0, p1),
          x: xRef.current,
          y: yRef.current,
        };
        return;
      }

      if (e.touches.length === 1) {
        const t = e.touches[0];
        if (scaleRef.current > 1.01) {
          // Pan zoomed image
          e.preventDefault();
          panStart.current = {
            x: t.clientX,
            y: t.clientY,
            ox: xRef.current,
            oy: yRef.current,
          };
          swipeStart.current = null;
        } else {
          // Allow native vertical scroll; track swipe-down to close
          panStart.current = null;
          pinchStart.current = null;
          swipeStart.current = { y: t.clientY };
        }
      }
    };

    const onTouchMove = (e: TouchEvent) => {
      if (e.touches.length >= 2 && pinchStart.current) {
        e.preventDefault();
        const a = e.touches[0];
        const b = e.touches[1];
        const p0 = { x: a.clientX, y: a.clientY };
        const p1 = { x: b.clientX, y: b.clientY };
        const dist = distance(p0, p1);
        const mid = midpoint(p0, p1);
        const start = pinchStart.current;
        if (start.dist < 1) return;
        const nextScale = Math.min(
          MAX_SCALE,
          Math.max(MIN_SCALE, start.scale * (dist / start.dist)),
        );
        const rect = viewport.getBoundingClientRect();
        const midLocal = {
          x: mid.x - rect.left - rect.width / 2,
          y: mid.y - rect.top - rect.height / 2,
        };
        const startMidLocal = {
          x: start.mid.x - rect.left - rect.width / 2,
          y: start.mid.y - rect.top - rect.height / 2,
        };
        const worldX = (startMidLocal.x - start.x) / start.scale;
        const worldY = (startMidLocal.y - start.y) / start.scale;
        xRef.current = midLocal.x - worldX * nextScale;
        yRef.current = midLocal.y - worldY * nextScale;
        scaleRef.current = nextScale;
        clampPan();
        apply();
        return;
      }

      if (e.touches.length === 1 && panStart.current && scaleRef.current > 1.01) {
        e.preventDefault();
        const t = e.touches[0];
        const start = panStart.current;
        xRef.current = start.ox + (t.clientX - start.x);
        yRef.current = start.oy + (t.clientY - start.y);
        clampPan();
        apply();
      }
    };

    const onTouchEnd = (e: TouchEvent) => {
      if (e.touches.length < 2) pinchStart.current = null;

      if (e.touches.length === 1 && scaleRef.current > 1.01) {
        const t = e.touches[0];
        panStart.current = {
          x: t.clientX,
          y: t.clientY,
          ox: xRef.current,
          oy: yRef.current,
        };
      }

      if (e.touches.length === 0) {
        if (
          swipeStart.current &&
          scaleRef.current <= 1.01 &&
          e.changedTouches[0]
        ) {
          const dy = e.changedTouches[0].clientY - swipeStart.current.y;
          if (dy > 80) onSwipeDownRef.current?.();
        }
        panStart.current = null;
        swipeStart.current = null;
        pointers.current.clear();
        if (scaleRef.current < 1.05) reset();
        else {
          clampPan();
          apply();
        }
      }
    };

    // Non-passive so we can preventDefault only during pinch / zoomed pan
    viewport.addEventListener("touchstart", onTouchStart, { passive: false });
    viewport.addEventListener("touchmove", onTouchMove, { passive: false });
    viewport.addEventListener("touchend", onTouchEnd);
    viewport.addEventListener("touchcancel", onTouchEnd);

    return () => {
      viewport.removeEventListener("touchstart", onTouchStart);
      viewport.removeEventListener("touchmove", onTouchMove);
      viewport.removeEventListener("touchend", onTouchEnd);
      viewport.removeEventListener("touchcancel", onTouchEnd);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div ref={viewportRef} className="lightbox-zoom-viewport" data-zoomed="0">
      <img ref={imageRef} src={src} alt="" className="lightbox-image" draggable={false} />
    </div>
  );
}
