"""
Nurbs main operations algorithms.
"""

from functools import lru_cache
import numpy as np
import design3d
from design3d.nurbs import core


def knot_insertion(degree, knotvector, ctrlpts, u, **kwargs):
    """
    Computes the control points of the rational/non-rational spline after knot insertion.

    Part of Algorithm A5.1 of The NURBS Book by Piegl & Tiller, 2nd Edition.

    Keyword Arguments:
        * ``num``: number of knot insertions. *Default: 1*
        * ``s``: multiplicity of the knot. *Default: computed via :func:`.find_multiplicity`*
        * ``span``: knot span. *Default: computed via :func:`.find_span_linear`*

    :param degree: degree
    :type degree: int
    :param knotvector: knot vector
    :type knotvector: list, tuple
    :param ctrlpts: control points
    :type ctrlpts: list
    :param u: knot to be inserted
    :type u: float
    :return: updated control points
    :rtype: list

    """
    # Get keyword arguments
    num_insertions = kwargs.get('num', 1)  # number of knot insertions
    knot_multiplicity = kwargs.get('s', core.find_multiplicity(u, knotvector))  # multiplicity
    knot_span = kwargs.get('span', core.find_span_linear(degree, knotvector, len(ctrlpts), u))  # knot span

    # Initialize variables
    num_ctrlpts_new = len(ctrlpts) + num_insertions

    # Initialize new control points array (control points may be weighted or not)
    ctrlpts_new = [np.empty_like(ctrlpts[0]) for _ in range(num_ctrlpts_new)]

    # Initialize a local array of length p + 1
    temp = [np.empty_like(ctrlpts[0]) for _ in range(degree + 1)]

    # Save unaltered control points
    ctrlpts_new[:knot_span - degree + 1] = ctrlpts[:knot_span - degree + 1]
    ctrlpts_new[knot_span - knot_multiplicity + num_insertions:] = ctrlpts[knot_span - knot_multiplicity:]

    # Start filling the temporary local array which will be used to update control points during knot insertion
    for i in range(degree - knot_multiplicity + 1):
        temp[i] = np.array(ctrlpts[knot_span - degree + i])

    # Insert knot "num_insertions" times
    for j in range(1, num_insertions + 1):
        new_knot_index = knot_span - degree + j
        for i in range(degree - j - knot_multiplicity + 1):
            alpha = knot_insertion_alpha(u, tuple(knotvector), knot_span, i, new_knot_index)
            temp[i] = alpha * temp[i + 1] + (1.0 - alpha) * temp[i]
        ctrlpts_new[new_knot_index] = temp[0]
        ctrlpts_new[knot_span + num_insertions - j - knot_multiplicity] = \
            temp[degree - j - knot_multiplicity]

    # Load remaining control points
    new_knot_index = knot_span - degree + num_insertions
    ctrlpts_new[new_knot_index + 1:knot_span - knot_multiplicity] = \
        temp[1:knot_span - knot_multiplicity - new_knot_index + 1]

    # Return control points after knot insertion
    return ctrlpts_new


@lru_cache(maxsize=128)
def knot_insertion_alpha(u, knotvector, span, idx, leg):
    """
    Computes :math:`\\alpha` coefficient for knot insertion algorithm.

    :param u: knot
    :type u: float
    :param knotvector: knot vector
    :type knotvector: tuple
    :param span: knot span
    :type span: int
    :param idx: index value (degree-dependent)
    :type idx: int
    :param leg: i-th leg of the control points polygon
    :type leg: int
    :return: coefficient value
    :rtype: float
    """
    return (u - knotvector[leg + idx]) / (knotvector[idx + span + 1] - knotvector[leg + idx])


def knot_insertion_kv(knotvector, u, span, num_insertions):
    """
    Computes the knot vector of the rational/non-rational spline after knot insertion.

    Part of Algorithm A5.1 of The NURBS Book by Piegl & Tiller, 2nd Edition.

    :param knotvector: knot vector
    :type knotvector: list, tuple
    :param u: knot
    :type u: float
    :param span: knot span
    :type span: int
    :param num_insertions: number of knot insertions
    :type num_insertions: int
    :return: updated knot vector
    :rtype: list
    """
    kv_size = len(knotvector)
    kv_updated = [0.0 for _ in range(kv_size + num_insertions)]

    # Compute new knot vector
    for i in range(0, span + 1):
        kv_updated[i] = knotvector[i]
    for i in range(1, num_insertions + 1):
        kv_updated[span + i] = u
    for i in range(span + 1, kv_size):
        kv_updated[i + num_insertions] = knotvector[i]

    # Return the new knot vector
    return np.array(kv_updated)


