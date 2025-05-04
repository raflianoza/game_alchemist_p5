import pygame
import math
import os

os.system("clear")

# ----- CONSTANTS -----
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 600
PLAYER_SIZE = 50
PLAYER_SPEED = 2.4
PLAYER_MAX_HEALTH = 100
ENEMY_SIZE = 80
ENEMY_MAX_HEALTH = 100
ENEMY_SPEED = 2
ENEMY_Y = SCREEN_HEIGHT // 3
PROJECTILE_SIZE = 10
PROJECTILE_SPEED = 6
BACKGROUND_PATH = './assets/bg.png'
INVENTORY_PATH = './assets/inventory.png'
CHAR_PATH = './assets/char.png'
ENEMY_PATH = './assets/enemy.png'
WIN_IMAGE_PATH = './assets/win.png'
CURSOR_PATH = './assets/cursor.png'
ATTACK_COOLDOWN = 500
ENEMY_ATTACK_COOLDOWN = 2000
RED_SHOT_PATTERN = ['q'] + ['w'] * 4
STUN_COMBO_PATTERN = ['e','e','r']
INVALID_DISPLAY = 500         # ms for 'INVALID'
BLINK_DURATION = 4000        # ms enemy blink before win
BLINK_INTERVAL = 500         # ms blink interval for enemy
WIN_BLINK_DURATION = 10000   # ms win.png blink
WIN_BLINK_INTERVAL = 1000    # ms blink interval for win.png
INVENTORY_SCALE = 1.5
HP_BAR_HEIGHT = 10
HP_BAR_MARGIN = 5

# ----- INIT -----
pygame.init()
font = pygame.font.Font(None, 24)

# ----- CLASSES -----
class Player:
    def __init__(self, sprite):
        self.rect = sprite.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        self.target = None
        self.health = PLAYER_MAX_HEALTH
        self.sprite = sprite
    def update(self):
        if self.target:
            dx = self.target[0] - self.rect.centerx
            dy = self.target[1] - self.rect.centery
            dist = math.hypot(dx, dy) or 1
            if dist > PLAYER_SPEED:
                self.rect.x += dx/dist * PLAYER_SPEED
                self.rect.y += dy/dist * PLAYER_SPEED
            else:
                self.target = None
    def draw(self, surface):
        surface.blit(self.sprite, self.rect)
    def set_target(self, pos):
        self.target = pos

