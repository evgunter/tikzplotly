import re
import warnings
from math import floor
import numpy as np
from ._tex import tex_text, get_tikz_colorscale
from ._color import convert_color

rep_digit = {'0': 'Z', '1': 'O', '2': 'T', '3': 'Th', '4': 'F', '5': 'Fi', '6': 'S', '7': 'Se', '8': 'E', '9': 'N'}
rep_digit = dict((re.escape(k), v) for k, v in rep_digit.items())
pattern_digit = re.compile("|".join(rep_digit.keys()))

def replace_all_digits(text):
    """Replace all digits in a string with their corresponding letter.

    Parameters
    ----------
    text
        string to replace digits in

    Returns
    -------
        string with digits replaced by their corresponding letter
    """
    return pattern_digit.sub(lambda m: rep_digit[re.escape(m.group(0))], text)

rep_mounts = {"January": '1', 'February': '2', 'March': '3', 'April': '4', 'May': '5', 'June': '6', 'July': '7', 'August': '8', 'September': '9', 'October': '10', 'November': '11', 'December': '12',
              'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6, 'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12}
rep_mounts = dict((re.escape(k), v) for k, v in rep_mounts.items())
pattern_mounts = re.compile("|".join(rep_mounts.keys()))

def replace_all_mounts(text):
    """Replace all mounts in a string with their corresponding number.

    Parameters
    ----------
    text
        string to replace mounts in

    Returns
    -------
        string with mounts replaced by their corresponding number
    """
    return pattern_mounts.sub(lambda m: rep_mounts[re.escape(m.group(0))], text)


def sanitize_text(text: str):
    return "".join(map(sanitize_char, text))

def sanitize_char(ch):
    if ch in "[]{}= ": return f"x{ord(ch):x}"
    # if not ascii, return hex
    if ord(ch) > 127: return f"x{ord(ch):x}"
    # if not printable, return hex
    if not ch.isprintable(): return f"x{ord(ch):x}"
    return ch

def sanitize_TeX_text(text: str):
    s = "".join(map(sanitize_TeX_char, text))
    if '[' in s or ']' in s:
        return "{" + s + "}"
    return s

def sanitize_TeX_char(ch):
    if ch in "_{}": return f"\\{ch}"
    # if not ascii, return hex
    if ord(ch) > 127:
        warnings.warn(f"Character {ch} has been replaced by \"x{ord(ch):x}\" in output file")
        return f"x{ord(ch):x}"
    # if not printable, return hex
    if not ch.isprintable():
        warnings.warn(f"Character {ch} has been replaced by \"x{ord(ch):x}\" in output file")
        return f"x{ord(ch):x}"
    return ch

def px_to_pt(px):
    """Convert size in pixel to a size in point

    Parameters
    ----------
    px
        size in pixel

    Returns
    -------
    float
        size in point
    """
    pt = px * .75
    if round(pt, 4) == int(pt): return int(pt)
    else: return pt

class Colorscale:
    def __init__(self, colorscale, colors_set, name="mycolor"):
        self.colorscale = colorscale
        self.name = name
        self.colors_set = colors_set

    def __str__(self):
        return get_tikz_colorscale(self.colorscale, self.colors_set, self.name)
    
    def __eq__(self, other):
        return self.colorscale == other.colorscale and self.name == other.name

def dict_to_tex_str(dictionary, sep=" "):
    """Convert a dictionary of options to a string of options for TikZ.

    Parameters
    ----------
    dictionary
        dictionary to convert to tex format
    sep, optional
        separator between options, by default " "

    Returns
    -------
    string
        string representing the dictionary for TikZ. Does not include the enclosing brackets, so it can be used with both [] and {}
    """
    lst = []
    for key, value in dictionary.items():
        if value is None:
            lst.append(f"{key}")
        elif isinstance(value, dict):
            lst.append(f"{key}=" + "{" + f"{dict_to_tex_str(value, sep)}" + "}")
        elif isinstance(value, str):
            lst.append(f"{key}={tex_text(value)}")
        elif isinstance(value, list):
            lst.append(f"{key}=" + "{" + f"{f',{sep}'.join(map(str, value))}" + "}")
        elif isinstance(value, int) or isinstance(value, float):
            lst.append(f"{key}={value}")
        elif isinstance(value, tuple):  # multiple arguments
            lst.append(f"{key}=" + "".join(["{" + dict_to_tex_str(v, sep) + "}" for v in value]))
        elif isinstance(value, Colorscale):
            lst.append(f"{key}={str(value)}")
        else:
            warnings.warn(f"Converting value {value} of type {type(value)} to string")
            lst.append(f"{key}={tex_text(str(value))}")
    return f",{sep}".join(lst)

