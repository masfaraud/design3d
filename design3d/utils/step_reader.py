"""
design3d utils for importing step files.
"""
import re

import design3d
import design3d.shells as d3dshells
from design3d import surfaces
from design3d.geometry import get_transfer_matrix_from_basis


def set_to_list(step_set):
    """
    Convert a string representation of a set to a list of strings.

    :param step_set: String representation of a set, e.g. "{A,B,C}"
    :type step_set: str
    :return: List of strings, e.g. ["A", "B", "C"]
    :rtype: List[str]
    """
    char_list = step_set.split(',')
    char_list[0] = char_list[0][1:]
    char_list[-1] = char_list[-1][:-1]
    return list(char_list)


def replace_unicode_escapes(step_content, pattern):
    """Define a function to replace matched escape sequences with their corresponding characters."""
    def replace_match(match):
        unicode_hex = match.group(1)
        if len(unicode_hex) == 4:
            unicode_char = chr(int(unicode_hex, 16))
        else:
            unicode_char = str(int(unicode_hex, 16))
        return unicode_char

    replaced_content = pattern.sub(replace_match, step_content)

    return replaced_content


def separate_entity_name_and_arguments(input_string: str) -> tuple[str]:
    """Helper function to separate entity name argument from the other arguments."""
    entity_name_str = ""
    input_string = input_string.strip()
    if input_string[0] == "'":
        end_index_name = input_string.find("',", 1) + 1
        if end_index_name != -1:
            entity_name_str = input_string[:end_index_name]
            entity_arg_str = input_string[end_index_name:]
        else:
            entity_arg_str = input_string
    else:
        entity_arg_str = input_string
    return entity_name_str, entity_arg_str


def step_split_arguments(entity_name_str: str, function_arg: str) -> list[str]:
    """
    Split the arguments of a function that doesn't start with '(' but end with ')'.

    ex: IN: '#123,#124,#125)'
       OUT: ['#123', '#124', '#125']
    """
    if entity_name_str:
        arguments = [entity_name_str]
    else:
        arguments = []
    # Remove all spaces from the string
    function_arg = remove_spaces_outside_quotes(function_arg)

    if not function_arg:
        return []

    if function_arg[-1] == ";":
        function_arg = function_arg[:-2]
    pattern = re.compile(r'\(.*?\)|[^,]+')
    # if double_brackets_start_indexes:
    if "((" in function_arg:
        pattern = re.compile(r"\([^()]*\)|'[^']*[^,]*',|[^,]+")
        double_brackets_start_indexes = [match.start() for match in re.finditer(r'\(\(', function_arg)]
        double_brackets_end_indexes = [match.end() for match in re.finditer(r'\)\)', function_arg)]
        starting_index = 0
        for start, end in zip(double_brackets_start_indexes, double_brackets_end_indexes):
            arguments.extend(pattern.findall(function_arg[starting_index:start]))
            arguments.append(function_arg[start:end])
            starting_index = end
        arguments.extend([arg.strip(",") for arg in pattern.findall(function_arg[starting_index:])])
        return arguments

    # Use regular expression to extract arguments
    for arg in pattern.findall(function_arg):
        arg = arg.strip(",")
        if arg == ")":
            arguments[-1] += arg
        else:
            arguments.append(arg)

    return arguments


def remove_spaces_outside_quotes(input_string: str) -> str:
    """Helper function to remove only space that are outside quotes."""
    quoted_strings = re.findall(r"'[^']*[^,]*',", input_string)

    result = input_string.replace(' ', '')
    # Restore the original quoted strings
    for quoted_string in quoted_strings:
        result = result.replace(quoted_string.replace(' ', ''), quoted_string)
    return result


def step_split_arguments_special(function_arg):
    """
    Split the arguments of a function that doesn't start with '(' but end with ')'.

    ex: IN: '#123,#124,#125)'
       OUT: ['#123', '#124', '#125']
    """
    function_arg = function_arg.strip()
    if len(function_arg) > 0 and function_arg[-1] != ')':
        function_arg += ')'
    arguments = []
    argument = ""
    if len(function_arg) > 0 and function_arg[0] == "(":
        function_arg += ")"
    parenthesis = 1
    is_str = False
    for char in function_arg:
        if char == "(":
            parenthesis += 1

        if char == "'" and not is_str:
            is_str = True
        elif char == "'" and is_str:
            is_str = False
        # if char != "," or parenthesis > 1 or is_str:
        #     argument += char
        if not is_str and char == " ":
            continue
        if parenthesis > 1 or is_str:
            argument += char
        elif char != ",":
            argument += char
        else:
            arguments.append(argument)
            argument = ""

        if char == ")":
            parenthesis -= 1
            if parenthesis == 0:
                arguments.append(argument[:-1])
                break
    return arguments


