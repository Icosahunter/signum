import xml.etree.ElementTree as ET
from pathlib import Path
from copy import deepcopy
from itertools import chain
import subprocess
import shlex
import re
import sys

class Icon:
    def __init__(self, src_filepath, section=None):
        self.src = src_filepath
        self.tree = ET.parse(self.src)
        self.root = self.tree.getroot()
        self.content = self.tree.findall('./{*}g')[0]
        viewbox = self.root.attrib['viewBox'].split()
        self.size = float(viewbox[2]), float(viewbox[3])
        self.section = section

    def write(self, filepath):
        self.tree.write(filepath)

    def color(self, palette):
        for n in self.tree.findall('.//*[@style]'):
            for k, v in palette.items():
                n.attrib['style'] = n.attrib['style'].replace('stroke:'+k, 'stroke:'+v)
                n.attrib['style'] = n.attrib['style'].replace('fill:'+k, 'fill:'+v)

    def insert(self, id, icon):

        elem = self.tree.findall(f".//*[@id='__{id}__']")

        if len(elem):

            elem = elem[0]
            elem_parent = self.tree.findall(f".//*[@id='__{id}__']..")[0]

            if icon:
                x = float(elem.attrib['x'])
                y = float(elem.attrib['y'])
                w = float(elem.attrib['width'])
                h = float(elem.attrib['height'])

                w3, h3 = Icon._fit_size(icon.size, (w, h))
                scale = (w3/icon.size[0])
                x3 = x + (w/2) - (w3/2)
                y3 = y + (h/2) - (h3/2)

                insert_node = deepcopy(icon.content)
                if 'transform' in insert_node.attrib:
                    insert_node.attrib['transform'] += f' translate({x3} {y3}) scale({scale})'
                else:
                    insert_node.attrib['transform'] = f' translate({x3} {y3}) scale({scale})'

                elem_parent.append(insert_node)

            elem_parent.remove(elem)

    def rotate(self, deg):
        x = self.size[0] / 2
        y = self.size[1] / 2
        if 'transform' in self.content.attrib:
            self.content.attrib['transform'] += f' rotate({deg} {x} {y})'
        else:
            self.content.attrib['transform'] = f' rotate({deg} {x} {y})'

    @staticmethod
    def _fit_size(size, desired_size):
        r1 = size[0] / size[1]
        r2 = desired_size[0] / desired_size[1]
        if r1 > r2:
            w = desired_size[0]
            h = (desired_size[0]/size[0])*size[1]
        else:
            h = desired_size[1]
            w = (desired_size[1]/size[1])*size[0]
        return w, h

class Environment:
    def __init__(self, file):
        self.palettes = {}
        self.template = ['name', 'base', 'palette']
        self.source_dir = Path('./')
        self.output_dir = Path('./output')
        self.config = Path(file)
        self.export_cmd = 'inkscape --export-width={size} --export-filename={dest} --export-area-drawing {src}'
        self.export_sizes = ['256']
        self.export_format = '.png'
        self.export_dir = Path('./dist')
        self.icons = {}
        self.section = ''
        self.load_icons()

    def load_icons(self):
        self.icons.clear()
        for file in self.source_dir.glob('**/*.svg'):
            self.icons[file.stem] = Icon(file)

    def do_inst(self, icon, inst):
        inst, args = inst.split('(')
        args = args[0:-1].split()
        if inst == 'insert':
            icon.insert(args[0], self.icons[args[1]])
        elif inst == 'color':
            icon.color(self.palettes[args[0]])
        elif inst == 'rotate':
            icon.rotate(args[0])

    def do_palette(self, palette_str):
        colors = palette_str.split()[1:]
        name = colors.pop(0)
        colors = dict(zip(colors[::2], colors[1::2]))
        self.palettes[name] = colors

    def do_source(self, source_str):
        self.source_dir = Path(source_str.split()[1])
        self.load_icons()

    def do_output(self, output_str):
        self.output_dir = Path(output_str.split()[1])

    def do_section(self, section_str):
        self.section = section_str.split()[1]

    def do_export(self, export_str):
        split = export_str.split()
        self.export_dir = Path(split[1])
        self.export_format = split[2]
        self.export_sizes = split[3:]

    def do_icon(self, icon_str):
        icon_def = re.findall(r"[\w\-\.]+(?:\([\w\-\.\t ]+\))?", icon_str)
        name = icon_def[0]
        base = icon_def[1]
        icon = deepcopy(self.icons[base])
        icon.section = self.section
        for inst in icon_def[2:]:
            self.do_inst(icon, inst)
        dest = (self.output_dir / name).with_suffix('.svg')
        dest.parent.mkdir(exist_ok=True, parents=True)
        self.icons[name] = icon

    def evaluate(self):
        with open(self.config) as f:
            for line in f:
                if not line.isspace():
                    if line.startswith('$source'):
                        self.do_source(line)
                    elif line.startswith('$output'):
                        self.do_output(line)
                    elif line.startswith('$export'):
                        self.do_export(line)
                    elif line.startswith('$section'):
                        self.do_section(line)
                    elif line.startswith('$palette'):
                        self.do_palette(line)
                    else:
                        self.do_icon(line)

    def output(self):
        for k, v in self.icons.items():
            v.write((self.output_dir / k).with_suffix('.svg'))

    def export(self):
        for k, v in self.icons.items():
            if v.section:
                for size in self.export_sizes:
                    dest = (self.export_dir / v.section / size / k).with_suffix(self.export_format)
                    dest.parent.mkdir(exist_ok=True, parents=True)
                    subprocess.run(shlex.split(self.export_cmd.format(size=size, src=v.src, dest=dest)))

if __name__ == '__main__':
    if len(sys.argv) > 1:
        env = Environment(sys.argv[1])
    else:
        env = Environment('icons.txt')
    env.evaluate()
    env.output()
    env.export()
