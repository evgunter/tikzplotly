from copy import deepcopy
import numpy as np
import io
from PIL import Image
from warnings import warn
from ._tex import tex_addplot
from ._axis import Axis
from ._color import DEFAULT_COLORSCALE
from ._utils import get_ticks_str, dict_to_tex_str, tex_text, Colorscale, px_to_pt
from ._defaults import get_axis_latex_font_size, needs_rotate, PLOTLY_DEFAULT_AXIS_DISPLAY_OPTIONS

def crop_image(img_data):
    """Crops an image to the smallest bounding box that contains all non-white pixels.

    Parameters
    ----------
    img_data
        A PIL Image object.

    Returns
    -------
        cropped_image : PIL Image
    """
    image_np = np.array(img_data)
    non_white_rows = np.any(image_np != [255, 255, 255, 255], axis=1)
    non_white_cols = np.any(image_np != [255, 255, 255, 255], axis=0)

    top, bottom = np.where(non_white_rows)[0][[0, -1]]
    left, right = np.where(non_white_cols)[0][[0, -1]]
    cropped_image = Image.fromarray(image_np[top:bottom+1, left:right+1])

    return cropped_image

def resize_image(img, nb_row, nb_col):
    """Resizes an image to a given number of rows and columns.

    Parameters
    ----------
    img
        A PIL Image object.
    nb_row
        The number of rows of the resized image.
    nb_col
        The number of columns of the resized image.

    Returns
    -------
        resized_image : PIL Image
    """
    resized_image = Image.new("RGBA", size = (nb_col, nb_row))
    block_size = (img.width // nb_col, img.height // nb_row)

    if block_size[0] != img.width / nb_col or block_size[1] != img.height / nb_row:
        warn("png image has not been reduced, see https://github.com/thomas-saigre/tikzplotly/issues/6#issuecomment-2106180586")
        return img

    for i in range(nb_row):
        for j in range(nb_col):
            color = img.getpixel((j * block_size[0], i * block_size[1]))
            resized_image.putpixel((j, i), color)

    return resized_image


def draw_heatmap(data, fig, axis: Axis, height, width, colors_set, options={}):
    """Draw a heatmap, and return the tikz code.

    Parameters
    ----------
    data
        data array to be plotted
    fig
        whole plotly figure
    axis
        axis object previously created
    height
        max height of the heatmap in px
    width
        max width of the heatmap in px

    Returns
    -------
        string of tikz code for the scatter trace
    """
    def set_opts(opts, override=False):
        for key, value in opts.items():
            # set the options if they're not already set
            if type(value) == dict and type(axis.get_option(key)) == dict:
                if override:
                    # override the existing options: the new value takes precedence
                    axis.update_option(key, value, lambda a, b: a | b)
                else:
                    # don't override the existing options: the existing value takes precedence
                    axis.update_option(key, value, lambda a, b: b | a)
            else:
                axis.update_option(key, value, lambda a, b: a if a is not None else b)
                
    # first, set any explicit options
    set_opts(options, override=True)
    
    # now, make it look more like the plotly defaults
    set_opts(PLOTLY_DEFAULT_AXIS_DISPLAY_OPTIONS, override=False)

    # technique similar to https://kristofferc.github.io/PGFPlotsX.jl/v1/examples/juliatypes/#D-2
    # create a 3D figure and view it from the top
    axis.add_option("view", ({0: None}, {90: None}))
    if not (fig.layout.coloraxis.showscale == False):   # If the value is True or None
        axis.add_option("colorbar", None)
        # TODO: these are the default plotly style options; use the actual plotly options instead
        axis.add_option("colorbar style", {"ytick style": {"draw": "none"}, "axis line style": {"draw": "none"}})

    options_dict = {"surf": None, "shader": {"flat": None}}

    # get a colorscale
    if (colorscale := data.colorscale) is not None:
        axis.add_option("colormap", Colorscale(colorscale, colors_set))
    elif (colorscale := fig.layout.coloraxis.colorscale) is not None:
        axis.add_option("colormap", Colorscale(colorscale, colors_set))
    elif data.showscale is not False:
        warn("No colorscale found, using default")
        axis.add_option("colormap", Colorscale(DEFAULT_COLORSCALE, colors_set))

    # does nothing, but makes it easy for the user to change the size after generation
    if "scale" not in axis.options:
        axis.add_option("scale", 1)

    row_sep = "\\\\"
    data_str = f"x y z {row_sep}\n"

    # it's apparently valid to have a heatmap without any data.
    # everything below this depends on the data, so just return early if there isn't any.
    if data.z is None:
        code = tex_addplot(data_str, type="table", options=dict_to_tex_str(options_dict), type_options="row sep={" + row_sep + "}", override=True, three_d=True, annotations_str=None)
        return code
    
    # TODO: this does not handle nans properly--they break the display. either we should specifically display gray or the corresponding squares should not exist

    figure_data = np.array(data.z)

    # this technique is actually plotting a surface on a grid.
    # so, we need to define the vertices of squares which will have the desired average height to have the correct color.
    # however, since this is a surface, it's required to be continuous. this is a problem when the data changes rapidly;
    # some of the vertices will have to deviate far from the desired height to make the average height of the square correct.
    # this will mess up a colormap which scales with the data.
    # so, we will cheat by having extremely narrow rectangles at the borders of our squares which change height very rapidly
    # but are narrow enough that they are invisible when actually plotted, giving the appearance of a discontinuity.

    # each original data point corresponds to 4 vertices in the grid
    grid = np.zeros((2 * figure_data.shape[0], 2 * figure_data.shape[1]))

    # expand the original data points to blocks
    grid[::2, ::2] = figure_data
    grid[1::2, ::2] = figure_data
    grid[::2, 1::2] = figure_data
    grid[1::2, 1::2] = figure_data

    # now write out the grid as a table
    for j in range(grid.shape[0]):
        for i in range(grid.shape[1]):
            # we make the grid squares corresponding to the actual values a normal size, and the borders very small
            data_str += f"{(i + 1) // 2 - (i % 2) * 0.000001} {(j + 1) // 2 - (j % 2) * 0.000001} {grid[j, i]} {row_sep}\n"
        data_str += f"{row_sep}\n"

    # now set xtick, ytick, xticklabels, and yticklabels so that the x and y ticks display at the center of the squares, with the correct labels
    axis.add_option("xtick", [str(i + 0.5) for i in range(figure_data.shape[1])])
    axis.add_option("xtick style", {"draw": "none"})
    if data.x is not None:
        axis.add_option("xticklabels", [tex_text(str(v)) for v in data.x])
    else:
        axis.add_option("xticklabels", [tex_text(str(i)) for i in range(figure_data.shape[1])])
        # add ticks at the center of the squares
    axis.add_option("ytick", [str(i + 0.5) for i in range(figure_data.shape[0])])
    axis.add_option("ytick style", {"draw": "none"})
    if data.y is not None:
        axis.add_option("yticklabels", [tex_text(str(v)) for v in data.y])
    else:
        axis.add_option("yticklabels", [tex_text(str(i)) for i in range(figure_data.shape[0])])
    # remove zticks, since this is a 2D plot
    axis.add_option("ztick", {})
    axis.add_option("zticklabels", {})
    axis.add_option("ztick style", {"draw": "none"})

    if axis.get_option("x tick label style").get("rotate", None) is None:
        # if rotate isn't explicitly set, guess whether any xticklabel is longer than the width of a heatmap square
        # and rotate them if so
        rotation = needs_rotate("xticklabels", axis, width / figure_data.shape[1])
        if rotation is not None:
            axis.update_option("x tick label style", {"rotate": rotation}, lambda a, b: b | a)
        
    tmp = np.where(figure_data == None, np.nan, figure_data)
    # these point meta min/max assignments shouldn't do anything because we should've set the meta max/min for each coloraxis already.
    # however, it may be possible to have a heatmap without a coloraxis, and it's not harmful to update them here
    # (if the max and min have already been set appropriately, it won't change anything)
    axis.update_option("point meta max", np.nanmax(tmp), max)
    axis.update_option("point meta min", np.nanmin(tmp), min)
    axis.update_option("xmin", 0, min)
    axis.update_option("xmax", figure_data.shape[1], max)
    axis.update_option("ymin", 0, min)
    axis.update_option("ymax", figure_data.shape[0], max)

    # remove xmin and xmax if xtick = data
    if axis.options.get("xtick", None) == "data":
        axis.remove_option("xmin")
        axis.remove_option("xmax")

    # make the box height and width the same so the boxes are square,
    # unless height and width have previously been seet for the axis.
    # (so, if you want non-square boxes, you must set the height and width before this.
    # you'll also probably get issues if you set only one of them)

    # first, find which of the max height and max width are proportionally smaller for this plot shape
    # (seems better to err on the side of making small figures rather than overlapping ones)
    box_height = height / figure_data.shape[0]
    box_width = width / figure_data.shape[1]

    # take the smaller of the real box height and box width and scale the other down to match
    box_dim = min(box_height, box_width)
    # if the height and width are explicitly specified, don't modify them
    axis.update_option("height", px_to_pt(box_dim * figure_data.shape[0]), lambda a, b: a if a is not None else b)
    axis.update_option("width", px_to_pt(box_dim * figure_data.shape[1]), lambda a, b: a if a is not None else b)

    # check if texttemplate or textauto is used
    if data.texttemplate:
        if data.texttemplate != "%{z}":
            warn(f"Text template is not supported yet; using plain values.")
        # add nodes for all the data values.
        # data is indexed from the lower left; the center of the square right i and up j from the lower left is at (i + 0.5, j + 0.5) in axis coordinates
        annotations_strs = []
        for i in range(figure_data.shape[0]):
            for j in range(figure_data.shape[1]):
                value = figure_data[j, i]
                if value.is_integer():
                    value = int(value)
                # the color=... is necessary because there's a weird bug in addplot3 where it just leaves the text color as the last color used
                # (so, the color of the upper right square of the heatmap) until the scope ends
                if value > (axis.get_option("point meta max") + axis.get_option("point meta min")) / 2:  # TODO: it would be great to actually look at the colormap here and use a contrast formula
                    color = "white"
                else:
                    color = "black"
                annotations_strs.append(f"node[color={color}] at ({i + 0.5}, {j + 0.5}) {{{tex_text(str(value))}}}")
    else:
        annotations_strs = None

    code = tex_addplot(data_str, type="table", options=dict_to_tex_str(options_dict), type_options="row sep={" + row_sep + "}", override=True, three_d=True, annotations_str=None if annotations_strs is None else "\n".join(annotations_strs))
    return code