def uncertainty_measure_with_unit(arguments, object_dict, *args, **kwargs):
    """
    Gets the length uncertainty related to the shape representation.

    :param arguments: step primitive arguments
    :param object_dict: dictionary containing already instantiated objects.
    :return: Global length uncertainty.
    """
    length_measure = float(arguments[0].split('(')[1][:-1])
    return length_measure * object_dict[arguments[1]]


def conversion_based_unit_length_unit_named_unit(arguments, object_dict, *args, **kwargs):
    """
    Gets the conversion based unit length.

    :param arguments: step primitive arguments
    :param object_dict: dictionary containing already instantiated objects.
    :return: conversion based unit length.
    """
    return object_dict[arguments[1]]


def length_measure_with_unit(arguments, object_dict, *args, **kwargs):
    """
    Calculates the step file's SI unit conversion factor.

    :param arguments: step primitive arguments
    :param object_dict: dictionary containing already instantiated objects.
    :return: si unit conversion factor.
    """
    if "(" in arguments[0]:
        length_measure = float(arguments[0].split('(')[1][:-1])
    else:
        length_measure = float(arguments[0])
    length_si_unit = object_dict[arguments[1]]
    return length_measure * length_si_unit


def conversion_based_unit_named_unit_plane_angle_unit(arguments, object_dict, *args, **kwargs):
    """
    Gets the conversion based plane unit angle.

    :param arguments: step primitive arguments
    :param object_dict: dictionary containing already instantiated objects.
    :return: conversion based unit length.
    """
    return object_dict[arguments[1]]


def named_unit_plane_angle_unit_si_unit(arguments, *args, **kwargs):
    """
    Returns the dimension of plane angle measure.

    :param arguments: step primitive arguments
    :return: SI unit dimension.
    """
    return SI_PREFIX[arguments[1]]


def named_unit_si_unit_solid_angle_unit(arguments, *args, **kwargs):
    """
    Returns the dimension of solid angle measure.

    :param arguments: step primitive arguments
    :return: SI unit dimension.
    """
    return SI_PREFIX[arguments[1]]


def named_unit_length_unit_si_unit(arguments, *args, **kwargs):
    """
    Returns the dimension of solid angle measure.

    :param arguments: step primitive arguments
    :return: SI unit dimension.
    """
    return SI_PREFIX[arguments[1]]


def plane_angle_measure_with_unit(arguments, object_dict, *args, **kwargs):
    """
    Returns the angle plane measure with the right unit.

    :param arguments: step primitive arguments
    :param object_dict: dictionary containing already instantiated objects.
    :return: angle measure in SI unit.
    """
    angle_measure = float(arguments[0].split('(')[1][:-1])
    angle_si_unit = object_dict[arguments[1]]
    return angle_measure * angle_si_unit


def length_unit_named_unit_si_unit(arguments, *args, **kwargs):
    """
    Gets the length si unit.

    :param arguments: step primitive arguments
    :return: length si unit
    """
    si_unit_length = SI_PREFIX[arguments[1]]
    return si_unit_length


def geometric_representation_context_global_uncertainty_assigned_context_global_unit_assigned_context_representation_context(
        arguments, object_dict, *args, **kwargs):
    """
    Gets the global length uncertainty.

    :param arguments: step primitive arguments
    :param object_dict: dictionary containing already instantiated objects.
    :return: Global length uncertainty.
    """
    length_global_uncertainty = object_dict[int(arguments[1][0][1:])]
    length_conversion_factor = object_dict[int(arguments[2][0][1:])]
    angle_conversion_factor = object_dict[int(arguments[2][1][1:])]
    return length_global_uncertainty, length_conversion_factor, angle_conversion_factor


def vertex_point(arguments, object_dict, *args, **kwargs):
    """
    Returns the data in case of a VERTEX.
    """
    return object_dict[arguments[1]]


def axis1_placement(arguments, object_dict, *args, **kwargs):
    """
    Returns the data in case of a AXIS1_PLACEMENT.
    """
    return object_dict[arguments[1]], object_dict[arguments[2]]


def oriented_edge(arguments, object_dict, *args, **kwargs):
    """
    Returns the data in case of an ORIENTED_EDGE.
    """
    if not object_dict[arguments[3]]:
        # This can happen when the edge is too small
        return None
    edge_orientation = arguments[4]
    if edge_orientation == '.T.':
        return object_dict[arguments[3]]
    return object_dict[arguments[3]].reverse()


def face_outer_bound(arguments, object_dict, *args, **kwargs):
    """
    Returns the data in case of a FACE_OUTER_BOUND.

    :param arguments: list containing the arguments of the FACE_OUTER_BOUND entity.
    :type arguments: list
    :param object_dict: Dictionary containing the objects already instantiated that will be used as arguments to the
        face_outer_bound entity.
    :type object_dict: dict
    :return: A Contour3D representing the BREP of a face.
    :rtype: design3d.wires.Contour3D
    """
    contour = object_dict[arguments[1]]
    if contour and arguments[2] == '.F.':
        contour = object_dict[arguments[1]].invert()
    if contour:
        contour.name = "face_outer_bound"
    return contour


