from copy import deepcopy
from warnings import warn
from plotly.express.colors import sample_colorscale

from ._tex import *
from ._color import *
from ._marker import marker_symbol_to_tex
from ._dash import *
from ._axis import Axis
from ._data import *
from ._utils import px_to_pt, dict_to_tex_str, sanitize_text
from numpy import round, array

def _x_y_to_str(x, y):
    coords = list(zip(x, y))
    return " ".join(f"({', '.join(tex_text(str(c)) for c in coord)})" for coord in coords)

class Bar:
    def __init__(self, bar, fig_info, options={'ymajorgrids': None, 'xtick style': {'draw': 'none'}, 'ytick style': {'draw': 'none'}, 'axis line style': {'draw': 'none'}, 'major grid style': {'color': 'white'}, 'axis background/.style': {'fill': 'blue!10'}}):
        """Create a Bar object from Plotly info.

        Parameters
        ----------
        bar
            bar trace from Plotly figure
        fig_info
            a dictionary of information about the figure (e.g. height, width, coloraxis)
        options
            dictionary of options to set for the bar plot
        """
        self.trace = bar
        self.fig_info = fig_info
        self.options = options

        self._split_bars()

    def update_axis(self, axis):
        """Update the axis with the options for the bar plot.

        Parameters
        ----------
        axis
            axis object previously created
        """

        axis_options = self._get_axis_parameters()
        for key, value in axis_options.items():
            axis.add_option(key, value)

    def _get_axis_parameters(self):
        """Update the axis with the options for the bar plot. Creates self.axis_options, a dictionary of options to set for the axis.

        Parameters
        ----------
        axis
            axis object previously created

        Returns
        -------
        axis_options
            dictionary of options to set for the axis
        """

        if hasattr(self, "axis_options"):
            return self.axis_options

        self.axis_options = {}

        # first, some stuff to make it look more like a plotly bar chart by default
        for key, value in self.options.items():
            self.axis_options[key] = value

        self.axis_options["xtick"] = "data"

        # pgfplots uses only the x tick coordinates from the first addplot command, so we need to add all the coordinates to the first plot
        self.axis_options["symbolic x coords"] = [tex_text(xv) for xv in self.trace.x]

        if 'y' not in self.options:
            # default to 'height' from the figure layout
            height = self.fig_info["height"]
            self.axis_options["y"] = f"{px_to_pt(height)}"

        if 'x' in self.options and 'bar width' in self.options and 'enlarge x limits' in self.options:
            pass
        elif 'x' not in self.options and 'bar width' not in self.options and 'enlarge x limits' not in self.options:  # if none are set, we can calculate defaults
            # x defaults to 'width' from the figure layout divided by the number of bars (since 'x' is the width of a single bar)
            x_width = self.fig_info["width"] / self.fig_info["n_bars"]
            self.axis_options["x"] = f"{px_to_pt(x_width)}"

            # bar width defaults to 75% of x
            self.axis_options["bar width"] = f"{px_to_pt(x_width * 0.75)}"

            # fraction of overall width (i.e. x range, x * (# bars - 1) since bars are centered on indices) by which to enlarge.
            # we want the absolute spacing added to be the same as the inter-bar spacing + 1/2 the width of a bar,
            # which is x - bar width + 1/2 bar width. so this should be (x - 1/2 bar width) / (x * (# bars - 1))
            if self.fig_info["n_bars"] > 1:
                self.axis_options["enlarge x limits"] = (x_width - x_width * 0.75 / 2) / (x_width * (self.fig_info["n_bars"] - 1))

            if 'x tick label style' not in self.options:
                # determine whether it is necessary to decrease the font size or rotate it.
                # we estimate this by noting that the default em is 10pt.
                # so, the caption text width is at most the number of characters * 10pt.
                # if the caption text would overlap if it's as wide as possible, and the figure is not too large,
                # we decrease the font size to 'tiny' (6pt) and see if this fits.
                # if it still doesn't fit, or if the figure is not that large to begin with,
                # we rotate the text by 30 degrees and shift it to align nicely with the bars.

                # determine if there may be an overlap
                text_pt = 10
                if any((len(v1) + len(v2)) * text_pt > 2*px_to_pt(x_width) for v1, v2 in zip(self.trace.x, self.trace.x[1:])):
                    x_tick_label_style = {}
                    if px_to_pt(x_width * self.fig_info["n_bars"]) < 300:
                        # the figure is small enough that it's likely not going to be scaled down, so it's ok to decrease the font size
                        x_tick_label_style['font'] = '\\tiny'
                        text_pt = 6
                    # check if the text is still too long
                    if any((len(v1) + len(v2)) * text_pt > 2*px_to_pt(x_width) for v1, v2 in zip(self.trace.x, self.trace.x[1:])):
                        x_tick_label_style['rotate'] = '-30'
                        x_tick_label_style['anchor'] = 'west'
                        x_tick_label_style['xshift'] = '-1mm'
                        x_tick_label_style['yshift'] = '-2mm'

                        if 'x label style' not in self.options:
                            # should be moved down by the height of the rotated text - the height of the unrotated text
                            # sin(30 degrees) = 1/2
                            rotated_text_height = max(len(xv) for xv in self.trace.x) * text_pt * 1/2
                            self.axis_options["x label style"] = {'yshift': - (rotated_text_height - text_pt)}
                    self.axis_options["x tick label style"] = x_tick_label_style

        else:  # if only some are set, can't get defaults without reading in latex-formatted distances (x may be in pts, px, cm, ...)
            warn("Bar chart x, bar width, and enlarge x limits must all be set together to calculate defaults; ignoring.")

        return self.axis_options

    def _convert_color(self, color):
        """Convert a color to its format for LaTeX.

        Parameters
        ----------
        color
            color to convert to LaTeX format

        Returns
        -------
        A 4-tuple containing the following:
        - the name of the color, or a hash of the color if it is not a named color
        - the type of the color, can be "RGB", "HTML" or None
        - the color string
        - the opacity value, 1 if the color is not an rgba string
        """
        # Leave color as None if it is None
        if color is None:
            return None, None

        return convert_color(color)

    def _sanitize_color(self, color):
        """Sanitize the color to be input to convert_color.

        Parameters
        ----------
        color
            color to sanitize

        Returns
        -------
        color
            a string representing the color which is in a format that convert_color can read
        """

        # Check if the color belongs to a colorscale, and convert it to RGB if it does
        if self._get_colorscale() is not None:
            try:
                int(color)
                is_numeric = True
            except Exception as e:
                is_numeric = False

            if is_numeric:
                return sample_colorscale(self.color_scale, [color], colortype="rgb")

        # If the color is a string, it's ready to be converted to LaTeX
        if isinstance(color, str):
            return color

        # If it's an integer array of length 3 or 4, try to format it as an RGB or RGBA string
        try:
            is_int_vals = all(isinstance(c, int) for c in color)
        except Exception as e:
            is_int_vals = False
        if is_int_vals:
            if len(color) == 3:
                color = f"rgb({', '.join(str(c) for c in color)})"
            elif len(color) == 4:
                color = f"rgba({', '.join(str(c) for c in color)})"
            else:
                warn(f"Unsupported color format for {color}.")
                color = "blue"
        else:
            warn(f"Unsupported color format for color '{color}'; interpreting as a name.")
        converted_color = convert_color(color)


        #    # if not recog
        #    warn(f"Bar chart color format not recognized; interpreting color '{color}' as a name.")
        #        return str(color), None

        if converted_color is not None:
            color = converted_color[0]
            color_set.add(converted_color[:3])

    def _get_colorscale(self):
        """Get the colorscale for the bar plot. Creates self.color_scale, the color scale used (None if no color scale is used)."""
        if hasattr(self, "color_scale"):
            return self.color_scale

        if getattr(self.trace, "color_continuous_scale", None) is not None:
            self.color_scale = [list(v) for v in self.trace.color_continuous_scale]
        elif getattr(self.fig_info.get("coloraxis", None), "colorscale", None) is not None:
            self.color_scale = [list(v) for v in self.fig_info["coloraxis"].colorscale]
        else:
            self.color_scale = None

        return self.color_scale


    def _get_colors(self):
        """Compute the colors of the bar plot.
        Creates self.colors, a list of RGBA colors

        Returns
        -------
        colors
            list of all the RGBA colors used in the bar plot
        """
        if hasattr(self, "colors"):
            return self.colors

        if not hasattr(self, "color_scale"):
            self._get_colorscale()

        # check if color is an array of the same length as x and y; if not, broadcast it
        try:
            color_len = len(self.trace.marker.color)
        except Exception as e:
            color_len = 0
        if color_len != len(self.trace.x):
            if color_len != 0:  # the color was an array, but not the same length as x and y
                warn(f"Bar chart color values have different lengths than x and y; trace {self.trace.name} is likely not being interpreted correctly!")
            self.colors = [self.trace.marker.color for _ in self.trace.x]
        else:
            if self.color_scale is not None:
                # we need to convert the colorscale to a list of fully specified colors to use in the subplots
                self.colors = sample_colorscale(self.color_scale, self.trace.marker.color, colortype="rgb")
            else:
                self.colors = self.trace.marker.color








        return self.colors


    def _split_bars(self):
        """
        Tries to split the bar trace into individual bars.
        Creates self.plots, a list of Plotly traces to draw
        """

        # check that the x and y values have the same length. if they don't, try to draw the whole trace at once
        if len(self.trace.x) != len(self.trace.y):
            warn(f"Bar chart x and y values have different lengths; trace {self.trace.name} is likely not being interpreted correctly!")
            self.plots = [self.trace]
            return

        # --- Split into individual bars ---
        colors = self._get_colors()

        # the first bar needs to have all the x tick coordinates, or they won't display
        all_x = [[xv] for xv in self.trace.x]
        all_y = [[yv] for yv in self.trace.y]
        all_x[0] = self.trace.x
        all_y[0] = self.trace.y

        self.plots = []

        for x, y, c in zip(all_x, all_y, colors):
            cur_bar = deepcopy(self.trace)
            cur_bar.x = array(x, dtype=self.trace.x.dtype)
            cur_bar.y = array(y, dtype=self.trace.y.dtype)
            cur_bar.marker.color = c
            self.plots.append(cur_bar)


    def update_color_set(self, color_set):
        """Update the color set with the colors used in the figure.

        Parameters
        ----------
        color_set
            set of colors used in the overall figure
        """
        for color in self._get_colors():
            color_set.add(color[:3])

    def to_tex(self):
        """Get code for a bar plot.

        Returns
        -------
            string of tikz code for the scatter trace
        """
        pass

