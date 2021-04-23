import os
from downlinx import *

pipeline = Downlinx(os.path.dirname(os.path.realpath(__file__)))

screen_size = Size(5040, 1920)

monitor1_pos = Pos(0, 0)
monitor1_size = Size(1200, 1920)

monitor2_pos = Pos(1200, 240)
monitor2_size = Size(2560, 1440)

monitor3_pos = Pos(3760, 240)
monitor3_size = Size(1280, 1024)

tmahlmann1 = Image('/home/neil/media/Pictures/sn8/Eo1W_1NWMAM7u1r.jpeg')
tmahlmann2 = Image('/home/neil/media/Pictures/sn8/Eo1PpUvWEAANRYZ.jpeg')

tmahlmann1_scaled = pipeline.resize(tmahlmann1, scale_to_height(tmahlmann1.size, monitor1_size.h))
tmahlmann1_cropped = pipeline.crop(tmahlmann1_scaled, Pos(800, 0), monitor1_size)

tmahlmann2_scaled = pipeline.resize(tmahlmann2, scale_to_height(tmahlmann2.size, monitor3_size.h+20))
tmahlmann2_cropped = pipeline.crop(tmahlmann2_scaled, Pos(0, 0), monitor3_size)

himawari8 = pipeline.clean_himawari8_large()
goes_east = pipeline.clean_goes_east_large()
earth_box_size = Size(int(monitor2_size.w/2), monitor2_size.h)
himawari8_scaled = pipeline.resize(himawari8, scale_to_fit(himawari8.size, earth_box_size))
goes_east_scaled = pipeline.resize(goes_east, scale_to_fit(goes_east.size, earth_box_size))

bg = pipeline.blank('black', screen_size)
bg = pipeline.place(tmahlmann1_cropped, monitor1_pos, bg)
bg = pipeline.place(tmahlmann2_cropped, monitor3_pos, bg)
bg = pipeline.place(goes_east_scaled, centering_offset(goes_east_scaled.size, earth_box_size, monitor2_pos), bg)
bg = pipeline.place(himawari8_scaled, centering_offset(goes_east_scaled.size, earth_box_size, add_pos(monitor2_pos, Pos(earth_box_size.w, 0))), bg)
set_background_wm_only(pipeline.to_jpg(bg))