def face_bound(arguments, object_dict, *args, **kwargs):
    """
    Returns the data in case of a FACE_BOUND.

    :param arguments: list containing the arguments of the FACE_BOUND entity.
    :type arguments: list
    :param object_dict: Dictionary containing the objects already instantiated that will be used as arguments to the
        face_outer_bound entity.
    :type object_dict: dict
    :return: A Contour3D representing the BREP of a face.
    :rtype: design3d.wires.Contour3D
    """
    return object_dict[arguments[1]]


def surface_curve(arguments, object_dict, *args, **kwargs):
    """
    Returns xx.

    :param arguments: DESCRIPTION
    :type arguments: TYPE
    :param object_dict: DESCRIPTION
    :type object_dict: TYPE
    :return: DESCRIPTION
    :rtype: TYPE

    """
    return object_dict[arguments[1]]


def seam_curve(arguments, object_dict, *args, **kwargs):
    """
    Returns xx.

    :param arguments: DESCRIPTION
    :type arguments: TYPE
    :param object_dict: DESCRIPTION
    :type object_dict: TYPE
    :return: DESCRIPTION
    :rtype: TYPE
    """
    return object_dict[arguments[1]]


def trimmed_curve(arguments, object_dict, *args, **kwargs):
    """
    Returns xx.

    :param arguments: DESCRIPTION
    :type arguments: TYPE
    :param object_dict: DESCRIPTION
    :type object_dict: TYPE
    :return: DESCRIPTION
    :rtype: TYPE
    """

    curve = object_dict[arguments[1]]
    if arguments[5] == '.PARAMETER.':
        length_conversion_factor = kwargs.get("length_conversion_factor")
        if isinstance(arguments[2], list):
            point1 = object_dict[int(arguments[2][0][1:])]
            point2 = object_dict[int(arguments[3][0][1:])]
        else:
            abscissa1 = _helper_get_parameter_value(arguments[2]) * length_conversion_factor
            abscissa2 = _helper_get_parameter_value(arguments[3]) * length_conversion_factor
            point1 = curve.point_at_abscissa(abscissa1)
            point2 = curve.point_at_abscissa(abscissa2)
    else:
        point1 = object_dict[int(arguments[2][0][1:])]
        point2 = object_dict[int(arguments[3][0][1:])]
    if curve.__class__.__name__ == "Line3D" and point1.is_close(point2):
        return None
    return curve.trim(point1=point1, point2=point2)


def _helper_get_parameter_value(string):
    # Define a regular expression pattern to match the numerical value
    pattern = r"\((-?\d+\.\d+)\)"

    # Use re.search to find the match
    match = re.search(pattern, string)

    if match:
        numerical_value = float(match.group(1))
        return numerical_value
    raise ValueError("No numerical value found in the input string.")


def vertex_loop(arguments, object_dict, *args, **kwargs):
    """
    Returns the data in case of a VERTEX_LOOP.
    """
    return object_dict[arguments[1]]


def composite_curve_segment(arguments, object_dict, *args, **kwargs):
    """
    Returns the data in case of a COMPOSITE_CURVE_SEGMENT.
    """
    # arguments[0] = trasition_code (unused)
    # The transition_code type conveys the continuity properties of a composite curve or surface.
    # The continuity referred to is geometric, not parametric continuity.
    # arguments[1] = same_sense : BOOLEAN;
    # arguments[2] = parent_curve : curve;
    edge = object_dict[arguments[2]]
    if arguments[1] == ".F.":
        edge = edge.reverse()
    return edge


def composite_curve(arguments, object_dict, *args, **kwargs):
    """
    Returns the data in case of a COMPOSITE_CURVE.
    """
    name = arguments[0]
    list_primitives = [object_dict[int(arg[1:])] for arg in arguments[1]]
    first_primitive = list_primitives[0]
    last_primitive = list_primitives[-1]
    if first_primitive.start.is_close(last_primitive.end):
        return design3d.wires.Contour3D(list_primitives, name=name)
    return design3d.wires.Wire3D(list_primitives, name=name)


def pcurve(arguments, object_dict, *args, **kwargs):
    """
    Returns the data in case of a PCURVE.
    """
    return object_dict[arguments[1]]


def geometric_curve_set(arguments, object_dict, *args, **kwargs):
    """
    Returns xx.

    :param arguments: DESCRIPTION
    :type arguments: TYPE
    :param object_dict: DESCRIPTION
    :type object_dict: TYPE
    :return: DESCRIPTION
    :rtype: TYPE

    """
    sub_objects = []
    for argument in arguments[1]:
        sub_obj = object_dict[int(argument[1:])]
        sub_objects.append(sub_obj)
    return sub_objects