def draw_bar(bar, axis: Axis, fig_info, color_set, options={'ymajorgrids': None, 'xtick style': {'draw': 'none'}, 'ytick style': {'draw': 'none'}, 'axis line style': {'draw': 'none'}, 'major grid style': {'color': 'white'}, 'axis background/.style': {'fill': 'blue!10'}}):
    """Get code for a bar plot.

    Parameters
    ----------
    bar
        bar trace from Plotly figure
    axis
        axis object previously created
    fig_info
        a dictionary of information about the figure (e.g. height, width, coloraxis)
    color_set
        set of colors used in the figure

    Returns
    -------
        string of tikz code for the scatter trace
    """

    # first, some stuff to make it look more like a plotly bar chart by default
    for key, value in options.items():
        axis.add_option(tex_text(key), value)

    if 'y' not in options:
        # default to 'height' from the figure layout
        height = fig_info["height"]
        axis.add_option("y", f"{px_to_pt(height)}")

    if 'x' in options and 'bar width' in options and 'enlarge x limits' in options:
        pass
    elif 'x' not in options and 'bar width' not in options and 'enlarge x limits' not in options:  # if none are set, we can calculate defaults
        # x defaults to 'width' from the figure layout divided by the number of bars (since 'x' is the width of a single bar)
        x_width = fig_info["width"] / fig_info["n_bars"]
        axis.add_option("x", f"{px_to_pt(x_width)}")

        # bar width defaults to 75% of x
        bar_width = x_width * 0.75
        axis.add_option("bar width", f"{px_to_pt(bar_width)}")

        # fraction of overall width (i.e. x range, x * (# bars - 1) since bars are centered on indices) by which to enlarge.
        # we want the absolute spacing added to be the same as the inter-bar spacing + 1/2 the width of a bar,
        # which is x - bar width + 1/2 bar width. so this should be (x - 1/2 bar width) / (x * (# bars - 1))
        if fig_info["n_bars"] > 1:
            axis.add_option("enlarge x limits", (x_width - bar_width / 2) / (x_width * (fig_info["n_bars"] - 1)))

        if 'x tick label style' not in options:
            # determine whether it is necessary to decrease the font size or rotate it.
            # we estimate this by noting that the default em is 10pt.
            # so, the caption text width is at most the number of characters * 10pt.
            # if the caption text would overlap if it's as wide as possible, and the figure is not too large,
            # we decrease the font size to 'tiny' (6pt) and see if this fits.
            # if it still doesn't fit, or if the figure is not that large to begin with,
            # we rotate the text by 30 degrees and shift it to align nicely with the bars.

            # determine if there may be an overlap
            text_pt = 10
            if any((len(v1) + len(v2)) * text_pt > 2*px_to_pt(x_width) for v1, v2 in zip(bar.x, bar.x[1:])):
                x_tick_label_style = {}
                if px_to_pt(x_width * fig_info["n_bars"]) < 300:  # the figure is small enough that it's likely not going to be scaled down, so it's ok to decrease the font size
                    x_tick_label_style['font'] = '\\tiny'
                    text_pt = 6
                # check if the text is still too long
                if any((len(v1) + len(v2)) * text_pt > 2*px_to_pt(x_width) for v1, v2 in zip(bar.x, bar.x[1:])):
                    x_tick_label_style['rotate'] = '-30'
                    x_tick_label_style['anchor'] = 'west'
                    x_tick_label_style['xshift'] = '-1mm'
                    x_tick_label_style['yshift'] = '-2mm'

                    if 'x label style' not in options:  # move the x label down to make room
                        # should be moved down by the height of the rotated text - the height of the unrotated text
                        # sin(30 degrees) = 1/2
                        rotated_text_height = max(len(xv) for xv in bar.x) * text_pt * 1/2
                        axis.add_option("x label style", {'yshift': - (rotated_text_height - text_pt)})
                axis.add_option("x tick label style", x_tick_label_style)

    else:  # if only some are set, can't get defaults without reading in latex-formatted distances (x may be in pts, px, cm, ...)
        warn("Bar chart x, bar width, and enlarge x limits must all be set together to calculate defaults; ignoring.")

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
        return draw_bar_indiv(bar, axis, color_set)

    else:
        code = ""

        # check if color is an array of the same length as x and y; if not, broadcast it
        if bar.marker.color is None or len(bar.marker.color) != len(bar.x):
            color = [bar.marker.color for _ in bar.x]
        else:
            if color_scale is not None:
                # we need to convert the colorscale to a list of fully specified colors to use in the subplots
                color = sample_colorscale(color_scale, bar.marker.color, colortype="rgb")
            else:
                color = bar.marker.color

        # pgfplots uses only the x tick coordinates from the first addplot command, so we need to add all the coordinates to the first plot
        for xv in bar.x:
            axis.update_option("symbolic x coords", [tex_text(xv)], lambda x, y: x if y in x else x + y)
        all_x = [[xv] for xv in bar.x]
        all_y = [[yv] for yv in bar.y]
        all_x[0] = bar.x  # put all coordinates in the first plot
        all_y[0] = bar.y

        for x, y, c in zip(all_x, all_y, color):
            cur_bar = deepcopy(bar)
            cur_bar.x = array(x, dtype=bar.x.dtype)
            cur_bar.y = array(y, dtype=bar.y.dtype)
            cur_bar.marker.color = c
            code += draw_bar_indiv(cur_bar, axis, color_set)

        return code


