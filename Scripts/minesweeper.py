from kandinsky import *
from ion import *
from random import *
from time import *
from math import *

# =====================
# CONFIG
# =====================

SCREEN_WIDTH, SCREEN_HEIGHT = 320, 222

HUD_HEIGHT = 22
GRID_WIDTH, GRID_HEIGHT = 16, 10
TILE_SIZE = 20

MINE_AMOUNT = 25

best_score = -1

# =====================
# INPUT
# =====================

class TapInputKey:
    key_code: int
    is_down: bool

    def __init__(self, key_code):
        self.key_code = key_code
        self.is_down = False
    
    def is_triggered(self) -> bool:
        if keydown(self.key_code):
            if not self.is_down:
                self.is_down = True
                return True
        else:
            self.is_down = False
        
        return False

class RepeatingInputKey:
    key_code: int
    initial_delay: float
    repeat_delay: float

    is_down: bool
    next_time: float

    def __init__(self, key_code, initial_delay, repeat_delay):
        self.key_code = key_code
        self.initial_delay = initial_delay
        self.repeat_delay = repeat_delay
        
        self.is_down = False
        self.next_time: float = 0.0

    def is_triggered(self) -> bool:
        now = monotonic()

        is_triggered = False

        if keydown(self.key_code):
            if not self.is_down:
                # Instant trigger on tap
                is_triggered = True

                self.is_down = True
                self.next_time = now + self.initial_delay
            
            elif now > self.next_time:
                # Repeated trigger
                is_triggered = True

                self.next_time = now + self.repeat_delay

        else:
            self.is_down = False
        
        return is_triggered

class DPadSelector:
    def __init__(self, max_x, max_y):
        self.UP_KEY = RepeatingInputKey(KEY_UP, 0.25, 0.05)
        self.DOWN_KEY = RepeatingInputKey(KEY_DOWN, 0.25, 0.05)
        self.LEFT_KEY = RepeatingInputKey(KEY_LEFT, 0.25, 0.05)
        self.RIGHT_KEY = RepeatingInputKey(KEY_RIGHT, 0.25, 0.05)

        self.x = 0
        self.y = 0
        self.max_x = max_x
        self.max_y = max_y
    
    def update(self):
        dx, dy = 0, 0

        if self.UP_KEY.is_triggered(): dy -= 1
        if self.DOWN_KEY.is_triggered(): dy += 1
        if self.LEFT_KEY.is_triggered(): dx -= 1
        if self.RIGHT_KEY.is_triggered(): dx += 1

        self.x = Util.clamp(self.x + dx, 0, self.max_x)
        self.y = Util.clamp(self.y + dy, 0, self.max_y)

        return (self.x, self.y)

class MinesweeperInputs:
    UNCOVER_KEY = TapInputKey(KEY_TOOLBOX)
    FLAG_KEY = TapInputKey(KEY_BACKSPACE)
    OK_KEY = TapInputKey(KEY_OK)

# =====================
# UTIL
# =====================

class Util:
    @staticmethod
    def clamp(value: int, minv: int, maxv: int) -> int:
        return max(minv, min(value, maxv))

# =====================
# GAME LOGIC
# =====================

class Tile:
    def __init__(self):
        self.is_mined = False
        self.neighboring_mine_count = 0

        self.is_uncovered = False
        self.is_flagged = False
        # Start with true to draw once at beginning
        self.needs_redraw = True

class GameState:
    PLAYING = 0
    WON = 1
    LOST = 2

