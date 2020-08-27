
import sys
import re
from os.path import exists, isfile, isabs, dirname, abspath, join
import json
import logging
from typing import Callable

import toml

import namespace as ns
from namespace import ConfigurationError


def get_config(cfgfile, log_callback:Callable[[ns.Namespace],None]=None) -> ns.Namespace:
    """Parse the config file, check validity, return as Namespace."""
    
    config = ns.dict2ns(toml.load(cfgfile))

    # Add config file and directory
    config.cfgfile = cfgfile
    config.cfgdir = dirname(cfgfile)

    # Minimal check for logging configuration
    local = ns.check_section(config, 'Local')
    ns.check_default(local, 'logdir', '')
    levels = 'critical,error,warning,info,debug'.split(',')
    ns.check_oneof(local, 'loglevel', levels, 'info')

    # Call callback to do final setup of logging
    log_callback(config)

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

def check(config:ns.Namespace):
    """Check validity of values in the parsed configuration."""

    # We need at least the Source and Config sections
    for name in ('Source', 'Local'):
        ns.check_section(config, name)
    
    # Check Source
    src = config.Source
    ns.check_oneof(src, 'type', ('github', 'directory'))
    ns.check_oneof(src, 'srctype', ('xml', 'udl'), 'udl')
    ns.check_encoding(src, 'encoding', 'UTF-8')
    
    # Set some defaults if needed
    ns.check_default(src, 'srcdir', '')
    ns.check_default(src, 'datadir', '')
    ns.check_default(src, 'cspdir', '')
    ns.check_default(src, 'skip', [])
    
    # Strip leading slash if present, we don't need it
    if src.srcdir == '/': src.srcdir = src.srcdir[1:]
    if src.datadir == '/': src.datadir = src.datadir[1:]
    if src.cspdir == '/': src.cspdir = src.cspdir[1:]

    # Check Local section
    local = config.Local
    ns.check_notempty(local, 'outfile')
    ns.check_default(local, 'deployment', False)
    ns.check_default(local, 'logdir', '')
    ns.check_default(local, 'loglevel', '')
    
    # Check CSP configuration
    if src.cspdir:
        csp = ns.check_section(config, 'CSP')
        if ns.check_default(csp, 'parsers', []):
            raise ConfigurationError("At least one [[CSP.parsers]] section for CSP items should be present.")
        for i, parser in enumerate(csp.parsers):
            if not isinstance(parser, ns.Namespace):
                raise ConfigurationError(f'Parser {i+1} must be a section.')
            ns.check_notempty(parser, 'regex')
            ns.check_notempty(parser, 'app')
            ns.check_notempty(parser, 'item')
            ns.check_oneof(parser, 'nomatch', ('skip', 'error'), 'error')
        ns.check_oneof(csp, 'export', ('embed', 'separate'), 'embed')
        
        # CSP items appear unsupported in deployments, so must be exported separately
        if local.deployment and csp.export == 'embed':
            raise ConfigurationError("When requesting a deployment, CSP export must be 'separate'.")
    
    # Check optional sections
    if src.type == 'directory':
        ns.check_section(config, 'Directory')
        ns.check_notempty(config.Directory, 'path')
        if 'structure' in config.Directory:
            logging.warning("Warning: setting 'structure' in section Directory no longer used.")
            del config.Directory.structure
        if not isabs(config.Directory.path):
            config.Directory.path = join(abspath(config.cfgdir), config.Directory.path)
    else:
        ns.check_section(config, 'GitHub')
        gh = config.GitHub
        ns.check_notempty(gh, 'user')
        ns.check_notempty(gh, 'repo')
        ns.check_notempty(gh, 'tag')
        ns.check_default(config.GitHub, 'token', '')

    if src.srctype == 'udl':
        # Server needed for conversion to XML
        ns.check_section(config, 'Server')
        svr = config.Server
        for name in 'host,port,namespace,user,password'.split(','):
            ns.check_notempty(svr, name)
        ns.check_default(config.Server, 'https', False)
        

# =====

def main(cfgfile):
    config = get_config(cfgfile)
    print(json.dumps(ns.ns2dict(config), indent=2, default=str))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <configfile>")
        sys.exit(1)

    cfgfile = sys.argv[1]
    if not exists(cfgfile) or not isfile(cfgfile):
        print(f"File {cfgfile} not found.\nUsage: {sys.argv[0]} <configfile>")
        sys.exit(1)
    
    main(cfgfile)
