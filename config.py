import re
import json
import os

RE_FIND_SECTION = re.compile('\[([\w\s\d]+)\]')
RE_FIND_NAMED_ROWS = re.compile('([\w\d]+)=(\s*.+)')
RE_FIND_HEADER = re.compile('#\?\s*config\:(.*)')
RE_FIND_PLACEHOLDER = re.compile('\$[\w\d]+')


class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def parse_str(string):
    """Parse simple row format to 'dotdict' using regular expressions"""

    SECS=[None]
    res_template = dotdict()
    string = string.replace(";", "\n")

    rows = string.split('\n')
    rows = [r.strip() for r in rows]
    row_0 = rows[0].strip()


    if RE_FIND_HEADER.match(row_0) is None:
        return None
    else:
        f_header = RE_FIND_HEADER.findall(row_0)
        if len(f_header) > 0:
            res_template["__description__"] = f_header[0].strip()


    for i in rows:
        f_name = RE_FIND_SECTION.findall(i)
        if len (f_name) > 0:
            if f_name[0] != SECS[-1]:
                NAME = f_name[0]
                new_sec = dotdict()
                if res_template.get(f_name[0]) is None:
                    res_template[f_name[0]] = new_sec

        if i.startswith('#') or len(i) < 1:
            continue

        if RE_FIND_SECTION.match(i) is not None:
            continue

        if RE_FIND_NAMED_ROWS.match(i) is not None:
            f_nr = RE_FIND_NAMED_ROWS.findall(i)
            if len(f_nr) > 0:
                if len(f_nr[0]) > 1:
                    name = f_nr[0][0].strip()
                    value = f_nr[0][1].strip()

                    value = value.split("#")[0].strip()

                    for p in RE_FIND_PLACEHOLDER.findall(value):
                        env = p[1:]
                        value = value.replace(p, os.environ.get(env))

                    if value.startswith("%"):
                        path = value[1:]
                        with open(path, "r") as f:
                            value = f.read().strip()

                    value_split = value.split(',')
                    if len(value_split) > 1:
                        is_type_dict = True if len(value_split[0].split(':')) > 1 else False

                        container_list = []
                        containter_dict = {}

                        for v in value_split:
                            value_split_split = v.split(':')
                            if len(value_split_split) > 1:
                                k, v = value_split_split[0].strip(), value_split_split[1].strip()
                                containter_dict.update({k: v})
                            else:
                                container_list.append(v.strip())

                        value = containter_dict if is_type_dict else container_list

                    kv = dotdict({name: value})
                    res_template[NAME].update(kv)

    return res_template



class Config:
    """Simple wrapper around dotdict content."""

    def __init__(self, filename):

        with open(filename, "r") as f:
            self.__dict__ = parse_str(f.read())

    def __str__(self):
        new_dict = dotdict({k:v for k, v in self.__dict__.items()})
        del new_dict["__description__"]
        json_str = json.dumps(new_dict, indent=8, ensure_ascii=False)
        return f"<cfg: {self.__description__}>" + json_str

    def sections(self):
        return self.__dict__.keys()

    def attributes(self):
        result = []
        for k in self.__dict__.keys():
            if k == "__description__":
                continue
            for i, v in self.__dict__[k].items():
                result.append((k,i,v))
        return result

    def as_table(self, colors=True, sec_indent=False):
        size_signature = [0, 0, 0]
        for attr in self.attributes():
            for i, s in enumerate(size_signature):
                li = len(str(attr[i]))
                if s < li:
                    size_signature[i] = li

        sumsig = sum(size_signature)
        string = "  # " + self.__dict__.__description__ + "\n " + (sumsig + 6) * "=" + "\n"
        last_section = None

        for i, (section, attribute, value) in enumerate(self.attributes()):
            color_num = "1;7" if i % 2 == 0 else 1
            color_start = f"\033[{color_num}m" if colors else ""
            color_end = f"\033[0m" if colors else ""
            s1, s2, s3 = size_signature
            value_str = str(value)

            if last_section is not None and last_section != section and sec_indent:
                string += " " + (sumsig + 6) * " " + "\n\n\n"
            last_section = section
            string += f" {color_start} {section: <{s1}}  {attribute: <{s2}}  {value_str: <{s3}} {color_end}\n"
        string += " " + (sumsig + 6) * "=" + "\n"
        return string
