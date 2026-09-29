#!/usr/bin/env python3
"""Ammolite Orbit — neon orbital-hop arcade for ElbowOS."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys

import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "AMMOLITE ORBIT"
HANDLE = "x.com/ElbowOS"
VOID = (6, 8, 18)
NAVY = (12, 18, 38)
GOLD = (255, 186, 64)
CRIM = (255, 72, 86)
TEAL = (48, 255, 214)
LIME = (186, 255, 92)
VIO = (168, 96, 255)
ICE = (236, 244, 255)
ASH = (70, 78, 110)
FLAKE_COLS = (GOLD, CRIM, TEAL, LIME, VIO)
RINGS = (210, 320, 430, 540)


class Spark:
    __slots__ = ("x", "y", "vx", "vy", "life", "col", "r")

    def __init__(self, x, y, vx, vy, life, col, r=5):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life, self.col, self.r = life, col, r


class Bit:
    __slots__ = ("ring", "ang", "spd", "kind", "col", "r")

    def __init__(self, ring, ang, spd, kind, col, r):
        self.ring, self.ang, self.spd = ring, ang, spd
        self.kind, self.col, self.r = kind, col, r


class Game:
    def __init__(self, record: bool):
        self.record = record
        self.surf = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.Font(None, 62)
        self.font_md = pygame.font.Font(None, 42)
        self.font_sm = pygame.font.Font(None, 30)
        self.cx, self.cy = W / 2, H / 2 + 40
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.combo = 0
        self.lives = 3
        self.pulse = 0.0
        self.over = False
        self.cool = 0.0
        self.ri = 1
        self.ang = -math.pi / 2
        self.omega = 1.15
        self.hop_cd = 0.0
        self.sparks: list[Spark] = []
        self.bits: list[Bit] = []
        self.stars = [(random.randrange(W), random.randrange(H), random.uniform(0.3, 2.2)) for _ in range(130)]
        self.spawn_t = 0.0
        for _ in range(10):
            self._spawn(True)

    def _pos(self, ring: int, ang: float) -> tuple[float, float]:
        r = RINGS[ring]
        return self.cx + math.cos(ang) * r, self.cy + math.sin(ang) * r

    def _spawn(self, start: bool = False) -> None:
        ring = random.randrange(4)
        kind = "rock" if random.random() < 0.28 else "flake"
        ang = random.random() * 6.2832
        if start:
            ang = random.uniform(0.4, 5.8)
        spd = random.uniform(0.35, 0.95) * random.choice((-1, 1))
        col = ASH if kind == "rock" else random.choice(FLAKE_COLS)
        r = random.randint(16, 24) if kind == "rock" else random.randint(12, 18)
        self.bits.append(Bit(ring, ang, spd, kind, col, r))

    def burst(self, x, y, col, n=14) -> None:
        for _ in range(n):
            a = random.random() * 6.2832
            s = random.uniform(70, 380)
            self.sparks.append(Spark(x, y, s * math.cos(a), s * math.sin(a),
                                     random.uniform(0.18, 0.48), col, random.randint(3, 8)))

    def autoplay(self) -> None:
        if self.over:
            if self.cool <= 0:
                self.reset()
            return
        px, py = self._pos(self.ri, self.ang)
        threat = None
        best_flake = None
        best_d = 1e9
        for b in self.bits:
            bx, by = self._pos(b.ring, b.ang)
            d = math.hypot(bx - px, by - py)
            if b.kind == "rock" and b.ring == self.ri and d < 160:
                threat = b
            if b.kind == "flake" and d < best_d:
                best_d, best_flake = d, b
        want = self.ri
        if threat is not None:
            want = 0 if self.ri > 0 else 1
            if threat.ring == 0:
                want = 1
            elif self.ri == 3:
                want = 2
            else:
                want = self.ri + 1 if random.random() < 0.5 else max(0, self.ri - 1)
        elif best_flake is not None:
            want = best_flake.ring
        if want != self.ri and self.hop_cd <= 0:
            self.ri = want
            self.hop_cd = 0.16
            hx, hy = self._pos(self.ri, self.ang)
            self.burst(hx, hy, TEAL, 8)

    def update(self, dt: float) -> None:
        self.pulse += dt
        self.cool = max(0.0, self.cool - dt)
        self.hop_cd = max(0.0, self.hop_cd - dt)
        if self.record:
            self.autoplay()
        else:
            keys = pygame.key.get_pressed()
            if self.hop_cd <= 0:
                if keys[pygame.K_UP] or keys[pygame.K_w]:
                    self.ri = max(0, self.ri - 1)
                    self.hop_cd = 0.14
                elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                    self.ri = min(3, self.ri + 1)
                    self.hop_cd = 0.14
        alive = []
        for sp in self.sparks:
            sp.life -= dt
            if sp.life <= 0:
                continue
            sp.x += sp.vx * dt
            sp.y += sp.vy * dt
            alive.append(sp)
        self.sparks = alive
        if self.over:
            return
        self.omega = 1.05 + min(0.9, self.score * 0.002)
        self.ang += self.omega * dt
        self.spawn_t -= dt
        if self.spawn_t <= 0:
            self._spawn()
            self.spawn_t = max(0.22, 0.62 - self.score * 0.00035)
        px, py = self._pos(self.ri, self.ang)
        kept = []
        for b in self.bits:
            b.ang += b.spd * dt
            bx, by = self._pos(b.ring, b.ang)
            if math.hypot(bx - px, by - py) < 36 + b.r:
                if b.kind == "rock":
                    self.lives -= 1
                    self.combo = 0
                    self.burst(bx, by, CRIM, 20)
                    if self.lives <= 0:
                        self.over = True
                        self.cool = 1.5
                    continue
                self.combo += 1
                self.score += 15 + self.combo * 4
                self.burst(bx, by, b.col, 16)
                continue
            kept.append(b)
        self.bits = kept[-28:]

    def handle(self, ev) -> None:
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_r:
                self.reset()
            elif ev.key in (pygame.K_UP, pygame.K_w) and self.hop_cd <= 0:
                self.ri = max(0, self.ri - 1)
                self.hop_cd = 0.12
            elif ev.key in (pygame.K_DOWN, pygame.K_s) and self.hop_cd <= 0:
                self.ri = min(3, self.ri + 1)
                self.hop_cd = 0.12

    def draw(self, s: pygame.Surface) -> None:
        s.fill(VOID)
        for sx, sy, sc in self.stars:
            yy = int((sy + self.pulse * 18 * sc) % H)
            pygame.draw.circle(s, (20 + int(12 * sc), 24, 48), (sx, yy), 1 if sc < 1.3 else 2)
        for i, rad in enumerate(RINGS):
            col = (28 + i * 10, 36 + i * 8, 72)
            pygame.draw.circle(s, col, (int(self.cx), int(self.cy)), rad, 3)
            glow = FLAKE_COLS[i]
            pygame.draw.circle(s, glow, (int(self.cx), int(self.cy)), rad, 1)
        for k in range(8):
            a = self.pulse * 1.6 + k * 0.785
            c = FLAKE_COLS[k % 5]
            x1 = int(self.cx + math.cos(a) * 28)
            y1 = int(self.cy + math.sin(a) * 28)
            x2 = int(self.cx + math.cos(a) * 86)
            y2 = int(self.cy + math.sin(a) * 86)
            pygame.draw.aaline(s, c, (x1, y1), (x2, y2))
        pygame.draw.circle(s, GOLD, (int(self.cx), int(self.cy)), 54)
        pygame.draw.circle(s, NAVY, (int(self.cx), int(self.cy)), 40)
        pygame.draw.circle(s, TEAL, (int(self.cx), int(self.cy)), 22)
        pygame.draw.circle(s, ICE, (int(self.cx - 8), int(self.cy - 10)), 7)
        for b in self.bits:
            bx, by = self._pos(b.ring, b.ang)
            pygame.draw.circle(s, b.col, (int(bx), int(by)), b.r + 4)
            inner = ASH if b.kind == "rock" else ICE
            pygame.draw.circle(s, inner, (int(bx), int(by)), max(4, b.r - 6))
            if b.kind == "rock":
                pygame.draw.circle(s, CRIM, (int(bx), int(by)), b.r, 2)
        px, py = self._pos(self.ri, self.ang)
        trail_a = self.ang - 0.22
        tx, ty = self._pos(self.ri, trail_a)
        pygame.draw.circle(s, TEAL, (int(tx), int(ty)), 10)
        pygame.draw.circle(s, GOLD, (int(px), int(py)), 30)
        pygame.draw.circle(s, NAVY, (int(px), int(py)), 20)
        pygame.draw.circle(s, LIME, (int(px), int(py)), 12)
        pygame.draw.circle(s, ICE, (int(px - 6), int(py - 6)), 5)
        for sp in self.sparks:
            pygame.draw.circle(s, sp.col, (int(sp.x), int(sp.y)), max(1, int(sp.r * sp.life * 2)))
        title = self.font_lg.render(TITLE, True, ICE)
        s.blit(title, title.get_rect(center=(W // 2, 64)))
        handle = self.font_sm.render(HANDLE, True, TEAL)
        s.blit(handle, handle.get_rect(center=(W // 2, 112)))
        meta = self.font_md.render(f"SCORE  {self.score}    COMBO  {self.combo}    HP  {self.lives}", True, GOLD)
        s.blit(meta, meta.get_rect(center=(W // 2, 168)))
        ring_txt = self.font_sm.render(f"ORBIT  {self.ri + 1} / 4", True, FLAKE_COLS[self.ri])
        s.blit(ring_txt, ring_txt.get_rect(center=(W // 2, 214)))
        hint = self.font_sm.render("W/S or UP/DOWN hop orbits   R reset", True, GOLD)
        s.blit(hint, hint.get_rect(center=(W // 2, H - 42)))
        if self.over:
            over = self.font_md.render("ORBIT SHATTERED", True, CRIM)
            s.blit(over, over.get_rect(center=(W // 2, 262)))

    def play(self) -> None:
        screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(TITLE)
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False
                else:
                    self.handle(ev)
            self.update(dt)
            self.draw(self.surf)
            screen.blit(self.surf, (0, 0))
            pygame.display.flip()

    def record_mp4(self, path: str) -> None:
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = FPS * 15
        for i in range(frames):
            self.update(1.0 / FPS)
            self.draw(self.surf)
            proc.stdin.write(pygame.image.tostring(self.surf, "RGB"))
            if i % 30 == 0:
                print(f"frame {i}/{frames}", flush=True)
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed: {rc}")
        print("wrote", path)


def main() -> None:
    record = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
    play = "--play" in sys.argv
    if record or not play:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    g = Game(record or not play)
    if record or not play:
        out = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/AMMOLITE_ORBIT_ElbowOS.mp4")
        g.record_mp4(out)
    else:
        g.play()
    pygame.quit()


if __name__ == "__main__":
    main()