def insert_knot_curve(obj, param, num, **kwargs):
    """
    Inserts knots n-times to a spline geometry.

    Keyword Arguments:
        * ``check_num``: enables/disables operation validity checks. *Default: True*

    :param obj: spline geometry
    :param param: knot(s) to be inserted in [u, v, w] format
    :type param: list, tuple
    :param num: number of knot insertions in [num_u, num_v, num_w] format
    :type num: list, tuple
    :return: updated spline geometry

    """
    # Get keyword arguments
    check_num = kwargs.get('check_num', True)  # can be set to False when the caller checks number of insertions

    if check_num:
        # Check the validity of number of insertions
        if not isinstance(num, (list, tuple)):
            raise ValueError("The number of insertions must be a list or a tuple")

        if len(num) != 1:
            raise ValueError("The length of the num array must be equal to the number of parametric dimensions")

        for val in num:
            if val < 0:
                raise ValueError('Number of insertions must be a positive integer value')

    if param[0] is not None and num[0] > 0:
        # Find knot multiplicity
        param_multiplicity = core.find_multiplicity(param[0], obj.knotvector)

        # Check if it is possible add that many number of knots
        if check_num and num[0] > obj.degree - param_multiplicity:
            raise ValueError("Knot " + str(param[0]) + " cannot be inserted " + str(num[0]) + " times")

        # Find knot span
        span = core.find_span_linear(obj.degree, obj.knotvector, len(obj.ctrlpts), param[0])

        # Compute new knot vector
        kv_new = knot_insertion_kv(obj.knotvector, param[0], span, num[0])

        # Compute new control points
        cpts = obj.ctrlptsw if obj.rational else obj.ctrlpts
        cpts_tmp = knot_insertion(obj.degree, obj.knotvector, cpts, param[0],
                                  num=num[0], s=param_multiplicity, span=span)
        weights = None
        if obj.rational:
            cpts_tmp, weights = separate_ctrlpts_weights(cpts_tmp)

        # Create new curve
        knots, knot_multiplicities = get_knots_and_multiplicities(kv_new)
        point_name = "Point" + obj.__class__.__name__[-2:]
        cpts_tmp = [getattr(design3d, point_name)(*point) for point in cpts_tmp]
        # Return new spline geometry
        if obj.__class__.__name__[:-2] == "BezierCurve":
            return obj.__class__(obj.degree, cpts_tmp)
        return obj.__class__(obj.degree, cpts_tmp, knot_multiplicities, knots, weights)
    return obj


def split_curve(obj, param, **kwargs):
    """
    Splits the curve at the input parametric coordinate.

    This method splits the curve into two pieces at the given parametric coordinate, generates two different
    curve objects and returns them. It does not modify the input curve.

    Keyword Arguments:
        * ``find_span_func``: FindSpan implementation. *Default:* :func:`.helpers.find_span_linear`
        * ``insert_knot_func``: knot insertion algorithm implementation. *Default:* :func:`.operations.insert_knot`

    :param obj: Curve to be split
    :type obj: abstract.Curve
    :param param: parameter
    :type param: float
    :return: a list of curve segments
    :rtype: list

    """
    if param in set(obj.domain):
        raise ValueError("Cannot split from the domain edge")
    param = float(f"{param:.18f}")
    # Find multiplicity of the knot and define how many times we need to add the knot
    knot_multiplicity = core.find_multiplicity(param, obj.knotvector)
    insertion_count = obj.degree - knot_multiplicity
    knot_span = core.find_span_linear(obj.degree, obj.knotvector, len(obj.ctrlpts), param) - obj.degree + 1

    # Insert knot
    temp_obj = insert_knot_curve(obj, [param], num=[insertion_count], check_num=False)

    # Knot vectors
    curve1_kv, curve2_kv = helper_split_knot_vectors(temp_obj.degree, temp_obj.knotvector, len(temp_obj.ctrlpts),
                                                     param,
                                                     core.find_span_linear)

    return construct_split_curve(temp_obj, curve1_kv, curve2_kv, knot_span, insertion_count)


def construct_split_curve(obj, curve1_kv, curve2_kv, knot_span, insertion_count):
    """
    Helper function to instantiate split curve.
    """
    control_points = obj.control_points
    curve1_ctrlpts = control_points[0:knot_span + insertion_count]
    curve2_ctrlpts = control_points[knot_span + insertion_count - 1:]
    if obj.rational:
        curve1_weights = obj.weights[0:knot_span + insertion_count]
        curve2_weights = obj.weights[knot_span + insertion_count - 1:]
    else:
        curve1_weights = None
        curve2_weights = None

    knots_1, knot_multiplicities_1 = get_knots_and_multiplicities(curve1_kv)

    knots_2, knot_multiplicities_2 = get_knots_and_multiplicities(curve2_kv)

    if obj.__class__.__name__[:-2] == "BezierCurve":
        return [obj.__class__(obj.degree, curve1_ctrlpts), obj.__class__(obj.degree, curve2_ctrlpts)]
    # Return the split curves
    return [obj.__class__(obj.degree, curve1_ctrlpts, knot_multiplicities_1, knots_1, curve1_weights),
            obj.__class__(obj.degree, curve2_ctrlpts, knot_multiplicities_2, knots_2, curve2_weights)]


