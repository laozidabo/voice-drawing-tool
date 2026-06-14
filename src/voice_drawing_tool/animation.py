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

class RainDrop:
    """单个雨滴 — 带线条尾迹、深度层、风力。"""
    __slots__ = ('x', 'y', 'vx', 'vy', 'length', 'life', 'max_life',
                 'color', 'alpha', 'depth', 'splash_timer')

    def __init__(self, x, y, vx, vy, length, life, color, alpha, depth):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.length = length
        self.life = life
        self.max_life = life
        self.color = color
        self.alpha = alpha
        self.depth = depth  # 0=最近(大亮快), 1=最远(小暗慢)
        self.splash_timer = 0.0

    def update(self, dt, wind):
        self.x += (self.vx + wind * self.depth * 0.3) * dt
        self.y += self.vy * dt
        self.life -= dt
        fade = max(0.0, self.life / self.max_life)
        self.alpha = fade * (1.0 - self.depth * 0.5)
        return self.life > 0


class RainAnimation(Animation):
    """真实下雨效果：雨滴线条 + 多层深度 + 底部水花 + 风力变化。"""

    def __init__(self, width: int, height: int, loop: bool = True):
        super().__init__(duration=0, loop=loop)
        self._width = width
        self._height = height
        self._drops: List[RainDrop] = []
        self._splashes: List[Particle] = []  # 水花粒子
        self._accum = 0.0
        self._wind = 0.0
        self._wind_target = 0.0
        self._wind_timer = 0.0

    def _spawn_drop(self):
        """生成一个雨滴，随机分配深度层。"""
        depth = np.random.uniform(0, 1)  # 0=近, 1=远
        # 近处：大、亮、快、长尾；远处：小、暗、慢、短尾
        speed_mult = 1.0 - depth * 0.4  # 0.6 ~ 1.0
        size_mult = 1.0 - depth * 0.6   # 0.4 ~ 1.0
        alpha_base = 0.9 - depth * 0.5  # 0.4 ~ 0.9

        x = np.random.uniform(-20, self._width + 20)
        y = np.random.uniform(-30, -5)
        vx = np.random.uniform(-15, 15) * speed_mult
        vy = np.random.uniform(350, 600) * speed_mult
        length = np.random.uniform(12, 30) * size_mult
        life = (self._height + 30) / abs(vy) + 0.5  # 保证落到屏幕底部

        # 颜色：近处偏白蓝，远处偏灰
        if depth < 0.3:
            color = (210, 220, 240)  # 近：亮白蓝
        elif depth < 0.7:
            color = (180, 195, 220)  # 中：中蓝灰
        else:
            color = (150, 165, 190)  # 远：暗蓝灰

        self._drops.append(RainDrop(x, y, vx, vy, length, life, color, alpha_base, depth))

    def _spawn_splash(self, x, y):
        """底部水花：2-4 个小粒子向两侧溅开。"""
        count = np.random.randint(2, 5)
        for _ in range(count):
            sx = x + np.random.uniform(-3, 3)
            sy = y + np.random.uniform(-2, 0)
            svx = np.random.uniform(-40, 40)
            svy = np.random.uniform(-50, -15)  # 向上溅
            life = np.random.uniform(0.15, 0.35)
            sz = np.random.uniform(0.5, 1.5)
            color = (200, 215, 235)
            self._splashes.append(Particle(sx, sy, svx, svy, life, color, sz, alpha=0.7))

    def update(self, dt: float, progress: float):
        # ── 风力变化（缓慢随机漂移）──
        self._wind_timer += dt
        if self._wind_timer > np.random.uniform(1.5, 4.0):
            self._wind_timer = 0.0
            self._wind_target = np.random.uniform(-60, 60)
        # 平滑过渡到目标风力
        self._wind += (self._wind_target - self._wind) * min(1.0, dt * 2.0)

        # ── 生成雨滴（密度随时间增加到稳态）──
        self._accum += dt
        spawn_interval = 0.012  # ~80 个/秒
        while self._accum >= spawn_interval:
            self._accum -= spawn_interval
            self._spawn_drop()

        # ── 更新雨滴 ──
        alive = []
        for d in self._drops:
            if d.update(dt, self._wind):
                alive.append(d)
            else:
                # 落到底部或超出边界 → 生成水花
                if d.y >= self._height - 5 and abs(d.vx) < 100:
                    self._spawn_splash(d.x, self._height - 2)
        self._drops = alive

        # ── 更新水花 ──
        self._splashes = [p for p in self._splashes if p.update(dt)]

    def render(self, img: np.ndarray, progress: float):
        h, w = img.shape[:2]

        # ── 渲染雨滴（线条）──
        for d in self._drops:
            xi, yi = int(d.x), int(d.y)
            if xi < -10 or xi >= w + 10 or yi < -10 or yi >= h + 10:
                continue
            # 雨滴尾迹：从当前位置向上画一条线
            tail_x = d.x - d.vx * d.length / abs(d.vy) if abs(d.vy) > 1 else d.x
            tail_y = d.y - d.length
            col = tuple(int(c * d.alpha) for c in d.color)
            thickness = max(1, int(1.5 * (1.0 - d.depth * 0.5)))
            cv2.line(img, (int(tail_x), int(tail_y)), (xi, yi), col, thickness, cv2.LINE_AA)

        # ── 渲染水花（小圆点）──
        for p in self._splashes:
            px, py = int(p.x), int(p.y)
            if 0 <= px < w and 0 <= py < h:
                col = tuple(int(c * p.alpha) for c in p.color)
                cv2.circle(img, (px, py), max(1, int(p.size)), col, -1, cv2.LINE_AA)


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


