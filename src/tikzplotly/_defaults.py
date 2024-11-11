from warnings import warn

from ._tex import tex_text

PLOTLY_TO_TIKZ_OPTIONS = {
    "solid": "solid",
    "dot": "densely dotted",
    "dash": "densely dashed",
    "longdash": "dashed",
    "dashdot": "densely dashdotted",
}

FONT_SIZE_RANGES = {
    "tiny": 6,  # i.e. \leq 6pt
    "scriptsize": 8,  # i.e. 6pt < \leq 8pt
    "footnotesize": 10,
    "small": 11,
    "normalsize": 12,
    "large": 14,
    "Large": 17,
    "LARGE": 20,
    "huge": 25,
    "Huge": 30,
}

# Default width and height in pixels for plotly figures
PLOTLY_DEFAULT_HEIGHT = 450
PLOTLY_DEFAULT_WIDTH = 700

PLOTLY_DEFAULT_AXIS_DISPLAY_OPTIONS = {
    'xtick style': {'draw': 'none'},
    'ytick style': {'draw': 'none'},
    'x tick label style': {'font': '\\normalsize'},
    'y tick label style': {"left": None, 'font': '\\normalsize'},
    'axis line style': {'draw': 'none'},
    'tick align': 'outside',
    "major tick length": 1.75
}

def get_title_font_size(figure_layout):
    specified_size = figure_layout.title.font.size
    if not specified_size:
        return 20  # default
    return specified_size

def get_axis_title_font_size(axis, figure_layout):
    if axis == "y":
        specified_size = figure_layout.yaxis.title.font.size
    else:
        if axis != "x":
            warn(f"Axis {axis} not recognized. Defaulting to x axis.")
        specified_size = figure_layout.xaxis.title.font.size
    if not specified_size:
        return 0.7 * get_title_font_size(figure_layout)
    return specified_size

def get_latex_equiv_font_size(in_size):
    for size_name, max_size in FONT_SIZE_RANGES.items():
        if in_size <= max_size:
            return size_name
    return "Huge"

def get_axis_latex_font_size(axis, default=FONT_SIZE_RANGES["normalsize"]):
    """
Input: axis object.
    
Output: font size in pt, and a boolean indicating whether the font size was explicitly set (True)
            or if we used a default (False).
"""
    # check if the font size is set
    font_size_pt = None
    for font_size in FONT_SIZE_RANGES.keys():
        if axis.get_option("x tick label style").get(f"\\{font_size}", None) is not None:
            if font_size_pt is not None:
                warn(f"Font size already set to {font_size_pt}pt. Overwriting with {FONT_SIZE_RANGES[font_size]}pt.")
                font_size_pt = FONT_SIZE_RANGES[font_size]
    if font_size_pt is not None:
        return font_size_pt, True
    else:
        return default, False
    
def latex_size_fmt(size):
    """Take a size in pt and output the LaTeX size command for the closest size"""
    return f"\\{get_latex_equiv_font_size(size)}"

def latex_text_size_fmt(text, size):
    """Take text and a size in pt and output the text modified by the closest LaTeX size command"""
    return f"{latex_size_fmt(size)} {tex_text(text)}"

def needs_rotate(labels_key, axis, per_label_width):
    if axis.get_option(labels_key) is None:
        warn(f"Option {labels_key} not found in axis. Not rotating x tick labels.")
        return None

    # if rotate isn't explicitly set, guess whether any xticklabel is longer than the width of a heatmap square
    # and rotate them if so
    font_size_pt, _ = get_axis_latex_font_size(axis)
    
    # check if any xticklabel might be longer than the width of a heatmap square (i.e. check the worst case where all characters are "m")
    max_label_length = max([len(label) for label in axis.get_option(labels_key)])
    if max_label_length * font_size_pt > per_label_width:
        # now check if it's ok to just rotate by 30 degrees or if we have to go to 90
        # if we assume the height of each label is about 2 * font_size_pt (with ascenders and descenders), the width between the top
        # of one label and the bottom of the next is sq_width - font_size_pt / sin(30 degrees) = sq_width - 2 * font_size_pt
        if per_label_width - 2 * 2 * font_size_pt < 0:
            axis.update_option("x tick label style", {"rotate": -90, "right": None}, lambda a, b: b | a)
        else:
            axis.update_option("x tick label style", {"rotate": -30, "right": None}, lambda a, b: b | a)