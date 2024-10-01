from warnings import warn
from ._color import convert_color
from ._tex import tex_begin_environment, tex_end_environment
from ._utils import sanitize_TeX_text, dict_to_tex_str
class Axis():

    def __init__(self, layout, colors_set, axis_options=None):
        """Initialize an Axis.

        Parameters
        ----------
        layout
            layout of the figure
        colors_set
            set of colors used in the figure, to be filled with the colors of the axis
        axis_options
            options given to the axis environment, by default None. Can be a dict ({option: value}) or a string ("option1=value1, option2=value2").
        """
        self.x_label = layout.xaxis.title.text
        self.y_label = layout.yaxis.title.text
        self.title = layout.title.text
        self.options = {}
        if isinstance(axis_options, dict):
            self.options = axis_options
        elif isinstance(axis_options, str):
            for option in axis_options.split(","):
                option = option.strip()
                if "=" in option:
                    key, value = option.split("=")
                    self.options[key] = value
                else:
                    self.options[option] = None
        self.environment = "axis"

        if layout.xaxis.visible is False:
            self.x_label = None
            self.add_option("hide x axis", None)
        if layout.yaxis.visible is False:
            self.y_label = None
            self.add_option("hide y axis", None)

        # Handle log axes
        if layout.xaxis.type == "log":
            self.add_option("xmode", "log")
        if layout.yaxis.type == "log":
            self.add_option("ymode", "log")

        # Handle range
        # In log mode, the range is the exponent of the range : https://plotly.com/python/reference/layout/xaxis/#layout-xaxis-range
        # For more information, refer to documentation https://plotly.com/python/reference/layout/xaxis/#layout-xaxis-autorange
        if layout.xaxis.autorange is False or layout.xaxis.range is not None:
            self.add_option("xmin", layout.xaxis.range[0] if layout.xaxis.type != "log" else 10**layout.xaxis.range[0])
            self.add_option("xmax", layout.xaxis.range[1] if layout.xaxis.type != "log" else 10**layout.xaxis.range[1])
        if layout.yaxis.autorange is False or layout.yaxis.range is not None:
            self.add_option("ymin", layout.yaxis.range[0] if layout.yaxis.type != "log" else 10**layout.yaxis.range[0])
            self.add_option("ymax", layout.yaxis.range[1] if layout.yaxis.type != "log" else 10**layout.yaxis.range[1])
        if layout.xaxis.autorange == "reversed":
            self.add_option("x dir", "reverse")
        if layout.yaxis.autorange == "reversed":
            self.add_option("y dir", "reverse")

        if layout.plot_bgcolor is not None:
            bg_color = convert_color(layout.plot_bgcolor)
            colors_set.add(bg_color[:3])
            opacity = bg_color[3]
            if opacity < 1:
                self.add_option("axis background/.style", f"{{fill={bg_color[0]}, opacity={opacity}}}")
            else:
                self.add_option("axis background/.style", f"{{fill={bg_color[0]}}}")

    def set_x_label(self, x_label):
        """Set the x label.

        Parameters
        ----------
        x_label
            x label
        """
        self.x_label = x_label

    def set_y_label(self, y_label):
        """Set the y label.

        Parameters
        ----------
        y_label
            y label
        """
        self.y_label = y_label

    def add_option(self, option, value):
        """Add an option to the axis, to be used in the axis environment.

        Parameters
        ----------
        option
            name of the option
        value
            value of the option, can be None
        """
        if option in self.options and value != self.options[option]:
            warn(f"Option {option} already exists. Overwriting '{self.options[option]}' with '{value}'.")
        self.options[option] = value

    def get_option(self, option):
        """Get the value of an option of the axis.

        Parameters
        ----------
        option
            name of the option

        Returns
        -------
            value of the option
        """
        return self.options.get(option, None)

    def remove_option(self, option):
        """Remove an option from the axis.

        Parameters
        ----------
        option
            name of the option
        """
        if option in self.options:
            del self.options[option]
        else:
            warn(f"Option {option} not found.")

    def update_option(self, option, value, update_fn):
        """Update an option of the axis.

        Parameters
        ----------
        option
            name of the option
        value
            new value of the option
        update_fn
            a function which takes the old value and the new value and returns the desired value
        """
        if option in self.options:
            try:
                self.options[option] = update_fn(self.options[option], value)
            except Exception as e:
                warn(f"update_fn failed with error {e}. Overwriting {self.options[option]} with {value}.")
                self.options[option] = value
        else:
            self.options[option] = value

    def append_option(self, option, value: str):
        """Append a new value to an option of the axis.
        Lists of values are strings formatted like {value1, value2, value3}

        Parameters
        ----------
        option
            name of the option
        value
            value to append to the option
        """
        if option in self.options:
             # Warn if the option is not a list (i.e. the first and last characters are not '{' and '}')
            if not isinstance(self.options[option], list):
                warn(f"Option {option} is not a list. Converting to a list.")
                if "," in self.options[option]:
                    warn(f"Singleton value being converted to a list contains commas. Result will be interpreted as multiple list elements.")
                    self.options[option] = [v.strip() for v in ",".split(self.options[option])]
                else:
                    self.options[option] = [self.options[option]]
            self.options[option].append(value)
        else:
            self.options[option] = [value]

    def open_environment(self, stack_env, groupplots=False):
        """Open the axis environment.

        Parameters
        ----------
        stack_env
            stack of environments, to be filled with the axis environment
        """
        if groupplots:
            options = self.get_options_string()
            if options is not None:
                return f"\\nextgroupplot[\n{options}\n]\n"
            else:
                return "\\nextgroupplot\n"

        else:
            return tex_begin_environment(self.environment, stack_env, options=self.get_options_string())

    def close_environment(self, stack_env, groupplots=False):
        """Close the axis environment.

        Parameters
        ----------
        stack_env
            stack of environments, to be filled with the axis environment
        """
        if groupplots:
            return "\n"
        else:
            return tex_end_environment(stack_env)


    def get_options_string(self):
        """Get options string for the axis environment.

        Returns
        -------
            string of all options with their values
        """
        if self.title is not None:
            self.options["title"] = sanitize_TeX_text(self.title)
        if self.x_label is not None:
            self.options["xlabel"] = sanitize_TeX_text(self.x_label)
        if self.y_label is not None:
            self.options["ylabel"] = sanitize_TeX_text(self.y_label)
        options_str = dict_to_tex_str(self.options, sep="\n")
        return options_str