class MinesweeperBoard:
    width: int
    height: int
    tiles: list[list[Tile]]

    game_state: GameState
    mine_amount: int

    uncovered_tiles_amount: int
    flags_left: int

    is_first_click: bool

    def __init__(self, width, height, mine_amount):
        self.width = width
        self.height = height
        self.tiles = [[Tile() for _ in range(width)] for _ in range(height)]

        self.game_state = GameState.PLAYING
        self.mine_amount = mine_amount

        self.uncovered_tiles_amount = 0
        self.flags_left = mine_amount

        self.is_first_click = True
    
    # --- ACCESS TILES ---

    def is_within_bounds(self, x, y) -> bool:
        within_x = x >= 0 and x < self.width
        within_y = y >= 0 and y < self.height
        return within_x and within_y
   
    def get_tile(self, x, y) -> Tile:
        if self.is_within_bounds(x, y):
            return self.tiles[y][x]
        else:
            return None
        
    # --- GENERATING MINES ---

    def get_neighbors(self, x, y) -> list[tuple[int, int]]:
        adj_pos = [
            (x + 1, y), (x - 1, y), # Left / Right
            (x, y + 1), (x, y - 1), # Top / Bottom
            (x - 1, y + 1), (x - 1, y - 1), # Leftmost corners
            (x + 1, y + 1), (x + 1, y - 1) # Rightmost corners
        ]

        valid_adj_pos = []

        for pos in adj_pos:
            x, y = pos
            if self.is_within_bounds(x, y):
                valid_adj_pos.append(pos)

        return valid_adj_pos

    def generate_mines(self, first_click_x, first_click_y) -> None:
        counter: int = 0

        while counter < self.mine_amount:
            x = randint(0, self.width - 1)
            y = randint(0, self.height - 1)
            tile = self.get_tile(x, y)
           
            if tile.is_mined:
                continue
            
            # Don't place mines around clicked area
            if abs(first_click_x - x) <= 1 and abs(first_click_y - y) <= 1:
                continue

            tile.is_mined = True

            # Increment neighboring mine counter
            for nx, ny in self.get_neighbors(x, y):
                tile = self.get_tile(nx, ny)
                tile.neighboring_mine_count += 1

            counter += 1

    # --- PLAYER ACTIONS ---

    def uncover_tile(self, start_x, start_y):
        tile = self.get_tile(start_x, start_y)

        # Can't uncover
        if tile.is_uncovered or tile.is_flagged:
            return

        # Generate mines on first click
        if self.is_first_click:
            self.generate_mines(start_x, start_y)
            self.is_first_click = False

        queue = [(start_x, start_y)]
        visited = set()

        while queue:
            x, y = queue.pop(0)

            if (x, y) in visited:
                continue
            visited.add((x, y))

            tile = self.get_tile(x, y)

            if tile.is_uncovered or tile.is_flagged:
                continue

            tile.is_uncovered = True
            tile.needs_redraw = True
            self.uncovered_tiles_amount += 1

            # Lose if mine hit
            if tile.is_mined:
                self.game_state = GameState.LOST
                return

            # Expand only if empty
            if tile.neighboring_mine_count == 0:
                for nx, ny in self.get_neighbors(x, y):
                    queue.append((nx, ny))

        # Win check
        if self.is_game_won():
            self.game_state = GameState.WON

    def flag_tile(self, x, y) -> None:
        tile = self.get_tile(x, y)

        if tile.is_uncovered:
            return

        # Remove flag
        if tile.is_flagged:
            tile.is_flagged = False
            self.flags_left += 1
        
        # Place flag
        else:
            # Can't place more flags
            if self.flags_left == 0:
                return
            tile.is_flagged = True
            self.flags_left -= 1
        
        tile.needs_redraw = True
    
    def reset(self) -> None:
        self.tiles = [[Tile() for _ in range(self.width)] for _ in range(self.height)]
        self.game_state = GameState.PLAYING
        self.uncovered_tiles_amount = 0
        self.flags_left = self.mine_amount
        self.is_first_click = True
    
    def is_game_won(self) -> bool:
        tiles_amount: int = self.width * self.height
        return (tiles_amount - self.mine_amount == self.uncovered_tiles_amount)

# =====================
# RENDERING
# =====================

# --- Util ---