def insert_knot_surface(obj, param, num, **kwargs):
    """
    Inserts knots n-times to a spline geometry.

    Keyword Arguments:
        * ``check_num``: enables/disables operation validity checks. *Default: True*

    :param obj: spline geometry
    :param param: knot(s) to be inserted in [u, v] format
    :type param: list, tuple
    :param num: number of knot insertions in [num_u, num_v] format
    :type num: list, tuple
    :return: updated spline geometry

    """
    # Get keyword arguments
    check_num = kwargs.get('check_num', True)  # can be set to False when the caller checks number of insertions
    # u-direction
    if param[0] is not None and num[0] > 0:
        # Find knot multiplicity
        knotvector = obj.knots_vector_u
        param_multiplicity = core.find_multiplicity(param[0], knotvector)

        # Check if it is possible add that many number of knots
        if check_num and num[0] > obj.degree_u - param_multiplicity:
            raise ValueError("Knot " + str(param[0]) + " cannot be inserted " + str(num[0]) + " times (u-dir)")

        # Find knot span
        span = core.find_span_linear(obj.degree_u, knotvector, obj.nb_u, param[0])

        # Compute new knot vector
        new_kv = knot_insertion_kv(knotvector, param[0], span, num[0])

        # Get curves
        cpts_tmp = []
        cpts = obj.ctrlptsw if obj.rational else obj.ctrlpts
        for v in range(obj.nb_v):
            ctrlpts = [cpts[v + (obj.nb_v * u)] for u in range(obj.nb_u)]
            ctrlpts_tmp = knot_insertion(obj.degree_u, knotvector, ctrlpts, param[0],
                                         num=num[0], s=param_multiplicity, span=span)
            cpts_tmp += ctrlpts_tmp

        # Update the surface after knot insertion
        knots, multiplicities = get_knots_and_multiplicities(new_kv)
        cpts_tmp = flip_ctrlpts_u(cpts_tmp, obj.nb_u + num[0], obj.nb_v)
        weights = None
        if obj.rational:
            cpts_tmp, weights = separate_ctrlpts_weights(cpts_tmp)
        control_points = [design3d.Point3D(*point) for point in cpts_tmp]
        obj = obj.__class__(obj.degree_u, obj.degree_v,
                            control_points,
                            obj.nb_u + num[0], obj.nb_v, multiplicities, obj.v_multiplicities,
                            knots, obj.v_knots, weights)
    # v-direction
    if param[1] is not None and num[1] > 0:
        # Find knot multiplicity
        knotvector = obj.knots_vector_v
        param_multiplicity = core.find_multiplicity(param[1], knotvector)

        # Check if it is possible add that many number of knots
        if check_num and num[1] > obj.degree_v - param_multiplicity:
            raise ValueError("Knot " + str(param[1]) + " cannot be inserted " + str(num[1]) + " times (v-dir)")

        # Find knot span
        span = core.find_span_linear(obj.degree_v, knotvector, obj.nb_v, param[1])

        # Compute new knot vector
        new_kv = knot_insertion_kv(knotvector, param[1], span, num[1])

        # Get curves
        cpts_tmp = []
        cpts = obj.ctrlptsw if obj.rational else obj.ctrlpts
        for u in range(obj.nb_u):
            ctrlpts = [cpts[v + (obj.nb_v * u)] for v in range(obj.nb_v)]
            ctrlpts_tmp = knot_insertion(obj.degree_v, knotvector, ctrlpts, param[1],
                                         num=num[1], s=param_multiplicity, span=span)
            cpts_tmp += ctrlpts_tmp

        knots, multiplicities = get_knots_and_multiplicities(new_kv)
        weights = None
        if obj.rational:
            cpts_tmp, weights = separate_ctrlpts_weights(cpts_tmp)
        control_points = [design3d.Point3D(*point) for point in cpts_tmp]
        # Update the surface after knot insertion
        obj = obj.__class__(obj.degree_u, obj.degree_v,
                            control_points, obj.nb_u, obj.nb_v + num[1], obj.u_multiplicities, multiplicities,
                            obj.u_knots, knots, weights)
    return obj