def geometric_set(arguments, object_dict, *args, **kwargs):
    """
    Returns xx.

    :param arguments: DESCRIPTION
    :type arguments: TYPE
    :param object_dict: DESCRIPTION
    :type object_dict: TYPE
    :return: DESCRIPTION
    :rtype: TYPE

    """
    # TODO: IS THIS RIGHT?
    primitives = [object_dict[int(node[1:])]
                  for node in arguments[1]]
    return primitives


def shell_based_surface_model(arguments, object_dict, *args, **kwargs):
    """
    Returns the data in case of a Shell3D.
    """
    if len(arguments[1]) == 1:
        return object_dict[int(arguments[1][0][1:])]
    primitives = [object_dict[int(arg[1:])] for arg in arguments[1]]
    compound = design3d.core.Compound(primitives)
    compound.compound_type = "manifold_solid_brep"
    return compound


def oriented_closed_shell(arguments, object_dict, *args, **kwargs):
    """
    Returns the data in case of a Shell3D.
    """
    # TODO: How to use the orientation (arguments[3]
    return object_dict[arguments[2]]


def item_defined_transformation(arguments, object_dict, *args, **kwargs):
    """
    Returns xx.

    :param arguments: DESCRIPTION
    :type arguments: TYPE
    :param object_dict: DESCRIPTION
    :type object_dict: TYPE
    :return: DESCRIPTION
    :rtype: TYPE

    """
    # Frame3D
    design3d_object1 = object_dict[arguments[2]]
    design3d_object2 = object_dict[arguments[3]]
    # TODO : how to frame map properly from these two Frame3D ?
    # return design3d_object2 - design3d_object1
    return [design3d_object1, design3d_object2]


def manifold_surface_shape_representation(arguments, object_dict, *args, **kwargs):
    """
    Returns the data in case of a manifold_surface_shape_representation, interpreted as shell3D.
    """
    primitives = []
    for arg in arguments[1]:
        primitive = object_dict[int(arg[1:])]
        if isinstance(primitive, d3dshells.Shell3D):
            primitives.append(primitive)
        if isinstance(primitive, design3d.core.Compound):
            counter = 0
            for sub_prim in primitive.primitives:
                if sub_prim:
                    sub_prim.name = arguments[0][1:-1] + str(counter)
                    counter += 1
            primitives.append(primitive)
    if len(primitives) == 1:
        return primitives[0]
    compound = design3d.core.Compound(primitives)
    compound.compound_type = "manifold_solid_brep"
    return compound


def faceted_brep(arguments, object_dict, *args, **kwargs):
    """
    Returns the data in case of a faceted_brep entity, interpreted as shell3D.
    """
    return object_dict[arguments[1]]


def faceted_brep_shape_representation(arguments, object_dict, *args, **kwargs):
    """
    Returns the data in case of a faceted_brep_shape_representation, interpreted as shell3D.
    """
    if len(arguments[1]) == 1:
        return object_dict[int(arguments[1][0][1:])]
    shells = []
    for arg in arguments[1]:
        if isinstance(object_dict[int(arg[1:])],
                      d3dshells.Shell3D):
            shell = object_dict[int(arg[1:])]
            shells.append(shell)
    return design3d.core.Compound(shells)


def manifold_solid_brep(arguments, object_dict, *args, **kwargs):
    """
    Returns the data in case of a manifold_solid_brep with voids.
    """
    return object_dict[arguments[1]]


def brep_with_voids(arguments, object_dict, *args, **kwargs):
    """
    Returns the data in case of a BREP with voids.
    """
    return object_dict[arguments[1]]


def shape_representation(arguments, object_dict, *args, **kwargs):
    """
    Returns xx.

    :param arguments: DESCRIPTION
    :type arguments: TYPE
    :param object_dict: DESCRIPTION
    :type object_dict: TYPE
    :return: DESCRIPTION
    :rtype: TYPE

    """
    # does it have the extra argument coming from
    # SHAPE_REPRESENTATION_RELATIONSHIP ? In this case return
    # them
    if len(arguments) == 4:
        shells = object_dict[int(arguments[3])]
        return shells
    shells = []
    frames = []
    for arg in arguments[1]:
        if int(arg[1:]) in object_dict and \
                isinstance(object_dict[int(arg[1:])], list) and \
                len(object_dict[int(arg[1:])]) == 1:
            shells.append(*object_dict[int(arg[1:])])
        elif int(arg[1:]) in object_dict and \
                isinstance(object_dict[int(arg[1:])],
                           d3dshells.Shell3D):
            shells.append(object_dict[int(arg[1:])])
        elif int(arg[1:]) in object_dict and isinstance(object_dict[int(arg[1:])], design3d.Frame3D):
            # TODO: Is there something to read here ?
            frame = object_dict[int(arg[1:])]
            if not all(component is None for component in [frame.u, frame.u, frame.w]):
                frames.append(frame)
        elif int(arg[1:]) in object_dict and \
                isinstance(object_dict[int(arg[1:])],
                           design3d.edges.Arc3D):
            shells.append(object_dict[int(arg[1:])])
        elif int(arg[1:]) in object_dict and \
                isinstance(object_dict[int(arg[1:])],
                           design3d.edges.BSplineCurve3D):
            shells.append(object_dict[int(arg[1:])])
        else:
            pass
    if not shells and frames:
        return frames
    return shells


