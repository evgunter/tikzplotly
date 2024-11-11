from pathlib import Path
from itertools import groupby, takewhile, chain
from .__about__ import __version__
from ._tex import *
from ._scatter import draw_scatter2d
from ._heatmap import draw_heatmap
from ._bar import draw_bar
from ._shape import draw_shape, FakeShape
from ._axis import Axis
from ._color import *
from ._annotations import str_from_annotation
from ._dataContainer import DataContainer
from ._utils import sanitize_TeX_text, dict_to_tex_str, find_subgrids, px_to_pt, add_zeroline
from ._defaults import PLOTLY_DEFAULT_WIDTH, PLOTLY_DEFAULT_HEIGHT, get_title_font_size, get_axis_title_font_size, latex_size_fmt, latex_text_size_fmt
from warnings import warn
import re
from copy import deepcopy

def get_tikz_code(
        fig,
        tikz_options = "scale=1",
        axis_options = None,
        include_disclamer = True,
    ):
    """Get the tikz code of a figure.

    Parameters
    ----------
    fig
        Plotly figure
    tikz_options, optional
        options given to the tikzpicture environment, by default {"scale": 1} (which changes nothing but makes it easy for the user to change the size)
    axis_options, optional
        options given to the axis environment, by default None
    include_disclamer, optional
        include a disclamer in the code, by default True

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
        if yd is None:
            return (yd, yr, xd, xr)
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
        # i'm not sure why this has " domain", but it seems to correspond to yref as usual
        shape_group = [shape for shape in figure_layout.shapes if (shape.xref, shape.yref.removesuffix(" domain")) in anchors]
        # we need null axes to be created to make the alignment correct when using groupplots, so trace_group may be empty
        trace_groups.append((trace_group, axis_group, shape_group))
    n_trace_groups = len(trace_groups)

    # find all the distinct coloraxes
    # this will store the name of the coloraxis and the corresponding coloraxis object,
    # and--not specified in plotly--the minimum and maximum values attained across all traces
    # (so that they can all use the same scale)
    coloraxes = {}  # name: (coloraxis, (min, max))
    for tg, _, _ in trace_groups:
        for trace in tg:
            cx_name = getattr(trace, "coloraxis", None)  # only some kinds of trace have a coloraxis attribute
            if cx_name is None:
                continue
            if trace.type != "heatmap":
                warn(f"Coloraxis with trace type {trace.type} is not supported. Treating like a heatmap, which may cause errors.")
            # find the minimum and maximum z values in this trace
            if trace.z is None:
                continue
            z_noneless = list(chain(*[z for z in trace.z if z is not None]))
            if len(z_noneless) == 0:
                continue
            z_min, z_max = min(z_noneless), max(z_noneless)
            if cx_name not in coloraxes:
                coloraxis = getattr(figure_layout, cx_name)
                coloraxes[cx_name] = (coloraxis, (z_min, z_max))
            else:
                coloraxis, (old_z_min, old_z_max) = coloraxes[cx_name]
                coloraxes[cx_name] = (coloraxis, (min(old_z_min, z_min), max(old_z_max, z_max)))

    # get the height and width from the figure layout.
    # height_total and width_total may be None, which indicates to use defaults
    height_total = figure_layout.height
    width_total = figure_layout.width
    # height total and width total may be None.
    # the behavior in this case depends on whether we're using groupplots, and is set below.

    # if there is more than one trace group, we will use group plots.
    # instead of an axis environment, we will have a groupplot environment
    # which indicates how the separate traces should be laid out.
    # when using this environment, we replace the axis environment with the command \nextgroupplot,
    # which takes the same options as the axis options.
    if n_trace_groups > 1:
        groupplots = True
        warn("Using groupplots. Add '\\usepgfplotslibrary{groupplots}' to preamble.")

        # get the plot layout from the figure layout
        # do this by determining how many distinct x and y domains there are
        # (this won't work if the original axes were not arranged in a grid)

        x_domains_lst, y_domains_lst = zip(*[(x_domain, y_domain) for (y_domain, y_range), (x_domain, x_range) in [key(axis_idx) for axis_idx in axis_idxs]])
        n_x_domains, n_y_domains = len(set(x_domains_lst)), len(set(y_domains_lst))

        # TODO: move this block into groupplots so we can indeed use the proportionally smaller of height and width
        if height_total is None and width_total is None:
            # the plotly height and width correspond to the whole figure,
            # while the latex ones correspond just to the plot.
            # so, it'll generally get better results to take the proportionally smaller of height and width

            candidate_height_total = PLOTLY_DEFAULT_HEIGHT
            candidate_width_total = PLOTLY_DEFAULT_WIDTH
            candidate_width = candidate_width_total / n_x_domains
            candidate_height = candidate_height_total / n_y_domains
            height = width = min(candidate_width, candidate_height)  # default to square plots
            height_total = height * n_y_domains
            width_total = width * n_x_domains
        elif height_total is None:
            height = width = width_total / n_x_domains  # default to square plots
            height_total = height * n_y_domains
        elif width_total is None:
            width = height = height_total / n_y_domains  # default to square plots
            width_total = width * n_x_domains
        else:
            width = width_total / n_x_domains
            height = height_total / n_y_domains
    else:
        groupplots = False

        if height_total is None and width_total is None:
            candidate_height = PLOTLY_DEFAULT_HEIGHT
            candidate_width = PLOTLY_DEFAULT_WIDTH
            # default to square plots
            height_total = width_total = height = width = min(candidate_height, candidate_width)
        elif height_total is None:
            height_total = width_total = height = width = width_total
        elif width_total is None:
            height_total = width_total = height = width = height_total
        else:
            height = height_total
            width = width_total

    tracegroup_info = []

    for trace_group, axis_group, shape_group in trace_groups:
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

        # use figure_layout.xaxisN.showticklabels to delete labels when they're not supposed to be displayed
        # (the plot functions should detect whether they're "\\empty" and leave them that way)
        xshowticklabels = [getattr(figure_layout, x_key).showticklabels for x_key in x_keys]
        if len(set(xshowticklabels)) > 1:
            warn("showticklabels is not consistent across all x axes in a group. Defaulting to last value.")
        if xshowticklabels:
            if xshowticklabels[-1] == False:  # i.e., specifically disabled, rather than None
                axis.update_option("x tick label style", {"opacity": 0}, lambda x, y: x | y)
        yshowticklabels = [getattr(figure_layout, y_key).showticklabels for y_key in y_keys]
        if len(set(yshowticklabels)) > 1:
            warn("showticklabels is not consistent across all y axes in a group. Defaulting to last value.")
        if yshowticklabels:
            if yshowticklabels[-1] == False:  # i.e., specifically disabled, rather than None
                axis.update_option("y tick label style", {"opacity": 0}, lambda x, y: x | y)

        # similarly, find the "ticks" axis properties, which can be "inside", "outside", "", or None (which defaults to "outside")
        xticks = [getattr(figure_layout, x_key).ticks for x_key in x_keys]
        if len(set(xticks)) > 1:
            warn("ticks is not consistent across all x axes in a group. Defaulting to last value.")
        if xticks:
            if xticks[-1] == "inside":
                axis.add_option("xtick align", "inside")
            elif xticks[-1] == "outside":
                axis.add_option("xtick align", "outside")
            elif xticks[-1] == "":
                axis.update_option("xtick style", {"draw": "none"}, lambda x, y: x | y)
        yticks = [getattr(figure_layout, y_key).ticks for y_key in y_keys]
        if len(set(yticks)) > 1:
            warn("ticks is not consistent across all y axes in a group. Defaulting to last value.")
        if yticks:
            if yticks[-1] == "inside":
                axis.add_option("ytick align", "inside")
            elif yticks[-1] == "outside":
                axis.add_option("ytick align", "outside")
            elif yticks[-1] == "":
                axis.update_option("ytick style", {"draw": "none"}, lambda x, y: x | y)

        if not trace_group:
            # if there aren't any traces, make the axes invisible
            axis.add_option("hide x axis", None)
            axis.add_option("hide y axis", None)

        if "scale" not in axis.options:
            # if the scale is not set, default to 1
            # this changes nothing, but makes it easy for the user to change the size
            axis.add_option("scale", 1)

        # also find the axis titles
        x_titles = [v for v in [getattr(figure_layout, x_key).title for x_key in x_keys] if v is not None and v.text is not None]
        if len(set(x_title.text for x_title in x_titles)) > 1:
            warn("x axis titles are not consistent across all x axes in a group. Defaulting to last value.")
        if x_titles:
            x_title = x_titles[-1]
            axis.add_option("xlabel", x_title.text)  # TODO: might be nice to use text width=<width> to avoid overlap
            # also add font size, etc
            x_title_style = {"align": "center"}  # TODO: might be nice to use text width=<width> to avoid overlap
            x_title_style["font"] = latex_size_fmt(get_axis_title_font_size("x", figure_layout))
            if x_title.font.color is not None:
                x_title_style["color"], _ = convert_color(x_title.font.color, colors_set)
            if x_title_style:
                axis.add_option("xlabel style", x_title_style)
        y_titles = [v for v in [getattr(figure_layout, y_key).title for y_key in y_keys] if v is not None and v.text is not None]
        if len(set(y_title.text for y_title in y_titles)) > 1:
            warn("y axis titles are not consistent across all y axes in a group. Defaulting to last value.")
        if y_titles:
            y_title = y_titles[-1]
            axis.add_option("ylabel", y_title.text)
            # also add font size, etc
            y_title_style = {"align": "center"}  # TODO: might be nice to use text width=<width of figure> to avoid overlap
            y_title_style["font"] = latex_size_fmt(get_axis_title_font_size("y", figure_layout))
            if y_title.font.color is not None:
                y_title_style["color"], _ = convert_color(y_title.font.color, colors_set)
            if y_title_style:
                axis.add_option("ylabel style", y_title_style)

        # set point meta min and max for all the traces based on coloraxis
        coloraxis_names = [v for v in [getattr(trace, "coloraxis", None) for trace in trace_group] if v is not None]
        if len(set(coloraxis_names)) > 1:
            warn("Coloraxis is not consistent across all traces in a group. Defaulting to last value.")
        if coloraxis_names:
            cx_name = coloraxis_names[-1]
            if coloraxes.get(cx_name, None) is not None:
                coloraxis, (z_min, z_max) = coloraxes[cx_name]
                axis.add_option("point meta min", z_min)
                axis.add_option("point meta max", z_max)

        # TODO: i think that the role of alignmentgroup is already covered by the shared axes, but it would be good to verify this

        # TODO: there may still be some configuration in figure_layout.template.data.{bar,heatmap,scatter} that isn't included
        
        # TODO: the below doesn't work. use mdframed instead? fundamentally the issue is that the plotly plot corresponds to a latex figure, not a tikzpicture
        # if figure_layout.template.layout.paper_bgcolor:
        #     # TODO: do this in a nicer way than a warning
        #     warn("Using a background. Add \\usetikzlibrary{backgrounds} to the preamble.")
        #     axis.add_option(f"background rectangle/.style", {"fill": convert_color(figure_layout.template.layout.paper_bgcolor, colors_set)[0]})
        #     axis.add_option("show background rectangle", None)
        # TODO remove once verified that this is always handled by the axis
        # TODO also if it is handled by the axis probably the rest of this stuff should move there too
        # if figure_layout.template.layout.plot_bgcolor:
        #     axis.add_option(f"axis background/.style", {"fill": convert_color(figure_layout.template.layout.plot_bgcolor, colors_set)[0]})
        if figure_layout.template.layout.xaxis.gridcolor:
            axis.add_option(f"major grid style", {"color": convert_color(figure_layout.template.layout.xaxis.gridcolor, colors_set)[0]})
        if figure_layout.template.layout.yaxis.gridcolor:
            axis.add_option(f"major grid style", {"color": convert_color(figure_layout.template.layout.yaxis.gridcolor, colors_set)[0]})
        if figure_layout.template.layout.xaxis.linecolor:
            axis.add_option(f"axis line style", {"color": convert_color(figure_layout.template.layout.xaxis.linecolor, colors_set)[0]})
        if figure_layout.template.layout.yaxis.linecolor:
            axis.add_option(f"axis line style", {"color": convert_color(figure_layout.template.layout.yaxis.linecolor, colors_set)[0]})

        # TODO: whether plotly shows zerolines depends on the kind of chart.
        # automatically adding them would be good, instead of only adding them when explicitly specified (as here).
        if figure_layout.template.layout.xaxis.zeroline:
            add_zeroline("x", axis, figure_layout.template.layout.xaxis)
        if figure_layout.template.layout.yaxis.zeroline:
            add_zeroline("y", axis, figure_layout.template.layout.yaxis)

        # get the code for each trace (and modify the axis as necessary)
        for trace in trace_group:
            if trace.type == "scatter":
                data_str.append( draw_scatter2d(data_container, trace, axis, colors_set) )
                if trace.name and trace['showlegend'] != False:
                    data_str.append( tex_add_legendentry(sanitize_TeX_text(trace.name)) )
                # TODO: i'm not sure where these colors actually get used later. superfluous, or need to be used here?
                
                # TODO remove if not needed
                # if trace.line.color is not None:
                #     convert_color(trace.line.color, colors_set)
                # if trace.fillcolor is not None:
                #     convert_color(trace.fillcolor, colors_set)

            elif trace.type == "heatmap":
                data_str.append( draw_heatmap(trace, fig, axis, height, width, colors_set) )

            elif trace.type == "bar":
                fig_info = {"height": px_to_pt(height), "width": px_to_pt(width), "n_bars": sum(len(trace.x) for trace in trace_group), "coloraxis": getattr(figure_layout, "coloraxis", None), "xaxis_template": figure_layout.template.layout.xaxis, "yaxis_template": figure_layout.template.layout.yaxis}
                if groupplots:
                    axis.add_option("x", False)
                    axis.add_option("y", False)

                data_str.append( draw_bar(trace, axis, fig_info, colors_set) )

            else:
                warn(f"Trace type {trace.type} is not supported yet.")
        
        for shape in shape_group:
            data_str.append( draw_shape(shape, axis, colors_set) )


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

    annotations = [] if not figure_layout.annotations else list(figure_layout.annotations)
    if groupplots:
        code += tex_begin_environment("groupplot", stack_env, options=dict_to_tex_str({"group style": {"group size": f"{n_x_domains} by {n_y_domains}", "horizontal sep": px_to_pt(0.2*width), "vertical sep": px_to_pt(0.2*height)}, "height": px_to_pt(height), "width": px_to_pt(width)}))

        # in this case, it's very likely that the annotations are actually titles of the subplots
        # so, we'll see if there are annotations that form an n_x_domains by n_y_domains grid and assume that these are titles

        def check_grid(grid, n_x_domains, n_y_domains, n_figures):
                # check that the input grid is valid; return a boolean for validity and a list of warnings for if it's dubious but not completely invalid

                # first, check that the grid is well-formed: there are the correct number of rows and columns, and all the rows/columns have common y/x coordinates
                if len(grid) != n_y_domains:
                    return False, ["Incorrect number of rows in grid; not parsing as titles."]
                if not all(len(row) == n_x_domains for row in grid):
                    return False, ["Incorrect number of columns in grid; not parsing as titles."]
                if not all(len(set(coord.y for coords in row for coord in coords)) == 1 for row in grid):
                    return False, ["Rows of grid do not have common y coordinates; not parsing as titles."]
                if not all(len(set(coord.x for coords in col for coord in coords)) == 1 for col in zip(*grid)):
                    return False, ["Columns of grid do not have common x coordinates; not parsing as titles."]

                # now check that the grid is properly populated
                warn_multiple_coords = False
                warn_missing_coords = False
                warn_extra_coords = False
                for r, row in enumerate(grid):
                    for c, selected_coords in enumerate(row):
                        if len(selected_coords) > 1:
                            warn_multiple_coords = True
                        plot_idx = r*n_x_domains + c
                        if plot_idx >= n_figures:
                            warn_extra_coords = True
                        elif len(selected_coords) == 0:
                            warn_missing_coords = True

                warnings = []
                if warn_multiple_coords:
                    warnings.append("Multiple titles found for a single subplot.")
                if warn_missing_coords:
                    warnings.append("No titles found for a subplot.")
                if warn_extra_coords:
                    warnings.append("Titles found for nonexistent subplots.")
                
                return True, warnings

        try:
            grid, _xc, _yc, warnings = next(find_subgrids(annotations, n_x_domains, n_y_domains, n_trace_groups, check_grid=check_grid))

            warn(f"Assuming annotations are titles")  # TODO change to a comment in the latex
            for warning in warnings:
                warn(warning)

            # add the titles to the traces
            removed_annotations = []
            for i, (_, axis) in enumerate(tracegroup_info):
                # TODO: ensure that the axes are in order!
                annotations_to_add = grid[i // n_x_domains][i % n_x_domains]
                removed_annotations.extend(annotations_to_add)
                ax_t = "\n".join(ann.text for ann in annotations_to_add)
                axis.add_option("title", {latex_text_size_fmt(ax_t, get_title_font_size(figure_layout)): None})

            # remove all the annotations that were in the grid
            annotations = [annotation for annotation in annotations if annotation not in removed_annotations]

            
        except StopIteration:
            # we didn't find a valid full grid, so we'll try to just find a single row of titles
            potential_top_titles = list(find_subgrids(annotations, n_x_domains, 1, n_x_domains, check_grid=check_grid))
            if len(potential_top_titles) == 1:
                grid, _xc, _yc, warnings = potential_top_titles[0]
                warn(f"Assuming annotations are first-row titles")  # TODO change to a comment in the latex
                
                # add the titles to the traces
                removed_annotations = []
                for i in range(n_x_domains):
                    annotations_to_add = grid[0][i]
                    removed_annotations.extend(annotations_to_add)
                    ax_t = "\n".join(ann.text for ann in annotations_to_add)
                    tracegroup_info[i][1].add_option("title", {latex_text_size_fmt(ax_t, get_title_font_size(figure_layout)): None})

                # remove all the annotations that were in the grid
                annotations = [annotation for annotation in annotations if annotation not in removed_annotations]

            elif len(potential_top_titles) > 1:
                warn(f"Assuming annotations are first-row titles, but found multiple potential title rows. Taking the one with the greatest y coordinate.")  # TODO change to a comment in the latex
                grid, _xc, _yc, warnings = max(potential_top_titles, key=lambda grid: max(coord.y for row in grid for coord in row))

                # add the titles to the traces
                removed_annotations = []
                for i in range(n_x_domains):
                    annotations_to_add = grid[0][i]
                    removed_annotations.extend(annotations_to_add)
                    tracegroup_info[i][1].add_option("title", {"\n".join(ann.text for ann in annotations_to_add): None})

                # remove all the annotations that were in the grid
                annotations = [annotation for annotation in annotations if annotation not in removed_annotations]
            else:
                # we didn't find a valid row of titles, so we won't try to parse the annotations as titles
                pass

    for data_str, axis in tracegroup_info:
        code += axis.open_environment(stack_env, groupplots=groupplots)

        for trace_str in data_str:
            code += trace_str

        code += axis.close_environment(stack_env, groupplots=groupplots)
        # since this is before the start of the next groupplot, it affects the size of the text in the plot above (for some reason)
        code += "\\normalsize\n"  # this should have no effect on the default display, but could help the user adjust the size of the labels (which are often too small)

    if groupplots:
        code += tex_end_environment(stack_env)

    if figure_layout.title.text:
        if annotations:  # awful hack: get an Annotation object by copying one of them and changing its properties
            title_annotation = deepcopy(annotations[0])
            if groupplots:
                title_annotation.x = f"$(group c1r1.north)!0.5!(group c{n_x_domains}r1.north)+(0,2cm)$"
                title_annotation.y = ""
            else:
                # set to the center top
                title_annotation.xref = "paper"
                title_annotation.yref = "paper"
                title_annotation.x = 0.5
                title_annotation.y = 1
            title_annotation.text = figure_layout.title.text
            # for whatever reason you can't just set the fonts equal, you have to do it entry by entry
            title_annotation.font.color = figure_layout.title.font.color
            title_annotation.font.size = get_title_font_size(figure_layout.title.font.size)
            annotations.append(title_annotation)
        else:
            # if there aren't any annotations, do an even more awful hack
            # TODO: make this less of an evil hack so it supports font color too, etc
            font_size = get_title_font_size(figure_layout)
            if groupplots:
                # this creates a title node slightly above the top of the top row of the groupplot, centered between the leftmost and rightmost subplots
                code += f"\\node (title) at ($(group c1r1.north)!0.5!(group c{n_x_domains}r1.north)+(0,0.4)$) {{{latex_text_size_fmt(figure_layout.title.text, font_size)}}};\n"
            else:
                if height_total is not None and width_total is not None:
                    code += f"\\node (title) at (0.5*{px_to_pt(width_total)}pt, {px_to_pt(height_total)}pt) [above] {{{tex_text(figure_layout.title.text)}}};\n"
                else:
                    # TODO: i don't think this is right
                    code += f"\\node (title) at (0.5, 1) [above] {{{tex_text(figure_layout.title.text)}}};\n"

    annotation_str = str_from_annotation(annotations, [axis for _, axis in tracegroup_info], colors_set, height_total, width_total)
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

    code = get_tikz_code(*args, **kwargs)
    with open(filepath, "w") as fd:
        fd.write(code)