def insert_control_points_surface_u(obj, param, num, **kwargs):
    """
    Caculates the control points equivalent to inserts knot n-times to a spline geometry.

    Keyword Arguments:
        * ``check_num``: enables/disables operation validity checks. *Default: True*

    :param obj: spline geometry
    :param param: knot to be inserted in u direction
    :type param: list, tuple
    :param num: number of knot insertions
    :type num: list, tuple
    :return: a list with the control points

    """
    # Get keyword arguments
    check_num = kwargs.get('check_num', True)  # can be set to False when the caller checks number of insertions
    # u-direction
    # Find knot multiplicity
    knotvector = obj.knots_vector_u
    param_multiplicity = core.find_multiplicity(param, knotvector)

    # Check if it is possible add that many number of knots
    if check_num and num > obj.degree_u - param_multiplicity:
        raise ValueError("Knot " + str(param) + " cannot be inserted " + str(num) + " times (u-dir)")

    # Find knot span
    span = core.find_span_linear(obj.degree_u, knotvector, obj.nb_u, param)

    # Get curves
    cpts_tmp = []
    cpts = obj.ctrlptsw if obj.rational else obj.ctrlpts
    for v in range(obj.nb_v):
        ctrlpts = [cpts[v + (obj.nb_v * u)] for u in range(obj.nb_u)]
        ctrlpts_tmp = knot_insertion(obj.degree_u, knotvector, ctrlpts, param,
                                     num=num, s=param_multiplicity, span=span)
        cpts_tmp += ctrlpts_tmp

    cpts_tmp = flip_ctrlpts_u(cpts_tmp, obj.nb_u + num, obj.nb_v)

    return cpts_tmp


def insert_control_points_surface_v(obj, param, num, **kwargs):
    """
    Caculates the control points equivalent to inserts knot n-times to a spline geometry.

    Keyword Arguments:
        * ``check_num``: enables/disables operation validity checks. *Default: True*

    :param obj: spline geometry
    :param param: knot to be inserted in v direction
    :type param: list, tuple
    :param num: number of knot insertions
    :type num: list, tuple
    :return: a list with the control points

    """
    check_num = kwargs.get('check_num', True)  # can be set to False when the caller checks number of insertions
    # v-direction

    # Find knot multiplicity
    knotvector = obj.knots_vector_v
    param_multiplicity = core.find_multiplicity(param, knotvector)

    # Check if it is possible add that many number of knots
    if check_num and num > obj.degree_v - param_multiplicity:
        raise ValueError("Knot " + str(param[1]) + " cannot be inserted " + str(num) + " times (v-dir)")

    # Find knot span
    span = core.find_span_linear(obj.degree_v, knotvector, obj.nb_v, param)

    # Get curves
    cpts_tmp = []
    cpts = obj.ctrlptsw if obj.rational else obj.ctrlpts
    for u in range(obj.nb_u):
        ctrlpts = [cpts[v + (obj.nb_v * u)] for v in range(obj.nb_v)]
        ctrlpts_tmp = knot_insertion(obj.degree_v, knotvector, ctrlpts, param,
                                     num=num, s=param_multiplicity, span=span)
        cpts_tmp += ctrlpts_tmp

    return cpts_tmp



def refine_knot_vector_surface(obj, u, v, **kwargs):
    """
    Splits the surface at the input parametric coordinate on the u-direction.

    This method splits the surface into two pieces at the given parametric coordinate on the u-direction,
    generates two different surface objects and returns them. It does not modify the input surface.

    Keyword Arguments:
        * ``find_span_func``: FindSpan implementation. *Default:* :func:`.helpers.find_span_linear`
        * ``insert_knot_func``: knot insertion algorithm implementation. *Default:* :func:`.operations.insert_knot`

    :param obj: surface
    :type obj: abstract.Surface
    :param param: parameter for the u-direction
    :type param: float
    :return: a list of surface patches
    :rtype: list

    """
    # Keyword arguments
    insert_knot_func = kwargs.get('insert_knot_func', insert_knot_surface)  # Knot insertion algorithm
    domain = obj.domain
    temp_obj = obj
    for param in u:
        if param in (domain[0], domain[1]):
            raise ValueError("Cannot split from the u-domain edge")

        # Find multiplicity of the knot
        knotvector_u = obj.knots_vector_u
        knot_multiplicity = core.find_multiplicity(param, knotvector_u)
        insertion_count = obj.degree_u - knot_multiplicity

        # Split the original surface
        temp_obj = insert_knot_func(obj, [param, None], num=[insertion_count, 0], check_num=False)
    for param in v:
        if param in (domain[2], domain[3]):
            raise ValueError("Cannot split from the v-domain edge")

        # Find multiplicity of the knot
        knotvector_v = temp_obj.knots_vector_v
        knot_multiplicity = core.find_multiplicity(param, knotvector_v)
        insertion_count = temp_obj.degree_v - knot_multiplicity

        # Split the original surface
        temp_obj = insert_knot_func(temp_obj, [None, param], num=[0, insertion_count], check_num=False)
    return temp_obj


