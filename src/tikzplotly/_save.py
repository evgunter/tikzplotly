from pathlib import Path
from itertools import groupby, takewhile
from .__about__ import __version__
from ._tex import *
from ._scatter import draw_scatter2d
from ._heatmap import draw_heatmap
from ._bar import draw_bar
from ._axis import Axis
from ._color import *
from ._annotations import str_from_annotation
from ._dataContainer import DataContainer
from ._utils import sanitize_TeX_text, px_to_pt, PLOTLY_DEFAULT_WIDTH, PLOTLY_DEFAULT_HEIGHT, dict_to_tex_str
from warnings import warn
import re

def get_tikz_code(
        fig,
        tikz_options = None,
        axis_options = None,
        include_disclamer = True,
        img_name = "heatmap.png",
    ):
    """Get the tikz code of a figure.

    Parameters
    ----------
    fig
        Plotly figure
    tikz_options, optional
        options given to the tikzpicture environment, by default None
    axis_options, optional
        options given to the axis environment, by default None
    include_disclamer, optional
        include a disclamer in the code, by default True
    img_name, optional
        name of the PNG file for heatmap, by default "heatmap.png"

    Returns
    -------
        string of tikz code
    """
    figure_data = fig.data
    figure_layout = fig.layout
    colors_set = set()

    if len(figure_data) == 0:
        warn("No data in figure.")

    # partition into distinct axes by whether the ranges and domains match
    def idx_to_axis(i):
        if i == 0:
            # it's in this order so that if we lexicographically sort the keys, the order of plots is correct
            return 'yaxis', 'xaxis'
        return f'yaxis{i+1}', f'xaxis{i+1}'
    axis_idxs = list(takewhile(lambda i: hasattr(figure_layout, idx_to_axis(i)[0]), range(len(figure_data))))
    def key(axis_idx):
        axis_keys = idx_to_axis(axis_idx)
        axis_specs = tuple([getattr(figure_layout, axis_key) for axis_key in axis_keys])
        return tuple([(getattr(axis_spec, 'domain', None), getattr(axis_spec, 'range', None)) for axis_spec in axis_specs])
    def key_(axis_idx):
        (yd, yr), (xd, xr) = key(axis_idx)
        ydl, ydr = yd
        # flip the sign of the y domain so that the axes are sorted in the correct order
        return ((-ydr, -ydl), yr, xd, xr)
    grouped_axes = [list(g) for _, g in groupby(sorted(axis_idxs, key=key_), key=key_)]

    data_container = DataContainer()

    # get the trace groups
    trace_groups = []
    for axis_group in grouped_axes:
        anchors = [(getattr(figure_layout, y_key).anchor, getattr(figure_layout, x_key).anchor) for y_key, x_key in [idx_to_axis(axis_idx) for axis_idx in axis_group]]
        trace_group = [trace for trace in figure_data if (trace.xaxis, trace.yaxis) in anchors]
        # we need null axes to be created to make the alignment correct when using groupplots, so trace_group may be empty
        trace_groups.append((trace_group, axis_group))

    # get the height and width from the figure layout, and revert to defaults if not specified
    # do it this way instead of using default value PLOTLY_DEFAULT_HEIGHT because height attribute may be None
    height_total = getattr(figure_layout, 'height', None)
    if height_total is None:
        height_total = PLOTLY_DEFAULT_HEIGHT
    width_total = getattr(figure_layout, 'width', None)
    if width_total is None:
        width_total = PLOTLY_DEFAULT_WIDTH

    # if there is more than one trace group, we will use group plots.
    # instead of an axis environment, we will have a groupplot environment
    # which indicates how the separate traces should be laid out.
    # when using this environment, we replace the axis environment with the command \nextgroupplot,
    # which takes the same options as the axis options.
    if len(trace_groups) > 1:
        groupplots = True
        warn("Using groupplots. Add '\\usepgfplotslibrary{groupplots}' to preamble.")

        # get the plot layout from the figure layout
        # do this by determining how many distinct x and y domains there are
        # (this won't work if the original axes were not arranged in a grid)

        x_domains_lst, y_domains_lst = zip(*[(x_domain, y_domain) for (y_domain, y_range), (x_domain, x_range) in [key(axis_idx) for axis_idx in axis_idxs]])
        n_x_domains, n_y_domains = len(set(x_domains_lst)), len(set(y_domains_lst))

        # find the margin, defaulting to plotly's default 80px if not specified
        margin_all = getattr(figure_layout, 'margin', None)
        # can't just use 80 as the default since e.g. margin_all.l may be None instead of raising an error
        margin_l, margin_r, margin_b, margin_t = [v if v is not None else 80 for v in [getattr(margin_all, dirn, None) for dirn in ['l', 'r', 'b', 't']]]


        # height_total = (individual plot height + margin_b + margin_t) * n_y_domains,
        # so individual plot height = height_total / n_y_domains - margin_b - margin_t

        height = px_to_pt( height_total / n_y_domains - margin_b - margin_t )
        width = px_to_pt( width_total / n_x_domains - margin_l - margin_r )

        # get the last trace group's x and y limits, by trying to get xmin

        groupplots_info = {"overall_height": height_total, "overall_width": width_total, "height": height, "width": width, "cols": n_x_domains, "rows": n_y_domains, "margin_l": margin_l, "margin_r": margin_r, "margin_b": margin_b, "margin_t": margin_t, "num_subplots": len(trace_groups)}
    else:
        groupplots = False
        groupplots_info = None

        height = px_to_pt( height_total )
        width = px_to_pt( width_total )

    tracegroup_info = []

    for trace_group, axis_group in trace_groups:
        data_str = []

        # set up the axis which will be shared for all the traces in the group
        axis = Axis(figure_layout, colors_set, axis_options=axis_options)

        tracegroup_info.append((data_str, axis))

        # check if all the axes in the group agree on showline. if not, issue a warning
        y_keys, x_keys = zip(*[idx_to_axis(axis_idx) for axis_idx in axis_group])
        x_showline_values = set(getattr(figure_layout, x_key).showline for x_key in x_keys)
        if len(x_showline_values) > 1:
            warn("showline is not consistent across all x axes in a group. Defaulting to last value.")
            if getattr(figure_layout, x_keys[-1]).showline == False:
                axis.add_option("axis x line", "none")
        y_showline_values = set(getattr(figure_layout, y_key).showline for y_key in y_keys)
        if len(y_showline_values) > 1:
            warn("showline is not consistent across all y axes in a group. Defaulting to last value.")
            if getattr(figure_layout, y_keys[-1]).showline == False:
                axis.add_option("axis y line", "none")

        if not trace_group:
            # if there aren't any traces, make the axes invisible
            axis.add_option("hide x axis", None)
            axis.add_option("hide y axis", None)

        # get the code for each trace (and modify the axis as necessary)
        # TODO: need to update the axis and colors_set now that generating the code does not do this automatically
        for trace in trace_group:
            if trace.type == "scatter":
                data_name_macro, y_name = data_container.addData(trace.x, trace.y, trace.name)
                data_str.append( draw_scatter2d(data_name_macro, trace, y_name, axis, colors_set) )
                if trace.name and trace['showlegend'] != False:
                    data_str.append( tex_add_legendentry(sanitize_TeX_text(trace.name)) )
                if trace.line.color is not None:
                    colors_set.add(convert_color(trace.line.color)[:3])
                if trace.fillcolor is not None:
                    colors_set.add(convert_color(trace.fillcolor)[:3])

            elif trace.type == "heatmap":
                data_str.append( draw_heatmap(trace, fig, axis) )

            elif trace.type == "bar":
                data_str.append( draw_bar(trace, axis, {"height": height, "width": width, "n_bars": sum(len(trace.x) for trace in trace_group), "corloraxis": getattr(figure_layout, "coloraxis", None)}, colors_set) )

            else:
                warn(f"Trace type {trace.type} is not supported yet.")

    annotation_str = str_from_annotation(figure_layout.annotations, [axis for _, axis in tracegroup_info], colors_set, groupplots_info=groupplots_info)

    code = """"""
    stack_env = []

    if include_disclamer:
        code += tex_comment(f"This file was created with tikzplotly version {__version__}.")

    if len(data_container.data) > 0:
        code += data_container.exportData()
        code += "\n"

    code += tex_begin_environment("tikzpicture", stack_env, options=tikz_options)

    code += "\n"
    color_list = list(colors_set)
    color_list.sort()
    for color in color_list:
        code += tex_add_color(color[0], color[1], color[2])
    code += "\n"

    if figure_layout.legend.title.text is not None and figure_layout.showlegend:
        code += "\\addlegendimage{empty legend}\n"
        code += tex_add_legendentry(sanitize_TeX_text(fig.layout.legend.title.text), options="yshift=5pt")

    if groupplots:
        code += tex_begin_environment("groupplot", stack_env, options=dict_to_tex_str({"group style": {"group size": f"{n_x_domains} by {n_y_domains}", "horizontal sep": margin_l + margin_r, "vertical sep": margin_b + margin_t}, "height": height, "width": width}))
    for data_str, axis in tracegroup_info:
        code += axis.open_environment(stack_env, groupplots=groupplots)

        for trace_str in data_str:
            code += trace_str

        code += axis.close_environment(stack_env, groupplots=groupplots)

    code += annotation_str

    code += tex_end_all_environment(stack_env)

    return code


def save(filepath, *args, **kwargs):
    """Save a figure to a file or a stream.

    Parameters
    ----------
    filepath : str or Path
        A string containing a path to a filename, or a Path object.
    *args, **kwargs
        Additional arguments are passed to the backend.
    """
    directory = Path(filepath).parent
    if not directory.exists():
        directory.mkdir(parents=True)

    if "img_name" in kwargs:
        img_name = kwargs["img_name"]
    else:
        img_name = str(directory / "heatmap.png")

    code = get_tikz_code(*args, img_name=img_name, **kwargs)
    with open(filepath, "w") as fd:
        fd.write(code)