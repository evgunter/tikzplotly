from ._axis import Axis
from ._tex import *
from ._color import convert_color
from ._utils import px_to_pt
from ._defaults import get_latex_equiv_font_size, latex_text_size_fmt

anchor_dict = {
    "left": "west",
    "right": "east",
    "top": "north",
    "bottom": "south",
    "middle": "",
    "center": "",
    None: ""
}


def get_coordinates(x, y, x_ref, y_ref):
    """Computed the coordinates of an annotation. The coordinates can be relative to the axis or absolute.
    If only one coordinate is relative and the other is absolute, the relative coordinate is converted to absolute,
    using the axis limits : x_return = xmin + x * (xmax - xmin) (idem for y)

    Parameters
    ----------
    x
        input x coordinate
    y
        input y coordinate
    x_ref
        reference of the x coordinate
    y_ref
        reference of the y coordinate

    Returns
    -------
        x coordinate, y coordinate, relative (boolean indicating if the coordinates are relative to the axis)
    """
    # this is the only circumstance where the coordinates are relative
    if x_ref == y_ref == "paper":
        return x, y, True
    # otherwise, we need to convert any relative coordinates to absolute
    def coord_text(name, val):
        return f"\\pgfkeysvalueof{{/pgfplots/{name}min}} + {val}*\\pgfkeysvalueof{{/pgfplots/{name}max}}-{val}*\\pgfkeysvalueof{{/pgfplots/{name}min}}"

    abs_x, abs_y = [(coord_text(name, coord) if ref == 'paper' else coord) for name, coord, ref in zip(['x', 'y'], [x, y], [x_ref, y_ref])]
    return abs_x, abs_y, False

def str_from_annotation(annotation_list, axes: list[Axis], colors_set, height=None, width=None):
    """Create a string of LaTeX code for the annotations of a figure.

    Parameters
    ----------
    annotation_list
        list of annotations from Plotly figure, in fig.layout.annotations
    axis
        Axis object previously created
    colors_set
        colors used in the figure, to be filled with the colors of the annotations
    height, optional
        if None, indicates groupplots are not being used. Otherwise, is the height of the groupplot in pixels
    width, optional
        if None, indicates groupplots are not being used. Otherwise, is the width of the groupplot in pixels

    Returns
    -------
        string of LaTeX code for the annotations
    """
    annotation_str = ""
    if len(annotation_list) > 0:
        for axis in axes:
            axis.add_option("clip", "false")
    for annotation in annotation_list:
        if type(annotation.x) != str:  # the normal case, where we haven't internally added symbolic coordinates
            x_anchor = anchor_dict[annotation.xanchor]
            y_anchor = anchor_dict[annotation.yanchor]
            x_ref = annotation.xref
            y_ref = annotation.yref
            x_coordinate, y_coordinate, relative = get_coordinates(round(annotation.x, 6), round(annotation.y, 6), x_ref, y_ref)
            groupplots = height is not None and width is not None
            # height and width must be set explicitly in this case
            if groupplots:
                if not relative:
                    warn("Only annotations with xref and yref 'paper' are supported when using groupplots.")
                x_coordinate, y_coordinate = f"{x_coordinate} * {px_to_pt(width)}", f"{y_coordinate} * {px_to_pt(height)}"
            anchor_option = f"{y_anchor} {x_anchor}".rstrip()
            if anchor_option != "":
                anchor_option = f"anchor={anchor_option}"
            node_options = anchor_option
            coords = (x_coordinate, y_coordinate)
            symbolic = False
        else:
            node_options = ""
            coords = annotation.x  # we previously set this to the desired string
            symbolic = True
            relative = False
        if annotation.font.color is not None:
            color, _ = convert_color(annotation.font.color, colors_set)
            if node_options != "":
                node_options += ", "
            node_options += f"color={color}"
        if annotation.font.size is not None:
            annotation.text = latex_text_size_fmt(annotation.text, annotation.font.size)
        annotation_str += tex_add_text(coords, annotation.text, options=node_options, relative=relative and not groupplots, axisless=groupplots, symbolic=symbolic)
    return annotation_str
