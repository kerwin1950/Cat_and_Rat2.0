import math, random, time
from browser import document, window

# ===============================
# 全局变量与常量
# ===============================
canvas = document["game_canvas"]
ctx = canvas.getContext("2d")

# Canvas 尺寸（初始时同步 HTML 中的 canvas 大小）
HORIZONTAL_LENGTH = canvas.width
VERTICAL_WIDTH = canvas.height
is_paused = False
game_running = True# 游戏是否正在运行
# 设计分辨率
DESIGN_WIDTH = 800
DESIGN_HEIGHT = 600
scale_factor = min(canvas.width / DESIGN_WIDTH, canvas.height / DESIGN_HEIGHT)
# 常量
BUTTON_WIDTH = 200
BUTTON_HEIGHT = 50
STEP_SIZE = 20
BASE_RAT_SIZE = 10  # 设计分辨率下的基础大小
RAT_SIZE = int(BASE_RAT_SIZE * scale_factor)
BASE_CAT_SIZE = 30  # 设计分辨率下的基础大小
CAT_SIZE = int(BASE_CAT_SIZE * scale_factor)
BASE_CHEESE_SIZE = 20  # 设计分辨率下的基础大小
CHEESE_SIZE = int(BASE_CHEESE_SIZE * scale_factor)
BASE_OBSTACLE_SIZE_LOW = 40  # 设计分辨率下的基础大小
BASE_OBSTACLE_SIZE_HIGH = 150  # 设计分辨率下的基础大小
OBSTACLE_SIZE_LOW = int(BASE_OBSTACLE_SIZE_LOW * scale_factor)
OBSTACLE_SIZE_HIGH = int(BASE_OBSTACLE_SIZE_HIGH * scale_factor)
# 颜色（RGB 格式）
WHITE       = (255, 255, 255)
BLACK       = (0, 0, 0)
DARK_GREEN  = (0, 100, 0)
BRIGHT_GREEN= (0, 155, 0)
GREY        = (128, 128, 128)
YELLOW      = (255, 255, 0)
# 资源路径
ICON_PATH         = "resources/logo.png"
BG_MUSIC_PATH     = "resources/bg.mp3"
EAT_SOUND_PATH    = "resources/eat.mp3"
HIT_SOUND_PATH    = "resources/hit.mp3"
LOSER_SOUND_PATH  = "resources/loser.mp3"
WINNER_SOUND_PATH = "resources/winer.mp3"

# 字体设置
FONT_LARGE  = "50px SimHei"
FONT_MIDDLE = "30px SimHei"
FONT_SMALL  = "20px SimHei"

# ===============================
# 类定义
# ===============================
class Rect:
    def __init__(self, x, y, width, height):
        self.x      = x
        self.y      = y
        self.width  = width
        self.height = height

    def copy(self):
        return Rect(self.x, self.y, self.width, self.height)

    @property
    def center(self):
        return (self.x + self.width / 2, self.y + self.height / 2)

    @center.setter
    def center(self, pos):
        cx, cy = pos
        self.x = cx - self.width / 2
        self.y = cy - self.height / 2

    def colliderect(self, other):
        return not (
            self.x + self.width <= other.x or 
            self.x >= other.x + other.width or
            self.y + self.height <= other.y or 
            self.y >= other.y + other.height
        )

class Vector2:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, other):
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar):
        return Vector2(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar):
        return Vector2(self.x / scalar, self.y / scalar)

    def length(self):
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def normalize(self):
        l = self.length()
        return self if l == 0 else self / l

    def copy(self):
        return Vector2(self.x, self.y)

def rgb_color(color):
    """将RGB元组转换为 CSS 格式字符串"""
    return "rgb({}, {}, {})".format(color[0], color[1], color[2])

