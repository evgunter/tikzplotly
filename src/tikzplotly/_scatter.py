from warnings import warn

from ._tex import *
from ._color import *
from ._marker import marker_symbol_to_tex
from ._dash import *
from ._axis import Axis
from ._data import *
from ._utils import px_to_pt, dict_to_tex_str, sanitize_text
from numpy import round

def draw_scatter2d(data_container, scatter, axis: Axis, colors_set):
    """Get code for a scatter trace and add the trace's data to the data container.

    Parameters
    ----------
    data_container
        data container that the data will be added to
    scatter
        scatter trace from Plotly figure
    axis
        axis object previously created
    colors_set
        set of colors used in the figure

    Returns
    -------
        string of tikz code for the scatter trace
    """
    # Handle the case where x or y is empty
    if scatter.x is None and scatter.y is None:
        warn("Adding empty trace.")
        return "\\addplot coordinates {};\n"
    else:
        if scatter.x is None:
            scatter.x = list(range(len(scatter.y)))
        if scatter.y is None:
            scatter.y = list(range(len(scatter.x)))
    data_name, y_name = data_container.addData(scatter.x, scatter.y, scatter.name)

    mode = scatter.mode
    marker = scatter.marker

    if data_type(scatter.x[0]) == "date":
        axis.add_option("date coordinates in", "x")
    if data_type(scatter.x[0]) == "month":
        scatter_x_str = "{" + ", ".join([tex_text(str(x)) for x in scatter.x]) + "}"
        axis.add_option("xticklabels", scatter_x_str)

    if mode is None:
        # by default, plot markers and lines
        mode = "markers+lines"

    options_dict = {}
    mark_option_dict = {}

    if mode == "markers":
        if marker.symbol is not None:
            symbol, symbol_options = marker_symbol_to_tex(marker.symbol)
            options_dict["mark"] = symbol
            options_dict["only marks"] = None
            if symbol_options is not None:
                mark_option_dict[symbol_options[0]] = symbol_options[1]
        else:
            options_dict["only marks"] = None

        if scatter.marker.size is not None:
            options_dict["mark size"] = px_to_pt(marker.size)

        if scatter.marker.color is not None:
            mark_option_dict["solid"] = None
            mark_option_dict["fill"], _ = convert_color(scatter.marker.color, colors_set)

        if (line:=scatter.marker.line) is not None:
            if line.color is not None:
                mark_option_dict["draw"], _ = convert_color(line.color, colors_set)
            if line.width is not None:
                mark_option_dict["line width"] = px_to_pt(line.width)

        if (angle:=scatter.marker.angle) is not None:
            mark_option_dict["rotate"] = -angle

        if (opacity:=scatter.opacity) is not None:
            options_dict["opacity"] = round(opacity, 2)
        if (opacity:=scatter.marker.opacity) is not None:
            mark_option_dict["opacity"] = round(opacity, 2)

        if mark_option_dict != {}:
            options_dict["mark options"] = mark_option_dict

    elif mode == "lines":
        options_dict["mark"] = "none"

    elif "lines" in mode and "markers" in mode:
        if marker.symbol is not None:
            symbol, symbol_options = marker_symbol_to_tex(marker.symbol)
            options_dict["mark"] = symbol
            if symbol_options is not None:
                mark_option_dict[symbol_options[0]] = symbol_options[1]

    else:
        warn(f"Scatter : Mode {mode} is not supported yet.")

    if scatter.line.width is not None:
        options_dict["line width"] = px_to_pt(scatter.line.width)
    if scatter.line.dash is not None:
        options_dict[DASH_PATTERN[scatter.line.dash]] = None
    if scatter.connectgaps in [False, None] and None in scatter.x:
        options_dict["unbounded coords"] = "jump"


    if scatter.line.color is not None:
        options_dict["color"], _ = convert_color(scatter.line.color, colors_set)
        if "mark" in mode:
            mark_option_dict["draw"], _ = convert_color(scatter.line.color, colors_set)
            mark_option_dict["solid"] = None

    if scatter.fill is not None:
        options_dict["fill"], opacity = convert_color(scatter.fillcolor, colors_set)
        if opacity < 1:
            options_dict["fill opacity"] = opacity

    if scatter.showlegend is False:
        options_dict["forget plot"] = None

    options = dict_to_tex_str(options_dict)
    code = ""
    code += tex_addplot(data_name, type="table", options=options, type_options=f"y={sanitize_text(y_name)}")

    if scatter.text is not None:
        for x_data, y_data, text_data in zip(scatter.x, scatter.y, scatter.text):
            code += tex_add_text((x_data, y_data), str(text_data).rstrip('.0'))

    return code