import pygame
from pygame import mixer
import serial
import sys
import random
import time

pygame.init() 
# ================= CONFIG (SAME AS YOURS) =================
DE1_PORT_NAME = 'COM5'
USE_DE1 = True
BAUD = 115200

BOARD_SIZE = 100
GRID_SIZE = 10
CELL_SIZE = 50

WIDTH = CELL_SIZE * GRID_SIZE
HEIGHT = CELL_SIZE * GRID_SIZE + 100 # Extra space for UI
# ==========================================================

# --- RETRO PIXEL PALETTE ---
COLOR_BG      = (20, 20, 25)    # Dark Blue-Black
COLOR_CELL1   = (40, 40, 60)    # Dark Cell
COLOR_CELL2   = (60, 60, 80)    # Light Cell
COLOR_TEXT    = (255, 255, 255) # White
COLOR_PLAYER  = (255, 236, 39)  # Pixel Yellow
COLOR_PLAYER2 = (0, 150, 255)
COLOR_SNAKE   = (255, 0, 68)    # Retro Red
COLOR_LADDER  = (0, 228, 54)    # Retro Green
COLOR_BORDER  = (10, 10, 10)    # Deep Black

# --- SOUND AND MUSIC ---
roll_sound = pygame.mixer.Sound("dice.wav")
ladder_sound = pygame.mixer.Sound("bell.wav")
snake_sound = pygame.mixer.Sound("snake.wav")
win_sound = pygame.mixer.Sound("win.wav")

# Game Modes: "MENU", "PVP", "AI"
game_mode = "MENU" 
ai_timer = 0 # To make the AI wait before rolling

# ---------- SERIAL (KEEPING YOUR WORKING CODE) ----------
ser_de1 = None
if USE_DE1:
    try:
        ser_de1 = serial.Serial(DE1_PORT_NAME, BAUD, timeout=0.01)
        print(f">> Connected to DE1 on {DE1_PORT_NAME}")
    except Exception as e:
        print(">> UART failed, keyboard mode:", e)
        USE_DE1 = False

def get_input():
    if USE_DE1 and ser_de1.in_waiting > 0:
        try:
            c = ser_de1.read().decode(errors='ignore')
            if c == '1':     # ROLL SIGNAL FROM YOUR BOARD
                return "ROLL"
            if c == '2': 
                win_sound.stop()
                return "RESTART"
            if c == '3': return "SET_PVP"
            if c == '4': return "SET_AI"
        except:
            pass

    for event in pygame.event.get():
        if event.type == pygame.QUIT: pygame.quit(); sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE: return "ROLL"
            if event.key == pygame.K_r: return "RESTART"
    return None

# ---------- GAME DATA ----------
snakes = {16: 6, 47: 26, 49: 11, 56: 53, 62: 19, 64: 60, 87: 24, 93: 73, 95: 75, 98: 78}
ladders = {1: 38, 4: 14, 9: 31, 21: 42, 28: 84, 36: 44, 51: 67, 71: 91, 80: 100}

# ---------- PYGAME SETUP ----------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("RETRO DE1 SNAKES & LADDERS")
# Use a blocky system font
font = pygame.font.SysFont("Courier New", 18, bold=True)
font_large = pygame.font.SysFont("Courier New", 32, bold=True)
clock = pygame.time.Clock()

player_pos = 1
last_roll = None
message = "K2 = AI | K1 = PvP"

# ---------- HELPERS ----------
def board_to_xy(pos):
    row = (pos - 1) // GRID_SIZE
    col = (pos - 1) % GRID_SIZE
    if row % 2 == 1:
        col = GRID_SIZE - 1 - col
    x = col * CELL_SIZE
    y = (HEIGHT - 100) - (row + 1) * CELL_SIZE
    return x, y

def draw_retro_board():
    for i in range(1, 101):
        x, y = board_to_xy(i)
        rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
        
        # Alternating "Checkered" Pixel Pattern
        color = COLOR_CELL1 if (i // 1 + i // 10) % 2 == 0 else COLOR_CELL2
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, COLOR_BORDER, rect, 2) # Pixel outline
        
        # Tile Number
        num_txt = font.render(str(i), True, (100, 100, 120))
        screen.blit(num_txt, (x + 5, y + 5))

