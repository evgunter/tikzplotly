from ._color import color_to_tex, hex2rgb
from warnings import warn

def tex_comment(text):
    """Create a LaTeX comment.

    Parameters
    ----------
    text :
        text to be inserted in the comment

    Returns
    -------
        LaTeX comment
    """
    return f"% {text}\n"

def tex_begin_environment(environment, stack_env, options=None):
    """Open a LaTeX environment.

    Parameters
    ----------
    environment
        name of the environment
    stack_env
        stack of opened environments
    options, optional
        option given to the environment, by default None

    Returns
    -------
        LaTeX code for the beginning of the environment
    """
    stack_env.append(environment)
    if options is not None:
        return f"\\begin{{{environment}}}[\n{options}\n]\n"
    else:
        return f"\\begin{{{environment}}}\n"

def tex_end_environment(stack_env):
    """Close the last opened LaTeX environment.

    Parameters
    ----------
    stack_env
        stack of opened environments

    Returns
    -------
        LaTeX code for the end of the environment
    """
    environment = stack_env.pop()
    return f"\\end{{{environment}}}\n"

def tex_end_all_environment(stack_env):
    """Close all opened LaTeX environments.

    Parameters
    ----------
    stack_env
        stack of opened environments

    Returns
    -------
        LaTeX code for the end of all environments
    """
    code = ""
    while len(stack_env) > 0:
        code += tex_end_environment(stack_env)
    return code

def tex_addplot(data_str, type="table", options=None, type_options=None, override=False, three_d=False, annotations_str=None):
    """Create a LaTeX addplot command.

    Parameters
    ----------
    data_str
        string containing the data
    type, optional
        type of data, by default "table"
    options, optional
        options given to the addplot command, by default None
    type_options, optional
        options given to the type of data, by default None
    override, optional
        whether to use \addplot[options] instead of \addplot+ [options], by default False

    Returns
    -------
        LaTeX code for the addplot command
    """
    code = "\\addplot"
    if three_d:
        code += "3"
    if not override:
        code += "+ "
    if options is not None:
        code += f"[{options}] "
    code += type
    if type_options is not None:
        code += f"[{type_options}]"
    code += " {" + data_str + "}"
    if annotations_str is not None:
        code += annotations_str
    code += ";\n"
    return code

def tex_add_text(coords, text, options=None, relative=False, axisless=False, symbolic=False):
    """Create a LaTeX node command.

    Parameters
    ----------
    coords coordinates of the node: either (x, y) or symbolic (a string)
    text
        text of the node
    options, optional
        options given to the node command, by default None
    relative, optional
        boolean indicating if the coordinates are relative to the axis, by default False
    axisless, optional
        boolean indicating if axis coordinates are used, by default False
        
    Returns
    -------
        LaTeX code for the node command
    """
    if symbolic:
        return f"\\node at ({coords}) {{{tex_text(text)}}};\n"
    x, y = coords
    if axisless:
        if options is not None:
            return f"\\node[{options}] at ({x}, {y}) {{{tex_text(text)}}};\n"
        else:
            return f"\\node at ({x},{y}) {{{tex_text(text)}}};\n"
    relative_text = ["", "rel "][relative]
    if options is not None:
        return f"\\node[{options}] at ({relative_text}axis cs:{x}, {y}) {{{tex_text(text)}}};\n"
    else:
        return f"\\node at (axis cs:{x},{y}) {{{tex_text(text)}}};\n"

def tex_add_color(color_name, type_color, color):
    """Create a LaTeX color definition.

    Parameters
    ----------
    color_name
        name of the color
    type_color
        type of the color
    color
        color string

    Returns
    -------
        LaTeX code for the color definition
    """
    if type_color is not None:
        return f"\\definecolor{{{color_name}}}{{{type_color}}}{{{color}}}\n"
    else:
        return ""

def tex_add_legendentry(legend, options=None):
    """Create a LaTeX legend entry.

    Parameters
    ----------
    legend
        legend text
    options, optional
        options given to the legend entry, by default None

    Returns
    -------
        LaTeX code for the legend entry
    """
    if options is not None:
        return f"\\addlegendentry[{options}]{{{legend}}}\n"
    else:
        return f"\\addlegendentry{{{legend}}}\n"


def tex_create_document(document_class="article", options=None, compatibility="newest"):
    """Create a LaTeX document.

    Parameters
    ----------
    document_class, optional
        document class, by default "article"
    options, optional
        options given to the document class, by default None
    compatibility, optional
        compatibility of the pgfplots package, by default "newest"

    Returns
    -------
        LaTeX code for the document
    """
    if options is not None:
        code = f"\\documentclass[{options}]{{{document_class}}}\n"
    else:
        code = f"\\documentclass{{{document_class}}}\n"
    code += "\\usepackage{pgfplots}\n"
    code += "\\pgfplotsset{compat=" + compatibility + "}\n\n"
    return code


def tex_text(text):
    """Convert a string to LaTeX,
    escaping the special characters %, _, &, #, $, {, }, ~.
    """
    return text.replace("<br>", "\n").replace("\n", "\\\\ ").replace("%", "\\%").replace("_", "\\_").replace("&", "\\&").replace("#", "\\#").replace("$", "\\$").replace("{", "\\{").replace("}", "\\}").replace("~", "\\textasciitilde ")

def get_tikz_colorscale(colorscale, colors_set, name="mycolor"):

    code = "{" + str(name) + "}{\n"
    for dist, color in colorscale:
        color_type, color_string = color_to_tex(color, colors_set)

        if color_type == "RGB":
            code += f"  rgb255({dist}cm)=({color_string})".replace(" ", "") + ";\n"
        else:
            if color_type != "HTML":
                warn(f"Color {color} type is not supported. Assuming HTML.") 
            rgb_color = hex2rgb(color)
            code += f"  rgb255({dist}cm)=({rgb_color})".replace(" ", "") + ";\n"
    code += "}"
    return code