# -------------------------------
# 实体类
# -------------------------------
class Rat:
    def __init__(self, speed, r, x, y, max_speed=400, min_speed=20):
        self.speed = speed
        self.max_speed = max_speed
        self.min_speed = min_speed
        self.r = r
        self.x = x
        self.y = y
        self.rect = Rect(x, y, r * 2, r * 2)
        self.color = (0, 255, 0)

    def draw(self, ctx):
        ctx.beginPath()
        ctx.arc(self.x, self.y, self.r, 0, 2 * math.pi)
        ctx.fillStyle = rgb_color(self.color)
        ctx.fill()

    def track(self, target_x, target_y, speed=None, obstacles=[]):
        if speed is None:
            speed = self.speed
        target_x = max(0, min(HORIZONTAL_LENGTH, target_x))
        target_y = max(0, min(VERTICAL_WIDTH, target_y))
        m_ab = max(math.sqrt((target_x - self.x) ** 2 + (target_y - self.y) ** 2), 0.001)
        if m_ab < 10:
            speed *= m_ab / 10
        if m_ab < 1:
            return
        sin_angle = (target_x - self.x) / m_ab
        cos_angle = (target_y - self.y) / m_ab
        new_x = self.x + speed / 60 * sin_angle
        new_y = self.y + speed / 60 * cos_angle
        new_rect = self.rect.copy()
        new_rect.center = (new_x, new_y)
        collision = any(new_rect.colliderect(obs.rect) for obs in obstacles)
        if not collision:
            self.x, self.y = new_x, new_y
            self.rect = new_rect

class Cat:
    def __init__(self, speed, r, x, y, max_speed=500, decay_rate=0.6, min_speed=10):
        self.speed = speed
        self.max_speed = max_speed
        self.min_speed = min_speed
        self.decay_rate = decay_rate
        self.r = r
        self.x = x
        self.y = y
        self.rect = Rect(x, y, r * 2, r * 2)
        self.color = (255, 0, 0)

    def draw(self, ctx):
        ctx.beginPath()
        ctx.arc(self.x, self.y, self.r, 0, 2 * math.pi)
        ctx.fillStyle = rgb_color(self.color)
        ctx.fill()

    def update_speed(self, pid_speed):
        self.speed = min(self.max_speed, max(self.min_speed, pid_speed))
        self.speed *= self.decay_rate

    def adjust_direction(self, current_direction, obstacle_rect, force_random=False):
        directions = [
            Vector2(1, 0), Vector2(-1, 0), Vector2(0, 1), Vector2(0, -1),
            Vector2(1, 1), Vector2(-1, 1), Vector2(1, -1), Vector2(-1, -1),
            Vector2(2, 0), Vector2(0, 2), Vector2(-2, 0), Vector2(0, -2)
        ]
        if force_random:
            random.shuffle(directions)
        speed_boost = 1.3
        for d in directions:
            test_rect = self.rect.copy()
            offset_x = d.x * self.speed * speed_boost / 60
            offset_y = d.y * self.speed * speed_boost / 60
            test_rect.center = (self.x + offset_x, self.y + offset_y)
            if not test_rect.colliderect(obstacle_rect):
                return d
        return None

    def track(self, target_x, target_y, speed=None, obstacles=[], delta_time=None):
        # 如果没有指定 speed，就使用对象的默认速度
        if speed is None:
            speed = self.speed

        # 如果没有传入 delta_time，则采用默认值（例如 1/60 秒）
        if delta_time is None:
            delta_time = 1 / 60

        # 计算目标方向向量
        direction = Vector2(target_x - self.x, target_y - self.y)
        if direction.length() == 0:
            return
        # 将方向向量归一化，保证它的长度为1
        direction = direction.normalize()

        # 计算本次更新中应移动的向量：运动 = 方向 * 速度 * delta_time
        movement = direction * speed * delta_time

        # 计算新位置
        new_x = self.x + movement.x
        new_y = self.y + movement.y

        # 复制当前矩形，并设置新的中心为新位置
        new_rect = self.rect.copy()
        new_rect.center = (new_x, new_y)

        # 检查是否与障碍物碰撞。如果碰撞，则调整方向
        for obs in obstacles:
            if new_rect.colliderect(obs.rect):
                # 调整方向以避免碰撞
                adjusted_direction = self.adjust_direction(direction, obs.rect)
                if adjusted_direction is not None:
                    # 重新计算移动向量，采用调整后的方向
                    movement = adjusted_direction * speed * delta_time
                    new_x = self.x + movement.x
                    new_y = self.y + movement.y
                    new_rect.center = (new_x, new_y)
                    # 如果调整后的方向可以避开障碍物，则退出检测
                    if not new_rect.colliderect(obs.rect):
                        break

        # 更新对象的位置和对应的碰撞矩形
        self.x = new_x
        self.y = new_y
        self.rect = new_rect