def extract_surface_curve_u(obj, param, curve_class, **kwargs):
    """
    Extract an isocurve from the surface at the input parametric coordinate on the u-direction.

    This method works by inserting knots to the surface so that from the new control points created we can extract
    the curve. Under the hood this method performs an incomplete process of splitting the surface.

    Keyword Arguments:
        * ``find_span_func``: FindSpan implementation. *Default:* :func:`.helpers.find_span_linear`

    :param obj: surface
    :type obj: design3d.surfaces.BSplineSurface3D
    :param param: parameter for the u-direction
    :type param: float
    :param curve_class: BSpline curve object
    :type curve_class: design3d.edges.BSplineCurve3D
    :return: The bspline curve at the specified parameter
    :rtype: design3d.surfaces.BSplineSurface3D

    """

    if param in (obj.domain[0], obj.domain[1]):
        raise ValueError("Cannot split from the u-domain edge")

    # Keyword arguments
    span_func = kwargs.get('find_span_func', core.find_span_linear)  # FindSpan implementation

    # Find multiplicity of the knot
    knotvector_u = obj.knots_vector_u
    knot_span = span_func(obj.degree_u, knotvector_u, obj.nb_u, param) - obj.degree_u + 1
    knot_multiplicity = core.find_multiplicity(param, knotvector_u)
    insertion_count = obj.degree_u - knot_multiplicity

    ctrlpts = insert_control_points_surface_u(obj, param, insertion_count, check_num=False)

    ctrlpts2d = np.reshape(ctrlpts, (obj.nb_u + insertion_count, obj.nb_v, -1))
    # takes the second part of the split surface for simplicity
    surf2_ctrlpts = ctrlpts2d_to_ctrlpts(ctrlpts2d[knot_span + insertion_count - 1:])[:obj.nb_v]
    weights = None
    if obj.rational:
        surf2_ctrlpts, weights = separate_ctrlpts_weights(surf2_ctrlpts)
    control_points = [design3d.Point3D(*point) for point in surf2_ctrlpts]

    return curve_class(obj.degree_v, control_points, obj.v_multiplicities, obj.v_knots, weights)


def extract_surface_curve_v(obj, param, curve_class, **kwargs):
    """
    Extract an isocurve from the surface at the input parametric coordinate on the v-direction.

    This method works by inserting knots to the surface so that from the new control points created we can extract
    the curve. Under the hood this method performs an incomplete process of splitting the surface.

    Keyword Arguments:
        * ``find_span_func``: FindSpan implementation. *Default:* :func:`.helpers.find_span_linear`

    :param obj: surface
    :type obj: design3d.surfaces.BSplineSurface3D
    :param param: parameter for the u-direction
    :type param: float
    :param curve_class: BSpline curve object
    :type curve_class: design3d.edges.BSplineCurve3D
    :return: The bspline curve at the specified parameter
    :rtype: design3d.surfaces.BSplineSurface3D

    """

    if param in (obj.domain[2], obj.domain[3]):
        raise ValueError("Cannot split from the v-domain edge")

    # Keyword arguments
    span_func = kwargs.get('find_span_func', core.find_span_linear)  # FindSpan implementation

    # Find multiplicity of the knot
    knotvector_v = obj.knots_vector_v
    knot_span = span_func(obj.degree_v, knotvector_v, obj.nb_v, param) - obj.degree_v + 1
    knot_multiplicity = core.find_multiplicity(param, knotvector_v)
    insertion_count = obj.degree_v - knot_multiplicity

    ctrlpts = insert_control_points_surface_v(obj, param, insertion_count, check_num=False)
    new_nb_v = obj.nb_v + insertion_count
    ctrlpts2d = np.reshape(ctrlpts, (obj.nb_u, new_nb_v, -1))
    # first slicing ([:, knot_span + insertion_count - 1:, :]) takes the control points of the second surface
    # second slicing ([:, 0, :]) takes only the first control point of each row
    surf2_ctrlpts = ctrlpts2d[:, knot_span + insertion_count - 1:, :][:, 0, :]
    weights = None
    if obj.rational:
        surf2_ctrlpts, weights = separate_ctrlpts_weights(surf2_ctrlpts)
    control_points = [design3d.Point3D(*point) for point in surf2_ctrlpts]

    return curve_class(obj.degree_u, control_points, obj.u_multiplicities, obj.u_knots, weights)


def split_surface_u(obj, param, **kwargs):
    """
    Splits the surface at the input parametric coordinate on the u-direction.

    This method splits the surface into two pieces at the given parametric coordinate on the u-direction,
    generates two different surface objects and returns them. It does not modify the input surface.

    Keyword Arguments:
        * ``find_span_func``: FindSpan implementation. *Default:* :func:`.helpers.find_span_linear`
        * ``insert_knot_func``: knot insertion algorithm implementation. *Default:* :func:`.operations.insert_knot`

    :param obj: surface
    :type obj: abstract.Surface
    :param param: parameter for the u-direction
    :type param: float
    :return: a list of surface patches
    :rtype: list

    """

    if param in (obj.domain[0], obj.domain[1]):
        raise ValueError("Cannot split from the u-domain edge")
    param = float(f"{param:.18f}")
    # Keyword arguments
    span_func = kwargs.get('find_span_func', core.find_span_linear)  # FindSpan implementation
    insert_knot_func = kwargs.get('insert_knot_func', insert_knot_surface)  # Knot insertion algorithm

    # Find multiplicity of the knot
    knotvector_u = obj.knots_vector_u
    knot_span = span_func(obj.degree_u, knotvector_u, obj.nb_u, param) - obj.degree_u + 1
    knot_multiplicity = core.find_multiplicity(param, knotvector_u)
    insertion_count = obj.degree_u - knot_multiplicity

    # Split the original surface
    temp_obj = insert_knot_func(obj, [param, None], num=[insertion_count, 0], check_num=False)

    # Knot vectors
    knotvectors = helper_split_knot_vectors(temp_obj.degree_u, temp_obj.knots_vector_u,
                                            temp_obj.nb_u, param, span_func)

    return construct_split_surfaces(temp_obj, knotvectors, "u", knot_span, insertion_count)


