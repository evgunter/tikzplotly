from copy import deepcopy
from warnings import warn
from plotly.express.colors import sample_colorscale

from ._tex import *
from ._color import *
from ._marker import marker_symbol_to_tex
from ._dash import *
from ._axis import Axis
from ._data import *
from ._utils import dict_to_tex_str, sanitize_text, add_zeroline, coords_to_str
from ._defaults import PLOTLY_DEFAULT_AXIS_DISPLAY_OPTIONS
from numpy import round, array, float64

V_H_CORRESP = {
    "orientation": ("v", "h"),
    "categorical_axis": ("x", "y"),
    "numerical_axis": ("y", "x"),
    "categorical_axis_idx": (0, 1),
    "numerical_axis_idx": (1, 0),
    "bar": ("ybar", "xbar"),
    "cat_anchor": ("west", "south"),
    "cat_parallel_shift": ("xshift", "yshift"),
    "cat_perp_shift": ("yshift", "xshift"),
}

X_Y_CORRESP = {
    "axis": ("x", "y"),
    "ticklabels": ("xticklabels", "yticklabels"),
    "enlarge limits": ("enlarge x limits", "enlarge y limits"),
    "direction": ("width", "height"),
    "tick": ("xtick", "ytick"),
    "tick label style": ("x tick label style", "y tick label style"),
    "majorgrids": ("xmajorgrids", "ymajorgrids"),
    "axis_template": ("xaxis_template", "yaxis_template"),
    "extra ticks": ("extra x ticks", "extra y ticks"),
    "extra tick labels": ("extra x tick labels", "extra y tick labels"),
    "extra tick style": ("extra x tick style", "extra y tick style"),
}

def orientation_to_idx(orientation):
    return 1 if orientation == "h" else 0