class Cheese:
    def __init__(self, x, y, size=CHEESE_SIZE):
        self.x = x
        self.y = y
        self.size = size
        self.rect = Rect(x - size // 2, y, size, size)

    def draw(self, ctx):
        ctx.beginPath()
        ctx.moveTo(self.x, self.y)
        ctx.lineTo(self.x + self.size / 2, self.y + self.size)
        ctx.lineTo(self.x - self.size / 2, self.y + self.size)
        ctx.closePath()
        ctx.fillStyle = rgb_color(YELLOW)
        ctx.fill()

class Obstacle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.length = random.randint(OBSTACLE_SIZE_LOW, OBSTACLE_SIZE_HIGH)
        self.width = random.randint(OBSTACLE_SIZE_LOW, OBSTACLE_SIZE_HIGH)
        self.color = (random.randint(0,255), random.randint(0,255), random.randint(0,255))
        self.rect = Rect(x, y, self.length, self.width)

    def draw(self, ctx):
        ctx.fillStyle = rgb_color(self.color)
        ctx.fillRect(self.x, self.y, self.length, self.width)

class Button:
    def __init__(self, color, x, y, width, height, text=''):
        self.color = color
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text

    def draw(self, ctx, font_str, outline=None):
        if outline:
            ctx.fillStyle = rgb_color(outline)
            ctx.fillRect(self.x - 5, self.y - 5, self.width + 10, self.height + 10)
        ctx.fillStyle = rgb_color(self.color)
        ctx.fillRect(self.x, self.y, self.width, self.height)
        if self.text:
            ctx.fillStyle = rgb_color(WHITE)
            ctx.font = font_str
            text_width = ctx.measureText(self.text).width
            text_x = self.x + (self.width - text_width) / 2
            text_y = self.y + self.height / 2 + 7
            ctx.fillText(self.text, text_x, text_y)

    def is_over(self, pos):
        x, y = pos
        return self.x < x < self.x + self.width and self.y < y < self.y + self.height

# -------------------------------
# 工具函数
# -------------------------------
class PID:
    def __init__(self, kp, ki, kd):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.previous_error = 0
        self.integral = 0
        self.last_time = time.time()

    def control(self, error):
        current_time = time.time()
        delta_time = max(current_time - self.last_time, 0.001)
        derivative = (error - self.previous_error) / delta_time
        self.integral += error * delta_time
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        self.previous_error = error
        self.last_time = current_time
        return output

def read_distance_sensor(a, b):
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)

def is_colliding(x, y, obstacles, radius):
    # 应实现圆形与矩形的真实碰撞检测
    for obs in obstacles:
        # 计算最近点
        closest_x = max(obs.rect.x, min(x, obs.rect.x + obs.rect.width))
        closest_y = max(obs.rect.y, min(y, obs.rect.y + obs.rect.height))
        distance = math.hypot(x - closest_x, y - closest_y)
        if distance < radius:
            return True
    return False

def generate_safe_position(radius, obstacles):
    while True:
        x = random.randint(radius, HORIZONTAL_LENGTH - radius)
        y = random.randint(radius, VERTICAL_WIDTH - radius)
        if not is_colliding(x, y, obstacles, radius):
            return x, y

