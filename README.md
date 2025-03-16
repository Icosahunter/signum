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
 - Do `python3 src/main.py [filename]` where `[filename]` is the name of your icon definition file (if blank, 'icons.txt' is used)

## Icon Def Files

You tell Signum how to make your icons using an icon definition file.
This file is a simple text file where each line is an instruction.
If a line begins with a `$` it is a "directive", otherwise the line is an icon definition.

Directives are used to configure Signum, valid directives are:
 - `$source <sourc_dir>` : Sets the directory to look for source icons in.
 - `$output <output_dir>` : Sets the directory to save output icons to.
 - `$export <export_dir> <export_format> <size> [size]...` : Configures the export directory, format (file extension, inlcuding `.`), and sizes (one or more sizes in pixels)
 - `$section <secion_name>` : Signifies the start of a section. Sections become subdirectories when exporting icons.
 - `$palette <color1> <color2> [color1 color2]...` : A palette converts colors. Every 2 colors is a pair, where the first color is mapped to the second. Use hex format starting with `#`.

Icon definitions are of the format `<name> <base_icon> [instruction(args)]...`
Instructions manipulate the icon, valid instructions are:
 - `insert(<id>, <icon>)` : Inserts the icon by the name of `<icon>` at position of the rectangle with id of `<id>`.
 - `color(<palette>)` : Applies the palette by the name of `<palette>` to the icon.
 - `rotate(<deg>)` : Rotates the icon about it's center by `<deg>` degrees.
