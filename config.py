
import sys
import re
from os.path import exists, isfile, isabs, dirname, abspath, join
import json

import toml

from namespace import Namespace, dict2ns, ns2dict, check_default
from namespace import check_encoding, check_notempty, check_oneof
from namespace import check_section, ConfigurationError


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
        spec = spec.replace('\\', '\\\\')
        spec = spec.replace('.', '\\.')
        # Create valid regex for star
        spec = spec.replace('*', '.*')
        regex = re.compile(spec)
        config.skip_regexes.append(regex)

    return config


# =====

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
    check_default(local, 'logdir', '')
    
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