def get_ticks_str(data, nticks):
    indices = np.arange(len(data))
    if nticks is not None:
        data_ = data[::len(data)//(nticks-1)]
        data = np.append(data_, [data[-1]])
        indices_ = indices[::len(indices)//(nticks-1)]
        indices = np.append(indices_, [indices[-1]])

    ticks = "{"
    ticklabels = "{"
    for i, val in zip(indices, data):
        ticks += tex_text(str(i)) + ","
        ticklabels += tex_text(str(val)) + ","
    ticks = ticks[:-1] + "}"
    ticklabels = ticklabels[:-1] + "}"

    return ticks, ticklabels

def get_tasks(df, prefix):
    return [t for t in df.get_column("task").unique() if t.startswith(prefix)]


def find_subgrids(coords, n_x_domains, n_y_domains, n_entries, check_grid, reduce_dirn=0):
    # within the given coords, find all valid n_x_domains by n_y_domains grids of n_entries coords;
    # n_x_domains*(n_y_domains-1) < n_entries <= n_x_domains*n_y_domains because the last row may be incomplete.
    # (coords may have more than n_x_domains distinct x coordinates and more than n_y_domains distinct y coordinates)

    # input: list of coordinates, number of x domains, number of y domains, total number of entries,
    # function to check grid validity, and direction to reduce in (used internally)
    # output: yields tuples of (grid, x_coords, y_coords, warnings) for all valid grids

    # to find the grids, we take the first remaining distinct x or y coordinate
    # (based on reduce_dirn and whether we've run out of x or y coordinates)
    # and assume that it is one of the coordinates of the grid.
    # then we recurse to find valid subgrids with the corresponding dimension reduced by 1 within the rest of the grid

    x_coords = sorted(list(set(coord.x for coord in coords)))
    # plotly indexes coordinates from lower left but tikz groupplots indexes from upper left
    y_coords = sorted(list(set(coord.y for coord in coords)))[::-1]

    # if there are fewer than n_x_domains distinct x_coords or n_y_domains distinct y_coords,
    # they can't reasonably be titles for an n_x_domains by n_y_domains grid
    if len(x_coords) < n_x_domains or len(y_coords) < n_y_domains:
        return
    
    if len(x_coords) == n_x_domains and len(y_coords) == n_y_domains:
        # we have just the right number of distinct coordinates to make a grid
        # so, we just check that all the required coordinates are present:
        # a prefix of the grid (lexicographically ordered) of len(trace_groups) coordinates
        grid = []
        for y in y_coords:
            rows = []
            for x in x_coords:
                selected_coords = []
                for coord in coords:
                    if coord.x == x and coord.y == y:
                        selected_coords.append(coord)
                rows.append(selected_coords)
            grid.append(rows)
        
        is_valid, warnings_lst = check_grid(grid, n_x_domains, n_y_domains, min(n_x_domains*n_y_domains, n_entries))
        if not is_valid:
            return
        yield grid, x_coords, y_coords, warnings_lst
        return
    
    def subgrid_core(xcs, ycs, nxd, nyd, reducing_y):
        if reducing_y:
            acs, nad, comp_sgn = ycs, nyd, 1
        else:
            acs, nad, comp_sgn = xcs, nxd, -1

        # in this case, all the remaining b coordinates must belong to the grid, so we only reduce the a coordinates
        for a in acs[:-(nad-1)]:
            valid_bs = set(coord.b for coord in coords if coord.a == a)
            sub_coords = [coord for coord in coords if (coord.b in valid_bs and comp_sgn*coord.a < comp_sgn*a)]
            # it seems like it should be faster to alternate reducing in x and y, but i'm not sure
            subgrids = find_subgrids(sub_coords, nxd - (0 if reducing_y else 1), nyd - (1 if reducing_y else 0), n_entries, check_grid, 1-reduce_dirn)
            candidate_grids_with_warnings = []
            for subgrid, xc, yc, w in subgrids:
                candidate_grid = subgrid.copy()
                if reducing_y:
                    # try to extend this subgrid to include the y we reserved
                    coords_at_y = [coord for coord in coords if (coord.y == y)]
                    new_row = []
                    for x in xc:
                        new_row.append([coord for coord in coords_at_y if coord.x == x])
                    # since y is greater than any y in the subgrid, we can just add the new row to the beginning of the candidate grid
                    candidate_grid.insert(0, new_row)
                    new_xc, new_yc = xc, [a] + yc
                else:
                    # try to extend this subgrid to include the x we reserved
                    coords_at_x = [coord for coord in coords if (coord.x == x and coord.y in yc)]
                    # since x is less than any x in the subgrid, we can just add the new column to the beginning of the candidate grid
                    for i, y in enumerate(yc):
                        candidate_grid[i].insert(0, [coord for coord in coords_at_x if coord.y == y])
                    new_xc, new_yc = [a] + xc, yc
                # TODO: i think the min isn't quite right, because what if we're checking the final row
                valid, warnings_lst = check_grid(candidate_grid, n_x_domains, n_y_domains, min(n_x_domains*n_y_domains, n_entries))
                if not valid:
                    continue
                if warnings_lst:
                    candidate_grids_with_warnings.append((candidate_grid, new_xc, new_yc, w | warnings_lst))  # include the warnings inherited from the subgrid
                else:
                    yield candidate_grid, new_xc, new_yc, []
            # after we yield all the completely valid grids, we yield the ones with warnings
            scgww = sorted(candidate_grids_with_warnings, key=lambda v: len(v[1]))
            for cgxy in scgww:
                yield cgxy

    if len(x_coords) == n_x_domains or reduce_dirn == 1:
        # in this case, all the remaining x coordinates must belong to the grid, so we only reduce the y coordinates
        yield from subgrid_core(x_coords, y_coords, n_x_domains, n_y_domains, 1)
    else:
        yield from subgrid_core(x_coords, y_coords, n_x_domains, n_y_domains, -1)

def add_zeroline(axis_type, axis, zeroline_haver):
    # TODO: this isn't perfect because in plotly, the zeroline is on top of other graph elements, and here it's not
    # (and setting "axis on top" affects all the grid lines)
    axis.add_option(f"extra {axis_type} ticks", 0)
    axis.add_option(f"extra {axis_type} tick labels", "")
    zeroline_style = {}
    if zeroline_haver.zerolinecolor:
        zeroline_style["color"], _ = convert_color(zeroline_haver.zerolinecolor)
    else:
        zeroline_style["color"] = "black"
    if zeroline_haver.zerolinewidth:
        zeroline_style["line width"] = px_to_pt(zeroline_haver.zerolinewidth)

    # this doesn't change the normal major grid style
    axis.add_option(f"extra {axis_type} tick style", { "grid": "major", "major grid style": zeroline_style })

def tup_to_tex_str(tup):
    return f"({','.join(tex_text(str(c)) for c in tup)})"

def coords_to_str(coords, errors=None, neg_errors=None):
    """Convert a list of coordinates of the form (x, y), optionally with symmetric or positive errors of the form (x_err, y_err), and optionally negative errors of the form (x_neg_err, y_neg_err) to a string."""
    if errors is None and neg_errors is None:
        return " ".join(tup_to_tex_str(coord) for coord in coords)
    elif neg_errors is None:
        return " ".join(f"{tup_to_tex_str(coord)} +- {tup_to_tex_str(error)}" for coord, error in zip(coords, errors))
    elif errors is None:
        raise ValueError("If neg_errors is provided, errors must also be provided.")
    else:
        return " ".join(f"{tup_to_tex_str(coord)} += {tup_to_tex_str(error)} -= {tup_to_tex_str(neg_error)}" for coord, error, neg_error in zip(coords, errors, neg_errors))
    