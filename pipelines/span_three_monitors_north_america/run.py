import os
from downlinx import *

pipeline = Downlinx(os.path.dirname(os.path.realpath(__file__)))

full_disk_clean = pipeline.clean_goes_east_large()
screen_size = Size(5040, 1920)
full_disk_scaled = pipeline.resize(full_disk_clean, scale_to_width(full_disk_clean.size, screen_size.w))
full_disk_cropped = pipeline.crop(full_disk_scaled, Pos(0, 0), screen_size)
set_background_wm_only(pipeline.to_jpg(full_disk_cropped))
