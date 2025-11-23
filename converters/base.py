"""
Base converter classes for converting PrusaSlicer INI settings to OrcaSlicer JSON.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple


class ConversionResult:
    """Result of a setting conversion, can contain multiple key-value pairs."""
    
    def __init__(self):
        self.settings: Dict[str, Any] = {}
        self.needs_manual_conversion: List[str] = []
        
    def add_setting(self, key: str, value: Any):
        """Add a converted setting."""
        self.settings[key] = value
        
    def mark_needs_conversion(self, key: str):
        """Mark a key that needs manual conversion."""
        self.needs_manual_conversion.append(key)
        
    def merge(self, other: 'ConversionResult'):
        """Merge another ConversionResult into this one."""
        self.settings.update(other.settings)
        self.needs_manual_conversion.extend(other.needs_manual_conversion)


class BaseConverter(ABC):
    """Base class for all setting converters."""
    
    @abstractmethod
    def can_convert(self, prusa_key: str, prusa_value: Any) -> bool:
        """Check if this converter can handle the given key."""
        pass
    
    @abstractmethod
    def convert(self, prusa_key: str, prusa_value: Any) -> ConversionResult:
        """
        Convert a PrusaSlicer setting to OrcaSlicer format.
        Returns a ConversionResult that may contain multiple settings.
        """
        pass


class SimpleKeyConverter(BaseConverter):
    """Converter for simple 1:1 key mappings with optional value transformation."""
    
    def __init__(self, prusa_key: str, orca_key: str, value_transform=None):
        """
        Args:
            prusa_key: The PrusaSlicer key to match
            orca_key: The OrcaSlicer key to output
            value_transform: Optional function to transform the value
        """
        self.prusa_key = prusa_key
        self.orca_key = orca_key
        self.value_transform = value_transform
        
    def can_convert(self, prusa_key: str, prusa_value: Any) -> bool:
        return prusa_key == self.prusa_key
    
    def convert(self, prusa_key: str, prusa_value: Any) -> ConversionResult:
        result = ConversionResult()
        value = self.value_transform(prusa_value) if self.value_transform else prusa_value
        result.add_setting(self.orca_key, value)
        return result


class MultiKeyConverter(BaseConverter):
    """Converter that matches multiple PrusaSlicer keys to a single OrcaSlicer key."""
    
    def __init__(self, prusa_keys: List[str], orca_key: str, value_transform=None):
        """
        Args:
            prusa_keys: List of PrusaSlicer keys that map to the same OrcaSlicer key
            orca_key: The OrcaSlicer key to output
            value_transform: Optional function to transform the value
        """
        self.prusa_keys = prusa_keys
        self.orca_key = orca_key
        self.value_transform = value_transform
        
    def can_convert(self, prusa_key: str, prusa_value: Any) -> bool:
        return prusa_key in self.prusa_keys
    
    def convert(self, prusa_key: str, prusa_value: Any) -> ConversionResult:
        result = ConversionResult()
        value = self.value_transform(prusa_value) if self.value_transform else prusa_value
        result.add_setting(self.orca_key, value)
        return result


class SplitConverter(BaseConverter):
    """Converter that splits one PrusaSlicer setting into multiple OrcaSlicer settings."""
    
    def __init__(self, prusa_key: str, conversions: List[Tuple[str, callable]]):
        """
        Args:
            prusa_key: The PrusaSlicer key to match
            conversions: List of (orca_key, value_function) tuples
                        where value_function takes the prusa_value and returns the orca value
        """
        self.prusa_key = prusa_key
        self.conversions = conversions
        
    def can_convert(self, prusa_key: str, prusa_value: Any) -> bool:
        return prusa_key == self.prusa_key
    
    def convert(self, prusa_key: str, prusa_value: Any) -> ConversionResult:
        result = ConversionResult()
        for orca_key, value_func in self.conversions:
            value = value_func(prusa_value)
            result.add_setting(orca_key, value)
        return result


class CustomConverter(BaseConverter):
    """Converter for custom conversion logic."""
    
    def __init__(self, can_convert_func: callable, convert_func: callable):
        """
        Args:
            can_convert_func: Function(prusa_key, prusa_value) -> bool
            convert_func: Function(prusa_key, prusa_value) -> ConversionResult
        """
        self.can_convert_func = can_convert_func
        self.convert_func = convert_func
        
    def can_convert(self, prusa_key: str, prusa_value: Any) -> bool:
        return self.can_convert_func(prusa_key, prusa_value)
    
    def convert(self, prusa_key: str, prusa_value: Any) -> ConversionResult:
        return self.convert_func(prusa_key, prusa_value)


class ConverterRegistry:
    """Registry that manages all converters and performs conversions."""
    
    def __init__(self):
        self.converters: List[BaseConverter] = []
        self.ignored_keys: set = set()
        self._orca_key_mappings: Dict[str, str] = {}  # Track orca_key -> prusa_key to detect conflicts
        self._mutually_exclusive_groups: Dict[str, set] = {}  # Track orca_key -> set of allowed prusa_keys
        
    def register(self, converter: BaseConverter):
        """Register a converter."""
        self.converters.append(converter)
        
    def register_simple(self, prusa_key: str, orca_key: str, value_transform=None):
        """Convenience method to register a simple key mapping."""
        # Check if this orca_key is already mapped from a different prusa_key
        if orca_key in self._orca_key_mappings:
            existing_prusa_key = self._orca_key_mappings[orca_key]
            if existing_prusa_key != prusa_key:
                # Check if this is part of a mutually exclusive group
                if orca_key in self._mutually_exclusive_groups:
                    allowed_keys = self._mutually_exclusive_groups[orca_key]
                    if prusa_key not in allowed_keys:
                        raise ValueError(
                            f"Duplicate mapping detected: OrcaSlicer key '{orca_key}' is already "
                            f"mapped from PrusaSlicer key '{existing_prusa_key}', cannot also map from '{prusa_key}'. "
                            f"Allowed mutually exclusive keys: {allowed_keys}"
                        )
                    # Valid mutually exclusive mapping, update the tracker
                    self._orca_key_mappings[orca_key] = prusa_key
                else:
                    raise ValueError(
                        f"Duplicate mapping detected: OrcaSlicer key '{orca_key}' is already "
                        f"mapped from PrusaSlicer key '{existing_prusa_key}', cannot also map from '{prusa_key}'"
                    )
        else:
            self._orca_key_mappings[orca_key] = prusa_key
        
        self.register(SimpleKeyConverter(prusa_key, orca_key, value_transform))
        
    def register_multi(self, prusa_keys: List[str], orca_key: str, value_transform=None):
        """Convenience method to register multiple PrusaSlicer keys to one OrcaSlicer key."""
        self.register(MultiKeyConverter(prusa_keys, orca_key, value_transform))
        
    def register_split(self, prusa_key: str, conversions: List[Tuple[str, callable]]):
        """Convenience method to register a split converter."""
        self.register(SplitConverter(prusa_key, conversions))
        
    def register_custom(self, can_convert_func: callable, convert_func: callable):
        """Convenience method to register a custom converter."""
        self.register(CustomConverter(can_convert_func, convert_func))
    
    def register_ignore(self, *prusa_keys: str):
        """Register settings to ignore (don't convert and don't mark as needing conversion)."""
        self.ignored_keys.update(prusa_keys)
    
    def register_mutually_exclusive(self, orca_key: str, *prusa_keys: str):
        """Register a group of mutually exclusive PrusaSlicer keys that map to the same OrcaSlicer key.
        
        Args:
            orca_key: The OrcaSlicer key that multiple PrusaSlicer keys can map to
            prusa_keys: The PrusaSlicer keys that are mutually exclusive
        """
        if orca_key in self._mutually_exclusive_groups:
            self._mutually_exclusive_groups[orca_key].update(prusa_keys)
        else:
            self._mutually_exclusive_groups[orca_key] = set(prusa_keys)
        
    def convert_setting(self, prusa_key: str, prusa_value: Any) -> ConversionResult:
        """
        Convert a single setting using registered converters.
        
        Supports multiple converters for the same key - all matching converters
        will be applied and their results merged.
        """
        # Check if this key should be ignored
        if prusa_key in self.ignored_keys:
            return ConversionResult()
        
        merged_result = ConversionResult()
        found_converter = False
        
        for converter in self.converters:
            if converter.can_convert(prusa_key, prusa_value):
                result = converter.convert(prusa_key, prusa_value)
                merged_result.merge(result)
                found_converter = True
        
        # No converter found
        if not found_converter:
            merged_result.mark_needs_conversion(prusa_key)
        
        return merged_result
    
    def convert_dict(self, prusa_settings: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Convert a dictionary of settings.
        Returns (converted_settings, needs_manual_conversion_keys)
        """
        converted = {}
        needs_conversion = []
        
        for key, value in prusa_settings.items():
            result = self.convert_setting(key, value)
            converted.update(result.settings)
            needs_conversion.extend(result.needs_manual_conversion)
        
        return converted, needs_conversion
    
    def get_reverse_mapping(self, orca_key: str) -> List[str]:
        """
        Get all PrusaSlicer keys that map to the given OrcaSlicer key.
        
        Args:
            orca_key: The OrcaSlicer key to look up
        
        Returns:
            List of PrusaSlicer keys that map to this OrcaSlicer key
        """
        prusa_keys = []
        
        for converter in self.converters:
            if isinstance(converter, SimpleKeyConverter):
                if converter.orca_key == orca_key:
                    prusa_keys.append(converter.prusa_key)
            elif isinstance(converter, MultiKeyConverter):
                if converter.orca_key == orca_key:
                    prusa_keys.extend(converter.prusa_keys)
        
        return prusa_keys