def draw_bar(bar, axis: Axis, fig_info, colors_set, options={}):
    """Get code for a bar plot.

    Parameters
    ----------
    bar
        bar trace from Plotly figure
    axis
        axis object previously created
    fig_info
        a dictionary of information about the figure (e.g. height, width, coloraxis, template)
    colors_set
        set of colors used in the figure

    Returns
    -------
        string of tikz code for the scatter trace
    """

    orientation = orientation_to_idx(bar.orientation)
    cat_vals = bar.x if orientation == 0 else bar.y

    for key, value in options.items():
        axis.add_option(tex_text(key), value)

    # first, some stuff to make it look more like a plotly bar chart by default
    # note that this doesn't override the default-setting stuff below since that checks whether these are explicitly set in options
    for key, value in PLOTLY_DEFAULT_AXIS_DISPLAY_OPTIONS.items():
        if key not in options:
            axis.add_option(tex_text(key), value)
    # TODO: i'm not totally sure what this does
    # axis.add_option(X_Y_CORRESP["tick"][orientation], "data")

    axis.update_option(X_Y_CORRESP["majorgrids"][1 - orientation], None, lambda a, b: a if a is not None else b)  # only update if it's not already set

    zeroline_haver = fig_info[X_Y_CORRESP["axis_template"][1 - orientation]]
    if zeroline_haver.zeroline != False:  # has to be specifically False, not None; the default is adding the zeroline, and False disables it
        add_zeroline(X_Y_CORRESP["axis"][1 - orientation], axis, zeroline_haver)

    # default to the dimensions of the figure (height and width)
    for label in ["categorical_axis", "numerical_axis"]:
        ax = V_H_CORRESP[label][orientation]
        x_y_corresp_idx = orientation if label == "categorical_axis" else 1 - orientation
        dirn = X_Y_CORRESP["direction"][x_y_corresp_idx]
        if axis.get_option(ax) is None:
            # here, none of these options are set, so we use the defaults
            if dirn in fig_info:
                if label == "categorical_axis":
                    # the categorical axis 'x' or 'y' defaults to 'width' or 'height' from the figure layout divided by the number of bars
                    # (since in latex 'x' or 'y is the width of a single bar)
                    cat_length = fig_info[dirn] / fig_info["n_bars"]
                    axis.add_option(ax, f"{cat_length}pt")

                    # fraction of overall width (i.e., for a vertical plot, x range, x * (# bars - 1) since bars are centered on indices) by which to enlarge.
                    # we want the absolute spacing added to be the same as the inter-bar spacing + 1/2 the width of a bar,
                    # which is (for a vertical plot) x - bar width + 1/2 bar width. so this should be (x - 1/2 bar width) / (x * (# bars - 1))
                    # if X_Y_CORRESP["enlarge limits"][x_y_corresp_idx] not in options and fig_info["n_bars"] > 1:
                    #     axis.add_option(X_Y_CORRESP["enlarge limits"][x_y_corresp_idx], (cat_length - bar_width / 2) / (cat_length * (fig_info["n_bars"] - 1)))
                    # TODO: i don't think plotly is actually doing this
                    # or like, i think we should do this but only if the bars are so wide they'd stick off the edge otherwise
                else:
                    # the numerical axis 'y' or 'x' defaults to 'height' or 'width' from the figure layout
                    axis.add_option(ax, f"{fig_info[dirn]}pt")
            
                if X_Y_CORRESP["tick label style"][x_y_corresp_idx] not in options:
                    # determine whether it is necessary to decrease the font size or rotate it.
                    # we estimate this by noting that the default em is 10pt.
                    # so, the caption text width is at most the number of characters * 10pt.
                    # if the caption text would overlap if it's as wide as possible, and the figure is not too large,
                    # we decrease the font size to 'tiny' (6pt) and see if this fits.
                    # if it still doesn't fit, or if the figure is not that large to begin with,
                    # we rotate the text by 30 degrees and shift it to align nicely with the bars.

                    # determine if there may be an overlap
                    text_pt = 10
                    if any((len(v1) + len(v2)) * text_pt > 2*cat_length for v1, v2 in zip(cat_vals, cat_vals[1:])):
                        cat_tick_label_style = {}
                        if cat_length * fig_info["n_bars"] < 300:
                            # the figure is small enough that it's likely not going to be scaled down, so it's ok to decrease the font size
                            cat_tick_label_style['font'] = '\\tiny'
                            text_pt = 6
                        # check if the text is still too long
                        if any((len(v1) + len(v2)) * text_pt > 2*cat_length for v1, v2 in zip(cat_vals, cat_vals[1:])):
                            cat_tick_label_style['rotate'] = "-30" if orientation == 0 else "30"
                            cat_tick_label_style['anchor'] = V_H_CORRESP["cat_anchor"][orientation]

                            if X_Y_CORRESP["tick label style"][x_y_corresp_idx] not in options:
                                # should be moved down by the height of the rotated text - the height of the unrotated text
                                rotated_text_height = max(len(xv) for xv in cat_vals) * text_pt * 1/2
                                axis.add_option(X_Y_CORRESP["tick label style"][x_y_corresp_idx], {V_H_CORRESP["cat_perp_shift"][orientation]: - (rotated_text_height - text_pt)})
                        axis.add_option(X_Y_CORRESP["tick label style"][x_y_corresp_idx], cat_tick_label_style)
        elif axis.get_option(ax) == False:  # it has to specifically be False, not None
            # here, setting the option to False means we don't want it to be set
            axis.remove_option(ax)

    if 'bar width' not in options:
        # plotly bar width defaults to 75%
        axis.add_option("bar width", 0.75)

    if getattr(bar, "color_continuous_scale", None) is not None:
        color_scale = [list(v) for v in bar.color_continuous_scale]
    elif getattr(fig_info.get("coloraxis", None), "colorscale", None) is not None:
        color_scale = [list(v) for v in fig_info["coloraxis"].colorscale]
    else:
        color_scale = None

    # split into individual bars
    # check that the x and y values have the same length
    if len(bar.x) != len(bar.y):
        warn(f"Bar chart x and y values have different lengths; trace {bar.name} is likely not being interpreted correctly!")
        return draw_bar_indiv(bar, colors_set)

    n_points = len(cat_vals)  # wlog
    code = ""

    # check if color is an array of the same length as x and y; if not, broadcast it
    if bar.marker.color is None or len(bar.marker.color) != n_points:
        color = [bar.marker.color for _ in range(n_points)]
    else:
        if color_scale is not None:
            # we need to convert the colorscale to a list of fully specified colors to use in the subplots
            color = sample_colorscale(color_scale, bar.marker.color, colortype="rgb")
        else:
            color = bar.marker.color

    # pgfplots uses only the tick coordinates from the first addplot command, so we need to add all the coordinates to the first plot
    for cv in cat_vals:
        new_label = tex_text(str(cv))
        labels = axis.get_option(X_Y_CORRESP["ticklabels"][orientation])
        if labels is None:
            labels = []
        if new_label not in labels:
            axis.update_option(X_Y_CORRESP["ticklabels"][orientation], [new_label], lambda x, y: x + y)
            axis.update_option(X_Y_CORRESP["tick"][orientation], [len(labels)], lambda x, y: x + y)
    
    # set the categorical axis to match the ticks, not the labels
    if orientation == 0:
        labels_to_ticks = dict(zip(axis.get_option("xticklabels"), axis.get_option("xtick")))
        print(f"labels to ticks {labels_to_ticks}; bar x {bar.x}")  # TODO remove
        xs = [labels_to_ticks[tex_text(tick)] for tick in bar.x]
        ys = bar.y
    else:
        xs = bar.x
        labels_to_ticks = dict(zip(axis.get_option("yticklabels"), axis.get_option("ytick")))
        print(f"labels to ticks {labels_to_ticks}; bar y {bar.y}")  # TODO remove
        ys = [labels_to_ticks[tex_text(tick)] for tick in bar.y]

    # TODO: i'm not seeing when this is not true.
    # this used to be a loop over all the elements of x and y, using draw_bar_indiv for each, but i'm not seeing when that's actually used
    assert len(bar.x) == len(bar.y) == len(color) == 1, f"length of x ({bar.x}), y ({bar.y}), or color ({color}) was not 1 in individual bar plot"
    print(f"bar x {bar.x}, y {bar.y}, color {color}")  # TODO remove
    print(f"xs {xs}, ys {ys}, color {color}")  # TODO remove

    cur_bar = deepcopy(bar)  # to get a bar object 
    
    cur_bar.x = array(xs, dtype=bar.x.dtype)
    cur_bar.y = array(ys, dtype=bar.y.dtype)
    print(f"cur bar x {cur_bar.x} (len {len(cur_bar.x)}), y {cur_bar.y} (len {len(cur_bar.y)})")  # TODO remove

    cur_bar.marker.color = color[0]
    code += draw_bar_indiv(cur_bar, colors_set)

    return code

