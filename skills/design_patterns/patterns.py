"""Design Patterns - Reusable solutions to common software design problems.

Organized into three categories:
- Creational: object creation mechanisms
- Structural: composition of classes/objects
- Behavioral: communication between objects
"""

from abc import ABC, abstractmethod


# === CREATIONAL: Singleton ===

class Singleton:
    """Ensure a class has only one instance.

    Use when: you need exactly one instance (config, connection pool, logger).
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


# === CREATIONAL: Factory ===

class Animal(ABC):
    @abstractmethod
    def speak(self):
        pass


class Dog(Animal):
    def speak(self):
        return "Woof!"


class Cat(Animal):
    def speak(self):
        return "Meow!"


class AnimalFactory:
    """Create objects without specifying the exact class.

    Use when: object creation logic is complex or varies by input.
    """
    @staticmethod
    def create(animal_type):
        animals = {"dog": Dog, "cat": Cat}
        cls = animals.get(animal_type.lower())
        if cls is None:
            raise ValueError(f"Unknown animal: {animal_type}")
        return cls()


# === STRUCTURAL: Observer ===

class EventEmitter:
    """Objects subscribe to events and get notified when they occur.

    Use when: you need loose coupling between components that react to changes.
    """
    def __init__(self):
        self._listeners = {}

    def on(self, event, callback):
        self._listeners.setdefault(event, []).append(callback)

    def off(self, event, callback):
        if event in self._listeners:
            self._listeners[event] = [
                cb for cb in self._listeners[event] if cb != callback
            ]

    def emit(self, event, *args, **kwargs):
        for callback in self._listeners.get(event, []):
            callback(*args, **kwargs)


# === BEHAVIORAL: Strategy ===

class SortStrategy(ABC):
    """Define a family of algorithms and make them interchangeable.

    Use when: you need to switch between algorithms at runtime.
    """
    @abstractmethod
    def sort(self, data):
        pass


class QuickSortStrategy(SortStrategy):
    def sort(self, data):
        if len(data) <= 1:
            return data
        pivot = data[len(data) // 2]
        left = [x for x in data if x < pivot]
        middle = [x for x in data if x == pivot]
        right = [x for x in data if x > pivot]
        return self.sort(left) + middle + self.sort(right)


class MergeSortStrategy(SortStrategy):
    def sort(self, data):
        if len(data) <= 1:
            return data
        mid = len(data) // 2
        left = self.sort(data[:mid])
        right = self.sort(data[mid:])
        return self._merge(left, right)

    def _merge(self, left, right):
        result, i, j = [], 0, 0
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                result.append(left[i])
                i += 1
            else:
                result.append(right[j])
                j += 1
        return result + left[i:] + right[j:]


class Sorter:
    def __init__(self, strategy: SortStrategy):
        self._strategy = strategy

    def set_strategy(self, strategy: SortStrategy):
        self._strategy = strategy

    def sort(self, data):
        return self._strategy.sort(data)