def advanced_brep_shape_representation(arguments, object_dict, *args, **kwargs):
    """
    Returns xx.

    :param arguments: DESCRIPTION
    :type arguments: TYPE
    :param object_dict: DESCRIPTION
    :type object_dict: TYPE
    :return: DESCRIPTION
    :rtype: TYPE

    """
    primitives = []
    for arg in arguments[1]:
        primitive = object_dict[int(arg[1:])]
        if isinstance(primitive, d3dshells.Shell3D):
            primitives.append(primitive)
        if isinstance(primitive, design3d.core.Compound):
            counter = 0
            for sub_prim in primitive.primitives:
                sub_prim.name = arguments[0][1:-1] + str(counter)
                counter += 1
            primitives.append(primitive)
    if len(primitives) == 1:
        return primitives[0]
    compound = design3d.core.Compound(primitives)
    compound.compound_type = "manifold_solid_brep"
    return compound


def geometrically_bounded_surface_shape_representation(arguments, object_dict, *args, **kwargs):
    """
    Returns xx.

    :param arguments: DESCRIPTION
    :type arguments: TYPE
    :param object_dict: DESCRIPTION
    :type object_dict: TYPE
    :return: DESCRIPTION
    :rtype: TYPE

    """
    primitives = []
    for arg in arguments[1]:
        primitives.extend(object_dict[int(arg[1:])])
    if len(primitives) > 1:
        compound = design3d.core.Compound(primitives, name=arguments[0])
        compound.compound_type = "geometric_curve_set"
        return compound
    return primitives[0]


def geometrically_bounded_wireframe_shape_representation(arguments, object_dict, *args, **kwargs):
    """
    Returns xx.

    :param arguments: DESCRIPTION
    :type arguments: TYPE
    :param object_dict: DESCRIPTION
    :type object_dict: TYPE
    :return: DESCRIPTION
    :rtype: TYPE

    """
    primitives = []
    for arg in arguments[1]:
        prim = object_dict[int(arg[1:])]
        if isinstance(prim, list):
            primitives.extend(prim)
    if len(primitives) > 1:
        compound = design3d.core.Compound(primitives, name=arguments[0])
        compound.compound_type = "geometric_curve_set"
        return compound
    return primitives[0]


def frame_map_closed_shell(closed_shells, item_defined_transformation_frames, shape_representation_frames):
    """
    Frame maps a closed shell in an assembly to its good position.

    :param closed_shells: DESCRIPTION
    :type closed_shells: d3dshells.OpenShell3D
    :param item_defined_transformation_frames: DESCRIPTION
    :type item_defined_transformation_frames: TYPE
    :param shape_representation_frames: DESCRIPTION
    :type shape_representation_frames: TYPE
    :return: DESCRIPTION
    :rtype: TYPE

    """
    if item_defined_transformation_frames[0] == item_defined_transformation_frames[1]:
        return closed_shells
    if shape_representation_frames[0].origin.is_close(design3d.O3D):
        global_frame = shape_representation_frames[0]
    else:
        global_frame = [frame for frame in item_defined_transformation_frames if frame.origin.is_close(design3d.O3D)][0]
    transformed_frame = [frame for frame in item_defined_transformation_frames if frame != global_frame][0]
    new_closedshells = []

    for shell3d in closed_shells:
        basis_a = global_frame.basis()
        basis_b = transformed_frame.basis()
        transfer_matrix = get_transfer_matrix_from_basis(basis_a, basis_b)
        new_frame = design3d.Frame3D(transformed_frame.origin, design3d.Vector3D(*transfer_matrix[0]),
                                    design3d.Vector3D(*transfer_matrix[1]), design3d.Vector3D(*transfer_matrix[2]))
        new_closedshells.append(shell3d.frame_mapping(new_frame, 'old'))
    return new_closedshells


def representation_relationship_representation_relationship_with_transformation_shape_representation_relationship(
        arguments, object_dict, *args, **kwargs):
    """
    Representation relationship with transformation shape. To clarify.
    """
    if arguments[2] in object_dict:
        if isinstance(object_dict[arguments[2]], list):  # arguments = {, , [], [], item_....}
            if object_dict[arguments[2]] and not isinstance(object_dict[arguments[2]][0], design3d.Frame3D) \
                    and isinstance(object_dict[arguments[3]][0], design3d.Frame3D):
                return frame_map_closed_shell(object_dict[arguments[2]],
                                              object_dict[arguments[4]], object_dict[arguments[3]])

            if object_dict[arguments[2]] and isinstance(object_dict[arguments[2]][0], design3d.Frame3D) and \
                    not isinstance(object_dict[arguments[3]][0], design3d.Frame3D):
                return frame_map_closed_shell(object_dict[arguments[3]],
                                              object_dict[arguments[4]], object_dict[arguments[2]])
            return []
        return []
    return []


