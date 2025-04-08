# Signum

Signum is a simple but powerful icon generation tool.

Currently Signum is only setup to work with SVG files (though you can export to any export format Inkscape supports).
In the future support for more formats may be added.

> [!NOTE]
> Signum is still in development and not ready for production use. Some features may be broken and syntax may change in the future.

## Using Signum

To try out Signum:
 - Make sure you have Python 3 and Inkscape installed
 - Clone this repository
 - Navigate to the cloned repo in your terminal
 - Do `python3 src/main.py [filename]` where `[filename]` is the name of your icon definition file (if blank, `icons.txt` is used)

## Icon Def Files

You tell Signum how to make your icons using an icon definition file.
This file is an INI style config file.
There are a few sections for setting things up (`__config__` and `__palettes__`) and then all other sections are for your icon definitions.

The `__config__` section can have the following options:
- `source` : Directory path containing all your source SVG files.
- `output` : Directory path to output the built icons to.
- `output_sizes` : Space separated list of numbers. These are the different widths to export the images at.
- `output_formats` : Space separated of file extensions for output files, must include the `.` (Example: `.png`)
- `output_command` : Shell command for outputting the files. By default Signum uses inkscape for exporting. The command should be a Python format string which can make use of the following values: `size`, `src`, `dest`, `format`.

For instance, here is the default config values for Signum:

```
[__config__]
source = ./
output = ./dist/{section}/{size}/{name}{format}
output_sizes = 512
output_formats = .png
output_command = inkscape --export-width={size} --export-filename={dest} --export-area-drawing {src}
```

The `__palettes__` section contains palette definitions.
The keys are the palette names, and the values are space separated lists of hex color values, where the odd colors get replaced with the even colors.
For instance:

```
[__palettes__]
red = #333 #300 #777 #700 #bbb #b00 #fff #f00
green = #333 #030 #777 #070 #bbb #0b0 #fff #0f0
blue = #333 #003 #777 #007 #bbb #00b #fff #00f
```

This defines 3 palettes named 'red', 'green', and 'blue', which turn various shades of gray into various shades of red, green, and blue respectively.
