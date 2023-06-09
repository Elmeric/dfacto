# Copyright (c) 2023, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

# mypy: ignore-errors

from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

_T = TypeVar("_T")


# https://stackoverflow.com/questions/75307905/python-typing-for-a-metaclass-singleton
class Singleton(type, Generic[_T]):
    """A Standard Singleton metaclass."""

    _instances: dict[Singleton[_T], _T] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> _T:
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ObjectFactory(Generic[_T]):
    """A general purpose object factory."""

    def __init__(self) -> None:
        self._builders: dict[str, type[_T]] = {}

    def register_builder(self, key: str, builder: type[_T]) -> None:
        self._builders[key] = builder

    def create(self, key: str, *args: Any, **kwargs: Any) -> _T:
        builder = self._builders.get(key)
        if not builder:
            raise ValueError(key)
        return builder(*args, **kwargs)


class Visitor:
    # pylint: disable=too-few-public-methods
    """Base class for visitors."""

    def visit(self, node, *args, **kwargs):
        """Visit a node.

        Calls 'visitClassName' on itself passing 'node', where 'ClassName' is
        the node's class.
        If the visitor does not implement an appropriate visitation method,
        will go up the `MRO` until a match is found.

        Args:
            node: The node to visit.

        Raises:
            NotImplementedError exception if the search exhausts all classes
                of 'node'.

        Returns:
            The return value of the called visitation method.
        """
        if isinstance(node, type):
            mro = node.mro()
        else:
            mro = type(node).mro()

        for cls in mro:
            cls_name = cls.__name__
            cls_name = cls_name[0].upper() + cls_name[1:]
            meth = getattr(self, "visit" + cls_name, None)
            if meth is not None:
                return meth(node, *args, **kwargs)

        cls_name = node.__class__.__name__
        cls_name = cls_name[0].upper() + cls_name[1:]
        raise NotImplementedError(f"No visitation method visit{cls_name}")


def visitable(cls):
    """A decorator to make a class 'visitable'.

    Args:
        cls: the class to decorate.

    Returns:
        the decorated class.
    """

    def accept(self, visitor: Visitor, *args, **kwargs):
        return visitor.visit(self, *args, **kwargs)

    cls.accept = accept
    return cls


# https://programmingideaswithjake.wordpress.com/2015/05/23/python-decorator-for-simplifying-delegate-pattern/
# https://gist.github.com/dubslow/b8996308fc6af2437bef436fa28e86fa
class DelegatedAttribute:
    def __init__(self, delegate_name: str, attr_name: Optional[str] = None) -> None:
        self.attr_name = attr_name
        self.delegate_name = delegate_name

    def __set_name__(self, owner: Any, name: str) -> None:
        if self.attr_name is None:
            self.attr_name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        # return obj.delegate.attr
        return getattr(self.delegate(instance), self.attr_name)

    def __set__(self, instance, value):
        # obj.delegate.attr = value
        setattr(self.delegate(instance), self.attr_name, value)

    def __delete__(self, instance):
        delattr(self.delegate(instance), self.attr_name)

    def delegate(self, obj):
        return getattr(obj, self.delegate_name)

    def __str__(self):
        return ""


def delegate_as(delegate_cls, to="delegate", include=None, ignore=None):
    # turn include and ignore into sets, if they aren't already
    if include is None:
        include = set()
    elif not isinstance(include, set):
        include = set(include)
    if ignore is None:
        ignore = set()
    elif not isinstance(ignore, set):
        ignore = set(ignore)
    delegate_attrs = set(delegate_cls.__dict__.keys())
    attributes = include | delegate_attrs - ignore

    def inner(cls):
        # create property for storing the delegate
        # setattr(cls, to, delegate_cls())
        # setattr(cls, to, SimpleProperty())
        # don't bother adding attributes that the class already has
        attrs = attributes - set(cls.__dict__.keys())
        # set all the attributes
        for attr in attrs:
            setattr(cls, attr, DelegatedAttribute(to, attr))
        return cls

    return inner


if __name__ == "__main__":
    # pylint: disable=all

    class A:
        def __init__(self):
            self.f1 = "f1 in A"
            self.f2 = "f2 in A"
            self._name = "A"

        def m1(self):
            print(f"I'm method m1 of class {self._name}")

        def m2(self):
            print("m2 in A")

        def m3(self):
            print("m3 in A")

    # @delegate_as(A, to="a")
    @delegate_as(A, to="a", include={"f1"}, ignore={"m2", "m3"})
    class B:
        def __init__(self):
            self._name = "B"
            self.f2 = "f2 in B"
            self.a = A()

        def m2(self):
            print("m2 in B")

        m3 = DelegatedAttribute("a")

    b = B()
    b.m1()
    b.m2()
    b.m3()
    x = B.m3
    assert str(x) == ""
    print(b.f1)
    print(b.f2)