def bounded_curve_b_spline_curve_b_spline_curve_with_knots_curve_geometric_representation_item_rational_b_spline_curve_representation_item(
        arguments, object_dict, *args, **kwargs):
    """
    Bounded b spline with knots curve geometric representation item. To clarify.
    """
    modified_arguments = [''] + arguments
    if modified_arguments[-1] == "''":
        modified_arguments.pop()
    return STEP_TO_design3d['BOUNDED_CURVE, '
                           'B_SPLINE_CURVE, '
                           'B_SPLINE_CURVE_WITH_KNOTS, '
                           'CURVE, GEOMETRIC_REPRESENTATION_ITEM, '
                           'RATIONAL_B_SPLINE_CURVE, '
                           'REPRESENTATION_ITEM'].from_step(
        modified_arguments, object_dict)


def b_spline_curve_b_spline_curve_with_knots_rational_b_spline_curve_bounded_curve_representation_item_geometric_representation_item_curve(
        arguments, object_dict, *args, **kwargs):
    """
    Bounded b spline with knots curve geometric representation item. To clarify.
    """
    return bounded_curve_b_spline_curve_b_spline_curve_with_knots_curve_geometric_representation_item_rational_b_spline_curve_representation_item(
        arguments, object_dict)


def bounded_surface_b_spline_surface_b_spline_surface_with_knots_geometric_representation_item_rational_b_spline_surface_representation_item_surface(
        arguments, object_dict, *args, **kwargs):
    """
    Bounded b spline surface with knots curve geometric representation item. To clarify.
    """
    modified_arguments = [''] + arguments
    if modified_arguments[-1] == "''":
        modified_arguments.pop()
    return STEP_TO_design3d['BOUNDED_SURFACE, B_SPLINE_SURFACE, '
                           'B_SPLINE_SURFACE_WITH_KNOTS, '
                           'GEOMETRIC_REPRESENTATION_ITEM, '
                           'RATIONAL_B_SPLINE_SURFACE, '
                           'REPRESENTATION_ITEM, SURFACE'].from_step(
        modified_arguments, object_dict)


def bounded_surface_b_spline_surface_b_spline_surface_with_knots_surface_geometric_representation_item_rational_b_spline_surface_representation_item(
        arguments, object_dict, *args, **kwargs):
    """
    Bounded b spline surface with knots curve geometric representation item. To clarify.
    """
    return bounded_surface_b_spline_surface_b_spline_surface_with_knots_geometric_representation_item_rational_b_spline_surface_representation_item_surface(
        arguments, object_dict)


def b_spline_surface_b_spline_surface_with_knots_rational_b_spline_surface_bounded_surface_representation_item_geometric_representation_item_surface(
        arguments, object_dict, *args, **kwargs):
    """
    Bounded b spline surface with knots curve geometric representation item. To clarify.
    """
    return bounded_surface_b_spline_surface_b_spline_surface_with_knots_geometric_representation_item_rational_b_spline_surface_representation_item_surface(
        arguments, object_dict)


def product_definition_shape(arguments, object_dict, *args, **kwargs):
    """
    Returns the data in case of a product_definition_shape.
    """
    return object_dict[arguments[2]]


def product_definition(arguments, object_dict, *args, **kwargs):
    """
    Returns the data in case of a product_definition.
    """
    return object_dict[arguments[2]]


def product_definition_formation(arguments, object_dict, *args, **kwargs):
    """
    Returns the data in case of a product_definition_formation.
    """
    return object_dict[arguments[2]]


def product_definition_formation_with_specified_source(arguments, object_dict, *args, **kwargs):
    """
    Returns the data in case of a product_definition_formation_with_specified_source.
    """
    return object_dict[arguments[2]]


def product(arguments, *args, **kwargs):
    """
    Returns the data in case of a product.
    """
    return arguments[0]


def application_context(arguments, *args, **kwargs):
    """
    Returns the data in case of an application_context.
    """
    return arguments[0]


def product_context(arguments, *args, **kwargs):
    """
    Returns the data in case of a product_context.
    """
    return arguments