def draw_entities():
    # Draw Ladders as thick pixel lines
    for start, end in ladders.items():
        s_x, s_y = board_to_xy(start)
        e_x, e_y = board_to_xy(end)
        pygame.draw.line(screen, COLOR_LADDER, 
                         (s_x + 25, s_y + 25), (e_x + 25, e_y + 25), 8)
        
    # Draw Snakes as thick pixel lines
    for start, end in snakes.items():
        s_x, s_y = board_to_xy(start)
        e_x, e_y = board_to_xy(end)
        pygame.draw.line(screen, COLOR_SNAKE, 
                         (s_x + 25, s_y + 25), (e_x + 25, e_y + 25), 8)

def draw_pixel_player(x, y):
    player_rect = (x + 10, y + 10, 30, 30)
    pygame.draw.rect(screen, COLOR_BORDER, (x + 8, y + 8, 34, 34))
    pygame.draw.rect(screen, COLOR_PLAYER, player_rect)
    pygame.draw.rect(screen, COLOR_BORDER, (x + 25, y + 15, 5, 5))

def draw_pixel_player2(x, y):
    player_rect = (x + 10, y + 10, 30, 30)
    pygame.draw.rect(screen, COLOR_BORDER, (x + 8, y + 8, 34, 34))
    pygame.draw.rect(screen, COLOR_PLAYER2, player_rect) # Assuming COLOR_PLAYER2 exists
    pygame.draw.rect(screen, COLOR_BORDER, (x + 25, y + 15, 5, 5))

state1 = True
state2 = False
pos1 = 0
pos2 = 0

v_x1, v_y1 = board_to_xy(pos1)
v_x2, v_y2 = board_to_xy(pos2)

check_event1 = False
check_event2 = False

# Set the animation speed (lower is slower/smoother)
# 0.1 to 0.2 usually looks best for a retro feel
lerp_speed = 0.15

def updpos(pos, playnum):
    global pos1, pos2
    if playnum == 1:
        pos1 = pos
    elif playnum == 2:
        pos2 = pos

def switch(s1, s2):
    global state1, state2
    if s1 == True and s2 == False:
        state1 = False
        state2 = True
    else:
        state1 = True
        state2 = False