class SpriteLibrary:
    CLOCK_SPRITE = (20, 20, bytes([
        0b00000000, 0b00000000, 0b00000000,
        0b00000000, 0b00000000, 0b00000000,
        0b00000000, 0b11110000, 0b00000000,
        0b00000011, 0b11111100, 0b00000000,
        0b00000111, 0b00001110, 0b00000000,
        0b00001100, 0b00000011, 0b00000000,
        0b00011000, 0b01100001, 0b10000000,
        0b00011000, 0b01100001, 0b10000000,
        0b00110000, 0b01100000, 0b11000000,
        0b00110000, 0b01111110, 0b11000000,
        0b00110000, 0b01111110, 0b11000000,
        0b00110000, 0b00000000, 0b11000000,
        0b00011000, 0b00000001, 0b10000000,
        0b00011000, 0b00000001, 0b10000000,
        0b00001100, 0b00000011, 0b00000000,
        0b00000111, 0b00001110, 0b00000000,
        0b00000011, 0b11111100, 0b00000000,
        0b00111111, 0b11111111, 0b11000000,
        0b00111111, 0b11111111, 0b11000000,
        0b00000000, 0b00000000, 0b00000000
    ]))

    FLAG_SPRITE = (20, 20, bytes([
        0b00000000, 0b00000000, 0b00000000,
        0b00000000, 0b00000000, 0b00000000,
        0b00001100, 0b00000000, 0b00000000,
        0b00001111, 0b10000000, 0b00000000,
        0b00001111, 0b11111000, 0b00000000,
        0b00001111, 0b11111111, 0b00000000,
        0b00001111, 0b11111111, 0b11000000,
        0b00001111, 0b11111111, 0b11000000,
        0b00001111, 0b11111111, 0b00000000,
        0b00001111, 0b11110000, 0b00000000,
        0b00001111, 0b00000000, 0b00000000,
        0b00001100, 0b00000000, 0b00000000,
        0b00001100, 0b00000000, 0b00000000,
        0b00001100, 0b00000000, 0b00000000,
        0b00001100, 0b00000000, 0b00000000,
        0b00001100, 0b00000000, 0b00000000,
        0b00011110, 0b00000000, 0b00000000,
        0b00011110, 0b00000000, 0b00000000,
        0b00000000, 0b00000000, 0b00000000,
        0b00000000, 0b00000000, 0b00000000
    ]))

    MINE_SPRITE = (20, 20, bytes([
        0b00000000, 0b00000000, 0b00000000,
        0b00000000, 0b00000000, 0b00000000,
        0b00000000, 0b11110000, 0b00000000,
        0b00000011, 0b11111100, 0b00000000,
        0b00000111, 0b11111110, 0b00000000,
        0b00001111, 0b11111111, 0b00000000,
        0b00011111, 0b11111111, 0b10000000,
        0b00011111, 0b11111111, 0b10000000,
        0b00111111, 0b11111111, 0b11000000,
        0b00111111, 0b11111111, 0b11000000,
        0b00111111, 0b11111111, 0b11000000,
        0b00111111, 0b11111111, 0b11000000,
        0b00011111, 0b11111111, 0b10000000,
        0b00011111, 0b11111111, 0b10000000,
        0b00001111, 0b11111111, 0b00000000,
        0b00000111, 0b11111110, 0b00000000,
        0b00000011, 0b11111100, 0b00000000,
        0b00000000, 0b11110000, 0b00000000,
        0b00000000, 0b00000000, 0b00000000,
        0b00000000, 0b00000000, 0b00000000
    ]))

    NUMBER_SPRITES = [
    (6, 9, bytes([
        0b01111000,
        0b11001100,
        0b11001100,
        0b11001100,
        0b11001100,
        0b11001100,
        0b11001100,
        0b11001100,
        0b01111000
    ])),
    (6, 9, bytes([
        0b11110000,
        0b00110000,
        0b00110000,
        0b00110000,
        0b00110000,
        0b00110000,
        0b00110000,
        0b00110000,
        0b11111100
    ])),
    (6, 9, bytes([
        0b01111000,
        0b11001100,
        0b00001100,
        0b00001100,
        0b00011000,
        0b00110000,
        0b01100000,
        0b11000000,
        0b11111100
    ])),
    (6, 9, bytes([
        0b01111000,
        0b11001100,
        0b00001100,
        0b00001100,
        0b00111000,
        0b00001100,
        0b00001100,
        0b11001100,
        0b01111000
    ])),
    (6, 9, bytes([
        0b00111100,
        0b00101100,
        0b01101100,
        0b01001100,
        0b11001100,
        0b11111100,
        0b00001100,
        0b00001100,
        0b00001100
    ])),
    (6, 9, bytes([
        0b11111100,
        0b11001100,
        0b11000000,
        0b11000000,
        0b11111000,
        0b00001100,
        0b00001100,
        0b11001100,
        0b01111000
    ])),
    (6, 9, bytes([
        0b01111000,
        0b11001100,
        0b11000000,
        0b11000000,
        0b11111000,
        0b11001100,
        0b11001100,
        0b11001100,
        0b01111000
    ])),
    (6, 9, bytes([
        0b11111100,
        0b11001100,
        0b00001100,
        0b00011000,
        0b00011000,
        0b00110000,
        0b00110000,
        0b01100000,
        0b01100000
    ])),
    (6, 9, bytes([
        0b01111000,
        0b11001100,
        0b11001100,
        0b11001100,
        0b01111000,
        0b11001100,
        0b11001100,
        0b11001100,
        0b01111000
    ])),
    (6, 9, bytes([
        0b01111000,
        0b11001100,
        0b11001100,
        0b11001100,
        0b01111100,
        0b00001100,
        0b00001100,
        0b11001100,
        0b01111000
    ]))]

    MINESWEEPER_SPRITE = (51, 7, bytes([
        0b10001010, 0b00000000, 0b00000000, 0b00000000, 0b00000000, 0b00000000, 0b00000000,
        0b11011000, 0b11100011, 0b00011010, 0b00100110, 0b00110011, 0b10001100, 0b10100000,
        0b10101010, 0b10010100, 0b10100010, 0b00101001, 0b01001010, 0b01010010, 0b11000000,
        0b10001010, 0b10010111, 0b10010010, 0b10101111, 0b01111010, 0b01011110, 0b10000000,
        0b10001010, 0b10010100, 0b00001010, 0b10101000, 0b01000011, 0b10010000, 0b10000000,
        0b10001010, 0b10010011, 0b00110001, 0b01000110, 0b00110010, 0b00001100, 0b10000000,
        0b00000000, 0b00000000, 0b00000000, 0b00000000, 0b00000010, 0b00000000, 0b00000000
    ]))

    PLAY_SPRITE = (16, 7, bytes([
        0b11100100, 0b00000000,
        0b10010100, 0b11001001,
        0b10010100, 0b00101001,
        0b11100100, 0b11101001,
        0b10000101, 0b00100111,
        0b10000100, 0b11100001,
        0b00000000, 0b00000110
    ]))

    RESET_SCORE_SPRITE = (48, 7, bytes([
        0b11100000, 0b00000000, 0b00010000, 0b00000000, 0b00000000, 0b00000000,
        0b10010011, 0b00011001, 0b10011000, 0b00011001, 0b11001100, 0b10100110,
        0b10010100, 0b10100010, 0b01010000, 0b00100010, 0b00010010, 0b11001001,
        0b11100111, 0b10010011, 0b11010000, 0b00010010, 0b00010010, 0b10001111,
        0b10010100, 0b00001010, 0b00010000, 0b00001010, 0b00010010, 0b10001000,
        0b10010011, 0b00110001, 0b10001000, 0b00110001, 0b11001100, 0b10000110,
        0b00000000, 0b00000000, 0b00000000, 0b00000000, 0b00000000, 0b00000000
    ]))

    QUIT_SPRITE = (15, 7, bytes([
        0b01110000, 0b00010100,
        0b10001010, 0b01000110,
        0b10001010, 0b01010100,
        0b10001010, 0b01010100,
        0b10001010, 0b01010100,
        0b01110001, 0b11010010,
        0b00011000, 0b00000000
    ]))

    ARROW_SPRITE = (7, 7, bytes([
        0b01000000,
        0b01100000,
        0b01110000,
        0b01111000,
        0b01110000,
        0b01100000,
        0b01000000
    ]))

    COLORS = {
        # --- GAME ---
        
        # Tile backgrounds
        "covered_1" : (255, 157, 62), # Darker brown
        "covered_2" : (245, 181, 84), # Lighter brown
        "uncovered_1" : (44, 201, 78), # Darker green
        "uncovered_2" : (141, 227, 93), # Lighter green
        "uncovered_border" : (250, 103, 53), # Maroon?
        
        # Tile numbers
        "num_1" : (76, 137, 238), # Light blue
        "num_2" : (11, 157, 95), # Green
        "num_3" : (232, 35, 55), # Red
        "num_4_and_up" : (105, 29, 140), # Purple

        # Other tile sprites
        "flag" : (232, 35, 55), # Red
        "mine" : (232, 35, 55), # Red
        "selection_border" : (255, 245, 122), # Bright yellow creme

        # --- HUD --- 
        "hud_bg" : (35, 124, 128), # Blue
        "hud_flag" : (232, 35, 55), # Red
        "hud_clock" : (105, 29, 140), # Purple
        "hud_numbers" : (4, 5, 25), # Black

        # --- MENU ---
        "menu_bg" : (245, 181, 84), # Orange
        "menu_text" : (75, 8, 67), # Purple
        "menu_numbers" : (75, 8, 67), # Purple
        "menu_arrow" : (75, 8, 67) # Purple
    }

    @staticmethod
    def draw_sprite(x, y, sprite, color, scale=1):
        width, height, data = sprite
        bytes_per_row = (width + 7) // 8

        for row in range(height):
            row_offset = row * bytes_per_row
            col = 0

            while col < width:
                byte = data[row_offset + (col >> 3)]
                mask = 0x80 >> (col & 7)

                if not (byte & mask):
                    col += 1
                    continue

                run_start = col
                while col < width:
                    byte = data[row_offset + (col >> 3)]
                    if not (byte & (0x80 >> (col & 7))):
                        break
                    col += 1

                run_len = col - run_start

                fill_rect(
                    x + run_start * scale,
                    y + row * scale,
                    run_len * scale,
                    scale,
                    color
                )
    
    @staticmethod
    def erase_sprite(x, y, sprite, bg_color, scale=1):
        width, height, _ = sprite
        fill_rect(x, y, width * scale, height * scale, bg_color)

    @staticmethod
    def draw_digit(x, y, digit, color, scale=1):
        SpriteLibrary.draw_sprite(
            x, y, 
            SpriteLibrary.NUMBER_SPRITES[digit],
            color, scale
        )
    
    @staticmethod
    def erase_digit(x, y, bg_color, scale=1):
        SpriteLibrary.erase_sprite(
            x, y, 
            SpriteLibrary.NUMBER_SPRITES[0],
            bg_color, scale
        )

