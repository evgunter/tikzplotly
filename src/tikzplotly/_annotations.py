from ._axis import Axis
from ._tex import *
from ._color import convert_color

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

def get_groupplots_coordinates(x, y, x_ref, y_ref, groupplots_info):
    """Compute the coordinates of an annotation when using groupplots. Coordinates must be relative.

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
    groupplots_info
        information about the dimensions of the groupplot

    Returns
    -------
        x coordinate, y coordinate
    """
    # In the case of group plots, we can't use axis coordinates since they refer to the axis coordinates
    # of a single subplot (the last one added, lower right). To correctly position annotations which are not
    # in the last subplot, we would need to know not just the height of the axis in the last subplot, but
    # the height of the entire subplot including the title, axis labels, etc.).
    # However, we can instead use coordinates in the overall plot; there, since we know the
    # height of the subplots and the margin sizes, we can correctly convert the coordinates.

    # The coordinates Plotly uses are the fraction of the overall height/width, and are relative to the lower left corner
    # The coordinates LaTeX uses are the fraction of a subplot's unit's height/width, and are relative to the lower left corner of the last subplot axis
    overall_height = groupplots_info["overall_height"] # height that the plot would be if it did include the outer margins
    overall_width = groupplots_info["overall_width"]

    x_coord_raw = f"{x} * {overall_width}"
    y_coord_raw = f"{y} * {overall_height}"

    # Find the offset of the last subplot's axis' lower left corner from the lower left corner of the overall plot.
    # The y offset is always just the lower margin since the last-added plot is at the bottom.
    last_col = (groupplots_info["num_subplots"] - 1) % groupplots_info["cols"]
    x_offset = (last_col * (groupplots_info["width"] + groupplots_info["margin_l"] + groupplots_info["margin_r"]) + groupplots_info["margin_l"]) * 100 / groupplots_info["width"]
    y_offset = groupplots_info["margin_b"]

    return f"{x_coord_raw} - {x_offset}", f"{y_coord_raw} * {overall_height / overall_width} - {y_offset * overall_height / overall_width}"



def str_from_annotation(annotation_list, axes: list[Axis], colors_set, groupplots_info=None):
    """Create a string of LaTeX code for the annotations of a figure.

    Parameters
    ----------
    annotation_list
        list of annotations from Plotly figure, in fig.layout.annotations
    axis
        Axis object previously created
    colors_set
        colors used in the figure, to be filled with the colors of the annotations
    groupplots_info, optional
        if None, indicates groupplots are not being used. Otherwise, includes information about
        the dimensions of the groupplot, by default None

    Returns
    -------
        string of LaTeX code for the annotations
    """
    annotation_str = ""
    if len(annotation_list) > 0:
        for axis in axes:
            axis.add_option("clip", "false")
    for annotation in annotation_list:
        x_anchor = anchor_dict[annotation.xanchor]
        y_anchor = anchor_dict[annotation.yanchor]
        x_ref = annotation.xref
        y_ref = annotation.yref
        x_coordinate, y_coordinate, relative = get_coordinates(round(annotation.x, 6), round(annotation.y, 6), x_ref, y_ref)
        if groupplots_info is not None:
            if not relative:
                warn("Only annotations with xref and yref 'paper' are supported when using groupplots.")
            x_coordinate, y_coordinate = get_groupplots_coordinates(x_coordinate, y_coordinate, x_ref, y_ref, groupplots_info)

        anchor_option = f"{y_anchor} {x_anchor}".rstrip()

        if anchor_option != "":
            anchor_option = f"anchor={anchor_option}"
        node_options = anchor_option
        if annotation.font.color is not None:
            color_converted = convert_color(annotation.font.color)
            colors_set.add(color_converted[:3])
            node_options += f", color={color_converted[0]}"
        annotation_str += tex_add_text(x_coordinate, y_coordinate, annotation.text, options=node_options, relative=relative and groupplots_info is None, axisless=groupplots_info is not None)
    return annotation_str