STEP_TO_design3d = {
    # GEOMETRICAL ENTITIES
    'CARTESIAN_POINT': design3d.Point3D,
    'DIRECTION': design3d.Vector3D,
    'VECTOR': design3d.Vector3D,

    'AXIS1_PLACEMENT': None,
    'AXIS2_PLACEMENT_2D': None,  # ??????????????????
    'AXIS2_PLACEMENT_3D': design3d.Frame3D,

    'LINE': design3d.curves.Line3D,  # LineSegment3D,
    'CIRCLE': design3d.curves.Circle3D,
    'ELLIPSE': design3d.curves.Ellipse3D,
    'PARABOLA': None,
    'HYPERBOLA': None,
    # 'PCURVE': None,
    'CURVE_REPLICA': None,
    'OFFSET_CURVE_3D': None,
    'TRIMMED_CURVE': None,  # BSplineCurve3D cannot be trimmed on FreeCAD
    'B_SPLINE_CURVE': design3d.edges.BSplineCurve3D,
    'B_SPLINE_CURVE_WITH_KNOTS': design3d.edges.BSplineCurve3D,
    'BEZIER_CURVE': design3d.edges.BSplineCurve3D,
    'RATIONAL_B_SPLINE_CURVE': design3d.edges.BSplineCurve3D,
    'UNIFORM_CURVE': design3d.edges.BSplineCurve3D,
    'QUASI_UNIFORM_CURVE': design3d.edges.BSplineCurve3D,
    'SURFACE_CURVE': None,  # TOPOLOGICAL EDGE
    'SEAM_CURVE': None,
    # LineSegment3D, # TOPOLOGICAL EDGE ############################
    'COMPOSITE_CURVE_SEGMENT': None,  # TOPOLOGICAL EDGE
    'COMPOSITE_CURVE': design3d.wires.Wire3D,  # TOPOLOGICAL WIRE
    'COMPOSITE_CURVE_ON_SURFACE': design3d.wires.Wire3D,  # TOPOLOGICAL WIRE
    'BOUNDARY_CURVE': design3d.wires.Wire3D,  # TOPOLOGICAL WIRE

    'PLANE': surfaces.Plane3D,
    'CYLINDRICAL_SURFACE': surfaces.CylindricalSurface3D,
    'CONICAL_SURFACE': surfaces.ConicalSurface3D,
    'SPHERICAL_SURFACE': surfaces.SphericalSurface3D,
    'TOROIDAL_SURFACE': surfaces.ToroidalSurface3D,
    'DEGENERATE_TOROIDAL_SURFACE': surfaces.ToroidalSurface3D,
    'B_SPLINE_SURFACE_WITH_KNOTS': surfaces.BSplineSurface3D,
    'B_SPLINE_SURFACE': surfaces.BSplineSurface3D,
    'BEZIER_SURFACE': surfaces.BSplineSurface3D,

    'OFFSET_SURFACE': None,
    'SURFACE_REPLICA': None,
    'RATIONAL_B_SPLINE_SURFACE': surfaces.BSplineSurface3D,
    'RECTANGULAR_TRIMMED_SURFACE': None,
    'SURFACE_OF_LINEAR_EXTRUSION': surfaces.ExtrusionSurface3D,
    # CAN BE A BSplineSurface3D
    'SURFACE_OF_REVOLUTION': surfaces.RevolutionSurface3D,
    'UNIFORM_SURFACE': surfaces.BSplineSurface3D,
    'QUASI_UNIFORM_SURFACE': surfaces.BSplineSurface3D,
    'RECTANGULAR_COMPOSITE_SURFACE': design3d.faces.PlaneFace3D,  # TOPOLOGICAL FACES
    'CURVE_BOUNDED_SURFACE': design3d.faces.PlaneFace3D,  # TOPOLOGICAL FACE

    # Bsplines
    'BOUNDED_SURFACE, B_SPLINE_SURFACE, B_SPLINE_SURFACE_WITH_KNOTS, GEOMETRIC_REPRESENTATION_ITEM,'
    ' RATIONAL_B_SPLINE_SURFACE, REPRESENTATION_ITEM, SURFACE': surfaces.BSplineSurface3D,
    "BOUNDED_SURFACE, B_SPLINE_SURFACE, B_SPLINE_SURFACE_WITH_KNOTS, SURFACE, GEOMETRIC_REPRESENTATION_ITEM,"
    " RATIONAL_B_SPLINE_SURFACE, REPRESENTATION_ITEM": surfaces.BSplineSurface3D,
    # TOPOLOGICAL ENTITIES
    'VERTEX_POINT': None,

    'EDGE_CURVE': design3d.edges.Edge,  # LineSegment3D, # TOPOLOGICAL EDGE
    'ORIENTED_EDGE': None,  # TOPOLOGICAL EDGE
    "GEOMETRIC_SET": None,
    # The one above can influence the direction with their last argument
    # TODO : maybe take them into consideration

    'FACE_BOUND': None,  # TOPOLOGICAL WIRE
    'FACE_OUTER_BOUND': None,  # TOPOLOGICAL WIRE
    # Both above can influence the direction with their last argument
    # TODO : maybe take them into consideration
    'EDGE_LOOP': design3d.wires.Contour3D,  # TOPOLOGICAL WIRE
    'POLY_LOOP': design3d.wires.Contour3D,  # TOPOLOGICAL WIRE
    'VERTEX_LOOP': None,  # TOPOLOGICAL WIRE

    'ADVANCED_FACE': design3d.faces.Face3D,
    'FACE_SURFACE': design3d.faces.Face3D,

    'CLOSED_SHELL': d3dshells.ClosedShell3D,
    'OPEN_SHELL': d3dshells.OpenShell3D,
    #        'ORIENTED_CLOSED_SHELL': None,
    'CONNECTED_FACE_SET': d3dshells.OpenShell3D,
    'GEOMETRIC_CURVE_SET': None,

    # step sub-functions

    'UNCERTAINTY_MEASURE_WITH_UNIT': None,
    'CONVERSION_BASED_UNIT, LENGTH_UNIT, NAMED_UNIT': None,
    'LENGTH_MEASURE_WITH_UNIT': None,
    'LENGTH_UNIT, NAMED_UNIT, SI_UNIT': None,
    'PLANE_ANGLE_MEASURE_WITH_UNIT': None,
    'NAMED_UNIT, PLANE_ANGLE_UNIT, SI_UNIT': None,
    'CONVERSION_BASED_UNIT, NAMED_UNIT, PLANE_ANGLE_UNIT': None,
    'GEOMETRIC_REPRESENTATION_CONTEXT, GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT, GLOBAL_UNIT_ASSIGNED_CONTEXT, REPRESENTATION_CONTEXT': None,
    'REPRESENTATION_RELATIONSHIP, REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION, SHAPE_REPRESENTATION_RELATIONSHIP': d3dshells.OpenShell3D.translation,
    'SHELL_BASED_SURFACE_MODEL': None,
    'MANIFOLD_SURFACE_SHAPE_REPRESENTATION': None,
    'MANIFOLD_SOLID_BREP': None,
    'BREP_WITH_VOIDS': None,
    'SHAPE_REPRESENTATION': None,
    'ADVANCED_BREP_SHAPE_REPRESENTATION': None,
    "FACETED_BREP_SHAPE_REPRESENTATION": None,
    "GEOMETRICALLY_BOUNDED_WIREFRAME_SHAPE_REPRESENTATION": None,
    "GEOMETRICALLY_BOUNDED_SURFACE_SHAPE_REPRESENTATION": None,
    "EDGE_BASED_WIREFRAME_SHAPE_REPRESENTATION": None,
    'ITEM_DEFINED_TRANSFORMATION': None,
    'SHAPE_REPRESENTATION_RELATIONSHIP': None,
    "NEXT_ASSEMBLY_USAGE_OCCURRENCE": None,

    'BOUNDED_CURVE, B_SPLINE_CURVE, B_SPLINE_CURVE_WITH_KNOTS, CURVE, GEOMETRIC_REPRESENTATION_ITEM, RATIONAL_B_SPLINE_CURVE, REPRESENTATION_ITEM': design3d.edges.BSplineCurve3D,
    "APPLICATION_CONTEXT": None,
    "PRODUCT_DEFINITION_SHAPE": None,
    "PRODUCT_DEFINITION": None,
    "PRODUCT_DEFINITION_FORMATION": None,
    "PRODUCT": None,
}

