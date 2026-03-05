"""Exercises: Design Patterns

Run with: python -m pytest exercises/python/test_patterns.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from skills.design_patterns.patterns import (
    Singleton, AnimalFactory, EventEmitter, Sorter,
    QuickSortStrategy, MergeSortStrategy
)


# --- Exercise 1: Singleton ---

def test_singleton():
    a = Singleton()
    b = Singleton()
    assert a is b


# --- Exercise 2: Factory ---

def test_factory():
    dog = AnimalFactory.create("dog")
    cat = AnimalFactory.create("cat")
    assert dog.speak() == "Woof!"
    assert cat.speak() == "Meow!"


# --- Exercise 3: Observer / EventEmitter ---

def test_event_emitter():
    emitter = EventEmitter()
    results = []

    def on_data(value):
        results.append(value)

    emitter.on("data", on_data)
    emitter.emit("data", 42)
    emitter.emit("data", 99)
    assert results == [42, 99]

    emitter.off("data", on_data)
    emitter.emit("data", 0)
    assert results == [42, 99]  # no change after unsubscribe


# --- Exercise 4: Strategy ---

def test_strategy_pattern():
    data = [5, 3, 8, 1, 9, 2]
    expected = [1, 2, 3, 5, 8, 9]

    sorter = Sorter(QuickSortStrategy())
    assert sorter.sort(data) == expected

    sorter.set_strategy(MergeSortStrategy())
    assert sorter.sort(data) == expected
