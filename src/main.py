import xml.etree.ElementTree as ET
from pathlib import Path
from copy import deepcopy
from itertools import chain
import subprocess
import shlex
import re
import sys
from configparser import ConfigParser
from toposort import toposort_flatten
from tempfile import TemporaryDirectory
import shutil

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

class IconDef:

    def __init__(self, icon_str, section):
        icon_def = re.findall(r"[\w\-\.]+(?:\([\w\-\.\t ]+\))?", icon_str)
        self.section = section
        self.base = icon_def[0]
        self.inst = []
        for x in icon_def[1:]:
            inst, args = x.split('(')
            args = args[0:-1].split()
            self.inst.append([inst, *args])
        self.deps = set([x[2] for x in self.inst if x[0] == 'insert'])
        self.deps.add(self.base)

class Environment:
    def __init__(self, file=None):
        self.palettes = {}
        self.icon_defs = {}
        self.icons = {}
        if file:
            self.load(file)

    def load(self, file):
        parser = ConfigParser()
        parser.read(file)
        self.load_config(parser['__config__'])
        self.load_source_files()
        self.load_palettes(parser['__palettes__'])
        self.load_icon_defs({x:parser[x] for x in parser.sections() if x not in ['__config__', '__palettes__']})

    def load_config(self, config):
        self.source = Path(config.get('source', './'))
        self.output = config.get('output', './dist/{section}/{size}/{name}{format}')
        self.output_sizes = [int(x) for x in config.get('output_sizes', '512').split()]
        self.output_formats = config.get('output_formats', ['.png'])
        self.output_command = config.get('output_command', 'inkscape --export-width={size} --export-filename={dest} --export-area-drawing {src}')

    def load_source_files(self):
        for file in self.source.glob('**/*.svg'):
            self.icons[file.stem] = Icon(file)

    def load_palettes(self, palettes):
        for k, v in palettes.items():
            colors = v.split()
            self.palettes[k] = dict(zip(colors[::2], colors[1::2]))

    def load_icon_defs(self, sections):
        for section_name, section in sections.items():
            for icon_name, icon in section.items():
                self.icon_defs[icon_name] = IconDef(icon, section_name)

    def build_icon(self, icon_def):
        #if icon_def.base in self.icons:
        base = deepcopy(self.icons[icon_def.base])
        base.section = icon_def.section
            #else:
        #    icon_file = next(self.source.glob(f'**/{icon_def.base}.svg'))
        #    base = Icon(icon_file, icon_def.section)
        for inst in icon_def.inst:
            if inst[0] == 'insert':
                base.insert(inst[1], self.icons[inst[2]])
            elif inst[0] == 'rotate':
                base.rotate(inst[1])
            elif inst[0] == 'color':
                base.color(self.palettes[inst[1]])
        return base

    def build_icons(self):
        deps_list = {k:v.deps for k, v in self.icon_defs.items()}
        sorted_icons = toposort_flatten(deps_list)
        sorted_icons = [x for x in sorted_icons if x not in self.icons]
        for icon in sorted_icons:
            self.icons[icon] = self.build_icon(self.icon_defs[icon])

    def output_icons(self):
        temp_dir = TemporaryDirectory()
        temp_dir_path = Path(temp_dir.name)

        for name, icon in self.icons.items():
            if icon.section != '__temporary__' and icon.section != None:
                icon.write((temp_dir_path / name).with_suffix('.svg'))
                for format in self.output_formats:
                    if format == '.svg':
                        src = (temp_dir_path / name).with_suffix('.svg')
                        dest = self.output.format(section=icon.section, size='scalable', name=name, format=format)
                        shutil.copy(src, dest)
                    for size in self.output_sizes:
                        src = (temp_dir_path / name).with_suffix('.svg')
                        dest = Path(self.output.format(section=icon.section, size=size, name=name, format=format))
                        dest.parent.mkdir(exist_ok=True, parents=True)
                        cmd = self.output_command.format(size=size, src=src, dest=dest, format=format)
                        subprocess.run(shlex.split(cmd))

    def run(self):
        self.build_icons()
        self.output_icons()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        env = Environment(sys.argv[1])
    else:
        env = Environment('icons.txt')
    env.run()
