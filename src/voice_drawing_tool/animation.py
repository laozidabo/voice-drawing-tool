import time
import math
import random
import numpy as np
import cv2
from typing import List, Optional, Tuple


class Animation:
    def __init__(self, duration: float, loop: bool = False, start_time: Optional[float] = None):
        self.duration = duration
        self.loop = loop
        self.start_time = start_time or time.time()
        self._done = False

    def get_progress(self) -> float:
        if self._done:
            return 1.0
        if self.duration <= 0:
            if self.loop:
                return 0.0
            self._done = True
            return 1.0
        elapsed = time.time() - self.start_time
        p = elapsed / self.duration
        if p >= 1.0:
            if self.loop:
                self.start_time = time.time()
                return 0.0
            self._done = True
            return 1.0
        return max(0.0, p)

    def is_done(self) -> bool:
        return self._done

    def update(self, dt: float, progress: float):
        pass

    def render(self, img: np.ndarray, progress: float):
        pass

    def finish(self, canvas_img: np.ndarray):
        pass


class AnimationManager:
    def __init__(self):
        self._animations: List[Animation] = []

    def add(self, anim: Animation):
        self._animations.append(anim)

    def clear(self):
        self._animations.clear()

    def update_and_render(self, dt: float, preview_img: np.ndarray, canvas_img: np.ndarray) -> bool:
        if not self._animations:
            return False
        alive = []
        for anim in self._animations:
            if anim.is_done():
                anim.finish(canvas_img)
                continue
            progress = anim.get_progress()
            if anim.is_done():
                anim.finish(canvas_img)
                continue
            anim.update(dt, progress)
            anim.render(preview_img, progress)
            alive.append(anim)
        self._animations = alive
        return len(self._animations) > 0

    @property
    def active_count(self) -> int:
        return len(self._animations)