class NumberDisplayer:
    digits: list[int]

    def __init__(self, x, y, color, bg_color, scale, spacing, max_digits):
        self.x = x
        self.y = y
        self.color = color
        self.bg_color = bg_color
        self.scale = scale
        self.spacing = spacing
        self.max_digits = max_digits
        self.digits =[-1 for _ in range(max_digits)]
    
    def update(self, num):
        if num < 0:
            num = 0

        num_str = str(num)

        while len(num_str) < self.max_digits:
            num_str = "0" + num_str

        for i in range(self.max_digits):
            pos_x = self.x + i * self.spacing
            pos_y = self.y
            new_digit = int(num_str[i])
            if self.digits[i] != new_digit:
                SpriteLibrary.erase_digit(pos_x, pos_y, self.bg_color, self.scale)
                SpriteLibrary.draw_digit(pos_x, pos_y, new_digit, self.color, self.scale)
                self.digits[i] = new_digit

# --- Game + Menu --- 

class MinesweeperDisplay:
    BORDER_WEIGHT: int = 2

    def __init__(self, offset_x, offset_y, tile_size):
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.tile_size = tile_size
    
    # --- HELPERS ---

    def get_bg_color(self, board: MinesweeperBoard, x, y):
        tile = board.get_tile(x, y)
        toggle: bool = (x + y) % 2 == 0

        if tile.is_uncovered:
            if toggle:
                return SpriteLibrary.COLORS["uncovered_1"]
            else:
                return SpriteLibrary.COLORS["uncovered_2"]
        else:
            if toggle:
                return SpriteLibrary.COLORS["covered_1"]
            else:
                return SpriteLibrary.COLORS["covered_2"]

    def get_num_color(self, num):
        if num == 1:
            return SpriteLibrary.COLORS["num_1"]
        elif num == 2:
            return SpriteLibrary.COLORS["num_2"]
        elif num == 3:
            return SpriteLibrary.COLORS["num_3"]
        else:
            return SpriteLibrary.COLORS["num_4_and_up"]

    def get_tile_borders(self, board: MinesweeperBoard, x, y):
        borders = [False, False, False, False]

        up_tile = board.get_tile(x, y - 1)
        down_tile = board.get_tile(x, y + 1)
        left_tile = board.get_tile(x - 1, y)
        right_tile = board.get_tile(x + 1, y)

        if up_tile and not up_tile.is_uncovered:
            borders[0] = True
        if down_tile and not down_tile.is_uncovered:
            borders[1] = True
        if left_tile and not left_tile.is_uncovered:
            borders[2] = True
        if right_tile and not right_tile.is_uncovered:
            borders[3] = True
        
        return borders

    # --- DRAWING TILES ---

    def draw_dirty_tiles(self, board: MinesweeperBoard):
        for y in range(board.height):
            for x in range(board.width):
                tile = board.get_tile(x, y)

                if tile.needs_redraw:
                    self.draw_tile(board, x, y)
                    tile.needs_redraw = False

                    # Redraw neighbors for border updates
                    for nx, ny in board.get_neighbors(x, y):
                        self.draw_tile(board, nx, ny)

    def draw_tile(self, board: MinesweeperBoard, x, y):
        tile = board.get_tile(x, y)
        screen_x = self.offset_x + x * self.tile_size
        screen_y = self.offset_y + y * self.tile_size

        # Draw background
        bg_color = self.get_bg_color(board, x, y)

        fill_rect(
            screen_x, screen_y,
            self.tile_size, self.tile_size,
            bg_color
        )

        # Draw borders
        if tile.is_uncovered:
            borders = self.get_tile_borders(board, x, y)
            border_color = SpriteLibrary.COLORS["uncovered_border"]
            w = self.BORDER_WEIGHT

            if borders[0]:
                fill_rect(screen_x, screen_y, self.tile_size, w, border_color) # Top
            if borders[1]:
                fill_rect(screen_x, screen_y + self.tile_size - w, self.tile_size, w, border_color) # Bottom
            if borders[2]:
                fill_rect(screen_x, screen_y, w, self.tile_size, border_color) # Left
            if borders[3]:
                fill_rect(screen_x + self.tile_size - w, screen_y, w, self.tile_size, border_color) # Right

        # Draw number
        if tile.is_uncovered and tile.neighboring_mine_count > 0 and not tile.is_mined:
            num = tile.neighboring_mine_count
            num_color = self.get_num_color(num)
            num_sprite = SpriteLibrary.NUMBER_SPRITES[num]
            SpriteLibrary.draw_sprite(screen_x + 7, screen_y + 6, num_sprite, num_color, 1)

        # Draw flag
        if tile.is_flagged:
            SpriteLibrary.draw_sprite(screen_x, screen_y, SpriteLibrary.FLAG_SPRITE, SpriteLibrary.COLORS["flag"], 1)
        
        # Draw mine
        if tile.is_uncovered and tile.is_mined:
            SpriteLibrary.draw_sprite(screen_x, screen_y, SpriteLibrary.MINE_SPRITE, SpriteLibrary.COLORS["mine"], 1)

    def draw_selection_border(self, x, y):
        t = self.tile_size
        w = self.BORDER_WEIGHT
        color = SpriteLibrary.COLORS["selection_border"]

        # Convert to screen coords
        x = self.offset_x + x * t
        y = self.offset_y + y * t

        fill_rect(x, y, t, w, color) # Top
        fill_rect(x, y + t - w, t, w, color) # Bottom
        fill_rect(x, y, w, t, color) # Left
        fill_rect(x + t - w, y, w, t, color) # Right