class Enemy:
    def __init__(self, sprite):
        self.rect = sprite.get_rect(midtop=(SCREEN_WIDTH//2, ENEMY_Y))
        self.health = ENEMY_MAX_HEALTH
        self.sprite = sprite
        self.alive = True
        self.dir = 1
        self.stunned = False
        self.stun_time = 0
    def update(self):
        now = pygame.time.get_ticks()
        if self.stunned and now - self.stun_time < 1000:
            return
        self.stunned = False
        if not self.alive:
            return
        self.rect.x += ENEMY_SPEED * self.dir
        if self.rect.right >= SCREEN_WIDTH or self.rect.left <= 0:
            self.dir *= -1
    def draw(self, surface, visible=True):
        # Draw sprite even if alive=False, during blink phase
        if not visible:
            return
        surface.blit(self.sprite, self.rect)
        # Draw HP bar only if alive
        if self.alive:
            bx, by = self.rect.x, self.rect.y - HP_BAR_HEIGHT - HP_BAR_MARGIN
            bw = self.rect.width
            pygame.draw.rect(surface, (200,0,0), (bx,by,bw,HP_BAR_HEIGHT))
            ratio = max(self.health, 0)/ENEMY_MAX_HEALTH
            pygame.draw.rect(surface, (0,200,0), (bx,by,int(bw*ratio),HP_BAR_HEIGHT))
            pygame.draw.rect(surface, (0,0,0), (bx,by,bw,HP_BAR_HEIGHT),1)

class Projectile:
    def __init__(self, start, target, color, damage, slow=False, wide=False):
        size = PROJECTILE_SIZE * (2 if wide else 1)
        self.rect = pygame.Rect(start[0], start[1], size, size)
        dx = target[0] - start[0]
        dy = target[1] - start[1]
        dist = math.hypot(dx,dy) or 1
        speed = PROJECTILE_SPEED * (0.5 if slow else 1)
        self.vx = dx/dist * speed; self.vy = dy/dist * speed
        self.color = color; self.damage = damage
        self.is_stun = slow and wide
    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy
    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)

# ----- MAIN -----
def main():
    pygame.display.set_caption("The Alchemist")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    # Assets
    bg = pygame.transform.scale(pygame.image.load(BACKGROUND_PATH), (SCREEN_WIDTH, SCREEN_HEIGHT))
    inv_img = pygame.image.load(INVENTORY_PATH).convert_alpha()
    iw, ih = inv_img.get_size()
    inv = pygame.transform.scale(inv_img, (int(iw*INVENTORY_SCALE), int(ih*INVENTORY_SCALE)))
    inv_w, inv_h = inv.get_size()
    inv_x, inv_y = (SCREEN_WIDTH-inv_w)//2, SCREEN_HEIGHT-inv_h-10
    char = pygame.transform.scale(pygame.image.load(CHAR_PATH), (PLAYER_SIZE, PLAYER_SIZE))
    enem_sprite = pygame.transform.scale(pygame.image.load(ENEMY_PATH), (ENEMY_SIZE, ENEMY_SIZE))
    win_img = pygame.image.load(WIN_IMAGE_PATH).convert_alpha()
    win_rect = win_img.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
    cursor = pygame.transform.scale(pygame.image.load(CURSOR_PATH), (16,16))
    pygame.mouse.set_visible(False)

    player = Player(char)
    enemy = Enemy(enem_sprite)
    p_list, e_list = [], []
    combo_buf, combo_text = [], ''
    last_attack = last_enemy = 0
    win_time = None
    invalid = False; invalid_time = 0
    attack_mode = False; attack_available = 0

    while True:
        now = pygame.time.get_ticks()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); return
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3:
                player.set_target(ev.pos)
            if ev.type == pygame.KEYDOWN:
                key, uni = ev.key, ev.unicode
                if key == pygame.K_x:
                    # Cast combos
                    if combo_buf == RED_SHOT_PATTERN:
                        mx,my = pygame.mouse.get_pos()
                        p_list.append(Projectile((player.rect.centerx,player.rect.centery),(mx,my),(255,0,0),20))
                    elif combo_buf == STUN_COMBO_PATTERN:
                        mx,my = pygame.mouse.get_pos()
                        p_list.append(Projectile((player.rect.centerx,player.rect.centery),(mx,my),(128,128,128),0,slow=True,wide=True))
                    elif len(combo_buf)==5 and combo_buf[:3]==['w','w','r'] and combo_buf[3]=='shift' and combo_buf[4].isdigit():
                        attack_available = int(combo_buf[4]); attack_mode = True
                    else:
                        invalid = True; invalid_time = now
                    combo_buf.clear(); combo_text = ''
                elif key in (pygame.K_q,pygame.K_w,pygame.K_r,pygame.K_e,pygame.K_LSHIFT,pygame.K_RSHIFT) or uni.isdigit():
                    if key == pygame.K_q:
                        combo_buf.append('q'); combo_text += 'c'
                    elif key == pygame.K_w:
                        combo_buf.append('w'); combo_text += 'h'
                    elif key == pygame.K_r:
                        combo_buf.append('r'); combo_text += 'o'
                    elif key == pygame.K_e:
                        combo_buf.append('e'); combo_text += 'n'
                    elif key in (pygame.K_LSHIFT,pygame.K_RSHIFT):
                        combo_buf.append('shift')
                    elif uni.isdigit() and uni!='0':
                        combo_buf.append(uni); combo_text += uni
                elif key == pygame.K_ESCAPE:
                    combo_buf.clear(); combo_text=''; attack_mode=False; attack_available=0

        # Attack execution
        if attack_mode and attack_available>0 and pygame.mouse.get_pressed()[0] and now-last_attack>=ATTACK_COOLDOWN:
            mx,my = pygame.mouse.get_pos()
            p_list.append(Projectile((player.rect.centerx,player.rect.centery),(mx,my),(0,0,255),10))
            attack_available -= 1; last_attack = now
            if attack_available <= 0:
                attack_mode = False

        # Updates
        player.update(); enemy.update()
        # Enemy shoot
        if enemy.alive and not enemy.stunned and now-last_enemy>=ENEMY_ATTACK_COOLDOWN:
            e_list.append(Projectile((enemy.rect.centerx,enemy.rect.centery),(player.rect.centerx,player.rect.centery),(255,0,0),2))
            last_enemy = now
        # Projectile collisions
        for p in p_list[:]:
            p.update()
            if not screen.get_rect().colliderect(p.rect): p_list.remove(p)
            elif enemy.rect.colliderect(p.rect):
                if p.is_stun:
                    enemy.stunned = True; enemy.stun_time = now
                else:
                    enemy.health -= p.damage
                p_list.remove(p)
                if enemy.health <= 0 and enemy.alive:
                    enemy.alive = False; win_time = now
        for eproj in e_list[:]:
            eproj.update()
            if not screen.get_rect().colliderect(eproj.rect): e_list.remove(eproj)
            elif eproj.rect.colliderect(player.rect): player.health -= eproj.damage; e_list.remove(eproj)

        # Draw
        screen.blit(bg, (0,0))
        player.draw(screen)
        # Enemy blink then win blink
        if win_time is not None:
            elapsed = now - win_time
            if elapsed < BLINK_DURATION:
                if (elapsed // BLINK_INTERVAL) % 2 == 0:
                    enemy.draw(screen, visible=True)
            elif elapsed < BLINK_DURATION + WIN_BLINK_DURATION:
                if ((elapsed - BLINK_DURATION) // WIN_BLINK_INTERVAL) % 2 == 0:
                    screen.blit(win_img, win_rect)
            # after blink durations, nothing stays on screen
        else:
            enemy.draw(screen, visible=True)

        for p in p_list: p.draw(screen)
        for eproj in e_list: eproj.draw(screen)

        # Inventory & HP
        screen.blit(inv, (inv_x, inv_y))
        pbx, pby = inv_x, inv_y - HP_BAR_HEIGHT - HP_BAR_MARGIN
        pygame.draw.rect(screen, (200,0,0), (pbx,pby,inv_w,HP_BAR_HEIGHT))
        pygame.draw.rect(screen, (0,200,0), (pbx,pby,int(inv_w*(player.health/PLAYER_MAX_HEALTH)),HP_BAR_HEIGHT))
        pygame.draw.rect(screen, (0,0,0), (pbx,pby,inv_w,HP_BAR_HEIGHT),1)

        # INVALID indicator
        if invalid and now - invalid_time <= INVALID_DISPLAY:
            t = font.render('INVALID', True, (255,0,0))
            screen.blit(t, t.get_rect(topright=(SCREEN_WIDTH-10,30)))
        else:
            invalid = False

        # Combo text & cursor
        txt = font.render(combo_text, True, (255,255,255))
        screen.blit(txt, txt.get_rect(topright=(SCREEN_WIDTH-10,10)))
        mx, my = pygame.mouse.get_pos()
        screen.blit(cursor, (mx-8, my-8))

        pygame.display.flip()
        clock.tick(60)

if __name__=='__main__':
    main()