class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max_life', 'color', 'size', 'alpha')

    def __init__(self, x: float, y: float, vx: float, vy: float,
                 life: float, color: Tuple[int, int, int], size: float, alpha: float = 1.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.alpha = alpha

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        self.alpha = max(0.0, self.life / self.max_life)
        return self.life > 0


class ParticleSystem:
    def __init__(self):
        self.particles: List[Particle] = []

    def emit(self, x: float, y: float, count: int, config: dict):
        vx_range = config.get('vx_range', (-50, 50))
        vy_range = config.get('vy_range', (-100, -50))
        life_range = config.get('life_range', (0.5, 1.5))
        size_range = config.get('size_range', (1.0, 3.0))
        colors = config.get('colors', [(255, 255, 255)])
        speed = config.get('speed', 1.0)
        for _ in range(count):
            vx = np.random.uniform(*vx_range) * speed
            vy = np.random.uniform(*vy_range) * speed
            life = np.random.uniform(*life_range)
            sz = np.random.uniform(*size_range)
            color = colors[np.random.randint(len(colors))]
            self.particles.append(Particle(x, y, vx, vy, life, color, sz))

    def update(self, dt: float):
        alive = [p for p in self.particles if p.update(dt)]
        self.particles = alive

    def render(self, img: np.ndarray):
        h, w = img.shape[:2]
        for p in self.particles:
            xi, yi = int(p.x), int(p.y)
            if 0 <= xi < w and 0 <= yi < h:
                col = tuple(min(255, int(c * p.alpha)) for c in p.color)
                cv2.circle(img, (xi, yi), max(1, int(p.size)), col, -1, cv2.LINE_AA)

    @property
    def count(self) -> int:
        return len(self.particles)


# ─── Concrete Animations ─────────────────────────────────────────────────────

class RainAnimation(Animation):
    def __init__(self, width: int, loop: bool = True):
        super().__init__(duration=0, loop=loop)
        self._width = width
        self._ps = ParticleSystem()
        self._accum = 0.0

    def update(self, dt: float, progress: float):
        self._accum += dt
        if self._accum > 0.05:
            self._accum = 0
            x = np.random.uniform(0, self._width)
            self._ps.emit(x, -5, 3, {
                'vx_range': (-10, 10),
                'vy_range': (250, 450),
                'life_range': (1.0, 2.5),
                'size_range': (1, 2),
                'colors': [(200, 210, 230), (180, 200, 220)],
                'speed': 1.0,
            })
        self._ps.update(dt)

    def render(self, img: np.ndarray, progress: float):
        self._ps.render(img)


class GrowFlowerAnimation(Animation):
    def __init__(self, cx: int, cy: int, color: Tuple[int, int, int],
                 stem_color: Tuple[int, int, int] = (50, 180, 50)):
        super().__init__(duration=3.0)
        self.cx = cx
        self.cy = cy
        self.color = color
        self.stem_color = stem_color
        self._stem_h = 0

    def update(self, dt: float, progress: float):
        self._stem_h = 60

    def render(self, img: np.ndarray, progress: float):
        h, w = img.shape[:2]
        cx, cy = self.cx, self.cy
        stem_h = 60
        if progress < 0.2:
            r = 3 + progress / 0.2 * 6
            cv2.circle(img, (cx, cy), int(r), self.color, -1, cv2.LINE_AA)
        elif progress < 0.4:
            sh = (progress - 0.2) / 0.2 * stem_h
            cv2.line(img, (cx, cy), (cx, cy - int(sh)), self.stem_color, 3, cv2.LINE_AA)
            cv2.circle(img, (cx, cy - int(sh)), 6, self.color, -1, cv2.LINE_AA)
        else:
            sh = stem_h
            cv2.line(img, (cx, cy), (cx, cy - sh), self.stem_color, 3, cv2.LINE_AA)
            petal_prog = (progress - 0.4) / 0.6
            petal_len = 8 + petal_prog * 18
            top_y = cy - sh
            for angle in range(0, 360, 60):
                rad = math.radians(angle)
                px = cx + int(petal_len * math.cos(rad))
                py = top_y + int(petal_len * math.sin(rad))
                cv2.ellipse(img, (px, py), (10, 5), angle, 0, 360, self.color, -1, cv2.LINE_AA)
            cv2.circle(img, (cx, top_y), 4, (min(255, self.color[0] + 40),
                                             min(255, self.color[1] + 40),
                                             min(255, self.color[2] + 40)), -1, cv2.LINE_AA)

    def finish(self, canvas_img: np.ndarray):
        h, w = canvas_img.shape[:2]
        cx, cy = self.cx, self.cy
        stem_h = 60
        cv2.line(canvas_img, (cx, cy), (cx, cy - stem_h), self.stem_color, 3, cv2.LINE_AA)
        for angle in range(0, 360, 60):
            rad = math.radians(angle)
            px = cx + int(26 * math.cos(rad))
            py = cy - stem_h + int(26 * math.sin(rad))
            cv2.ellipse(canvas_img, (px, py), (10, 5), angle, 0, 360, self.color, -1, cv2.LINE_AA)
        cv2.circle(canvas_img, (cx, cy - stem_h), 4,
                   (min(255, self.color[0] + 40), min(255, self.color[1] + 40),
                    min(255, self.color[2] + 40)), -1, cv2.LINE_AA)


class FirefliesAnimation(Animation):
    def __init__(self, width: int, height: int, count: int = 30):
        super().__init__(duration=0, loop=True)
        self._ps = ParticleSystem()
        for _ in range(count):
            x = np.random.uniform(0, width)
            y = np.random.uniform(0, height)
            vx = np.random.uniform(-12, 12)
            vy = np.random.uniform(-12, 12)
            life = np.random.uniform(1.5, 4.0)
            sz = np.random.uniform(2, 4)
            self._ps.particles.append(Particle(x, y, vx, vy, life, (60, 210, 180), sz))
        self._w, self._h = width, height
        self._accum = 0.0

    def update(self, dt: float, progress: float):
        self._accum += dt
        if self._accum > 0.3:
            self._accum = 0
            if len(self._ps.particles) < 60:
                self._ps.particles.append(Particle(
                    np.random.uniform(0, self._w), np.random.uniform(0, self._h),
                    np.random.uniform(-12, 12), np.random.uniform(-12, 12),
                    np.random.uniform(1.5, 4.0), (60, 210, 180),
                    np.random.uniform(2, 4)))
        for p in self._ps.particles:
            p.vx += np.random.uniform(-3, 3) * dt
            p.vy += np.random.uniform(-3, 3) * dt
            p.vx = max(-15, min(15, p.vx))
            p.vy = max(-15, min(15, p.vy))
        self._ps.update(dt)
        self._ps.particles = [p for p in self._ps.particles
                              if 0 <= p.x <= self._w and 0 <= p.y <= self._h]

    def render(self, img: np.ndarray, progress: float):
        for p in self._ps.particles:
            xi, yi = int(p.x), int(p.y)
            if 0 <= xi < self._w and 0 <= yi < self._h:
                glow = max(0, math.sin(p.life * 3) * 0.4 + 0.6)
                col = tuple(min(255, int(c * glow * p.alpha)) for c in (60, 210, 180))
                cv2.circle(img, (xi, yi), int(p.size * 2), col, -1, cv2.LINE_AA)
                cv2.circle(img, (xi, yi), int(p.size * 4),
                           tuple(c // 3 for c in col), -1, cv2.LINE_AA)
                cv2.circle(img, (xi, yi), int(p.size), (255, 255, 230), -1, cv2.LINE_AA)


class GrowTreeAnimation(Animation):
    def __init__(self, cx: int, cy: int):
        super().__init__(duration=4.0)
        self.cx = cx
        self.cy = cy
        self._trunk_h = 80

    def render(self, img: np.ndarray, progress: float):
        cx, cy = self.cx, self.cy
        trunk_h = self._trunk_h
        if progress < 0.3:
            th = progress / 0.3 * trunk_h
            cv2.rectangle(img, (cx - 4, cy - int(th)), (cx + 4, cy), (30, 110, 60), -1)
        elif progress < 0.5:
            cv2.rectangle(img, (cx - 4, cy - trunk_h), (cx + 4, cy), (30, 110, 60), -1)
            branch_p = (progress - 0.3) / 0.2
            for side in (-1, 1):
                bx = cx + side * int(branch_p * 30)
                by = cy - trunk_h + 20
                cv2.line(img, (cx, cy - trunk_h + 10), (bx, by), (30, 110, 60), 3, cv2.LINE_AA)
        else:
            crown_p = (progress - 0.5) / 0.5
            r = int(15 + crown_p * 35)
            cv2.rectangle(img, (cx - 4, cy - trunk_h), (cx + 4, cy), (30, 110, 60), -1)
            for side in (-1, 1):
                bx = cx + side * 30
                by = cy - trunk_h + 20
                cv2.line(img, (cx, cy - trunk_h + 10), (bx, by), (30, 110, 60), 3, cv2.LINE_AA)
            for dcx, dcy in [(0, -trunk_h), (-30, -trunk_h + 20), (30, -trunk_h + 20)]:
                cv2.circle(img, (cx + dcx, cy + dcy), r, (40, 180, 70), -1, cv2.LINE_AA)
                cv2.circle(img, (cx + dcx, cy + dcy), r,
                           (60, 210, 100), 2, cv2.LINE_AA)

    def finish(self, canvas_img: np.ndarray):
        self.render(canvas_img, 1.0)


# ─── Phase 3: Particle Magic ─────────────────────────────────────────────────

class FireworksAnimation(Animation):
    def __init__(self, cx: int, cy: int, color: Optional[Tuple[int, int, int]] = None):
        super().__init__(duration=2.5)
        self.cx = cx
        self.cy = cy
        self.burst_color = color or (random.randint(100, 255),
                                     random.randint(50, 200),
                                     random.randint(50, 200))
        self._ps = ParticleSystem()
        self._has_burst = False
        self._start_y = cy + 60

    def update(self, dt: float, progress: float):
        if progress < 0.25:
            pass
        elif not self._has_burst:
            self._has_burst = True
            colors = [
                self.burst_color,
                (min(255, self.burst_color[0] + 60),
                 min(255, self.burst_color[1] + 60),
                 min(255, self.burst_color[2] + 60)),
                (255, 255, 255),
                (min(255, self.burst_color[0] + 30),
                 max(0, self.burst_color[1] - 30),
                 max(0, self.burst_color[2] - 30)),
            ]
            for _ in range(100):
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(100, 280)
                vx = speed * math.cos(angle)
                vy = speed * math.sin(angle) - 40
                life = random.uniform(0.5, 1.8)
                color = colors[random.randint(0, len(colors) - 1)]
                sz = random.uniform(1.5, 3.5)
                self._ps.particles.append(Particle(self.cx, self.cy, vx, vy, life, color, sz))
            # Sparkle tail particles
            for _ in range(30):
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(50, 120)
                vx = speed * math.cos(angle)
                vy = speed * math.sin(angle)
                life = random.uniform(0.3, 0.8)
                self._ps.particles.append(Particle(self.cx, self.cy, vx, vy, life,
                                                  (255, 255, 230), random.uniform(1, 2)))
        self._ps.update(dt)

    def render(self, img: np.ndarray, progress: float):
        if progress < 0.25:
            rpy = int(self._start_y - (self._start_y - self.cy) * (progress / 0.25))
            cv2.line(img, (self.cx, rpy + 20), (self.cx, rpy - 2),
                     (200, 180, 100), 2, cv2.LINE_AA)
            cv2.circle(img, (self.cx, rpy - 2), 3, (255, 220, 150), -1, cv2.LINE_AA)
        self._ps.render(img)


class SparkleAnimation(Animation):
    def __init__(self, cx: int, cy: int, radius: int = 120, count: int = 25):
        super().__init__(duration=1.8)
        self.cx = cx
        self.cy = cy
        self._sparkles = []
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(5, radius)
            self._sparkles.append({
                'x': cx + dist * math.cos(angle),
                'y': cy + dist * math.sin(angle),
                'phase': random.uniform(0, math.pi * 2),
                'speed': random.uniform(3, 7),
                'size': random.uniform(1.5, 4),
                'color': (random.randint(200, 255), random.randint(200, 255),
                          random.randint(150, 255)),
            })

    def render(self, img: np.ndarray, progress: float):
        h, w = img.shape[:2]
        fade = 1.0 - progress * 0.6
        for s in self._sparkles:
            brightness = math.sin(progress * s['speed'] * math.pi + s['phase'])
            brightness = max(0, brightness) * fade
            if brightness < 0.05:
                continue
            xi, yi = int(s['x']), int(s['y'])
            if not (0 <= xi < w and 0 <= yi < h):
                continue
            col = tuple(min(255, int(c * brightness)) for c in s['color'])
            sz = int(s['size'])
            cv2.line(img, (xi - sz * 2, yi), (xi + sz * 2, yi), col, 1, cv2.LINE_AA)
            cv2.line(img, (xi, yi - sz * 2), (xi, yi + sz * 2), col, 1, cv2.LINE_AA)
            cv2.line(img, (xi - sz, yi - sz), (xi + sz, yi + sz), col, 1, cv2.LINE_AA)
            cv2.line(img, (xi + sz, yi - sz), (xi - sz, yi + sz), col, 1, cv2.LINE_AA)


class MagicCircleAnimation(Animation):
    def __init__(self, cx: int, cy: int, color: Optional[Tuple[int, int, int]] = None):
        super().__init__(duration=2.5)
        self.cx = cx
        self.cy = cy
        self.color = color or (220, 130, 60)

    def render(self, img: np.ndarray, progress: float):
        cx, cy = self.cx, self.cy
        if progress < 0.2:
            r = int(10 + progress / 0.2 * 80)
            cv2.circle(img, (cx, cy), r, self.color, 2, cv2.LINE_AA)
            cv2.circle(img, (cx, cy), r + 5, (min(255, self.color[0] + 30),
                                              min(255, self.color[1] + 30),
                                              min(255, self.color[2] + 30)), 1, cv2.LINE_AA)
        elif progress < 0.5:
            r = 90
            alpha = (progress - 0.2) / 0.3
            cv2.circle(img, (cx, cy), r, self.color, 2, cv2.LINE_AA)
            # Inner rotating ring
            inner_r = int(40 + alpha * 30)
            cv2.circle(img, (cx, cy), inner_r,
                       (min(255, self.color[0] + 50), min(255, self.color[1] + 50),
                        min(255, self.color[2] + 50)), 1, cv2.LINE_AA)
            # Radial lines
            for i in range(8):
                angle = math.radians(i * 45 + alpha * 45)
                x1 = cx + int(inner_r * math.cos(angle))
                y1 = cy + int(inner_r * math.sin(angle))
                x2 = cx + int(r * math.cos(angle))
                y2 = cy + int(r * math.sin(angle))
                cv2.line(img, (x1, y1), (x2, y2), self.color, 1, cv2.LINE_AA)
            # Center
            cv2.circle(img, (cx, cy), 3,
                       (min(255, self.color[0] + 80), min(255, self.color[1] + 80),
                        min(255, self.color[2] + 80)), -1, cv2.LINE_AA)
        else:
            alpha = (progress - 0.5) / 0.5
            r = 90
            glow = int(max(0, 255 * (1 - alpha)))
            col = (min(255, self.color[0] + int(50 * alpha)),
                   min(255, self.color[1] + int(50 * alpha)),
                   min(255, self.color[2] + int(50 * alpha)))
            cv2.circle(img, (cx, cy), r, col, 2, cv2.LINE_AA)
            inner_r = 70
            for i in range(12):
                angle = math.radians(i * 30 + alpha * 90)
                x2 = cx + int(r * math.cos(angle))
                y2 = cy + int(r * math.sin(angle))
                cv2.line(img, (cx, cy), (x2, y2), col, 1, cv2.LINE_AA)
            cv2.circle(img, (cx, cy), inner_r, (glow, glow, glow), 1, cv2.LINE_AA)
            cv2.circle(img, (cx, cy), 4, (255, 255, 255), -1, cv2.LINE_AA)

    def finish(self, canvas_img: np.ndarray):
        cx, cy = self.cx, self.cy
        cv2.circle(canvas_img, (cx, cy), 90, self.color, 2, cv2.LINE_AA)
        cv2.circle(canvas_img, (cx, cy), 3,
                   (min(255, self.color[0] + 80), min(255, self.color[1] + 80),
                    min(255, self.color[2] + 80)), -1, cv2.LINE_AA)


class StarfallAnimation(Animation):
    def __init__(self, width: int, height: int):
        super().__init__(duration=0, loop=True)
        self._w, self._h = width, height
        self._stars: List[dict] = []
        self._accum = 0.0

    def update(self, dt: float, progress: float):
        self._accum += dt
        if self._accum > random.uniform(0.8, 2.5):
            self._accum = 0
            x = random.uniform(50, self._w - 50)
            self._stars.append({
                'x': x,
                'y': -10,
                'vx': random.uniform(60, 150),
                'vy': random.uniform(180, 350),
                'life': random.uniform(0.8, 1.8),
                'age': 0.0,
                'size': random.uniform(1.5, 3),
                'brightness': random.uniform(0.6, 1.0),
            })
        alive = []
        for s in self._stars:
            s['x'] += s['vx'] * dt
            s['y'] += s['vy'] * dt
            s['age'] += dt
            if s['age'] < s['life'] and 0 <= s['x'] <= self._w and s['y'] < self._h + 20:
                alive.append(s)
        self._stars = alive

    def render(self, img: np.ndarray, progress: float):
        h, w = img.shape[:2]
        for s in self._stars:
            xi, yi = int(s['x']), int(s['y'])
            if not (0 <= xi < w and 0 <= yi < h):
                continue
            life_p = s['age'] / s['life']
            b = s['brightness'] * (1 - life_p * 0.7)
            col = tuple(int(200 * b) for _ in range(3))
            sz = int(s['size'])
            # Trail
            trail_len = int(12 * (1 - life_p))
            if trail_len > 2:
                cv2.line(img, (xi, yi), (xi - int(s['vx'] * 0.01 * trail_len),
                                         yi - int(s['vy'] * 0.01 * trail_len)),
                         tuple(c // 2 for c in col), 1, cv2.LINE_AA)
            # Star head
            cv2.line(img, (xi - sz, yi), (xi + sz, yi), col, 1, cv2.LINE_AA)
            cv2.line(img, (xi, yi - sz), (xi, yi + sz), col, 1, cv2.LINE_AA)