def draw_bar_indiv(bar, axis: Axis, color_set):
    """Get code for a single bar in a bar plot."""

    code = ""

    marker = bar.marker

    options_dict = {"ybar": None}

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
            color = marker.color
            converted_color = convert_color(color)
        elif is_numeric:
            # if it's a single number, assume it goes with a colorscale
            color = str(marker.color)
            converted_color = None
        else:
            # if it's an integer array, assume it's an rgb or rgba array
            try:
                is_int_vals = all(isinstance(c, int) for c in marker.color)
            except Exception as e:
                is_int_vals = False
            if is_int_vals:
                if len(marker.color) == 3:
                    color = f"rgb({', '.join(str(c) for c in marker.color)})"
                elif len(marker.color) == 4:
                    color = f"rgba({', '.join(str(c) for c in marker.color)})"
                else:
                    warn(f"Unsupported color format for {marker.color}; falling back to blue.")
                    color = "blue"
            else:
                warn(f"Unsupported color format for {marker.color}; falling back to blue.")
                color = "blue"
            converted_color = convert_color(color)
        if converted_color is not None:
            color = converted_color[0]
            color_set.add(converted_color[:3])

    options_dict["fill"] = color
    options_dict["draw"] = "none"  # to make it look more like plotly defaults

    options = dict_to_tex_str(options_dict)
    code += tex_addplot(_x_y_to_str(bar.x, bar.y), type="coordinates", options=options, override=True)

    return code
