
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
    stack_env.append(environment)
    if options is not None:
        return f"\\begin{{{environment}}}[\n{options}\n]\n"
    else:
        return f"\\begin{{{environment}}}\n"
    
def tex_end_environment(stack_env):
    environment = stack_env.pop()
    return f"\\end{{{environment}}}\n"

def tex_end_all_environment(stack_env):
    code = ""
    while len(stack_env) > 0:
        code += tex_end_environment(stack_env)
    return code

def tex_addplot(data_str, type="table", options=None):
    code = "\\addplot+ "
    if options is not None:
        code += f"[{options}] "
    code += type + " {%\n"
    code += data_str
    code += "};\n"
    return code

def tex_add_text(x, y, text, color="black"):
    return f"\draw (axis cs:{x},{y}) node[scale=0.5, anchor=south east, text={color}, rotate=0.0]{{{text}}};\n"

def tex_add_color(color_name, type_color, color):
    if type_color is not None:
        return f"\\definecolor{{{color_name}}}{{{type_color}}}{{{color}}}\n"
    else:
        return ""

def tex_add_legendentry(legend, options=None):
    if options is not None:
        return f"\\addlegendentry[{options}]{{{legend}}}\n"
    else:
        return f"\\addlegendentry{{{legend}}}\n"


def tex_create_document(document_class="article", options=None, compatibility="newest"):
    if options is not None:
        code = f"\\documentclass[{options}]{{{document_class}}}\n"
    else:
        code = f"\\documentclass{{{document_class}}}\n"
    code += "\\usepackage{pgf, tikz}\n\\usepackage{pgfplots}\n"
    code += "\\pgfplotsset{compat=" + compatibility + "}\n\n"
    return code
