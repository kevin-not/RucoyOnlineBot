import os

from datetime import datetime

from ahk import AHK

from rucoy_online import RucoyOnline
import geometry

def shutdown():
    fin = open("data.txt", "a")
    # current date and time
    fin.write(f'\nFinished at: {datetime.now().strftime("%m/%d/%Y, %H:%M:%S")}')
    fin.close()
    window.close()
    #os.system("shutdown /s /t 1")

s = 'C:\\Program Files\\AutoHotkey\\AutoHotKey.exe'
ahk = AHK()

window = ahk.win_get(title='BlueStacks App Player')
if window is None or not window.exist:
    raise Exception("BlueStacks window not active")
window.move(x=0, y=0, width=900, height=520)  # is HARDCODED for 900 x 520 resolution?
window.activate()
bluestacks_window_rectangle = geometry.create_rectangle_from_ahk_window(window)
rucoy = RucoyOnline(bluestacks_window_rectangle)
rucoy.automate_training()
#shutdown()