packet_timer = 0
pending_packet = None
# ---------- MAIN LOOP ----------
while True:
    command = get_input()

    # --- RESTART LOGIC ---
    if command == "RESTART":
        updpos(0, 1)
        updpos(0, 2)
        v_x1, v_y1 = board_to_xy(1)
        v_x2, v_y2 = board_to_xy(1)
        state1 = True
        state2 = False
        color = COLOR_TEXT
        last_roll = 0
        if USE_DE1 and ser_de1:
            # Tell the board to clear the HEX displays
            ser_de1.write(bytes([255, 0, 1, 0, 0])) 
            ser_de1.write(bytes([255, 0, 2, 0, 0]))
        game_mode = "MENU"
        time.sleep(0.5)  # Small delay to avoid multiple restarts
        message = "K2 = AI | K1 = PvP"

    if game_mode == "MENU":
        color = COLOR_TEXT
        if command == "SET_PVP":
            game_mode = "PVP"
            message = "PLAYER 1 TURN"
        elif command == "SET_AI":
            game_mode = "AI"
            message = "AI MODE: PLAYER 1 TURN"
    
    else:
        if state1 == True and state2 == False:
            player = 1
            player_pos = pos1
            #color = COLOR_PLAYER2
        else:
            player = 2
            player_pos = pos2
            #color = COLOR_PLAYER

        if game_mode == "AI" and state2 and not check_event2:
            # Check if P2 visual square has finished moving before AI rolls
            if abs(v_x2 - board_to_xy(pos2)[0]) < 1:
                ai_timer += 1
                if ai_timer > 53: # less than 2 seconds
                    command = "ROLL"
                    ai_timer = 0

        if command == "ROLL" and player_pos < 100:
            roll_sound.play()
            roll = random.randint(1, 6)
            last_roll = roll
            
            player_pos += roll
            if player_pos > 100:
                player_pos = 200 - player_pos
                
            message = f"ROLLED {roll}"
            color = COLOR_PLAYER if player == 1 else COLOR_PLAYER2 # Sets color to the player
            
            # Update logical position for animation to start
            updpos(player_pos, player)
            
            # Set flag to check for snakes/ladders AFTER arrival
            if player == 1: check_event1 = True
            else: check_event2 = True

            # Send to Board
            if USE_DE1 and ser_de1:
                tens = player_pos // 10
                ones = player_pos % 10
                pending_packet = [255, roll, player, tens, ones]
                packet_timer = 10 

            switch(state1, state2)

        if packet_timer > 0:
            packet_timer -= 1
            if packet_timer == 0 and pending_packet:
                ser_de1.write(bytes(pending_packet))
                pending_packet = None

    # -- ANIMATION LOGIC --
    target_x1, target_y1 = board_to_xy(pos1)
    target_x2, target_y2 = board_to_xy(pos2)

    v_x1 += (target_x1 - v_x1) * lerp_speed
    v_y1 += (target_y1 - v_y1) * lerp_speed
    v_x2 += (target_x2 - v_x2) * lerp_speed
    v_y2 += (target_y2 - v_y2) * lerp_speed

    # --- STAGE 2: THE EVENT (Checks for Snake/Ladder after arriving) ---
    # Check Player 1 Arrival
    if check_event1 and abs(v_x1 - target_x1) < 1 and abs(v_y1 - target_y1) < 1:
        if pos1 in ladders:
            pos1 = ladders[pos1]
            message = "P1 GOING UP THE LADDER!"
            ladder_sound.play()
            if USE_DE1: ser_de1.write(bytes([255, last_roll, 1, pos1//10, pos1%10]))
        elif pos1 in snakes:
            pos1 = snakes[pos1]
            message = "A SNAKE BIT P1!"
            snake_sound.play()
            if USE_DE1: ser_de1.write(bytes([255, last_roll, 1, pos1//10, pos1%10]))
        check_event1 = False # Reset flag

    # Check Player 2 Arrival
    if check_event2 and abs(v_x2 - target_x2) < 1 and abs(v_y2 - target_y2) < 1:
        if pos2 in ladders:
            pos2 = ladders[pos2]
            message = "P2 GOING UP THE LADDER!"
            ladder_sound.play()
            if USE_DE1: ser_de1.write(bytes([255, last_roll, 2, pos2//10, pos2%10]))
        elif pos2 in snakes:
            pos2 = snakes[pos2]
            message = "A SNAKE BIT P2!"
            snake_sound.play()
            if USE_DE1: ser_de1.write(bytes([255, last_roll, 2, pos2//10, pos2%10]))
        check_event2 = False

    if pos1 == 100:
        win_sound.play()
        message = "P1 WINS!"
    elif pos2 == 100:
        win_sound.play()
        message = "P2 WINS!"

    # -- DRAWING --
    screen.fill(COLOR_BG)
    draw_retro_board()
    draw_entities()
    
    draw_pixel_player(v_x1, v_y1)
    draw_pixel_player2(v_x2, v_y2)

    # UI Area at bottom
    ui_height = 100
    ui_top = HEIGHT - ui_height
    ui_rect = pygame.Rect(0, ui_top, WIDTH, ui_height)
    pygame.draw.rect(screen, COLOR_BORDER, ui_rect)
    pygame.draw.rect(screen, COLOR_CELL2, ui_rect, 4)

    # 1. Render the main game message
    text_msg = font_large.render(message, True, color)
    
    # 2. Get the rectangle of the text and set its center 
    # This automatically calculates the correct X to make it centered
    msg_rect = text_msg.get_rect(center=(WIDTH // 2, ui_top + 50))
    
    # 3. Blit using the rect instead of a coordinate tuple
    screen.blit(text_msg, msg_rect)

    pygame.display.flip()
    clock.tick(30)