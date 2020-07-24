"""Provide a Namespace supporting both ns.value and ns['value'].

Expected use is to represent configuration files. To that end,
a few functions are also present to ease checking configuration
validity."""


from types import SimpleNamespace
from typing import Optional, Tuple
import codecs


class Namespace(SimpleNamespace):
    """Namespace that also supports mapping access."""

    def __getitem__(self, name):
        """ Adds support for value = ns['key'] """
        return self.__dict__[name]
    
    def __setitem__(self, key, value):
        """ Adds support for ns['key'] = value """
        self.__dict__[key] = value

    def __getattribute__(self, name):
        """ Adds support for local attributes """
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return self.__dict__[name]
    
    def _get(self, key, default=None):
        """ Retrieves a value, or default if not found """
        return self.__dict__.get(key, default)


def dict2ns(input:dict, key_name:Optional[str]=None) -> Namespace:
    """Convert a dict to a namespace for attribute access."""

    ns = Namespace()
    for k, v in input.items():
        if isinstance(v, dict):
            ns[k] = dict2ns(v, key_name)
            if key_name:
                ns[k][key_name] = k
        else:
            ns[k] = v
    return ns

def ns2dict(input:Namespace) -> dict:
    """Convert a Namespace to a dict."""

    d = {}
    for k, v in input.__dict__.items():
        if isinstance(v, Namespace):
            d[k] = ns2dict(v)
        else:
            d[k] = v
    return d


# =====

class ConfigurationError(ValueError): pass

def check_section(config:Namespace, name:str) -> Namespace:
    """ Checks that a section with the sepcified name is present """

    section = config._get(name)
    if section is None:
        raise ConfigurationError(f"Section {name} not found in configuration")
    if not isinstance(section, Namespace):
        raise ConfigurationError(f"Configuration error: {name} not a section")
    return section

def check_default(section:Namespace, name:str, default) -> bool:
    """ Checks if a value is present, setting default if not """

    value = section._get(name)
    if value is None or value == '':
        section[name] = default
        return True
    return False

def check_oneof(section:Namespace, name:str, oneof:Tuple[str], default=None):
    """ Raises if value not in supplied list of options """

    value = section._get(name)
    if (value is None or value == '') and not default is None:
        section[name] = default
        return
    if value in oneof: return
    raise ConfigurationError(f"Configuration error: {section._name}:{name} must be one of {str(oneof)}")

def check_notempty(section:Namespace, name:str):
    """ Raises if value not supplied or empty """

    value = section._get(name)
    if value: return
    raise ConfigurationError(f"Configuration error: {section._name}:{name} must be present and non-empty")

def check_encoding(section:Namespace, name:str, default):
    if check_default(section, name, default): return
    encoding = section[name]
    try:
        codecs.lookup(encoding)
    except LookupError:
        msg = f"Configuration error: {section._name}:{name}: '{encoding}' is an unrecognised encoding"
        raise ConfigurationError(msg) from None
