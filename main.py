import xml.etree.ElementTree as ET
from pathlib import Path
from copy import deepcopy

class Icon:
    def __init__(self, src_filepath):
        self.src = src_filepath
        self.tree = ET.parse(self.src)
        self.root = self.tree.getroot()
        self.content = self.tree.findall('/{*}g')[0]
        viewbox = self.root.attrib['viewBox'].split()
        self.size = float(viewbox[2]), float(viewbox[3])

    def write(self, filepath):
        self.tree.write(filepath)

    def color(self, palette):
        for n in self.tree.findall('//*[@style]'):
            for k, v in palette.items():
                n.attrib['style'] = n.attrib['style'].replace('stroke:'+k, 'stroke:'+v)
                n.attrib['style'] = n.attrib['style'].replace('fill:'+k, 'fill:'+v)

    def insert(self, icon, id):

        elem = self.tree.findall(f"//*[@id='__{id}__']")

        if len(elem):

            elem = elem[0]
            elem_parent = self.tree.findall(f"//*[@id='__{id}__']..")[0]

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
                insert_node.attrib['transform'] = f'translate({x3} {y3}) scale({scale})'

                elem_parent.append(insert_node)

            elem_parent.remove(elem)

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
        self.source = Path('./')
        self.output = Path('./output')
        self.config = Path(file)

    def do_palette(self, palette_str):
        colors = palette_str.split()[1:]
        name = colors.pop(0)
        colors = dict(zip(colors[::2], colors[1::2]))
        self.palettes[name] = colors

    def do_template(self, template_str):
        self.template = template_str.split()[1:]

    def do_source(self, source_str):
        self.source = Path(source_str.split()[1])

    def do_output(self, output_str):
        self.output = Path(output_str.split()[1])

    def do_icon(self, icon_str):
        icon_zip = list(zip(self.template, icon_str.split()[1:]))
        base = [x[1] for x in icon_zip if x[0]=='base'][0]
        name = [x[1] for x in icon_zip if x[0]=='name'][0]
        icon = Icon((self.source / base).with_suffix('.svg'))
        for k, v in icon_zip:
            if k == 'palette':
                icon.color(self.palettes[v])
            elif k not in ['base', 'name']:
                if v == '.':
                    icon.insert(None, k)
                else:
                    icon.insert(Icon((self.source / v).with_suffix('.svg')), k)
        dest = (self.output / name).with_suffix('.svg')
        dest.parent.mkdir(exist_ok=True, parents=True)
        icon.write(dest)

    def run(self):
        with open(self.config) as f:
            for line in f:
                if line.startswith('source'):
                    self.do_source(line)
                elif line.startswith('output'):
                    self.do_output(line)
                elif line.startswith('template'):
                    self.do_template(line)
                elif line.startswith('palette'):
                    self.do_palette(line)
                elif line.startswith('icon'):
                    self.do_icon(line)

env = Environment('icons.txt')
env.run()
