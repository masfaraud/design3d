#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base models for design3d.
"""


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 24 22:09:20 2025

@author: steven
"""

import sys
import math
import warnings
import inspect
import collections
import collections.abc
import orjson
from ast import literal_eval
from typing import get_origin, get_args, Union, Any, BinaryIO, TextIO, Dict
from functools import cached_property

import numpy as npy
import networkx as nx
# import dessia_common.utils.types as dcty
# from dessia_common.abstract import CoreDessiaObject
# from dessia_common.typings import InstanceOf, JsonSerializable
# from dessia_common.breakdown import get_in_object_from_path

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
    """ Check if given obj is exactly of type list (not instance of). Used mainly for performance. """
    return obj.__class__ == list


def is_tuple(obj) -> bool:
    """ Check if given obj is exactly of type tuple (not instance of). Used mainly for performance. """
    return obj.__class__ == tuple

def is_simple(obj):
    """ Return True if given object is a int or a str or None. Used mainly for performance. """
    return obj is None or obj.__class__ in [int, str]


def isinstance_base_types(obj):
    """ Return True if the object is either a str, a float an int or None. """
    if is_simple(obj):
        # Performance improvements for trivial types
        return True
    return isinstance(obj, (str, float, int))

def full_classname(object_):
    return f"{object_.__class__.__module__}.{object_.__class__.__name__}"

def dict_to_object(dict_):
    pass




class SerializableObject:
    """ Object that can travel on the web. """
    _non_serializable_attributes = []

    def base_dict(self):
        """ A base dict for to_dict: set up a dict with object class and version. """
        package_name = self.__module__.split('.', maxsplit=1)[0]
        if package_name in sys.modules:
            package = sys.modules[package_name]
            if hasattr(package, '__version__'):
                package_version = package.__version__
            else:
                package_version = None
        else:
            package_version = None

        dict_ = {'object_class': self.full_classname}
        if package_version:
            dict_['package_version'] = package_version
        return dict_

    def _serializable_dict(self):
        """
        Return a dict of attribute_name, values (still python, not serialized).

        Keys are filtered with non serializable attributes controls.
        """

        dict_ = {k: v for k, v in self.__dict__.items()
                 if k not in self._non_serializable_attributes and not k.startswith('_')}
        return dict_

    # def to_dict(self, use_pointers: bool = True, memo=None, path: str = '#'):
    #     """ Generic to_dict method. """
    #     if memo is None:
    #         memo = {}

    #     # Default to dict
    #     serialized_dict = self.base_dict()
    #     dict_ = self._serializable_dict()
    #     if use_pointers:
    #         serialized_dict.update(serialize_dict_with_pointers(dict_, memo, path)[0])
    #     else:
    #         serialized_dict.update(serialize_dict(dict_))

        # return serialized_dict
        # def to_dict(self):
            


    @classmethod
    def dict_to_object(cls, dict_) -> 'SerializableObject':
        """ Generic dict_to_object method. """
        if 'object_class' in dict_:
            obj = dict_to_object(dict_=dict_)
            return obj

        raise NotImplementedError("No object_class in dict")

    @cached_property
    def full_classname(self):
        """ Full classname of class like: package.module.submodule.classname. """
        return full_classname(self)

    # def copy(self):
    #     """ Copy object. Not implemented at base level. """
    #     raise NotImplementedError("Method copy is not implemented for SerializableObject."
    #                               "Please inherit from DessiaObject")

        
def data_eq(value1, value2):
    """ Returns if two values are equal on data equality. """
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
    if hasattr(value1, '_data_eq'):
        custom_method = value1._data_eq.__code__ is not SerializableObject._data_eq.__code__
        if custom_method:
            return value1._data_eq(value2)

    # Not custom, use generic implementation
    eq_dict = value1._data_eq_dict()
    if 'name' in eq_dict:
        del eq_dict['name']

    other_eq_dict = value2._data_eq_dict()
    return dict_data_eq(eq_dict, other_eq_dict)


def dict_data_eq(dict1, dict2):
    """ Returns True if two dictionaries are equal on data equality, False otherwise. """
    for key, value in dict1.items():
        if key not in dict2:
            return False
        if not data_eq(value, dict2[key]):
            return False
    return True


def sequence_data_eq(seq1, seq2):
    """ Returns if two sequences are equal on data equality. """
    if len(seq1) != len(seq2):
        return False

    for v1, v2 in zip(seq1, seq2):
        if not data_eq(v1, v2):
            return False
    return True
        
class DataEqualityObject(SerializableObject):
    
    def __hash__(self):
        """ Compute a int from object. """
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