def draw_bar_indiv(bar, colors_set):
    """Get code for a single bar in a bar plot."""

    code = ""
    marker = bar.marker
    orientation = orientation_to_idx(bar.orientation)
    options_dict = {V_H_CORRESP["bar"][orientation]: None}

    font_schema = {"color": None, "family": None, "size": None, "style": None, "variant": None, "weight": None}
    tickformatstops_schema = {"dtickrange": None, "enabled": None, "name": None, "templateitemname": None, "value": None}

    marker_schema = {
        "pattern": {"arg": None, "bgcolor": None, "bgcolorsrc": None, "fgcolor": None, "fgcolorsrc": None, "fgopacity": None,
                    "fillmode": None, "shape": None, "shapesrc": None, "size": None, "sizesrc": None, "solidity": None, "soliditisrc": None},
        "colorbar": {"arg": None, "bgcolor": None, "bordercolor": None, "borderwidth": None, "dtick": None, "exponentformat": None,
                     "labelalias": None, "len": None, "lenmode": None, "minexponent": None, "nticks": None, "orientation": None,
                     "outlinecolor": None, "outlinewidth": None, "separatethousands": None, "showexponent": None, "showticklabels": None,
                     "showtickprefix": None, "showticksuffix": None, "thickness": None, "thicknessmode": None, "tick0": None, "tickangle": None,
                     "tickcolor": None,
                     "tickfont": font_schema,
                     "tickformat": None,
                     "tickformatstops": tickformatstops_schema,
                     "tickformatstopdefaults": tickformatstops_schema,
                     "ticklabeloverflow": None, "ticklabelposition": None, "ticklabelstep": None, "ticklen": None, "tickmode": None,
                     "tickprefix": None, "ticks": None, "ticksuffix": None, "ticktext": None, "ticktextsrc": None, "tickvals": None,
                     "tickvalssrc": None, "tickwidth": None,
                     "title": {
                         "font": font_schema,
                         "side": None, "text": None
                     },
                     "titlefont": font_schema,
                     "titleside": None, "x": None, "xanchor": None,
                     "xpad": None, "xref": None, "y": None, "yanchor": None, "ypad": None, "yref": None},
        "line": {"arg": None, "autocolorscale": None, "cauto": None, "cmax": None, "cmid": None, "cmin": None, "color": None, "coloraxis": None,
                    "colorscale": None, "colorsrc": None, "reversescale": None, "width": None, "widthsrc": None}
    }

    def recursive_nonempty(obj, schema):
        # get the items which have a leaf node which is not None or ''
        if schema is None:
            out = obj if obj not in [None, ''] else None
        else:
            out = {k: v for k, v in {key: recursive_nonempty(getattr(obj, key), value) for key, value in list(schema.items()) if getattr(obj, key, None) is not None}.items() if v is not None}
        if out:
            return out
        else:
            return None
        
    nonempty_options = recursive_nonempty(marker, marker_schema)
    if nonempty_options:
        warn(f"Bar chart marker properties are not supported; ignoring options {nonempty_options}.")

    if marker.color is not None:
        try:
            int(marker.color)
            is_numeric = True
        except Exception as e:
            is_numeric = False

        if isinstance(marker.color, str):
            color, _ = convert_color(marker.color, colors_set)
            if color is None:
                color = marker.color
        elif is_numeric:
            # if it's a single number, assume it goes with a colorscale
            color = str(marker.color)
        else:
            # if it's an integer array, assume it's an rgb or rgba array
            try:
                is_int_vals = all(isinstance(c, int) for c in marker.color)
            except Exception as e:
                is_int_vals = False
            if is_int_vals:
                if len(marker.color) == 3:
                    color_str = f"rgb({', '.join(str(c) for c in marker.color)})"
                elif len(marker.color) == 4:
                    color_str = f"rgba({', '.join(str(c) for c in marker.color)})"
                else:
                    warn(f"Unsupported color format for {marker.color}; falling back to blue.")
                    color_str = "blue"
            else:
                warn(f"Unsupported color format for {marker.color}; falling back to blue.")
                color_str = "blue"
            color, _ = convert_color(color_str, colors_set)
            if color is None:
                color = color_str

    options_dict["fill"] = color
    options_dict["draw"] = "none"  # to make it look more like plotly defaults

    error_opts = {}

    def zeros_if_none(arr, default_len):
        return arr if arr is not None else [0] * default_len

    if bar.error_x is not None or bar.error_y is not None:
        options_dict["error bars/.cd"] = None
        options_dict["error bar style"] = {"black": None}
        if bar.error_x is not None:
            options_dict["x dir"] = "both"
            options_dict["x explicit"] = None
        if bar.error_y is not None:
            options_dict["y dir"] = "both"
            options_dict["y explicit"] = None

        x_err = zeros_if_none(bar.error_x.array, len(bar.x))
        y_err = zeros_if_none(bar.error_y.array, len(bar.y))
        error_opts["errors"] = zip(x_err, y_err)
        if bar.error_x.arrayminus is not None or bar.error_y.arrayminus is not None:
            # we have to set all of them if we set any of them so that zipping them together works
            x_err_neg = bar.error_x.arrayminus if bar.error_x.arrayminus is not None else x_err
            y_err_neg = bar.error_y.arrayminus if bar.error_y.arrayminus is not None else y_err
            error_opts["errors_neg"] = zip(x_err_neg, y_err_neg)

    print("bar x", bar.x, "bar y", bar.y, "err opts", error_opts)  # TODO remove
    options = dict_to_tex_str(options_dict)

    code += tex_addplot(coords_to_str(zip(bar.x, bar.y), **error_opts), type="coordinates", options=options, override=True)

    return code