# ─── Phase 5: Premium Effects (quality over quantity) ────────────────────────

class SnowAnimation(Animation):
    def __init__(self, width: int, height: int):
        super().__init__(duration=0, loop=True)
        self._w, self._h = width, height
        self._flakes: List[dict] = []
        self._accum = 0.0
        self._wind = 0.0

    def update(self, dt: float, progress: float):
        self._accum += dt * 18
        self._wind += random.uniform(-8, 8) * dt
        self._wind = max(-40, min(40, self._wind))
        while self._accum > 0 and len(self._flakes) < 140:
            self._accum -= 1
            self._flakes.append({
                'x': random.uniform(-20, self._w + 20),
                'y': random.uniform(-30, -5),
                'size': random.uniform(1.5, 4.5),
                'speed': random.uniform(40, 90),
                'sway_amp': random.uniform(15, 45),
                'sway_freq': random.uniform(1.2, 3.0),
                'phase': random.uniform(0, math.pi * 2),
                'opacity': random.uniform(0.6, 1.0),
                'life': random.uniform(4.0, 10.0),
                'age': 0.0,
            })
        alive = []
        for f in self._flakes:
            f['age'] += dt
            sway = math.sin(f['age'] * f['sway_freq'] + f['phase']) * f['sway_amp']
            f['x'] += self._wind * dt + sway * 0.3 * dt
            f['y'] += f['speed'] * dt
            if f['age'] < f['life'] and f['y'] < self._h + 10 and f['x'] > -40 and f['x'] < self._w + 40:
                alive.append(f)
        self._flakes = alive

    def render(self, img: np.ndarray, progress: float):
        h, w = img.shape[:2]
        for f in self._flakes:
            xi, yi = int(f['x']), int(f['y'])
            if not (-5 <= xi < w + 5 and -5 <= yi < h + 5):
                continue
            life_p = f['age'] / f['life']
            fade = f['opacity']
            if life_p < 0.1:
                fade *= life_p / 0.1
            if life_p > 0.85:
                fade *= (1 - life_p) / 0.15
            sz = f['size']
            icol = int(255 * fade)
            col = (icol, icol, icol)
            # Glow (soft outer halo)
            gsz = int(sz * 3)
            if gsz > 0:
                cv2.circle(img, (xi, yi), gsz, (icol // 3, icol // 3, icol // 3), -1, cv2.LINE_AA)
            # Core
            csz = max(1, int(sz))
            cv2.circle(img, (xi, yi), csz, col, -1, cv2.LINE_AA)
            # Bright highlight
            if sz > 2.5:
                cv2.circle(img, (xi - 1, yi - 1), max(1, csz - 1),
                           (min(255, icol + 40), min(255, icol + 40), min(255, icol + 40)),
                           -1, cv2.LINE_AA)


class BubblesAnimation(Animation):
    def __init__(self, width: int, height: int):
        super().__init__(duration=0, loop=True)
        self._w, self._h = width, height
        self._bubbles: List[dict] = []
        self._accum = 0.0
        self._pop_particles: List[dict] = []
        # Seed bubbles at random visible heights for instant feedback
        for _ in range(15):
            age = random.uniform(0.5, 5.0)
            self._bubbles.append({
                'x': random.uniform(30, width - 30),
                'y': random.uniform(40, height - 20),
                'size': random.uniform(6, 22),
                'speed': random.uniform(25, 60),
                'hue': random.uniform(0.5, 0.85),
                'wobble_amp': random.uniform(0.5, 1.5),
                'wobble_freq': random.uniform(2.0, 4.0),
                'phase': random.uniform(0, math.pi * 2),
                'life': random.uniform(4.0, 8.0),
                'age': age,
            })

    def _spawn_pop(self, bx: float, by: float, hue: float):
        for _ in range(12):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(30, 80)
            self._pop_particles.append({
                'x': bx, 'y': by,
                'vx': speed * math.cos(angle),
                'vy': speed * math.sin(angle),
                'life': random.uniform(0.2, 0.5),
                'age': 0.0,
                'size': random.uniform(1.5, 3),
                'hue': hue + random.uniform(-0.1, 0.1),
            })

    def update(self, dt: float, progress: float):
        self._accum += dt * 6
        while self._accum > 0 and len(self._bubbles) < 35:
            self._accum -= 1
            x = random.uniform(30, self._w - 30)
            sz = random.uniform(6, 22)
            self._bubbles.append({
                'x': x,
                'y': self._h + sz,
                'size': sz,
                'speed': random.uniform(25, 60),
                'hue': random.uniform(0.5, 0.85),
                'wobble_amp': random.uniform(0.5, 1.5),
                'wobble_freq': random.uniform(2.0, 4.0),
                'phase': random.uniform(0, math.pi * 2),
                'life': random.uniform(4.0, 8.0),
                'age': 0.0,
            })
        for b in self._bubbles:
            b['age'] += dt
            if b['age'] >= b['life']:
                self._spawn_pop(b['x'], b['y'], b['hue'])
        self._bubbles = [b for b in self._bubbles if b['age'] < b['life']]
        # Update pop particles
        dead_pop = []
        for p in self._pop_particles:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['age'] += dt
            if p['age'] >= p['life']:
                dead_pop.append(p)
        for p in dead_pop:
            self._pop_particles.remove(p)

    def _hsv_to_bgr(self, hue: float, sat: float, val: float):
        h = hue * 180
        s = int(sat * 255)
        v = int(val * 255)
        hi = int(h / 30) % 6
        f = h / 30 - hi
        p = v * (1 - s / 255)
        q = v * (1 - f * s / 255)
        t = v * (1 - (1 - f) * s / 255)
        if hi == 0:
            return (v, t, p)
        if hi == 1:
            return (q, v, p)
        if hi == 2:
            return (p, v, t)
        if hi == 3:
            return (p, q, v)
        if hi == 4:
            return (t, p, v)
        return (v, p, q)

    def render(self, img: np.ndarray, progress: float):
        h, w = img.shape[:2]
        overlay = img.copy()
        # Render bubbles
        for b in self._bubbles:
            xi, yi = int(b['x']), int(b['y'])
            if not (0 <= xi < w and 0 <= yi < h):
                continue
            life_p = b['age'] / b['life']
            fade = 1.0
            if life_p < 0.05:
                fade = life_p / 0.05
            if life_p > 0.9:
                fade = (1 - life_p) / 0.1
            r = int(b['size'])
            wobble = math.sin(b['age'] * b['wobble_freq'] + b['phase']) * b['wobble_amp']
            yi += int(wobble)
            # Body color (iridescent)
            hue_shift = math.sin(b['age'] * 0.5) * 0.08
            col = self._hsv_to_bgr(b['hue'] + hue_shift, 0.25, 1.0)
            col = tuple(int(c * fade) for c in col)
            # Main circle (translucent via overlay)
            cv2.circle(overlay, (xi, yi), r, col, -1, cv2.LINE_AA)
            # Rim highlight
            rim_col = (min(255, col[0] + 80), min(255, col[1] + 80), min(255, col[2] + 80))
            cv2.circle(overlay, (xi, yi), r, rim_col, 1, cv2.LINE_AA)
            # Reflection highlight (top-left)
            hl_x, hl_y = xi - r // 3, yi - r // 3
            hl_r = max(1, r // 5)
            cv2.circle(overlay, (hl_x, hl_y), hl_r,
                       (255, 255, 255), -1, cv2.LINE_AA)
        # Blend overlay with transparency
        alpha = 0.35
        cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
        # Render pop particles (bright)
        for p in self._pop_particles:
            xi, yi = int(p['x']), int(p['y'])
            if not (0 <= xi < w and 0 <= yi < h):
                continue
            life_p = p['age'] / p['life']
            b = int(255 * (1 - life_p))
            col = self._hsv_to_bgr(p['hue'], 0.8, 1.0)
            col = tuple(int(c * (1 - life_p)) for c in col)
            sz = int(p['size'] * (1 - life_p * 0.5))
            if sz > 0:
                cv2.circle(img, (xi, yi), sz, col, -1, cv2.LINE_AA)


class AuroraAnimation(Animation):
    def __init__(self, width: int, height: int):
        super().__init__(duration=0, loop=True)
        self._w, self._h = width, height
        self._time = 0.0
        self._bands = [
            {'hue': 0.33, 'speed': 0.3, 'amp': 30, 'freq': 0.015, 'y_offset': 0.0},
            {'hue': 0.45, 'speed': 0.45, 'amp': 45, 'freq': 0.022, 'y_offset': 25},
            {'hue': 0.55, 'speed': 0.6, 'amp': 35, 'freq': 0.018, 'y_offset': 50},
            {'hue': 0.65, 'speed': 0.35, 'amp': 25, 'freq': 0.025, 'y_offset': 70},
            {'hue': 0.75, 'speed': 0.5, 'amp': 40, 'freq': 0.02, 'y_offset': 90},
        ]
        self._strip_height = height // 3
        # Pre-compute positions for performance
        self._x_coords = np.arange(0, width, 2)

    def _aurora_bgr(self, hue: float, brightness: float):
        h = hue * 180
        hi = int(h / 30) % 6
        f = h / 30 - hi
        b = int(255 * brightness)
        p = int(b * 0.4)
        q = int(b * (1 - f * 0.6))
        t = int(b * (1 - (1 - f) * 0.6))
        if hi == 0:
            return (b, t, p)
        if hi == 1:
            return (q, b, p)
        if hi == 2:
            return (p, b, t)
        if hi == 3:
            return (p, q, b)
        if hi == 4:
            return (t, p, b)
        return (b, p, q)

    def update(self, dt: float, progress: float):
        self._time += dt

    def render(self, img: np.ndarray, progress: float):
        h, w = img.shape[:2]
        overlay = np.zeros_like(img, dtype=np.float32)
        base_y = h // 2 - self._strip_height // 2
        for band in self._bands:
            y_off = band['y_offset']
            speed = band['speed']
            amp = band['amp']
            freq = band['freq']
            for step, xi in enumerate(self._x_coords):
                wave = math.sin(xi * freq + self._time * speed) * amp
                wave += math.sin(xi * freq * 1.7 + self._time * speed * 0.6) * amp * 0.3
                wy = base_y + y_off + wave
                if wy < 0 or wy >= h:
                    continue
                vert_fade = 1.0
                dist_from_center = abs(wy - (base_y + 45))
                if dist_from_center > 40:
                    vert_fade = max(0, 1 - (dist_from_center - 40) / 60)
                if vert_fade < 0.02:
                    continue
                brightness = vert_fade * random.uniform(0.85, 1.0)
                col = self._aurora_bgr(band['hue'], brightness)
                # Draw as a vertical column with slight spread
                for dy in range(-2, 3):
                    py = int(wy) + dy
                    if 0 <= py < h:
                        fade_dy = 1 - abs(dy) * 0.3
                        overlay[py, xi] += np.array(col, dtype=np.float32) * 0.6 * fade_dy
        # Clip and blend
        overlay = np.clip(overlay, 0, 255).astype(np.uint8)
        mask = np.any(overlay > 5, axis=2)
        blended = cv2.addWeighted(img, 0.55, overlay, 0.45, 0)
        img[mask] = blended[mask]
