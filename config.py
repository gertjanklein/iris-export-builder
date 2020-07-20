
import sys
import re
from os.path import exists, isfile, isabs, dirname, abspath, join
import json
import codecs

from typing import Tuple

import toml

from namespace import Namespace, dict2ns, ns2dict


def get_config(cfgfile) -> Namespace:
    """Parse the config file, check validity, return as Namespace."""
    
    config = dict2ns(toml.load(cfgfile), '_name')

    # Add config file and directory
    config.cfgfile = cfgfile
    config.cfgdir = dirname(cfgfile)

    # Make sure configuration is complete
    check(config)
    
    # Converts specification(s) of files to skip to regexes
    config.skip_regexes = []
    for spec in config.Source.skip:
        spec = spec.replace('.', '\\.')
        spec = spec.replace('\\', '\\\\')
        # Create valid regex for star
        spec = spec.replace('*', '.*')
        regex = re.compile(spec)
        config.skip_regexes.append(regex)

    return config


# =====

class ConfigurationError(ValueError): pass

def check(config:Namespace):
    """Check validity of values in the parsed configuration."""

    # We need at least the Source and Config sections
    for name in ('Source', 'Local'):
        check_section(config, name)
    
    # Check Source
    src = config.Source
    check_oneof(src, 'type', ('github', 'directory'))
    check_oneof(src, 'srctype', ('xml', 'udl'), 'udl')
    check_encoding(src, 'encoding', 'UTF-8')
    
    # Set some defaults if needed
    check_default(src, 'srcdir', '')
    check_default(src, 'cspdir', '')
    check_default(src, 'skip', [])

    # Check Local section
    local = config.Local
    check_notempty(local, 'outfile')
    check_default(local, 'deployment', False)
    
    # Check optional sections
    if src.type == 'directory':
        check_section(config, 'Directory')
        check_notempty(config.Directory, 'path')
        check_oneof(config.Directory, 'structure', ('flat', 'nested'), 'nested')
        if not isabs(config.Directory.path):
            config.Directory.path = join(abspath(config.cfgdir), config.Directory.path)
        if src.cspdir:
            raise ConfigurationError("CSP items not yet supported in filesystem-type repository.")
    else:
        check_section(config, 'GitHub')
        gh = config.GitHub
        check_notempty(gh, 'user')
        check_notempty(gh, 'repo')
        check_notempty(gh, 'tag')
        check_default(config.GitHub, 'token', '')

    if src.srctype == 'udl':
        # Server needed for conversion to XML
        check_section(config, 'Server')
        svr = config.Server
        for name in 'host,port,namespace,user,password'.split(','):
            check_notempty(svr, name)
        check_default(config.Server, 'https', False)
        

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


# =====

def main(cfgfile):
    config = get_config(cfgfile)
    print(json.dumps(ns2dict(config), indent=2, default=str))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <configfile>")
        sys.exit(1)

    cfgfile = sys.argv[1]
    if not exists(cfgfile) or not isfile(cfgfile):
        print(f"File {cfgfile} not found.\nUsage: {sys.argv[0]} <configfile>")
        sys.exit(1)
    
    main(cfgfile)
