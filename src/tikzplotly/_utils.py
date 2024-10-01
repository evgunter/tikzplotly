import re
import warnings
from math import floor
import numpy as np
from ._tex import tex_text, get_tikz_colorscale

# Default width and height in pixels for plotly figures
PLOTLY_DEFAULT_HEIGHT = 450
PLOTLY_DEFAULT_WIDTH = 700

rep_digit = {'0': 'Z', '1': 'O', '2': 'T', '3': 'Th', '4': 'F', '5': 'Fi', '6': 'S', '7': 'Se', '8': 'E', '9': 'N'}
rep_digit = dict((re.escape(k), v) for k, v in rep_digit.items())
pattern_digit = re.compile("|".join(rep_digit.keys()))

def replace_all_digits(text):
    """Replace all digits in a string with their corresponding letter.

    Parameters
    ----------
    text
        string to replace digits in

    Returns
    -------
        string with digits replaced by their corresponding letter
    """
    return pattern_digit.sub(lambda m: rep_digit[re.escape(m.group(0))], text)

rep_mounts = {"January": '1', 'February': '2', 'March': '3', 'April': '4', 'May': '5', 'June': '6', 'July': '7', 'August': '8', 'September': '9', 'October': '10', 'November': '11', 'December': '12',
              'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6, 'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12}
rep_mounts = dict((re.escape(k), v) for k, v in rep_mounts.items())
pattern_mounts = re.compile("|".join(rep_mounts.keys()))

def replace_all_mounts(text):
    """Replace all mounts in a string with their corresponding number.

    Parameters
    ----------
    text
        string to replace mounts in

    Returns
    -------
        string with mounts replaced by their corresponding number
    """
    return pattern_mounts.sub(lambda m: rep_mounts[re.escape(m.group(0))], text)


def sanitize_text(text: str):
    return "".join(map(sanitize_char, text))

def sanitize_char(ch):
    if ch in "[]{}= ": return f"x{ord(ch):x}"
    # if not ascii, return hex
    if ord(ch) > 127: return f"x{ord(ch):x}"
    # if not printable, return hex
    if not ch.isprintable(): return f"x{ord(ch):x}"
    return ch

def sanitize_TeX_text(text: str):
    s = "".join(map(sanitize_TeX_char, text))
    if '[' in s or ']' in s:
        return "{" + s + "}"
    return s

def sanitize_TeX_char(ch):
    if ch in "_{}": return f"\\{ch}"
    # if not ascii, return hex
    if ord(ch) > 127:
        warnings.warn(f"Character {ch} has been replaced by \"x{ord(ch):x}\" in output file")
        return f"x{ord(ch):x}"
    # if not printable, return hex
    if not ch.isprintable():
        warnings.warn(f"Character {ch} has been replaced by \"x{ord(ch):x}\" in output file")
        return f"x{ord(ch):x}"
    return ch

def px_to_pt(px):
    """Convert size in pixel to a size in point

    Parameters
    ----------
    px
        size in pixel

    Returns
    -------
    float
        size in point
    """
    pt = px * .75
    if floor(pt) == pt: return int(pt)
    else: return pt

class Colorscale:
    def __init__(self, colorscale, name="mycolor"):
        self.colorscale = colorscale
        self.name = name

    def __str__(self):
        return get_tikz_colorscale(self.colorscale, self.name)

    def __eq__(self, other):
        return self.colorscale == other.colorscale and self.name == other.name

def dict_to_tex_str(dictionary, sep=" "):
    """Convert a dictionary of options to a string of options for TikZ.

    Parameters
    ----------
    dictionary
        dictionary of options to convert to tex format
    sep, optional
        separator between options, by default " "

    Returns
    -------
    string
        string representing the dictionary for TikZ. Does not include the enclosing brackets, so it can be used with both [] and {}
    """
    lst = []
    for key, value in dictionary.items():
        if value is None:
            lst.append(f"{key}")
        elif isinstance(value, dict):
            lst.append(f"{key}=" + "{" + f"{dict_to_tex_str(value, sep)}" + "}")
        elif isinstance(value, str):
            lst.append(f"{key}={tex_text(value)}")
        elif isinstance(value, list):
            lst.append(f"{key}=" + "{" + f"{f',{sep}'.join(map(str, value))}" + "}")
        elif isinstance(value, int) or isinstance(value, float):
            lst.append(f"{key}={value}")
        elif isinstance(value, tuple):  # multiple arguments
            lst.append(f"{key}=" + "".join(["{" + dict_to_tex_str(v, sep) + "}" for v in value]))
        elif isinstance(value, Colorscale):
            lst.append(f"{key}={str(value)}")
        else:
            warnings.warn(f"Converting value {value} of type {type(value)} to string")
            lst.append(f"{key}={tex_text(str(value))}")
    return f",{sep}".join(lst)

def get_ticks_str(data, nticks):
    indices = np.arange(len(data))
    if nticks is not None:
        data_ = data[::len(data)//(nticks-1)]
        data = np.append(data_, [data[-1]])
        indices_ = indices[::len(indices)//(nticks-1)]
        indices = np.append(indices_, [indices[-1]])

    ticks = "{"
    ticklabels = "{"
    for i, val in zip(indices, data):
        ticks += str(i) + ","
        ticklabels += str(val) + ","
    ticks = ticks[:-1] + "}"
    ticklabels = ticklabels[:-1] + "}"

    return ticks, ticklabels

def get_tasks(df, prefix):
    return [t for t in df.get_column("task").unique() if t.startswith(prefix)]
