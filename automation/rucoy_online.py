import random
import time
import datetime
from collections import Counter

from colormap import rgb2hex
import cv2

from images import ScreenImage, image_to_cv
from geometry import Rectangle, Point, closest_rectangle_from_point

from geometry import Rectangle

# tool for getting hex colors
# used in distinguishing between elites
def get_hex_color_at_point(image, x, y):
    # Get the color at a specific point and convert it to hex
    b, g, r = image[y, x][:3]  # Ignore alpha if present
    return f'#{r:02x}{g:02x}{b:02x}'

# debug _ tool
# rectangle = Rectangle(0, 0, 1200, 900)  # Adjust dimensions as needed
# small_image_path = 'path_to_arrow_image.png'  # Path to your arrow template image
# debug_screen_image(rectangle, small_image_path, threshold=0.7)
def debug_screen_image(rectangle: Rectangle, small_image_path, threshold):
    # Initialize ScreenImage
    screen_img = ScreenImage(rectangle)
    
    # Load small image
    small_image = image_to_cv(small_image_path, True) 
    mask = None
    if small_image.shape[-1] == 4:  # Check if image has alpha channel
        mask = small_image[:, :, 3]
        small_image = small_image[:, :, :3]
    # Find matches on screen
    rectangles = screen_img.find_on_screen(small_image, threshold, mask)
    hex_strings = [get_hex_color_at_point(screen_img.img_rgb, rect.l_top.x + 10, rect.l_top.y + 10) for rect in rectangles]
    for rect in rectangles:
        print(rect.l_top.x + 10, rect.l_top.y + 10)
    counts = Counter(hex_strings)
    print(counts)
    # Draw rectangles on screen
    screen_img.draw_rectangle_on_screen(rectangles, image_output='debug_draw_result.png')
    
    # Print number of matches found
    print(f"Number of matches found: {len(rectangles)}")

    # Display the result image
    result_img = cv2.imread('debug_draw_result.png')
    cv2.imshow('Debug Result', result_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def find_matches(rectangle: Rectangle, small_image_path, threshold):
    # Initialize ScreenImage
    screen_img = ScreenImage(rectangle)
    # Load small image
    small_image = image_to_cv(small_image_path)

    # Find matches on screen
    rectangles = screen_img.find_on_screen(small_image, threshold)
    
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    # return # of rectangles
    return len(rectangles)



class MobDen:

    def __init__(self, tile_colors, mob_img_urls):
        self.tile_colors = tile_colors
        self.cv_img_templates = [image_to_cv(img, alpha=True) for img in mob_img_urls]


class RucoyOnline:

    # These will NOT be the tile colors you see on screen. use .print_center_colors to find out what the mapping is
    MOB_DENS = {'vampire': MobDen(tile_colors=['#584836', '#5A4931'], mob_img_urls=['imgs/rucoy_online/vampire_white.png']),
                'skeleton_ground_level': MobDen(tile_colors=['#1C4548', '#29382C'],
                                                mob_img_urls=['imgs/rucoy_online/skeleton_warrior_white.png']),
                'minotaur_lv_225': MobDen(tile_colors= ['#296DBD'], mob_img_urls=['imgs/rucoy_online/transparent_minotaur.png'])}
    
    # config depending on binds
    KEY_BINDS = {
        'up': 'w',
        'down' : 's',
        'left': 'a',
        'right' : 'd',
        'spec': '',
        'melee': '1',
        'dist': '2',
        'mag': '3',
        'hp': 'r',
        'mana': 'e'
    }

    Potions = {}

    current_mob_den = MOB_DENS['minotaur_lv_225']
    current_mana_potion = None
    current_hp_potion = None

    screen_matrix = [[0 for _ in range(13)] for _ in range(7)] # assuming 7x13 array of tiles on screen
    matrix_to_rectangle_map = {} # we store (row, col) -> rectangle as well as rectangle -> (row, col) here

    arrow_number_cvs = {i: image_to_cv(f'imgs/rucoy_online/arrow_amount_numbers/{i}.png') for i in range(0, 10)}
    exhausted_mob_message = image_to_cv('imgs/rucoy_online/exhausted_mob.png')
    skeleton_stairs = image_to_cv('imgs/rucoy_online/skeleton_stairs_down.png')
    back_button_image = image_to_cv('imgs/rucoy_online/back_button.png')
    

    def __init__(self, window_rec: Rectangle):
        self.window_rec = window_rec
        self.right_navbar_margin, self.top_navbar_margin = 35, 35

        # update screenshot to call functions
        self.__update_screenshot__()
        # calculate all rectangle, from clickable buttons to others
        self.__calculate_tile_rectangles__()
        self.__calculate_left_bottom_rectangles()
        self.__calculate_top_right_rectangles()
        self.__calculate_player_rectangle()

    # calculate rectangles for special ability, mana, and health
    def __calculate_left_bottom_rectangles(self):
        l_bot = self.window_rec.l_bot
        b_width, b_height = 65, 80
        # special is first, then mana, then health. work from top to bottom
        self.special_ability_rectangle = Rectangle(l_bot.x + 8, l_bot.y - (3 * b_height), b_width, b_height - 10)
        self.mana_potion_rectangle = Rectangle(l_bot.x + 8, l_bot.y - (2 * b_height), b_width, b_height - 10)
        self.health_potion_rectangle = Rectangle(l_bot.x + 8, l_bot.y - b_height, b_width, b_height - 10)

    # calculate rectangles for menus items on top right (including back button)
    def __calculate_top_right_rectangles(self):
        r_top = self.window_rec.r_top
        b_width, b_height = 50, 50

        self.map_rectangle = Rectangle(r_top.x - (4 * b_width) - self.right_navbar_margin - 12,
                                       r_top.y + self.top_navbar_margin, b_width, b_height)

        self.chat_rectangle = Rectangle(r_top.x - (3 * b_width) - self.right_navbar_margin - 8,
                                        r_top.y + self.top_navbar_margin, b_width, b_height)

        self.friends_rectangle = Rectangle(r_top.x - (2 * b_width) - self.right_navbar_margin - 4,
                                           r_top.y + self.top_navbar_margin, b_width, b_height)

        self.settings_rectangle = Rectangle(r_top.x - b_width - self.right_navbar_margin,
                                            r_top.y + self.top_navbar_margin, b_width, b_height)

        self.back_rectangle = self.settings_rectangle.copy()

        # this pixel will be white if the back button is there
        self.back_button_point = Point(r_top.x - self.right_navbar_margin - 40, r_top.y + self.top_navbar_margin + 20)
        # self.back_button_point.move_mouse()

    # box around the player, so we don't accidentally touch em
    def __calculate_player_rectangle(self):
        p_tile = closest_rectangle_from_point(self.window_rec.center, self.tile_rectangles)

        # mark player on screen matrix
        p_row = self.matrix_to_rectangle_map.get(p_tile, (3,6))[0]
        p_col = self.matrix_to_rectangle_map.get(p_tile, (3,6))[1]
        self.screen_matrix[p_row][p_col] = -1

        margin = 10
        self.player_rectangle = Rectangle(p_tile.l_top.x - margin, p_tile.l_top.y - margin,
                                          p_tile.width + (2 * margin), p_tile.height + (2 * margin))

    def __calculate_tile_rectangles__(self):
        x_current, y_current = 84, 89
        x_spacing, y_spacing = 5.1, 5.09  # this is the best spacing I could find that finds all rectangles perfectly

        num_cols, num_rows = 13, 7
        
        self.tile_width, self.tile_height = 49, 49

        rectangles = []
        for col in range(0, num_cols):
            space_to_next_x = (col * self.tile_width + col * x_spacing)
            row_rec = Rectangle(x_current + space_to_next_x, y_current, self.tile_width, self.tile_height)
            rectangles.append(row_rec)
            for row in range(1, num_rows):
                # the rest of the rows
                rectangle = row_rec.shift_rectangle_down(self.tile_height * row + y_spacing * row)
                rectangles.append(rectangle)
                self.matrix_to_rectangle_map.update({rectangle : (row, col)})
                self.matrix_to_rectangle_map.update({(row, col) : rectangle})

        # calculate neighbors
        for index_, rec in enumerate(rectangles):
            col = int(index_ / num_rows)
            row = index_ % num_rows
            # top
            if row > 0:
                rec.neighbor_rectangles.append(rectangles[index_ - 1])

            # bottom
            if row < num_rows - 1:
                rec.neighbor_rectangles.append(rectangles[index_ + 1])

            # left
            if col > 0:
                rec.neighbor_rectangles.append(rectangles[index_ - num_rows])

            # right
            if col < num_cols - 1:
                rec.neighbor_rectangles.append(rectangles[index_ + num_rows])

        self.tile_rectangles = rectangles
        for row in self.screen_matrix:
            print(row)
        x1, y1 = rectangles[0].l_top.x, rectangles[0].l_top.y
        x2, y2 = rectangles[-1].r_bot.x, rectangles[-1].r_bot.y
        self.clickable_area_rectangle = Rectangle(x1, y1, x2 - x1, y2 - y1)

    def __update_screenshot__(self):
        self.current_screen_image = ScreenImage(self.window_rec)

    def print_center_colors(self):
        hex_strings = [self.get_hex_color_at_point(tr.center) for tr in self.tile_rectangles]
        counts = Counter(hex_strings)
        print(counts)

    def mob_is_exhausted(self):
        rec = self.current_screen_image.find_on_screen(self.exhausted_mob_message)
        return len(rec) > 0

    def get_mob_rectangles(self):
        mob_image = self.current_mob_den.cv_img_templates[0]
        mask = None
        if mob_image.shape[-1] == 4:  # Check if image has alpha channel
            mask = mob_image[:, :, 3]
            mob_image = mob_image[:, :, :3]
        
        # get all mobs
        name_recs = self.current_screen_image.find_on_screen(mob_image, mask=mask)
        
        # try to land a point in the mob by moving the point down and to the right
        # we have to push 3/4 of a tile down since the name is on top of the tile (sometimes way up)
        point_touching_mobs = [Point(nr.center.x, nr.center.y + (self.tile_height * (3 / 4))) for nr in name_recs]

        # name_recs start at the beginning of the name, so move the box down and to the right
        mob_rectangles = [closest_rectangle_from_point(p, self.tile_rectangles) for p in point_touching_mobs]

        for mob_rectangle in mob_rectangles:
            if mob_rectangle in self.matrix_to_rectangle_map:
                (mrow, mcol) = self.matrix_to_rectangle_map.get(mob_rectangle)
                self.screen_matrix[mrow][mcol] = 2

        # get the center of monster mob_rectangles and sort by closest to player
        mob_rectangles.sort(key=lambda r: (r.center.x - self.player_rectangle.center.x) ** 2 +
                                          (r.center.y - self.player_rectangle.center.y) ** 2)

        return mob_rectangles
    
    def get_mob_beside_player(self):
        # get all mobs
        player_surroundings = ScreenImage(Rectangle(320, 160, 540, 350))  # Adjust dimensions as needed


        mob_image = self.current_mob_den.cv_img_templates[0]
        mask = None
        if mob_image.shape[-1] == 4:  # Check if image has alpha channel
            mask = mob_image[:, :, 3]
            mob_image = mob_image[:, :, :3]
        # Find matches on screen

        name_recs = player_surroundings.find_on_screen(mob_image, threshold =0.6, mask=mask)

        elite_points = []
        for nr in name_recs:
            hex_color = get_hex_color_at_point(player_surroundings.img_rgb, nr.l_top.x + 10, nr.l_top.y + 10)
            if hex_color in ['#824a8a', '#ef75ff', '#884c90']:
                elite_points.append(Point(nr.center.x + 320, nr.center.y + 160 + (self.tile_height * (3 / 4))))
        if len(elite_points) > 0:
            elite_array = [closest_rectangle_from_point(p, self.tile_rectangles) for p in elite_points]
            elite_array.sort(key=lambda r: (r.center.x - self.player_rectangle.center.x) ** 2 +
                                          (r.center.y - self.player_rectangle.center.y) ** 2)
            self.deal_with_elites(elite_array)
        
        # try to land a point in the mob by moving the point down and to the right
        # we have to push 3/4 of a tile down since the name is on top of the tile (sometimes way up)
        # and account for offset of the player surroundings relative to full screen
        
        point_touching_mobs = [Point(nr.center.x + 320, nr.center.y + 160 + (self.tile_height * (3 / 4))) for nr in name_recs]

        # name_recs start at the beginning of the name, so move the box down and to the right
        mob_rectangles = [closest_rectangle_from_point(p, self.tile_rectangles) for p in point_touching_mobs]

        # get the center of monster mob_rectangles and sort by closest to player
        mob_rectangles.sort(key=lambda r: (r.center.x - self.player_rectangle.center.x) ** 2 +
                                          (r.center.y - self.player_rectangle.center.y) ** 2)
        return mob_rectangles

    def get_hex_color_at_point(self, point: Point):
        rgb = self.current_screen_image.pillow_img.getpixel((point.x, point.y))
        return rgb2hex(rgb[0], rgb[1], rgb[2])

    def has_back_button(self):
        #color = self.get_hex_color_at_point(self.back_button_point)
        #return color == '#C9C9C9'
        rec = self.current_screen_image.find_on_screen(self.back_button_image)
        return len(rec) > 0

    def get_clickable_tiles(self, tile_list=None):
        if tile_list is None:
            tile_list = self.tile_rectangles
            
        clickable_tiles = [tile for tile in tile_list if
                        self.get_hex_color_at_point(tile.center) in self.current_mob_den.tile_colors]
        
        for tile in clickable_tiles:
            matrix_position = self.matrix_to_rectangle_map.get(tile)
            if matrix_position is not None:
                mrow, mcol = matrix_position
                self.screen_matrix[mrow][mcol] = 1
        
        return clickable_tiles


    def can_click_point(self, p: Point):
        # we can click a point if it's in the clickable tiles but not on the player
        can_click = self.clickable_area_rectangle.contains_point(p) \
                    and not self.player_rectangle.contains_point(p)

        # don't click on stairs
        stairs_rec = self.current_screen_image.find_on_screen(self.skeleton_stairs)
        if len(stairs_rec) > 0:
            stairs_rec = closest_rectangle_from_point(stairs_rec[0].center, self.tile_rectangles)
            can_click = can_click and not stairs_rec.contains_point(p)

        return can_click

    def needs_health(self):
        # get a pixel at the end of the health bar
        x_margin, y_margin = 230, 10 + self.top_navbar_margin
        point = Point(self.window_rec.l_top.x + x_margin, self.window_rec.l_top.y + y_margin)
        # health bar is gray
        color = self.get_hex_color_at_point(point)
        return color == '#6B696B'

    def needs_mana(self):
        # get a pixel at the end of the mana bar
        point = Point(self.window_rec.l_top.x + 260, self.window_rec.l_top.y + self.top_navbar_margin + 28)
        # mana bar is gray
        color = self.get_hex_color_at_point(point)
        return color == '#6c6c6c'

    # read the arrow images left to right (sort by the x-axis)
    def __read_num_arrows_from_screen__(self):

        x_dictionary = {}
        for i, num_cv in self.arrow_number_cvs.items():
            #print(num_cv)
                    # Example usage
            #rectangle = Rectangle(0, 0, 1200, 900)  # Adjust dimensions as needed
            #debug_screen_image(rectangle, num_cv, threshold=0.7)
            for rec in self.current_screen_image.find_on_screen(num_cv, threshold=0.9):
                x_dictionary[rec.l_top.x] = str(i)

        if len(x_dictionary.keys()) > 0:
            num_string = ''.join([x_dictionary[key] for key in sorted(x_dictionary.keys())])
        else:
            num_string = '0'
        print(num_string)
        return int(num_string)

    def click_back_button_out_of_existence(self):
        while self.has_back_button():
            self.back_rectangle.random_point().click()
            time.sleep(random.uniform(0.2, 0.5))
            self.__update_screenshot__()

    # need to check multiple times as sometimes the chat blocks the numbers
    def get_num_arrows(self):
        current_num_arrows = 0

        for i in range(0, 120):
            current_num_arrows = self.__read_num_arrows_from_screen__()
            if current_num_arrows > 0:
                break
            else:
                print(f'0 arrows at loop #{i}')
                time.sleep(random.uniform(1, 2))
            self.__update_screenshot__()

        return current_num_arrows

    def trigger_special_ability(self, times=1):
        for i in range(0, times):
            time.sleep(random.uniform(1, 3))
            # trigger special ability
            self.special_ability_rectangle.random_point().click()
            if self.needs_mana():
                self.mana_potion_rectangle.random_point().click()

    def switch_weapon(self, old_wep, new_wep):

        screen = ScreenImage(Rectangle(800, 330, 900, 520))
        old_wep_img = image_to_cv(old_wep, True) 
        mask = None
        if old_wep_img.shape[-1] == 4:  # Check if image has alpha channel
            mask = old_wep_img[:, :, 3]
            old_wep_img = old_wep_img[:, :, :3]
        # Find matches on screen
        weapon = screen.find_on_screen(old_wep_img, 0.8, mask) # returns an array so we access it by doing [0]
        weapon_point = Point(weapon[0].center.x + 800, weapon[0].center.y + 330)

        weapon_point.click()
        time.sleep(0.3)
        
        screen2 = ScreenImage(Rectangle(740, 330, 900, 520))
        new_wep_img = image_to_cv(new_wep, True) 
        mask = None
        if new_wep_img.shape[-1] == 4:  # Check if image has alpha channel
            mask = new_wep_img[:, :, 3]
            new_wep_img = new_wep_img[:, :, :3]
        # Find matches on screen
        weapon = screen2.find_on_screen(new_wep_img, 0.8, mask)
        print(len(weapon))
        weapon_point = Point(weapon[0].center.x + 740, weapon[0].center.y + 330)
        weapon_point.click()

        pass

    # deal with elite monsters
    def deal_with_elites(self, mob_array):
        for mob in mob_array:
            if (mob.center.x, mob.center.y) in [(432, 221), (378, 275), (486, 275), (432, 329)]:
                kill_time = random.randint(45, 60)
                training_end_time = time.time() + kill_time
                self.switch_weapon('imgs/rucoy_online/15_dagger.png', 'imgs/rucoy_online/drag_sword_blue.png')

                point = mob.random_point()
                point.click()

                while time.time() < training_end_time:

                    min_timeout, max_timeout = 1, 2
                    self.__update_screenshot__()
                    if self.needs_health():
                        self.health_potion_rectangle.random_point().click()

                    time.sleep(random.randint(min_timeout, max_timeout))

                self.switch_weapon('imgs/rucoy_online/drag_sword_blue.png', 'imgs/rucoy_online/15_dagger.png')
            else:
                continue

    def automate_training(self):
        
        screen = Rectangle(0, 0, 900, 520)  # Adjust dimensions as needed
        small_image_path = 'imgs/rucoy_online/minotaur.png'
        debug_screen_image(screen, small_image_path, threshold=0.75)
        

        mode = 0  # 0 for melee train, 1 for dist train, 2 for mage train (minos), 3 for melee ptrain?

        # initially start off "not training"
        min_training_time = 6 * 60  # 6 minutes in seconds
        max_training_time = 8 * 60  # 8 minutes in seconds
        training_time = random.randint(min_training_time, max_training_time)
        training_end_time = 0

        #(x,y) of the currently sel ected monster, used to determine when mob currently training has disappeared
        # top 432 221
        # left 378 275
        # right 486 275
        # bottom 432 329
        currently_selected = (None, None)
        # type for either 'elite' or 'reg'
        while mode == 1:
            min_timeout, max_timeout = 6, 8
            self.__update_screenshot__()

            self.click_back_button_out_of_existence()

            if self.get_num_arrows() == 0:
                # no arrows
                break

            if self.needs_health():
                self.health_potion_rectangle.random_point().click()
                self.trigger_special_ability(times=1)
            

            # mob is exhausted, trigger special
            if self.mob_is_exhausted():
                self.trigger_special_ability(times=2)

            # click on the mob and any neighbor rectangles
            mob_rectangles = self.get_mob_rectangles()

            if len(mob_rectangles) > 0:
                clickable_points = []
                point = mob_rectangles[0].random_point()
                clickable_points.append(point)

                neighbor_tiles = self.get_clickable_tiles(mob_rectangles[0].neighbor_rectangles)
                if len(neighbor_tiles) > 0:
                    neighbor_tile = random.choice(neighbor_tiles)
                    clickable_points.append(neighbor_tile.random_point())

                for p in clickable_points:
                    if self.can_click_point(p):
                        p.click()

            else:
                # no monsters
                clickable_tiles = self.get_clickable_tiles()
                if len(clickable_tiles) > 0:
                    random_point = random.choice(clickable_tiles).random_point()

                    if self.can_click_point(random_point):
                        random_point.click()
                min_timeout, max_timeout = 1, 2

            time.sleep(random.uniform(min_timeout, max_timeout))

        while mode == 0:
            min_timeout, max_timeout = 1, 3
            self.__update_screenshot__()
    
            self.click_back_button_out_of_existence() # fixed

            if self.needs_health():
                self.health_potion_rectangle.random_point().click()
                #self.trigger_special_ability(times=1)

            # mob is exhausted, trigger special
            if self.mob_is_exhausted():
                self.trigger_special_ability(times=2)

            # click on the mob and any neighbor rectangles
            mobs_beside_player = self.get_mob_beside_player()

            is_still_training = False
            if mobs_beside_player:
                in_mob_list = any((mob_beside_player.center.x, mob_beside_player.center.y) == currently_selected for mob_beside_player in mobs_beside_player)
                if in_mob_list:
                    is_still_training = True
            else:
                is_still_training = True  # just for logic issues


            # change to if len(mob_rectangles) > 0 and timer is done
            if (len(mobs_beside_player) > 0 and time.time() >= training_end_time) or not is_still_training:
                print("need to switch/target mobs")
                if time.time() >= training_end_time:
                    print(" because timer ran out ")
                
                # select mob
                mob_rectangles = self.get_mob_beside_player()


                # Now iterate over the sorted list
                for mob in mob_rectangles:
                    if (mob.center.x, mob.center.y) != currently_selected and \
                        (mob.center.x, mob.center.y) in [(432, 221), (378, 275), (486, 275), (432, 329)]:
                        mob_to_attack = mob
                        break
                if mob_to_attack is None:
                    # If no such mob is found, select the first mob
                    mob_to_attack = mob_rectangles[0]

                point = mob_to_attack.random_point()
                currently_selected = (mob_to_attack.center.x, mob_to_attack.center.y)
                point.click()

                # start/reset timer
                training_time = random.randint(min_training_time, max_training_time)
                print("timer set for " + str(training_time) + " seconds and will end at " +  datetime.datetime.fromtimestamp(time.time() + training_time).strftime('%c'))
                training_end_time = time.time() + training_time

            # if there are mobs and its still training then just continue
            elif len(mobs_beside_player) > 0:
                continue

            else:
                # no monsters, so move and stop timer
                print('moving to another area')
                clickable_tiles = self.get_clickable_tiles()
                #print(len(clickable_tiles))
                if len(clickable_tiles) > 0:
                    random_point = random.choice(clickable_tiles).random_point()
                    if self.can_click_point(random_point):
                        random_point.click()
                min_walk_time, max_walk_time = 2, 4
                # set timer to 0 and set selected mob to null 
                training_end_time = 0
                currently_selected = (None, None)
                time.sleep(random.uniform(min_walk_time, max_walk_time)) # make sure player walks to the right location

            time.sleep(random.uniform(min_timeout, max_timeout))

        while mode == 'DEBUG':
            self.__update_screenshot__()
            self.print_center_colors()
            mobs = self.get_mob_rectangles()
            clickable_tiles = self.get_clickable_tiles()
            #print(clickable_tiles)
            #for tile in clickable_tiles:
                #tile.click()
            for row in self.screen_matrix:
                print(row)
            break
