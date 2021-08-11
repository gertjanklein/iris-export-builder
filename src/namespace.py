"""Provide a Namespace supporting both ns.value and ns['value'].

Expected use is to represent configuration files. To that end,
a few functions are also present to ease checking configuration
validity.

Nested namespaces have their name in a property "_name".
"""


from types import SimpleNamespace
from typing import Optional, Mapping, Iterable
import codecs


class Namespace(SimpleNamespace):
    """Namespace that also supports mapping access."""

    def __getitem__(self, name):
        """Add support for value = ns['key']."""

        return self.__dict__[name]
    
    def __setitem__(self, key, value):
        """Add support for ns['key'] = value."""

        self.__dict__[key] = value

    def __getattribute__(self, name):
        """Add support for local attributes."""

        try:
            # If an actual attribute <name> is present, return that
            return object.__getattribute__(self, name)
        except AttributeError:
            # Delegate to the key/value dictionary
            try:
                return self.__dict__[name]
            except KeyError:
                raise AttributeError(name) from None
    
    def __delattr__(self, name):
        """Add support for deleting values."""

        d = object.__getattribute__(self, '__dict__')
        del d[name]

    def __contains__(self, name):
        """Add support for in operator."""
        return self.__dict__.__contains__(name)

    def __iter__(self):
        """Add support for iteration."""

        return self.__dict__.__iter__()

    # ----- Helper methods

    def _get(self, key, default=None):
        """Retrieve a value, or default if not found."""

        return self.__dict__.get(key, default)

    def _flattened(self, _prefix=None):
        """Yields (dotted name, value) pairs for all values."""
        
        for key in self:
            if key == '_name':
                continue
            value = self[key]
            key = f"{_prefix}.{key}" if _prefix else key
            if isinstance(value, type(self)):
                yield from value._flattened(key)
            else:
                yield key, value




def dict2ns(input:Mapping) -> Namespace:
    """Convert a dict to a namespace for attribute access."""

    ns = Namespace()
    for k, v in input.items():
        if isinstance(v, dict):
            ns[k] = dict2ns(v)
            ns[k]['_name'] = k
        elif isinstance(v, list):
            ns[k] = v
            for i, v2 in enumerate(v):
                if not isinstance(v2, dict):
                    continue
                v[i] = dict2ns(v2)
                v[i]['_name'] = f'{k}[{i+1}]'
        else:
            ns[k] = v
    return ns

def ns2dict(input:Namespace) -> dict:
    """Convert a Namespace to a dict."""

    d = {}
    for k, v in input.__dict__.items():
        if isinstance(v, Namespace):
            d[k] = ns2dict(v)
            if '_name' in d[k]:
                del d[k]['_name']
        else:
            d[k] = v
    return d


# =====

def set_in_path(ns:Namespace, path:str, value):
    """Sets a value in a sub-namespace, assuring it exists."""

    parts = path.split('.')
    # Add sub-namespaces, if not present
    for name in parts[:-1]:
        if not name in ns:
            ns[name] = Namespace()
            ns[name]['_name'] = name
        elif not isinstance(ns[name], Namespace):
            raise ConfigurationError(f"Configuration error: {name} in configuration should be a section")
        ns = ns[name]
    # Set value
    value_name = parts[-1]
    ns[value_name] = value

def get_in_path(ns:Namespace, path:str, default=None):
    """Gets a value in a sub-namespace, if present. Never raises."""

    assert '.' in path
    parts = path.split('.')
    # Add sub-namespaces, if not present
    for name in parts[:-1]:
        if not name in ns:
            return default
        ns = ns[name]
        if not isinstance(ns, Namespace):
            return None
    value_name = parts[-1]
    return ns._get(value_name, default)


# =====

class ConfigurationError(ValueError):
    """Exception to signal detected error in configuration."""

def get_section(config:Namespace, name:str, create=False) -> Optional[Namespace]:
    """Returns a section if it exists; optionally creates if not."""
    
    section = config._get(name)
    if section is None:
        if not create:
            return None
        
        section = Namespace()
        config[name] = section
        config[name]['_name'] = name
        return section
        
    if not isinstance(section, Namespace):
        raise ConfigurationError(f"Configuration error: {name} not a section")
    return section

def check_section(config:Namespace, name:str) -> Namespace:
    """Check that a section with the specified name is present."""

    section = config._get(name)
    if section is None:
        raise ConfigurationError(f"Section {name} not found in configuration")
    if not isinstance(section, Namespace):
        raise ConfigurationError(f"Configuration error: {name} not a section")
    return section

def check_default(section:Namespace, name:str, default) -> bool:
    """Check if a value is present, setting default if not."""

    value = section._get(name)
    if value is None or value == '':
        section[name] = default
        return True
    return False

def check_oneof(section:Namespace, name:str, oneof:Iterable, default=None):
    """Raises if value not in supplied list of options."""

    value = section._get(name)
    if (value is None or value == '') and not default is None:
        section[name] = default
        return
    if value in oneof: return
    disp_name = f'{section._name}:{name}' if '_name' in section else name
    raise ConfigurationError(f"Configuration error: {disp_name} must be one of {str(oneof)}")

def check_notempty(section:Namespace, name:str):
    """Raises if value not supplied or empty."""

    value = section._get(name)
    if value: return
    disp_name = f'{section._name}:{name}' if '_name' in section else name
    raise ConfigurationError(f"Configuration error: {disp_name} must be present and non-empty")

def check_encoding(section:Namespace, name:str, default):
    """Raises if specified encoding is unknown."""
    if check_default(section, name, default):
        return
    encoding = section[name]
    try:
        codecs.lookup(encoding)
    except LookupError:
        disp_name = f'{section._name}:{name}' if '_name' in section else name
        msg = f"Configuration error: {disp_name}: '{encoding}' is an unrecognised encoding"
        raise ConfigurationError(msg) from None
