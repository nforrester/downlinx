import os
from downlinx import *

pipeline = Downlinx(os.path.dirname(os.path.realpath(__file__)))

earth = pipeline.clean_goes_east_large()

monitor_size = Size(1920, 1080)
exact_fit_size = scale_to_fit(earth.size, monitor_size)
comfortable_fit_size = scale_factor(exact_fit_size, 0.9)
earth_scaled = pipeline.resize(earth, comfortable_fit_size)

position_of_earth_on_monitor = centering_offset(earth_scaled.size, monitor_size)
black_background = pipeline.blank('black', monitor_size)
final_background = pipeline.place(earth_scaled, position_of_earth_on_monitor, black_background)

set_background_gnome3(final_background)
