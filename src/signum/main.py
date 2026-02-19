import xml.etree.ElementTree as ET
from pathlib import Path
from copy import deepcopy
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
        ET.register_namespace('', 'http://www.w3.org/2000/svg')
        self.root = self.tree.getroot()
        content = self.tree.findall('./{*}g')[0]
        group = ET.Element('g')
        self.root.remove(content)
        group.append(content)
        self.root.append(group)
        self.content = group
        viewbox = self.root.attrib['viewBox'].split()
        self.size = float(viewbox[2]), float(viewbox[3])
        self.section = section

    def write(self, filepath):
        self.tree.write(filepath)

    def color(self, palette):
        for n in self.tree.findall('.//*[@style]'):
            res = re.search('stroke:#[\\dabcdef]*', n.attrib['style'])
            if res and res.group(0)[7:] in palette.keys():
                n.attrib['style'] = n.attrib['style'].replace(res.group(0), 'stroke:'+palette[res.group(0)[7:]])
            res = re.search('fill:#[\\dabcdef]*', n.attrib['style'])
            if res and res.group(0)[5:] in palette.keys():
                n.attrib['style'] = n.attrib['style'].replace(res.group(0), 'fill:'+palette[res.group(0)[5:]])

    def clean_inserts(self):
        inserts = re.findall(r'id="([a-zA-Z0-9:_\.\-]+)\.INS"', str(ET.tostring(self.root)))
        for insert in inserts:
            self.insert(insert)

    def insert(self, id, icon=None, scale_stroke_width=False):

        elem = self.tree.findall(f".//*[@id='{id}.INS']")

        if len(elem):

            elem = elem[0]
            elem_parent = self.tree.findall(f".//*[@id='{id}.INS']..")[0]

            if icon:
                x = float(elem.attrib['x'])
                y = float(elem.attrib['y'])
                w = float(elem.attrib['width'])
                h = float(elem.attrib['height'])
                tx = elem.attrib.get('transform', '')

                w3, h3 = Icon._fit_size(icon.size, (w, h))
                scale = (w3/icon.size[0])
                x3 = x + (w/2) - (w3/2)
                y3 = y + (h/2) - (h3/2)

                if not scale_stroke_width:
                    icon.scale_stroke_width(1/scale)

                insert_group = ET.Element('g')
                insert_group.attrib['transform'] = tx + f' translate({x3} {y3}) scale({scale})'

                insert_node = icon.content

                insert_group.append(insert_node)

                elem_parent.append(insert_group)

            elem_parent.remove(elem)

    def mirror(self, dir='v'):

        if dir == 'v':
            self.content.attrib['transform'] = self.content.attrib.get('transform', '') + f' scale(-1, 1) translate({-self.size[0]}, 0)'
        elif dir == 'h':
            self.content.attrib['transform'] = self.content.attrib.get('transform', '') + f' scale(1, -1) translate(0, {-self.size[1]})'

    def rotate(self, deg):
        x = self.size[0] / 2
        y = self.size[1] / 2
        self.content.attrib['transform'] = self.content.attrib.get('transform', '') + f' rotate({deg} {x} {y})'

    def scale_stroke_width(self, scale):
        for n in self.tree.findall('.//*[@style]'):
            n.attrib['style'] = re.sub(r'stroke-width:(\d*\.?\d+);', lambda x : f'stroke-width:{scale*float(x.group(1))};', n.attrib['style'])

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
            if '(' in x:
                inst, args = x.split('(')
                args = args[0:-1].split()
            else:
                inst = x
                args = []
            self.inst.append([inst, *args])
        self.deps = set([x[2] for x in self.inst if x[0] == 'insert' and len(x) > 2])
        self.deps.add(self.base)

class Environment:
    def __init__(self, file=None):
        self.palettes = {}
        self.icon_defs = {}
        self.icons = {}
        self.scale_stroke_width = True
        self.clean_inserts = False
        if file:
            self.load(file)

    def load(self, file):
        parser = ConfigParser()
        parser.read(file)
        self.load_config(parser)
        self.load_source_files()
        self.load_palettes(parser['__palettes__'])
        self.load_icon_defs({x:parser[x] for x in parser.sections() if x not in ['__config__', '__palettes__']})

    def load_config(self, parser):
        self.source = Path(parser.get('__config__', 'source', fallback='./'))
        self.output = parser.get('__config__', 'output', fallback='./dist/{section}/{size}/{name}{format}')
        self.output_sizes = [int(x) for x in parser.get('__config__', 'output_sizes', fallback='512').split()]
        self.output_formats = parser.get('__config__', 'output_formats', fallback='.png').split()
        self.output_command = parser.get('__config__', 'output_command', fallback='inkscape --export-width={size} --export-filename={dest} --export-area-drawing {src}')
        self.scale_stroke_width = parser.getboolean('__config__', 'scale_stroke_width', fallback=True)
        self.clean_inserts = parser.getboolean('__config__', 'clean_inserts', fallback=False)

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
                icon_to_insert = deepcopy(self.icons[inst[2]]) if len(inst) > 2 else None
                base.insert(inst[1], icon_to_insert, self.scale_stroke_width)
            elif inst[0] == 'rotate':
                base.rotate(inst[1] if len(inst) > 1 else '90')
            elif inst[0] == 'color':
                base.color(self.palettes[inst[1]])
            elif inst[0] == 'mirror':
                print('WARNING: The mirror instruction is experimental and may not work properly in some circumstances.')
                base.mirror(inst[1] if len(inst) > 1 else 'v')
            elif inst[0] == 'clean':
                base.clean_inserts()
            else:
                raise Exception(f'Undefined instruction "{inst}"')
        return base

    def build_icons(self):
        deps_list = {k:v.deps for k, v in self.icon_defs.items()}
        sorted_icons = toposort_flatten(deps_list)
        sorted_icons = [x for x in sorted_icons if x not in self.icons]
        for icon in sorted_icons:
            if icon in self.icon_defs:
                self.icons[icon] = self.build_icon(self.icon_defs[icon])
            else:
                raise Exception(f'Undefined icon "{icon}"')

    def output_icons(self):
        temp_dir = TemporaryDirectory()
        temp_dir_path = Path(temp_dir.name)

        for name, icon in self.icons.items():
            if icon.section != '__temporary__' and icon.section != None:
                if self.clean_inserts:
                    icon.clean_inserts()
                icon.write((temp_dir_path / name).with_suffix('.svg'))
                for format in self.output_formats:
                    if format == '.svg':
                        src = (temp_dir_path / name).with_suffix('.svg')
                        dest = Path(self.output.format(section=icon.section, size='scalable', name=name, format=format))
                        dest.parent.mkdir(exist_ok=True, parents=True)
                        shutil.copy(src, dest)
                    else:
                        for size in self.output_sizes:
                            src = (temp_dir_path / name).with_suffix('.svg')
                            dest = Path(self.output.format(section=icon.section, size=size, name=name, format=format))
                            dest.parent.mkdir(exist_ok=True, parents=True)
                            cmd = self.output_command.format(size=size, src=src, dest=dest, format=format)
                            subprocess.run(shlex.split(cmd))

    def run(self):
        self.build_icons()
        self.output_icons()

def run():
    if len(sys.argv) > 1:
        env = Environment(sys.argv[1])
    else:
        env = Environment('icons.txt')
    env.run()

if __name__ == '__main__':
    run()
