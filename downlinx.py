#!/usr/bin/env python3

import datetime
from distutils.spawn import find_executable
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
from typing import List, NamedTuple, Optional


def _is_legacy_imagemagick() -> Optional[bool]:
    """Check if legacy imagemagick installed

    Returns True if legacy, False if new version and None if neither
    """

    magick = bool(find_executable("magick"))
    convert = bool(find_executable("convert"))
    if magick:
        return False
    elif convert:
        return True
    return None

LEGACY_IMAGE_MAGICK = _is_legacy_imagemagick()

def _has_whitespace(string: str) -> bool:
    """Return True if a string has whitespace."""
    return bool(re.search(r'\s', string))

def _assert_no_whitespace(string: str) -> None:
    """Assert that a string has no whitespace in it."""
    assert not _has_whitespace(string)

def _quote_if_has_whitespace(string: str) -> str:
    """Single-quote a string if it has whitespace, escaping any single-quotes inside with a backslash."""
    if not _has_whitespace(string):
        return string
    return "'{}'".format(string.replace("'", "\\'"))

def _check_call_with_echo(cmd: List[str], *args, **kwargs) -> None:
    """Like subprocess.check_call(), but it echos the command."""
    print(*map(_quote_if_has_whitespace, cmd))
    subprocess.check_call(cmd, *args, **kwargs)

def _replace_spaces(source_name: str) -> str:
    """Replace the spaces in a source name with underscores to
    produce something nice for filenames."""
    replaced = source_name.replace(' ', '_')
    _assert_no_whitespace(replaced)
    return replaced

def _ensure_directory_exists(filepath: str) -> None:
    """Ensure that the directory required to house the file with the given path exists."""
    dirpath = os.path.dirname(filepath)
    os.makedirs(dirpath, exist_ok=True)

def magick(*args) -> None:
    """Invoke ImageMagick with the specified arguments."""
    cmdline = list(args)

    if LEGACY_IMAGE_MAGICK is False:
        cmdline.insert(0, 'magick')
    elif args[0] != 'convert':
        cmdline.insert(0, 'convert')

    _check_call_with_echo(cmdline)

MAGICK_PNG_COLOR = ['-define', 'png:color-type=6']
"""This needs to always come before the output image name in any ImageMagick command
producing a PNG in order to ensure that the output image has the correct colorspace."""

class Pos(NamedTuple):
    """A position, in pixels, with (0, 0) at the top left, x increasing to the right, and y increasing down."""
    x: int
    y: int

class Size(NamedTuple):
    """A size, in pixels."""
    w: int
    h: int

def scale_factor(orig: Size, factor: float) -> Size:
    """Multiply a Size by a scale factor."""
    return Size(int(orig.w * factor), int(orig.h * factor))

def scale_to_width(orig: Size, width: int) -> Size:
    """Compute Size(width, height) such that it matches the aspect ratio of (orig.w, orig.h)."""
    height = int(width / aspect_ratio(orig))
    return Size(width, height)

def scale_to_height(orig: Size, height: int) -> Size:
    """Compute Size(width, height) such that it matches the aspect ratio of (orig.w, orig.h)."""
    width = int(height * aspect_ratio(orig))
    return Size(width, height)

def scale_to_fit(orig: Size, bounding_box: Size) -> Size:
    """Scale orig so that it fits in bounding_box."""
    if aspect_ratio(orig) > aspect_ratio(bounding_box):
        return scale_to_width(orig, bounding_box.w)
    return scale_to_height(orig, bounding_box.h)

def add_pos(pos1: Pos, pos2: Pos) -> Pos:
    """Vector addition on Pos."""
    return Pos(pos1.x+pos2.x, pos1.y+pos2.y)

def aspect_ratio(size: Size) -> float:
    """Return the aspect ratio of the given Size."""
    return float(size.w) / size.h

def centering_offset(image_size: Size, frame_size: Size, frame_offset: Pos = Pos(0, 0)) -> Pos:
    """Return the offset that will place the image in the center of the frame."""
    return add_pos(frame_offset, Pos(int(frame_size.w/2 - image_size.w/2), int(frame_size.h/2 - image_size.h/2)))

class Image(object):
    """Represents an image in the pipeline. Stores the filename and image size."""

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        cmdline = ['identify', '-ping', '-format', '%w %h', filepath]
        if LEGACY_IMAGE_MAGICK is False:
            cmdline.insert(0, 'magick')
        output = subprocess.check_output(cmdline)
        self.size = Size(*map(int, output.split(b' ')))