def split_surface_v(obj, param, **kwargs):
    """
    Splits the surface at the input parametric coordinate on the v-direction.

    This method splits the surface into two pieces at the given parametric coordinate on the v-direction,
    generates two different surface objects and returns them. It does not modify the input surface.

    Keyword Arguments:
        * ``find_span_func``: FindSpan implementation. *Default:* :func:`.helpers.find_span_linear`
        * ``insert_knot_func``: knot insertion algorithm implementation. *Default:* :func:`.operations.insert_knot`

    :param obj: surface
    :type obj: abstract.Surface
    :param param: parameter for the v-direction
    :type param: float
    :return: a list of surface patches
    :rtype: list

    """
    if param in (obj.domain[2], obj.domain[3]):
        raise ValueError("Cannot split from the v-domain edge")
    param = float(f"{param:.18f}")
    # Keyword arguments
    span_func = kwargs.get('find_span_func', core.find_span_linear)  # FindSpan implementation
    insert_knot_func = kwargs.get('insert_knot_func', insert_knot_surface)  # Knot insertion algorithm

    # Find multiplicity of the knot
    knotvector_v = obj.knots_vector_v
    knot_span = span_func(obj.degree_v, knotvector_v, obj.nb_v, param) - obj.degree_v + 1
    knot_multiplicity = core.find_multiplicity(param, knotvector_v)
    insertion_count = obj.degree_v - knot_multiplicity

    # Split the original surface
    temp_obj = insert_knot_func(obj, [None, param], num=[0, insertion_count], check_num=False)

    # Knot vectors
    knotvectors = helper_split_knot_vectors(temp_obj.degree_v, temp_obj.knots_vector_v,
                                            temp_obj.nb_v, param, span_func)

    return construct_split_surfaces(temp_obj, knotvectors, "v", knot_span, insertion_count)


def separate_ctrlpts_weights(ctrlptsw):
    """
    Divides weighted control points by weights to generate unweighted control points and weights vector.

    This function is dimension agnostic, i.e. control points can be in any dimension but the last element of the array
    should indicate the weight.

    :param ctrlptsw: weighted control points
    :type ctrlptsw: list, tuple
    :return: unweighted control points and weights vector
    :rtype: list
    """
    ctrlpts = []
    weights = []
    for ptw in ctrlptsw:
        temp = [float(pw / ptw[-1]) for pw in ptw[:-1]]
        ctrlpts.append(temp)
        weights.append(ptw[-1])

    return [ctrlpts, weights]


def flip_ctrlpts_u(ctrlpts, size_u, size_v):
    """
    Flips a list of 1-dimensional control points from u-row order to v-row order.

    **u-row order**: each row corresponds to a list of u values

    **v-row order**: each row corresponds to a list of v values

    :param ctrlpts: control points in u-row order
    :type ctrlpts: list, tuple
    :param size_u: size in u-direction
    :type size_u: int
    :param size_v: size in v-direction
    :type size_v: int
    :return: control points in v-row order
    :rtype: list
    """
    new_ctrlpts = []
    for i in range(0, size_u):
        for j in range(0, size_v):
            temp = [float(c) for c in ctrlpts[i + (j * size_u)]]
            new_ctrlpts.append(temp)

    return new_ctrlpts


def ctrlpts2d_to_ctrlpts(control_points_table):
    """
    Transform the control_points m x n.
    """
    size_u = len(control_points_table)
    size_v = len(control_points_table[0])

    # Make sure that all numbers are float type
    ctrlpts = [[] for _ in range(size_u * size_v)]
    for u in range(size_u):
        for v in range(size_v):
            idx = v + (size_v * u)
            ctrlpts[idx] = [float(coord) for coord in control_points_table[u][v]]

    return ctrlpts


def helper_split_knot_vectors(degree, knotvector, num_ctrlpts, param, span_func):
    """
    Computes knot vectors to split object into two pieces.
    """
    knot_span_new = span_func(degree, knotvector, num_ctrlpts, param) + 1
    kv_1 = np.array(list(knotvector[0:knot_span_new]) + [param])
    kv_2 = np.array([param for _ in range(0, degree + 1)] + list(knotvector[knot_span_new:]))
    return kv_1, kv_2


