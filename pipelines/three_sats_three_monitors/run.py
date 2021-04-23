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

himawari8 = pipeline.clean_himawari8_large()
goes_west = pipeline.clean_goes_west_large()
goes_east = pipeline.clean_goes_east_large()

himawari8_scaled = pipeline.resize(himawari8, scale_to_fit(himawari8.size, monitor1_size))
goes_west_scaled = pipeline.resize(goes_west, scale_to_fit(goes_west.size, monitor2_size))
goes_east_scaled = pipeline.resize(goes_east, scale_to_fit(goes_east.size, monitor3_size))

bg = pipeline.blank('black', screen_size)
bg = pipeline.place(himawari8_scaled, centering_offset(himawari8_scaled.size, monitor1_size, monitor1_pos), bg)
bg = pipeline.place(goes_west_scaled, centering_offset(goes_west_scaled.size, monitor2_size, monitor2_pos), bg)
bg = pipeline.place(goes_east_scaled, centering_offset(goes_east_scaled.size, monitor3_size, monitor3_pos), bg)
set_background_wm_only(pipeline.to_jpg(bg))