class Pipeline(object):
    """Represents the state of a generic image processing pipeline,
    and provides functions for processing images."""

    def __init__(self, pipeline_dir: str) -> None:
        self.images_dir = os.path.join(pipeline_dir, 'images')
        self.generated_image_count = 0

    def _image_path(self, filename: str) -> str:
        """Tack the filename for an image onto the images directory."""
        return os.path.join(self.images_dir, filename)

    def _new(self, image_type: str) -> str:
        """Generate a path for a new image of a given type that you can write to,
        ensure the directory for it exists, and delete the image if it exists."""
        filename = f'generated{self.generated_image_count}.{image_type}'
        filepath = self._image_path(filename)
        _assert_no_whitespace(filepath)
        _ensure_directory_exists(filepath)
        self.generated_image_count += 1
        if os.path.isfile(filepath):
            os.remove(filepath)
        return filepath

    def crop(self, image: Image, offset: Pos, size: Size) -> Image:
        """Crop an Image. Return the new Image."""
        cropped = self._new('png')
        magick('convert', image.filepath, '-crop', f'{size.w}x{size.h}+{offset.x}+{offset.y}', *MAGICK_PNG_COLOR, cropped)
        return Image(cropped)

    def blank(self, color: str, size: Size) -> Image:
        """Create a blank Image with the specified color and dimensions. Return the new Image."""
        new = self._new('png')
        magick('convert', '-size', f'{size.w}x{size.h}', f'canvas:{color}', *MAGICK_PNG_COLOR, new)
        return Image(new)

    def place(self, new: Image, offset: Pos, base: Image) -> Image:
        """Place a new Image on top of a base Image. Return the new Image."""
        combined = self._new('png')
        magick('convert', base.filepath, new.filepath, '-geometry', f'+{offset.x}+{offset.y}', '-composite', *MAGICK_PNG_COLOR, combined)
        return Image(combined)

    def resize(self, image: Image, size: Size) -> Image:
        """Resize an Image. Return the new Image."""
        resized = self._new('png')
        magick('convert', image.filepath, '-resize', f'{size.w}x{size.h}', *MAGICK_PNG_COLOR, resized)
        return Image(resized)

    def to_jpg(self, image: Image) -> Image:
        """Convert an Image to jpg. Return the new Image."""
        jpg = self._new('jpg')
        magick('convert', image.filepath, jpg)
        return Image(jpg)

class Downlinx(Pipeline):
    """Subclass of Pipeline with functions specifically useful for processing satellite images."""
    def __init__(self, pipeline_dir: str) -> None:
        super().__init__(pipeline_dir)

        # Search for sources.json first in the config directory, or fall back to the version shipped with
        # downlinx otherwise.
        script_dir = os.path.dirname(os.path.realpath(__file__))
        sources_path = os.path.join(pipeline_dir, 'sources.json')
        if not os.path.isfile(sources_path):
            sources_path = os.path.join(script_dir, 'sources.json')

        with open(sources_path) as f:
            self.sources = json.load(f)['sources']
        self._assert_unique_names()
        self._assert_all_formats_expected()

    def _assert_unique_names(self) -> None:
        """Assert that all image source names are unique, and remain so under _replace_spaces()."""
        unique_names = set()
        unique_names_no_spaces = set()
        for s in self.sources:
            name = s['name']
            name_no_spaces = _replace_spaces(name)
            if name in unique_names:
                raise Exception(f'Name "{name}" is not unique in the sources list')
            if name_no_spaces in unique_names_no_spaces:
                raise Exception(f'Spaceless name "{name_no_spaces}" is not unique in the sources list')
            unique_names.add(name)
            unique_names_no_spaces.add(name_no_spaces)

    def _assert_all_formats_expected(self) -> None:
        """Assert that all image source URLs return the expected image format."""
        for s in self.sources:
            for sz, u in s['url'].items():
                assert u.endswith('.jpg')

    def _source(self, source_name: str):
        """Retrieve an image source by name."""
        for s in self.sources:
            if s['name'] == source_name:
                return s

    def get(self, source_name: str, size: str) -> Image:
        """Get an Image from one of the sources, or if it's already present and recent enough, don't."""
        filename = '{}_{}.jpg'.format(_replace_spaces(source_name), size)
        filepath = self._image_path(filename)
        _assert_no_whitespace(filepath)
        _ensure_directory_exists(filepath)

        source = self._source(source_name)

        # Don't download again if we already have a sufficiently recent version.
        if os.path.isfile(filepath):
            modification_time = datetime.datetime.fromtimestamp(pathlib.Path(filepath).stat().st_mtime)
            now = datetime.datetime.now()
            age = (now - modification_time).seconds
            if age < source['interval']:
                print(f"Skipping download of {filename}, it's only {age} seconds old.")
                return Image(filepath)

        # Download the image.
        url = source['url'][size]
        _check_call_with_echo(['curl', '-o', filepath, url])
        return Image(filepath)

    def _clean_goes_large(self, source_name: str) -> Image:
        """Return a cleaned up large full disk GOES image from the given source."""
        full_disk = self.get(source_name, 'large')
        full_disk_minus_info_bar = self.crop(full_disk, Pos(0, 0), Size(full_disk.size.w, full_disk.size.h - 47))
        logo_hider = self.blank('black', Size(400, 400))
        full_disk_clean = self.place(logo_hider, Pos(0, full_disk_minus_info_bar.size.h - logo_hider.size.h), full_disk_minus_info_bar)
        return full_disk_clean

    def clean_goes_east_large(self) -> Image:
        """Return a cleaned up large full disk GOES-East image."""
        return self._clean_goes_large('GOES-East Full Disk')

    def clean_goes_west_large(self) -> Image:
        """Return a cleaned up large full disk GOES-West image."""
        return self._clean_goes_large('GOES-West Full Disk')

    def clean_himawari8_large(self) -> Image:
        """Return a cleaned up large full disk Himawari-8 image."""
        full_disk = self.get('Himawari-8 Full Disk', 'large')
        logo_hider = self.blank('black', Size(1000, 450))
        full_disk_clean = self.place(logo_hider, Pos(0, full_disk.size.h - logo_hider.size.h), full_disk)
        return full_disk_clean