class Hud:
    WIDTH = SCREEN_WIDTH
    HEIGHT = HUD_HEIGHT

    FLAG_SPRITE_POS = (107, 2)
    FLAG_NUM_POS = (130, 8)

    CLOCK_SPRITE_POS = (168, 1)
    CLOCK_NUM_POS = (193, 8)

    NUM_SPACING = 9

    # Draw icons and bg once
    def reset(self):
        fill_rect(
             0, 0, 
            self.WIDTH, self.HEIGHT,
            SpriteLibrary.COLORS["hud_bg"]
        )

        fx, fy = self.FLAG_SPRITE_POS
        SpriteLibrary.draw_sprite(
            fx, fy, SpriteLibrary.FLAG_SPRITE, SpriteLibrary.COLORS["hud_flag"]
        )

        cx, cy = self.CLOCK_SPRITE_POS
        SpriteLibrary.draw_sprite(
            cx, cy, SpriteLibrary.CLOCK_SPRITE, SpriteLibrary.COLORS["hud_clock"]
        )

        fx, fy = self.FLAG_NUM_POS
        self.flags_left_displayer = NumberDisplayer(
            fx, fy, 
            SpriteLibrary.COLORS["hud_numbers"], SpriteLibrary.COLORS["hud_bg"],
            1, self.NUM_SPACING, 2
        )

        cx, cy = self.CLOCK_NUM_POS
        self.time_taken_displayer = NumberDisplayer(
            cx, cy,
            SpriteLibrary.COLORS["hud_numbers"], SpriteLibrary.COLORS["hud_bg"],
            1, self.NUM_SPACING, 3
        )
        
        self.update_flags_left(0)
        self.update_time_taken(0)

    def update_flags_left(self, flags_left: int):
        self.flags_left_displayer.update(flags_left)

    def update_time_taken(self, time_taken: int):
        self.time_taken_displayer.update(time_taken)