def generate_cheese_position(obstacles):
    while True:
        x = random.randint(1, (HORIZONTAL_LENGTH - 20) // STEP_SIZE - 1) * STEP_SIZE
        y = random.randint(1, (VERTICAL_WIDTH - 20) // STEP_SIZE - 1) * STEP_SIZE
        cheese = Cheese(x, y)
        if not any(cheese.rect.colliderect(obs.rect) for obs in obstacles):
            return cheese

def initialize_obstacles(num_obstacles):
    return [Obstacle(random.randint(0, HORIZONTAL_LENGTH - 80),
                     random.randint(0, VERTICAL_WIDTH - 80))
            for _ in range(num_obstacles)]

def update_timer(start_time):
    seconds = int(time.time() - start_time)
    time_left = 60 - seconds
    return max(time_left, 0)

# ===============================
# 音频资源加载（需在 HTML 中预定义 <audio> 标签）
# ===============================
BG_MUSIC     = document["bg_music"]
EAT_SOUND    = document["eat_sound"]
HIT_SOUND    = document["hit_sound"]
LOSER_SOUND  = document["loser_sound"]
WINNER_SOUND = document["winner_sound"]

# ===============================
# 全局变量（游戏状态）
# ===============================
mouse_x = 0
mouse_y = 0

rat = None
cat = None
cheeses = []
obstacles = []
pid_controller = None
last_catch_time = 0
catch_cooldown = 2000  # 毫秒
start_ticks = window.Date.now() / 1000  # 转换为秒
scores = 0
lives_count = 3

# ===============================
# 鼠标事件绑定（全局更新鼠标位置）
# ===============================
def update_mouse(event):
    rect = canvas.getBoundingClientRect()
    global mouse_x, mouse_y
    mouse_x = event.clientX - rect.left
    mouse_y = event.clientY - rect.top

document.bind("mousemove", update_mouse)

# ===============================
# 各界面事件处理通用函数（使用 lambda 传递额外参数）
# ===============================
def handle_mouse_move(event, button, base_color, hover_color):
    rect = canvas.getBoundingClientRect()
    pos = (event.clientX - rect.left, event.clientY - rect.top)
    button.color = hover_color if button.is_over(pos) else base_color

def handle_mouse_click(event, button, callback):
    rect = canvas.getBoundingClientRect()
    pos = (event.clientX - rect.left, event.clientY - rect.top)
    if button.is_over(pos):
        callback()

# ===============================
# 界面显示函数
# ===============================
def show_instructions():
    button_color = DARK_GREEN
    hover_color = BRIGHT_GREEN
    # 居中计算按钮位置（相对于 canvas 尺寸）
    return_button = Button(button_color, (canvas.width - BUTTON_WIDTH) / 2,
                           (canvas.height - BUTTON_HEIGHT) / 2 + 50,
                           BUTTON_WIDTH, BUTTON_HEIGHT, 'Return')
    instruction_running = {"running": True}

    # 使用 lambda 包装函数传递 return_button 参数
    help_mouse_move = lambda event: handle_mouse_move(event, return_button, button_color, hover_color)
    help_mouse_click = lambda event: handle_mouse_click(event, return_button, lambda: close_instructions(instruction_running))
    document.bind("mousemove", help_mouse_move)
    document.bind("click", help_mouse_click)

    def render_instructions(timestamp):
        if not instruction_running["running"]:
            return
        ctx.fillStyle = rgb_color(BLACK)
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        return_button.draw(ctx, "20px Arial", GREY)
        ctx.fillStyle = rgb_color(WHITE)
        ctx.font = FONT_MIDDLE
        ctx.fillText("游戏规则介绍", (canvas.width - BUTTON_WIDTH) / 2, (canvas.height - BUTTON_HEIGHT) / 2 - 200)
        ctx.font = FONT_SMALL
        ctx.fillText("红色大球代表猫，会追逐老鼠。", (canvas.width - BUTTON_WIDTH) / 2 - 50, (canvas.height - BUTTON_HEIGHT) / 2 - 150)
        ctx.fillText("绿色小球代表老鼠，由鼠标控制，点击左键可加速。", (canvas.width - BUTTON_WIDTH) / 2 - 50, (canvas.height - BUTTON_HEIGHT) / 2 - 120)
        ctx.fillText("黄色三角代表奶酪，老鼠吃到可以加分。", (canvas.width - BUTTON_WIDTH) / 2 - 50, (canvas.height - BUTTON_HEIGHT) / 2 - 90)
        ctx.fillText("老鼠有三条命，请在一分钟内尽量存活。", (canvas.width - BUTTON_WIDTH) / 2 - 50, (canvas.height - BUTTON_HEIGHT) / 2 - 60)
        window.requestAnimationFrame(render_instructions)
    window.requestAnimationFrame(render_instructions)

def close_instructions(running):
    running["running"] = False
    document.unbind("mousemove", help_mouse_move)
    document.unbind("click", help_mouse_click)

def show_start_screen(callback):
    button_color = DARK_GREEN
    hover_color = BRIGHT_GREEN
    start_button = Button(button_color, (canvas.width - BUTTON_WIDTH) / 2,
                          (canvas.height - BUTTON_HEIGHT) / 2,
                          BUTTON_WIDTH, BUTTON_HEIGHT, 'Start Game')
    help_button = Button(button_color, (canvas.width - BUTTON_WIDTH) / 2,
                         (canvas.height - BUTTON_HEIGHT) / 2 + 100,
                         BUTTON_WIDTH, BUTTON_HEIGHT, 'Help')
    exit_button = Button(button_color, (canvas.width - BUTTON_WIDTH) / 2,
                         (canvas.height - BUTTON_HEIGHT) / 2 + 200,
                         BUTTON_WIDTH, BUTTON_HEIGHT, 'Exit')
    WINNER_SOUND.volume = 0.5
    WINNER_SOUND.play()
    start_screen_running = {"running": True}

    def on_mouse_click(event):
        rect = canvas.getBoundingClientRect()
        pos = (event.clientX - rect.left, event.clientY - rect.top)
        if start_button.is_over(pos):
            WINNER_SOUND.pause()
            BG_MUSIC.volume = 0.2
            BG_MUSIC.play()
            start_screen_running["running"] = False
            document.unbind("click", on_mouse_click)
            callback(True)
        elif help_button.is_over(pos):
            show_instructions()
        elif exit_button.is_over(pos):
            start_screen_running["running"] = False
            document.unbind("click", on_mouse_click)
            callback(False)

    document.bind("click", on_mouse_click)

    def render_start_screen(timestamp):
        if not start_screen_running["running"]:
            return
        ctx.fillStyle = rgb_color(BLACK)
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        ctx.fillStyle = rgb_color(WHITE)
        ctx.font = "40px Arial"
        ctx.fillText("Welcome!", canvas.width/2-100, canvas.height/2-100)
        start_button.draw(ctx, "20px Arial", GREY)
        help_button.draw(ctx, "20px Arial", GREY)
        exit_button.draw(ctx, "20px Arial", GREY)
        window.requestAnimationFrame(render_start_screen)
    window.requestAnimationFrame(render_start_screen)

def show_exit_screen(scores, lives_count, callback):
    ctx.fillStyle = rgb_color(BLACK)
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    button_color = DARK_GREEN
    hover_color = BRIGHT_GREEN
    restart_button = Button(button_color,  (canvas.width - BUTTON_WIDTH) / 2, canvas.height/2+120, BUTTON_WIDTH, BUTTON_HEIGHT, 'Restart Game')
    exit_button = Button(button_color, (canvas.width - BUTTON_WIDTH) / 2,canvas.height/2+200, BUTTON_WIDTH, BUTTON_HEIGHT, 'Exit')
    total_score = lives_count * scores if lives_count >= 1 else scores
    ctx.fillStyle = rgb_color(WHITE)
    ctx.font = "40px Arial"
    ctx.fillText("Game Over!",  (canvas.width - BUTTON_WIDTH) / 2, canvas.height/2-100)
    ctx.font = "20px Arial"
    ctx.fillText("奶酪数量： {}".format(scores),  (canvas.width - BUTTON_WIDTH) / 2,canvas.height/2-50)
    ctx.fillText("剩余生命： {}".format(lives_count),  (canvas.width - BUTTON_WIDTH) / 2, canvas.height/2)
    ctx.fillText("最终得分：{}".format(total_score), (canvas.width - BUTTON_WIDTH) / 2, canvas.height/2+50)
    LOSER_SOUND.volume = 0.2
    LOSER_SOUND.play()
    state = {"waiting": True, "restart": None}

    def on_mouse_move(event):
        rect = canvas.getBoundingClientRect()
        pos = (event.clientX - rect.left, event.clientY - rect.top)
        restart_button.color = hover_color if restart_button.is_over(pos) else button_color
        exit_button.color = hover_color if exit_button.is_over(pos) else button_color

    def on_mouse_click(event):
        rect = canvas.getBoundingClientRect()
        pos = (event.clientX - rect.left, event.clientY - rect.top)
        if restart_button.is_over(pos):
            LOSER_SOUND.pause()
            BG_MUSIC.volume = 0.2
            BG_MUSIC.play()
            state["restart"] = True
            state["waiting"] = False
            document.unbind("mousemove", on_mouse_move)
            document.unbind("click", on_mouse_click)
        elif exit_button.is_over(pos):
            clean_exit()

    document.bind("mousemove", on_mouse_move)
    document.bind("click", on_mouse_click)

    def render_exit(timestamp):
        if not state["waiting"]:
            callback(state["restart"])
            return
        ctx.fillStyle = rgb_color(BLACK)
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        ctx.fillStyle = rgb_color(WHITE)
        ctx.font = "40px Arial"
        ctx.fillText("Game Over!", canvas.width/2-100, canvas.height/2-100)
        ctx.font = "20px Arial"
        ctx.fillText("奶酪数量： {}".format(scores), canvas.width/2,canvas.height/2-50)
        ctx.fillText("剩余生命： {}".format(lives_count), canvas.width/2, canvas.height/2)
        ctx.fillText("最终得分：{}".format(total_score),canvas.width/2, canvas.height/2+50)
        restart_button.draw(ctx, "20px Arial", GREY)
        exit_button.draw(ctx, "20px Arial", GREY)
        window.requestAnimationFrame(render_exit)
    window.requestAnimationFrame(render_exit)

# ===============================
# 游戏运行事件及主循环
# ===============================
def on_game_click(event):
    global rat, is_paused, game_running
    if not game_running:
        document.unbind("click", on_game_click)
        return
    rect = canvas.getBoundingClientRect()# 获取画布相对于视口的位置
    click_x = event.clientX - rect.left# 获取鼠标点击的x坐标
    click_y = event.clientY - rect.top

    # 暂停按钮区域检测
    pause_button_x = canvas.width - 100
    pause_button_y = 10
    pause_button_width = 80
    pause_button_height = 30
    if (pause_button_x <= click_x <= pause_button_x + pause_button_width and
        pause_button_y <= click_y <= pause_button_y + pause_button_height):
        is_paused = not is_paused# 切换暂停状态
    else:
        if not is_paused:
            if rat is not None:# 如果老鼠对象存在
                rat.speed = min(rat.speed + 50, rat.max_speed)# 增加老鼠速度
        else:# 如果游戏暂停
            # 继续按钮区域
            resume_button_x = canvas.width/2 - 100
            resume_button_y = canvas.height/2 - 60
            resume_button_width = 200
            resume_button_height = 50
            if (resume_button_x <= click_x <= resume_button_x + resume_button_width and
                resume_button_y <= click_y <= resume_button_y + resume_button_height):
                is_paused = False
            
            # 返回主菜单按钮区域
            menu_button_x = canvas.width/2 - 100
            menu_button_y = canvas.height/2 + 10
            menu_button_width = 200
            menu_button_height = 50
            if (menu_button_x <= click_x <= menu_button_x + menu_button_width and
                menu_button_y <= click_y <= menu_button_y + menu_button_height):# 如果点击了返回主菜单按钮
                is_paused = False
                game_running = False
                document.unbind("click", on_game_click)  # 新增解绑
                BG_MUSIC.pause()
                main()# 重新开始游戏
def main_loop(timestamp):
    global rat, cat, cheeses, obstacles, pid_controller, last_catch_time, start_ticks, lives_count, scores, is_paused, game_running
    
    if not game_running:
        return

    if not is_paused:
        # 检查游戏剩余时间，如果用完就显示退出界面
        if update_timer(start_ticks) <= 0:
            # 定义退出回调（例如重启或退出）
            def exit_callback(restart):
                global start_ticks, lives_count, scores, obstacles, cat, rat, pid_controller, cheeses
                if restart:
                    start_ticks = time.time()
                    lives_count = 3
                    scores = 0
                    obstacles = initialize_obstacles(20)
                    cat_x, cat_y = generate_safe_position(CAT_SIZE, obstacles)
                    rat_x, rat_y = generate_safe_position(RAT_SIZE, obstacles)
                    pid_controller = PID(0.9, 0.1, 0.01)
                    cat = Cat(random.randint(60, 300), CAT_SIZE, cat_x, cat_y)
                    rat = Rat(random.randint(60, 300), RAT_SIZE, rat_x, rat_y)
                    cheeses.clear()
                    cheeses.append(generate_cheese_position(obstacles))
                    window.requestAnimationFrame(main_loop)
            show_exit_screen(scores, lives_count, exit_callback)
            return

        # 正常的游戏更新逻辑开始
    ctx.fillStyle = rgb_color(BLACK)
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    target_x, target_y = mouse_x, mouse_y
    error = read_distance_sensor(rat, cat)
    pid_speed = max(pid_controller.control(error), 0)
    rat.speed = max(rat.min_speed, rat.speed - 1)
    cat.update_speed(pid_speed)
    rat.track(target_x, target_y, obstacles=obstacles)
    for obs in obstacles:
        obs.draw(ctx)
    rat.draw(ctx)
    cat.track(rat.x, rat.y, cat.speed, obstacles=obstacles)
    cat.draw(ctx)
    for cheese in cheeses:
        cheese.draw(ctx)
    for cheese in list(cheeses):
        if rat.rect.colliderect(cheese.rect):
            scores += 1
            EAT_SOUND.volume = 0.2
            EAT_SOUND.play()
            cheeses.remove(cheese)
            for _ in range(random.choice([1, 2, 3])):
                cheeses.append(generate_cheese_position(obstacles))
            break
    current_time = time.time()  # 获取当前时间（秒）
    if abs(cat.x - rat.x) < 10 and abs(cat.y - rat.y) < 10:
        if current_time - last_catch_time >= catch_cooldown / 1000:
            last_catch_time = current_time
            HIT_SOUND.volume = 0.2
            HIT_SOUND.play()
            lives_count -= 1
            if lives_count == 0:
                def exit_callback(restart):
                    global start_ticks, lives_count, scores, obstacles, cat, rat, pid_controller, cheeses
                    if restart:
                        start_ticks = time.time()
                        lives_count = 3
                        scores = 0
                        obstacles = initialize_obstacles(20)
                        cat_x, cat_y = generate_safe_position(CAT_SIZE, obstacles)
                        rat_x, rat_y = generate_safe_position(RAT_SIZE, obstacles)
                        pid_controller = PID(0.9, 0.1, 0.01)
                        cat = Cat(random.randint(60, 300), CAT_SIZE, cat_x, cat_y)
                        rat = Rat(random.randint(60, 300), RAT_SIZE, rat_x, rat_y)
                        cheeses.clear()
                        cheeses.append(generate_cheese_position(obstacles))
                        window.requestAnimationFrame(main_loop)
                show_exit_screen(scores, lives_count, exit_callback)
                return
    ctx.fillStyle = rgb_color(WHITE)
    ctx.font = "20px Arial"
    ctx.fillText("Time: {}".format(update_timer(start_ticks)),10, 30)
    ctx.fillText("生命: {}".format(lives_count), 100, 30)
    ctx.fillText("奶酪: {}".format(scores), 200, 30)
     # 绘制暂停按钮
    pause_button_text = "继续" if is_paused else "暂停"
    ctx.fillStyle = rgb_color(DARK_GREEN)
    ctx.fillRect(canvas.width - 100, 10, 80, 30)
    ctx.fillStyle = rgb_color(WHITE)
    ctx.font = "20px Arial"
    ctx.fillText(pause_button_text, canvas.width - 90, 30)

    # 绘制暂停菜单
    if is_paused:
        ctx.fillStyle = "rgba(0, 0, 0, 0.7)"
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        
        # 继续按钮
        ctx.fillStyle = rgb_color(DARK_GREEN)
        ctx.fillRect(canvas.width/2 - 100, canvas.height/2 - 60, 200, 50)
        ctx.fillStyle = rgb_color(WHITE)
        ctx.fillText("继续", canvas.width/2 - 30, canvas.height/2 - 25)
        
        # 返回主菜单按钮
        ctx.fillStyle = rgb_color(DARK_GREEN)
        ctx.fillRect(canvas.width/2 - 100, canvas.height/2 + 10, 200, 50)
        ctx.fillStyle = rgb_color(WHITE)
        ctx.fillText("返回主菜单", canvas.width/2 - 60, canvas.height/2 + 35)
    window.requestAnimationFrame(main_loop)


def clean_exit():
    BG_MUSIC.pause()
    BG_MUSIC.currentTime = 0
    window.location.reload()

def main():
    global game_running, is_paused, rat, cat, cheeses, obstacles, pid_controller, lives_count, scores, start_ticks
    # 完全重置所有游戏状态
    game_running = True
    is_paused = False
    lives_count = 3
    scores = 0
    start_ticks = time.time()
    # 清除旧的游戏对象
    rat = None
    cat = None
    cheeses = []
    obstacles = initialize_obstacles(20)
     # 确保移除旧的事件监听
    try:
        document.unbind("click", on_game_click)
    except:
        pass
    cat_x, cat_y = generate_safe_position(CAT_SIZE, obstacles)
    rat_x, rat_y = generate_safe_position(RAT_SIZE, obstacles)
    cheeses = [generate_cheese_position(obstacles) for _ in range(3)]
    cat = Cat(random.randint(60, 300), CAT_SIZE, cat_x, cat_y)
    rat = Rat(random.randint(60, 300), RAT_SIZE, rat_x, rat_y)
    pid_controller = PID(0.9, 0.1, 0.01)
    last_catch_time = 0
    start_ticks = time.time()

    def start_callback(started):
        if started:
            document.bind("click", on_game_click)
            window.requestAnimationFrame(main_loop)
        else:
            clean_exit()
    show_start_screen(start_callback)

main()