SI_PREFIX = {'.EXA.': 1e18, '.PETA.': 1e15, '.TERA.': 1e12, '.GIGA.': 1e9, '.MEGA.': 1e6, '.KILO.': 1e3,
             '.HECTO.': 1e2, '.DECA.': 1e1, '$': 1, '.DECI.': 1e-1, '.CENTI.': 1e-2, '.MILLI.': 1e-3, '.MICRO.': 1e-6,
             '.NANO.': 1e-9, '.PICO.': 1e-12, '.FEMTO.': 1e-15, '.ATTO.': 1e-18}

STEP_REPRESENTATION_ENTITIES = {"ADVANCED_BREP_SHAPE_REPRESENTATION", "FACETED_BREP_SHAPE_REPRESENTATION",
                                "MANIFOLD_SURFACE_SHAPE_REPRESENTATION",
                                "GEOMETRICALLY_BOUNDED_WIREFRAME_SHAPE_REPRESENTATION",
                                "GEOMETRICALLY_BOUNDED_SURFACE_SHAPE_REPRESENTATION",
                                "EDGE_BASED_WIREFRAME_SHAPE_REPRESENTATION"
                                }

WIREFRAME_STEP_REPRESENTATION_ENTITIES = {"GEOMETRICALLY_BOUNDED_WIREFRAME_SHAPE_REPRESENTATION",
                                          "EDGE_BASED_WIREFRAME_SHAPE_REPRESENTATION"}

design3d_TO_STEP = {}
for k, v in STEP_TO_design3d.items():
    if v:
        if v in design3d_TO_STEP:
            design3d_TO_STEP[v].append(k)
        else:
            design3d_TO_STEP[v] = [k]