def get_knots_and_multiplicities(knotvector):
    """
    Get knots and multiplicities from knotvector in u and v direction.
    """
    knotvector = np.asarray(knotvector, dtype=np.float64)
    knots = np.unique(knotvector).tolist()
    multiplicities = [core.find_multiplicity(knot, knotvector) for knot in knots]
    return knots, multiplicities


def construct_split_surfaces(obj, knotvectors, direction, knot_span, insertion_count):
    """
    Helper function to construct split surfaces.
    """
    surf1_kv, surf2_kv = knotvectors
    if direction == "u":
        ctrlpts2d = obj.ctrlpts2d()
        surf1_ctrlpts = ctrlpts2d_to_ctrlpts(ctrlpts2d[0:knot_span + insertion_count])
        surf2_ctrlpts = ctrlpts2d_to_ctrlpts(ctrlpts2d[knot_span + insertion_count - 1:])
        u_knots, u_multiplicities = get_knots_and_multiplicities(surf1_kv)
        v_knots, v_multiplicities = obj.v_knots, obj.v_multiplicities
        surf1_nb_u = knot_span + insertion_count
        surf1_nb_v = obj.nb_v
        surf2_nb_u = obj.nb_u - (knot_span + insertion_count - 1)
        surf2_nb_v = obj.nb_v
    else:
        surf1_ctrlpts = []
        surf2_ctrlpts = []
        for v_row in obj.ctrlpts2d():
            temp = v_row[0:knot_span + insertion_count]
            surf1_ctrlpts.extend(temp)
            temp = v_row[knot_span + insertion_count - 1:]
            surf2_ctrlpts.extend(temp)
        u_knots, u_multiplicities = obj.u_knots, obj.u_multiplicities
        v_knots, v_multiplicities = get_knots_and_multiplicities(surf1_kv)
        surf1_nb_u = obj.nb_u
        surf1_nb_v = knot_span + insertion_count
        surf2_nb_u = obj.nb_u
        surf2_nb_v = obj.nb_v - (knot_span + insertion_count - 1)
    weights = None
    if obj.rational:
        surf1_ctrlpts, weights = separate_ctrlpts_weights(surf1_ctrlpts)
    control_points = [design3d.Point3D(*point) for point in surf1_ctrlpts]
    surf1 = obj.__class__(obj.degree_u, obj.degree_v, control_points, surf1_nb_u,
                          surf1_nb_v, u_multiplicities, v_multiplicities, u_knots, v_knots, weights)

    # knots
    if direction == "u":
        u_knots, u_multiplicities = get_knots_and_multiplicities(surf2_kv)
    else:
        v_knots, v_multiplicities = get_knots_and_multiplicities(surf2_kv)
    weights = None
    if obj.rational:
        surf2_ctrlpts, weights = separate_ctrlpts_weights(surf2_ctrlpts)
    control_points = [design3d.Point3D(*point) for point in surf2_ctrlpts]
    surf2 = obj.__class__(obj.degree_u, obj.degree_v, control_points,
                          surf2_nb_u, surf2_nb_v, u_multiplicities, v_multiplicities, u_knots, v_knots, weights)

    # Return the new surfaces
    return [surf1, surf2]


def decompose_curve(obj, return_params: bool = False, number_max_patches: int = None, **kwargs):
    """
    Generator: Decomposes the curve into Bézier curve segments of the same degree.

    :param obj: Curve to be decomposed
    :type obj: BSplineCurve
    :param return_params: If True, returns the parameters from start and end of each Bézier patch with repect to the
     input curve.
    :type return_params: bool
    :param number_max_patches: number max of patches, if limiting is needed.
    :type: int
    :return: a generator element with a Bezier segment.
    :rtype: Generator element.
    """
    curve = obj
    if number_max_patches:
        umin, umax = curve.domain
        knots = np.linspace(umin, umax, number_max_patches)[1:-1]
    else:
        knots = curve.knotvector[curve.degree + 1:-(curve.degree + 1)]
    params = []
    umin, umax = obj.domain
    param_start = umin
    while knots.any():
        knot = knots[0]
        curves = split_curve(curve, param=knot, **kwargs)
        curve = curves[1]
        knots = curve.knotvector[curve.degree + 1:-(curve.degree + 1)]
        if return_params:
            umax_0 = knot * (umax - param_start) + param_start
            params.append((param_start, umax_0))
            yield curves[0], (param_start, umax_0)
            param_start = umax_0
            continue
        yield curves[0]
    if return_params:
        yield curve, (param_start, umax)
    else:
        yield curve