def set_background_wm_only(image: Image) -> None:
    """Put an Image up on the desktop background. It should be a JPG because PNGs can have colors distorted.
    This function is for people using a window manager (like XMonad or Openbox) but no desktop environment."""
    _check_call_with_echo(['xloadimage', '-onroot', image.filepath])

# NOTE: set_background_gnome2() has not been tested. It might not work! Consider submitting a PR if you figure it out.
def set_background_gnome2(image: Image) -> None:
    """Put an Image up on the desktop background.
    This function is for people using GNOME 2."""
    _check_call_with_echo(['gconftool-2', '--type=string', '--set', '/desktop/gnome/background/picture_filename', os.path.abspath(image.filepath)])

# NOTE: set_background_gnome3() has not been tested. It might not work! Consider submitting a PR if you figure it out.
def set_background_gnome3(image: Image) -> None:
    """Put an Image up on the desktop background.
    This function is for people using GNOME 3 or Unity."""
    _check_call_with_echo(['gsettings', 'set', 'org.gnome.desktop.background', 'picture-uri', 'file://' + os.path.abspath(image.filepath)])
    _check_call_with_echo(['gsettings', 'set', 'org.gnome.desktop.background', 'picture-options', 'spanned'])

def set_background_xfce(monitor: str, image: Image) -> None:
    """Put an Image up on the desktop background on the specified monitor and workspace (for example, 'screen0/monitorHDMI-0/workspace0').
    Valid monitor identifiers can be listed with 'xfconf-query --channel xfce4-desktop --list'.
    Unlike the other background setting functions, this one work on only one monitor at a time,
    so you will need to compose multiple images (or produce multiple crops).
    This function is for people using Xfce."""
    _check_call_with_echo(['xfconf-query', '--channel', 'xfce4-desktop', '--property', '/backdrop/' + monitor + '/last-image', '--set', os.path.abspath(image.filepath)])

def eog(image: Image) -> None:
    """Open an Image in the EOG image viewer. Useful for debugging. This call will block until EOG exits."""
    _check_call_with_echo(['eog', image.filepath])

def main():
    """Run run.py in the directory specified on the command line."""
    if LEGACY_IMAGE_MAGICK is None:
        print('ImageMagick was not found. Please install!')
        sys.exit(1)
    if len(sys.argv) != 2 or not os.path.isfile(os.path.join(sys.argv[1], 'run.py')):
        print('downlinx.py takes one command line argument: the pipeline directory (containing run.py).')
        print('For example:')
        print('    ./downlinx.py pipelines/simple')
        sys.exit(1)

    run_path = os.path.join(sys.argv[1], 'run.py')
    spec = importlib.util.spec_from_file_location('run', run_path)
    run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run)

if __name__ == '__main__':
    main()