class MenuDisplay:
    TITLE_POS = (35, 17)

    BUTTON_1_POS = (134, 76)
    BUTTON_2_POS = (90, 111)
    BUTTON_3_POS = (137, 145)

    ARROW_1_POS = (55, 78)
    ARROW_2_POS = (55, 113)
    ARROW_3_POS = (55, 148)

    BEST_SCORE_POS = (136, 192)
    NUM_SPACING = 18

    def reset(self):
        fill_rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, SpriteLibrary.COLORS["menu_bg"])

        tx, ty = self.TITLE_POS
        SpriteLibrary.draw_sprite(tx, ty, SpriteLibrary.MINESWEEPER_SPRITE, SpriteLibrary.COLORS["menu_text"], 5)
        b1x, b1y = self.BUTTON_1_POS
        SpriteLibrary.draw_sprite(b1x, b1y, SpriteLibrary.PLAY_SPRITE, SpriteLibrary.COLORS["menu_text"], 3)
        b2x, b2y = self.BUTTON_2_POS
        SpriteLibrary.draw_sprite(b2x, b2y, SpriteLibrary.RESET_SCORE_SPRITE, SpriteLibrary.COLORS["menu_text"], 3)
        b3x, b3y = self.BUTTON_3_POS
        SpriteLibrary.draw_sprite(b3x, b3y, SpriteLibrary.QUIT_SPRITE, SpriteLibrary.COLORS["menu_text"], 3)

        self.selector_pos = -1
        self.update_selector_pos(0)

        bsx, bsy = self.BEST_SCORE_POS
        self.best_score_drawer = NumberDisplayer(
            bsx, bsy,
            SpriteLibrary.COLORS["menu_numbers"], SpriteLibrary.COLORS["menu_bg"],
            3, self.NUM_SPACING, 3
        )

    def update_selector_pos(self, pos: int):
        if self.selector_pos != pos:
            x, y = 0, 0
            
            # Erase old
            if self.selector_pos == 0:
                x, y = self.ARROW_1_POS
            elif self.selector_pos == 1:
                x, y = self.ARROW_2_POS
            elif self.selector_pos == 2:
                x, y = self.ARROW_3_POS
            
            fill_rect(x, y, 17, 17, SpriteLibrary.COLORS["menu_bg"])

            # Draw new
            self.selector_pos = pos
            if pos == 0:
                x, y = self.ARROW_1_POS
            elif pos == 1:
                x, y = self.ARROW_2_POS
            elif pos == 2:
                x, y = self.ARROW_3_POS
            
            SpriteLibrary.draw_sprite(x, y, SpriteLibrary.ARROW_SPRITE, SpriteLibrary.COLORS["menu_text"], 2)

    def update_best_score(self, best_score: int):
        self.best_score_drawer.update(best_score)

