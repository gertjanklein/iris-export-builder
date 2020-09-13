
import sys
import os
from os.path import exists, isfile, isabs, dirname, abspath, join, splitext, basename
import re
import datetime
import logging

import toml

import namespace as ns
from namespace import ConfigurationError


def get_config() -> ns.Namespace:
    """Parse the config file, check validity, return as Namespace."""
    
    # Get configuration filename from commandline
    cfgfile = parse_args()

    # Initial logging setup: file next to config file. Errors parsing the
    # config file will be logged here.
    setup_basic_logging(cfgfile)
    
    # Log unhandled exceptions
    sys.excepthook = unhandled_exception

    # Load configuration from file
    config = ns.dict2ns(toml.load(cfgfile))

    # Add config file and directory
    config.cfgfile = cfgfile
    config.cfgdir = dirname(cfgfile)

    # Minimal check for logging configuration
    local = ns.check_section(config, 'Local')
    ns.check_default(local, 'logdir', '')
    levels = 'debug,info,warning,error,critical'.split(',')
    ns.check_oneof(local, 'loglevel', levels, 'info')

    # Do final setup of logging
    setup_logging(config)

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
        

# ==========

def setup_basic_logging(cfgfile):
    """ Initial logging setup: log to file next to config file """

    # Determine log file name
    base, ext = splitext(cfgfile)
    if ext.lower() == '.toml':
        logfile = f'{base}.log'
    else:
        logfile = f'{cfgfile}.log'
    
    # Create handler with delayed creation of log file
    handlers = [logging.FileHandler(logfile, delay=True)]

    # Display what we log as-is, no level strings etc.
    logging.basicConfig(handlers=handlers, level=logging.INFO,
        format='%(message)s')


def setup_logging(config):
    """ Final logging setup: allow log location override in config """

    logdir:str = config.Local.logdir
    loglevel:str = config.Local.loglevel

    # Determine filename (without path)
    base, ext = splitext(basename(config.cfgfile))
    if ext.lower() == '.toml':
        logfile = f'{base}.log'
    else:
        logfile = f'{base}.{ext}.log'

    # Determine filename (with path)
    name = join(logdir, logfile)
    if not isabs(logdir):
        # Logdir not absolute: make it relative to dir config file is in
        name = join(dirname(config.cfgfile), name)

    # Make sure the log directory exists
    logdir = dirname(name)
    os.makedirs(logdir, exist_ok=True)

    # Replace the current logging handler with one using the newly
    # determined path
    logger = logging.getLogger()
    logger.handlers.clear()
    logger.handlers.append(logging.FileHandler(name, 'a'))

    if loglevel is not None:
        logger.setLevel(loglevel.upper())

    # Log appends; create visible separation for this run
    logging.info(f"\n\n===== Starting at {str(datetime.datetime.now()).split('.')[0]}")
    
# =====

def unhandled_exception(exc_type, exc_value, exc_traceback):
    """ Handle otherwise unhandled exceptions by logging them """

    if exc_type == ConfigurationError:
        msg = exc_value.args[0]
        logging.error("\n%s", msg)
    else:
        msg = f"An error occurred; please see the log file for details.\n\n{exc_value}"
        logging.exception("\n##### Unhandled exception:", exc_info=(exc_type, exc_value, exc_traceback))
    msgbox(msg, True)
    sys.exit(1)

# =====

def msgbox(msg, is_error=False):
    """ Display, if on Windows, a message box """

    if os.name == 'nt':
        if is_error:
            flags = 0x30
            title = "Error"
        else:
            flags = 0
            title = "Info"
        import ctypes
        MessageBox = ctypes.windll.user32.MessageBoxW
        MessageBox(None, msg, title, flags)
    else:
        print(msg)

# =====

def parse_args():
    """Parse command line arguments; return configuration file."""

    if len(sys.argv) < 2:
        msgbox(f"Usage: {sys.argv[0]} <cfgfile>", True)
        sys.exit(1)

    cfgfile = sys.argv[1]
    if not isabs(cfgfile) and not exists(cfgfile):
        cfgfile = join(dirname(__file__), cfgfile)
    
    if not exists(cfgfile) or not isfile(cfgfile):
        msgbox(f"File {cfgfile} not found.\nUsage: {sys.argv[0]} <cfgfile>", True)
        sys.exit(1)
    
    if not isabs(cfgfile):
        cfgfile = abspath(cfgfile)
    
    return cfgfile


