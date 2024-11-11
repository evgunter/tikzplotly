from tikzplotly._color import convert_color
from tikzplotly._utils import dict_to_tex_str, px_to_pt
from tikzplotly._defaults import PLOTLY_TO_TIKZ_OPTIONS
from warnings import warn

class FakeShape:
    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)
    def __eq__(self, other):
        return self.__dict__ == other.__dict__
    # return None if we call getattr for an attribute that doesn't exist
    def __getattr__(self, name):
        if name not in self.__dict__:
            return None
        return self.__dict__[name]

def draw_shape(shape, axis, colors_set):
    # TODO: this doesn't work properly for categorical axes; plotly seems to set them 0-1 but i'm setting them as the number of categories
    # (and it seems to be measured from the middle of the bar rather than the edge of the plot)
    
    if shape.type == "line":
        options = {}
        start_x, start_y = shape.x0, shape.y0
        end_x, end_y = shape.x1, shape.y1
        if axis.get_option("xtick") is not None and len(axis.get_option("xtick")) > 1:  # this is supposed to indicate that it's a categorical axis, but this may not always be true
            sorted_xticks = sorted(axis.get_option("xtick"))
            if set([start_x, end_x]) != set([0,1]):
                warn(f"Shapes on a categorical axis are not fully supported; the line will be drawn all the way across the plot.")
            # it won't be drawn outside of the plot area, so it's ok that we have a big margin here
            start_x = sorted_xticks[0] - max(1, sorted_xticks[1] - sorted_xticks[0])
            end_x = sorted_xticks[-1] + max(1, sorted_xticks[-1] - sorted_xticks[-2])
        if axis.get_option("ytick") is not None and len(axis.get_option("ytick")) > 1:  # this is supposed to indicate that it's a categorical axis, but this may not always be true
            sorted_yticks = sorted(axis.get_option("ytick"))
            if set([start_y, end_y]) != set([0,1]):
                warn(f"Shapes on a categorical axis are not fully supported; the line will be drawn all the way across the plot.")
            # it won't be drawn outside of the plot area, so it's ok that we have a big margin here
            start_y = sorted_yticks[0] - max(1, sorted_yticks[1] - sorted_yticks[0])
            end_y = sorted_yticks[-1] + max(1, sorted_yticks[-1] - sorted_yticks[-2])
        if shape.line.dash:
            dash = PLOTLY_TO_TIKZ_OPTIONS.get(shape.line.dash, None)
            if dash is None:
                dash = "solid"
                warn(f"Shape: Line dash {shape.line.dash} is not supported yet. Defaulting to solid.")
            options[dash] = None
        if shape.line.width:
            options["line width"] = px_to_pt(shape.line.width)
        else:
            # plotly's lines seem to default to thick latex lines for dotted/dashed lines and normal for solid
            if shape.line.dash:
                if dash != "solid":
                    options["thick"] = None
        if shape.line.color:
            options["color"], _ = convert_color(shape.line.color, colors_set)
        return f"\\draw[{dict_to_tex_str(options)}] ({start_x},{start_y}) -- ({end_x},{end_y});\n"
    elif shape.type == "rect":
        start_x, start_y = shape.x0, shape.y0
        end_x, end_y = shape.x1, shape.y1
        return f"\\draw ({start_x},{start_y}) rectangle ({end_x},{end_y});\n"
    else:
        warn(f"Shape: Type {shape.type} is not supported yet; ignoring.")
        return ""