def decompose_surface(obj, return_params, **kwargs):
    """
    Decomposes the surface into Bezier surface patches of the same degree.

    :param obj: surface
    :type obj: BSplineSurface3D
    :param return_params: If True, returns the parameters from start and end of each Bézier patch with repect to the
     input curve.
    :type return_params: bool
    :return: a list of Bezier patches
    :rtype: list
    """

    # Validate input
    if obj.__class__.__name__ != "BSplineSurface3D":
        raise ValueError("Input shape must be an instance of BSplineSurface3D class")

    # Get keyword arguments
    decompose_dir = kwargs.get('decompose_dir', 'uv')  # possible directions: u, v, uv
    if "decompose_dir" in kwargs:
        kwargs.pop("decompose_dir")
    domain = obj.domain
    # Only u-direction
    if decompose_dir == 'u':
        return helper_decompose(obj, 0, split_surface_u, return_params, (domain[2], domain[3]), **kwargs)

    # Only v-direction
    if decompose_dir == 'v':
        return helper_decompose(obj, 1, split_surface_v, return_params, (domain[0], domain[1]), **kwargs)

    # Both u- and v-directions
    if decompose_dir == 'uv':
        result = []
        if return_params:
            for sfu, params in helper_decompose(obj, 0, split_surface_u, return_params,
                                                (domain[2], domain[3]), **kwargs):
                result.extend(helper_decompose(sfu, 1, split_surface_v, return_params, params[0], **kwargs))
        else:
            for sfu in helper_decompose(obj, 0, split_surface_u, return_params, **kwargs):
                result.extend(helper_decompose(sfu, 1, split_surface_v, return_params, **kwargs))
        return result

    raise ValueError("Cannot decompose in " + str(decompose_dir) + " direction. Acceptable values: u, v, uv")


def helper_decompose(srf, idx, split_func, return_params, other_direction_params=None, **kws):
    """
    Helper function to decompose_surface.
    """
    # pylint: disable=too-many-locals
    surf_degrees = [srf.degree_u, srf.degree_v]
    knots = srf.knotvector[idx][surf_degrees[idx] + 1:-(surf_degrees[idx] + 1)]
    param_min, param_max = 0.0, 1.0
    if return_params:
        domain = srf.domain
        if idx == 0:
            param_min, param_max = domain[0], domain[1]
        else:
            param_min, param_max = domain[2], domain[3]
    param_start = param_min
    result = []
    while knots.any():
        knot = knots[0]
        srfs = split_func(srf, param=knot, **kws)
        srf = srfs[1]
        knots = srf.knotvector[idx][surf_degrees[idx] + 1:-(surf_degrees[idx] + 1)]
        if return_params:
            param_end = knot * (param_max - param_start) + param_start
            if idx == 0:
                result.append([srfs[0], ((param_start, param_end), other_direction_params)])
            else:
                result.append([srfs[0], (other_direction_params, (param_start, param_end))])
            param_start = param_end
        else:
            result.append(srfs[0])

    if return_params:
        if idx == 0:
            result.append([srf, ((param_start, param_max), other_direction_params)])
        else:
            result.append([srf, (other_direction_params, (param_start, param_max))])
    else:
        result.append(srf)
    return result


def link_curves(curves, tol: float = 1e-7, validate: bool = True):
    """
    Links the input curves together.

    The end control point of the curve k has to be the same with the start control point of the curve k + 1.

    :return: a tuple containing: knots, knots multiplicities, control points and weights vector
    """

    # Validate input
    if validate:
        for idx in range(len(curves) - 1):
            if np.linalg.norm(curves[idx].ctrlpts[-1] - curves[idx + 1].ctrlpts[0]) > tol:
                raise ValueError("Curve #" + str(idx) + " and Curve #" + str(idx + 1) + " don't touch each other")

    knotvector = []  # new knot vector
    cpts = []  # new control points array
    wgts = []  # new weights array
    pdomain_end = 0
    curve = curves[0]
    # Loop though the curves
    for curve in curves:
        # Process knot vectors
        if not knotvector:
            # get rid of the last superfluous knot to maintain split curve notation
            knotvector += list(curve.knotvector[:-(curve.degree + 1)])
            cpts += list(curve.ctrlpts)
            # Process control points
            if curve.rational:
                wgts += list(curve.weights)
            else:
                tmp_w = [1.0 for _ in range(len(curve.ctrlpts))]
                wgts += tmp_w
        else:
            tmp_kv = [pdomain_end + k for k in curve.knotvector[1:-(curve.degree + 1)]]
            knotvector += tmp_kv
            cpts += list(curve.ctrlpts[1:])
            # Process control points
            if curve.rational:
                wgts += list(curve.weights[1:])
            else:
                tmp_w = [1.0 for _ in range(len(curve.ctrlpts) - 1)]
                wgts += tmp_w

        pdomain_end += curve.knotvector[-1]

    # Fix curve by appending the last knot to the end
    knotvector += [pdomain_end for _ in range(curve.degree + 1)]
    wgts = [] if all(weight == 1 for weight in wgts) else wgts
    knots, multiplicities = get_knots_and_multiplicities(np.asarray(knotvector, dtype=np.float64))
    return knots, multiplicities, cpts, wgts
