#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base models for design3d.
"""

import sys
import json
import math
import warnings
import inspect
import collections
import collections.abc
from copy import copy, deepcopy

import orjson
from importlib import import_module
from ast import literal_eval
from typing import get_origin, get_args, Union, Any, BinaryIO, TextIO, Dict, Type
from functools import cached_property

import numpy as npy

# import networkx as nx

FLOAT_TOLERANCE = 1e-9


def is_sequence(obj) -> bool:
    """
    Return True if object is sequence (but not string), else False.

    :param obj: Object to check
    :return: bool. True if object is a sequence but not a string. False otherwise
    """
    if not hasattr(obj, "__len__") or not hasattr(obj, "__getitem__"):
        # Performance improvements for trivial checks
        return False

    if is_list(obj) or is_tuple(obj):
        # Performance improvements for trivial checks
        return True
    return isinstance(obj, collections.abc.Sequence) and not isinstance(obj, str)


def is_list(obj) -> bool:
    """Check if given obj is exactly of type list (not instance of). Used mainly for performance."""
    return obj.__class__ == list


def is_tuple(obj) -> bool:
    """Check if given obj is exactly of type tuple (not instance of). Used mainly for performance."""
    return obj.__class__ == tuple


def is_simple(obj):
    """Return True if given object is a int or a str or None. Used mainly for performance."""
    return obj is None or obj.__class__ in [int, str]


def isinstance_base_types(obj):
    """Return True if the object is either a str, a float an int or None."""
    if is_simple(obj):
        # Performance improvements for trivial types
        return True
    return isinstance(obj, (str, float, int))


def full_classname(object_):
    return f"{object_.__class__.__module__}.{object_.__class__.__name__}"


def serialize_dict(dict_):
    """Serialize dictionary values."""
    return {k: serialize(v) for k, v in dict_.items()}


def serialize_sequence(seq):
    """Serialize a sequence (list or sequence) into a list of dictionaries."""
    return [serialize(v) for v in seq]


def serialize(value):
    """
    Calls recursively itself serialize_sequence and serialize_dict.
    """
    if isinstance(value, SerializableObject):
        try:
            serialized_value = value.to_dict(use_pointers=False)
        except TypeError:
            warnings.warn(
                f"specific to_dict of class {value.__class__} "
                "should implement use_pointers, memo and path arguments",
                Warning,
            )
            serialized_value = value.to_dict()
    elif isinstance(value, dict):
        serialized_value = serialize_dict(value)
    elif is_sequence(value):
        serialized_value = serialize_sequence(value)
    elif isinstance(value, npy.int64):
        serialized_value = int(value)
    elif isinstance(value, npy.float64):
        serialized_value = float(value)
    elif hasattr(value, "to_dict"):
        to_dict_method = getattr(value, "to_dict", None)
        if callable(to_dict_method):
            return to_dict_method()
    else:
        serialized_value = value
    return serialized_value


_PYTHON_CLASS_CACHE = {}


def get_python_class_from_class_name(full_class_name: str) -> Type:
    """Get python class object corresponding to given class name."""
    cached_value = _PYTHON_CLASS_CACHE.get(full_class_name, None)
    if cached_value is not None:
        return cached_value

    if "." not in full_class_name:
        return literal_eval(full_class_name)
    module_name, class_name = full_class_name.rsplit(".", 1)

    module = import_module(module_name)
    class_ = getattr(module, class_name)
    # Storing in cache
    _PYTHON_CLASS_CACHE[full_class_name] = class_
    return class_


def deserialize_sequence(sequence):
    """Transform a sequence into an object."""
    deserialized_sequence = [deserialize(elt) for elt in sequence]

    # if origin is tuple:
    #     # Keeping as a tuple
    #     return tuple(deserialized_sequence)
    return deserialized_sequence


def deserialize(serialized_element):
    """Main function for deserialization."""

    if isinstance(serialized_element, dict):
        return deserialize_dict(serialized_element)
    if is_sequence(serialized_element):
        return deserialize_sequence(sequence=serialized_element)
    # if isinstance(serialized_element, str):
    #     is_class_transformed = dcty.is_classname_transform(serialized_element)
    #     if is_class_transformed:
    #         return is_class_transformed
    return serialized_element


_ARGSSPEC_CACHE = {}


def deserialize_dict(dict_):
    """Transform a dictionnary into an object."""
    class_argspec = None

    # if class_ is None and
    class_ = None
    if "object_class" in dict_:
        class_ = get_python_class_from_class_name(dict_["object_class"])

    # Create init_dict
    if class_ is not None and hasattr(class_, "dict_to_object"):
        different_methods = class_.dict_to_object.__func__ is not SerializableObject.dict_to_object.__func__
        if different_methods:  # and not force_generic:
            return class_.dict_to_object(dict_)

        if class_ in _ARGSSPEC_CACHE:
            class_argspec = _ARGSSPEC_CACHE[class_]
        else:
            class_argspec = inspect.getfullargspec(class_)
            _ARGSSPEC_CACHE[class_] = class_argspec

        init_dict = {k: v for k, v in dict_.items() if k in class_argspec.args + class_argspec.kwonlyargs}
        # TOCHECK Class method to generate init_dict ??
    else:
        init_dict = dict_
        init_dict.pop("object_class", None)

    subobjects = {}
    for key, value in init_dict.items():
        # if class_argspec is not None and key in class_argspec.annotations:
        #     annotation = class_argspec.annotations[key]
        # else:
        #     annotation = None

        subobjects[key] = deserialize(value)

    if class_ is not None:
        obj = class_(**subobjects)
    else:
        obj = subobjects
    return obj


class SerializableObject:
    """Object that can travel on the web."""

    def copy(self, deep: bool = True, memo=None):
        """
        Copy object.

        :param deep: If False, perform a shallow copy. If True, perform a deep copy.
        :param memo: A dict that keep track of references.
        """
        if deep:
            return deepcopy(self, memo=memo)
        return copy(self)

    def __copy__(self):
        """Generic copy use init of objects."""
        class_name = self.full_classname
        if class_name in _ARGSSPEC_CACHE:
            class_argspec = _ARGSSPEC_CACHE[class_name]
        else:
            class_argspec = inspect.getfullargspec(self.__class__)
            _ARGSSPEC_CACHE[class_name] = class_argspec

        dict_ = {}
        for arg in class_argspec.args:
            if arg != "self":
                value = self.__dict__[arg]
                if hasattr(value, "__copy__"):
                    dict_[arg] = value.__copy__()
                else:
                    dict_[arg] = value
        return self.__class__(**dict_)

    def base_dict(self):
        """A base dict for to_dict: set up a dict with object class and version."""
        package_name = self.__module__.split(".", maxsplit=1)[0]
        if package_name in sys.modules:
            package = sys.modules[package_name]
            if hasattr(package, "__version__"):
                package_version = package.__version__
            else:
                package_version = None
        else:
            package_version = None

        dict_ = {"object_class": self.full_classname}
        if package_version:
            dict_["package_version"] = package_version
        return dict_

    def _serializable_dict(self):
        """
        Return a dict of attribute_name, values (still python, not serialized).

        Keys are filtered with non serializable attributes controls.
        """

        dict_ = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
        return dict_

    def to_dict(self):
        dict_ = serialize_dict(self._serializable_dict())
        dict_.update({"object_class": self.full_classname})
        return dict_

    @classmethod
    def dict_to_object(cls, dict_) -> "SerializableObject":
        """Generic dict_to_object method."""
        return deserialize(dict_)

    @cached_property
    def full_classname(self):
        """Full classname of class like: package.module.submodule.classname."""
        return full_classname(self)

    @classmethod
    def from_json(cls, filepath: str):
        with open(filepath, "r") as file:
            return cls.dict_to_object(json.load(file))


def data_eq(value1, value2):
    """Returns if two values are equal on data equality."""
    if is_sequence(value1) and is_sequence(value2):
        return sequence_data_eq(value1, value2)

    if isinstance(value1, npy.int64) or isinstance(value2, npy.int64):
        return value1 == value2

    if isinstance(value1, npy.float64) or isinstance(value2, npy.float64):
        return math.isclose(value1, value2, abs_tol=FLOAT_TOLERANCE)

    if not isinstance(value2, type(value1)) and not isinstance(value1, type(value2)):
        return False

    if isinstance_base_types(value1):
        if isinstance(value1, float):
            return math.isclose(value1, value2, abs_tol=FLOAT_TOLERANCE)
        return value1 == value2

    if isinstance(value1, dict):
        return dict_data_eq(value1, value2)

    # if isinstance(value1, type):
    #     return full_classname(value1) == full_classname(value2)

    # Else: its an object
    if full_classname(value1) != full_classname(value2):
        return False

    # Test if _data_eq is customized
    if hasattr(value1, "_data_eq"):
        custom_method = value1._data_eq.__code__ is not SerializableObject._data_eq.__code__
        if custom_method:
            return value1._data_eq(value2)

    # Not custom, use generic implementation
    eq_dict = value1._data_eq_dict()
    if "name" in eq_dict:
        del eq_dict["name"]

    other_eq_dict = value2._data_eq_dict()
    return dict_data_eq(eq_dict, other_eq_dict)


def dict_data_eq(dict1, dict2):
    """Returns True if two dictionaries are equal on data equality, False otherwise."""
    for key, value in dict1.items():
        if key not in dict2:
            return False
        if not data_eq(value, dict2[key]):
            return False
    return True


def sequence_data_eq(seq1, seq2):
    """Returns if two sequences are equal on data equality."""
    if len(seq1) != len(seq2):
        return False

    for v1, v2 in zip(seq1, seq2):
        if not data_eq(v1, v2):
            return False
    return True


class DataEqualityObject(SerializableObject):

    def __hash__(self):
        """Compute a int from object."""
        return self._data_hash()

    def __eq__(self, other_object):
        """
        Generic equality of two objects.

        Behavior can be controlled by class attribute _eq_is_data_eq to tell if we must use python equality (based on
        memory addresses) (_eq_is_data_eq = False) or a data equality (True).
        """
        if hash(self) != hash(other_object):
            return False
        if self.__class__.__name__ != other_object.__class__.__name__:
            return False
        return data_eq(self, other_object)

    def _data_eq_dict(self):
        """Returns a dict of what to look at for data eq."""
        return {k: v for k, v in self._serializable_dict().items() if k not in ["package_version", "name"]}