# =====================
# PROGRAM FLOW
# =====================

class ProgramState:
    GAME = 0
    MENU = 1
    QUIT = 2

class MinesweeperManager:
    selector = DPadSelector(GRID_WIDTH -   1, GRID_HEIGHT - 1)

    board = MinesweeperBoard(GRID_WIDTH, GRID_HEIGHT, MINE_AMOUNT)
    display = MinesweeperDisplay(0, HUD_HEIGHT, TILE_SIZE)

    hud = Hud()

    start_time: float
    time_taken: int

    def reset(self):
        self.start_time = monotonic()
        self.time_taken = 0

        self.board.reset()
        self.display.draw_dirty_tiles(self.board)

        self.selector.x = 0
        self.selector.y = 0

        self.hud.reset()

    def update(self) -> ProgramState:
        now = monotonic()
        self.time_taken = int(now - self.start_time)

        # INPUT
        prev_x, prev_y = self.selector.x, self.selector.y
        self.selector.update()
        x, y = self.selector.x, self.selector.y

        # ACTIONS
        if MinesweeperInputs.FLAG_KEY.is_triggered():
            self.board.flag_tile(x, y)
        
        if MinesweeperInputs.UNCOVER_KEY.is_triggered():
            self.board.uncover_tile(x, y)

        # RENDER
        if x != prev_x or y != prev_y:
            # Erase prev selection border
            self.board.get_tile(prev_x, prev_y).needs_redraw = True
        
        self.display.draw_dirty_tiles(self.board)
        self.display.draw_selection_border(x, y)
        
        # UPDATE HUD
        self.hud.update_flags_left(self.board.flags_left)
        self.hud.update_time_taken(self.time_taken)
        
        # CHECK GAME STATE
        if self.board.game_state == GameState.WON:
            self.win()
            return ProgramState.MENU
        
        elif self.board.game_state == GameState.LOST:
            self.lose()
            return ProgramState.MENU
        
        return ProgramState.GAME
    
    def win(self):
        # Update high score
        current_score: int = floor(self.time_taken)
        current_written_score: int = best_score

        if current_written_score == -1 or current_score < current_written_score:
            best_score = current_score

        sleep(1.0)
    
    def lose(self):
        sleep(1.0)

class MenuManager:
    selector = DPadSelector(0, 2) # 3 options
    menu_display = MenuDisplay()

    def reset(self):
        self.selector.y = 0
        self.menu_display.reset()

        if best_score != -1:
            self.menu_display.update_best_score(best_score)
    
    def update(self) -> ProgramState:
        self.selector.update()

        selector_pos = self.selector.y

        self.menu_display.update_selector_pos(selector_pos)

        if MinesweeperInputs.OK_KEY.is_triggered():
            if selector_pos == 0:
                # Start game
                return ProgramState.GAME

            elif self.selector.y == 1:
                # Reset best score
                best_score = -1
                self.menu_display.update_best_score(best_score)

            elif self.selector.y == 2:
                # Quit
                return ProgramState.QUIT
                
        return ProgramState.MENU

game = MinesweeperManager()

def enter_game():
    game.reset()
    while True:
        result = game.update()
        if result == ProgramState.MENU:
            enter_menu()

menu = MenuManager()

def enter_menu():
    menu.reset()
    while True:
        result = menu.update()
        if result == ProgramState.GAME:
            enter_game()
        elif result == ProgramState.QUIT:
            break

enter_menu()