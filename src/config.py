
import sys
import os
from os.path import exists, isfile, isabs, dirname, abspath, join, splitext, basename
import re
import datetime
import argparse
from io import StringIO
import logging

from typing import cast

import toml

import namespace as ns
from namespace import ConfigurationError


def get_config() -> ns.Namespace:
    """Parse the config file, check validity, return as Namespace."""
    
    # Get configuration filename from commandline
    args = parse_args()
    cfgfile = args.config

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

    # Merge-in setting from the file specified in augment_from, if any
    merge_augmented_settings(config)

    # Do final setup of logging
    setup_logging(config)

    # Merge command line overrides into configuration
    merge_overrides(args, config)

    # Make sure configuration is complete
    check(config)
    
    # # Converts specification(s) of files to skip/take to regexes
    for src, dst in (('skip', 'skip_regexes'), ('take', 'take_regexes')):
        config[dst] = []
        for spec in config.Source[src]:
            spec = spec.replace('\\', '\\\\')
            spec = spec.replace('.', '\\.')
            # Create valid regex for star
            spec = spec.replace('*', '.*')
            regex = re.compile(spec, re.I)
            config[dst].append(regex)
    
    # Load token contents from file, if specified
    if config.Source.type == 'github' and config.GitHub.token and config.GitHub.token[0] == '@':
        path = config.GitHub.token[1:]
        if not isabs(path):
            path = join(abspath(config.cfgdir), path)
        try:
            with open(path, encoding='UTF-8') as f:
                config.GitHub.token = f.read().strip()
        except OSError as e:
            raise ConfigurationError(f"Error reading token file {path}: {e}") from None
    
    return config


# =====

def merge_augmented_settings(config:ns.Namespace):
    """ Merges settings from file in setting augment_from, if any """
    
    local = ns.get_section(config, 'Local')
    if local is None:
        return
    fname = local._get('augment_from')
    if fname is None:
        return
    if not isabs(fname):
        fname = join(config.cfgdir, fname)
    if not exists(fname):
        raise ConfigurationError(f"augment_from file {local._get('augment_from')} not found")
    cs = ns.dict2ns(toml.load(fname))
    if (aug_local := ns.get_section(cs, 'Local')) and 'augment_from' in aug_local:
        raise ConfigurationError("Recursive augment_from not supported")
    # Add/override each key/value in augment_from
    for k, v in cs._flattened():
        ns.set_in_path(config, k, v)


def merge_overrides(args:argparse.Namespace, config:ns.Namespace):
    """Merge command line overrides into configuration"""
    
    config.no_gui = args.no_gui
    for arg in ARGS:
        value = getattr(args, cast(str, arg['name']))
        if not value:
            continue
        ns.set_in_path(config, cast(str, arg['path']), value)
        

def check(config:ns.Namespace):
    """Check validity of values in the parsed configuration."""

    # We need at least the Source and Config sections
    for name in ('Source', 'Local'):
        ns.check_section(config, name)
    
    # Check Source
    src = config.Source
    ns.check_oneof(src, 'type', ('github', 'bitbucket', 'directory'))
    ns.check_oneof(src, 'srctype', ('xml', 'udl'), 'udl')
    ns.check_encoding(src, 'encoding', 'UTF-8')
    
    # Set some defaults if needed
    ns.check_default(src, 'srcdir', '')
    ns.check_default(src, 'datadir', '')
    ns.check_default(src, 'cspdir', '')
    ns.check_default(src, 'skip', [])
    ns.check_default(src, 'take', [])
    
    # Strip leading slash if present, we don't need it
    if src.srcdir == '/':
        src.srcdir = src.srcdir[1:]
    if src.datadir == '/':
        src.datadir = src.datadir[1:]
    if src.cspdir == '/':
        src.cspdir = src.cspdir[1:]

    # Check Local section
    local = config.Local
    ns.check_notempty(local, 'outfile')
    ns.check_default(local, 'deployment', False)
    ns.check_default(local, 'logdir', '')
    ns.check_default(local, 'loglevel', '')
    ns.check_default(local, 'threads', 1)
    ns.check_default(local, 'sort', False)
    ns.check_oneof(local, 'timestamps', ('clear', 'update', 'leave'), 'leave')
    ns.check_oneof(local, 'export_version', (25, 26, '', None), '')
    if local.export_version == '':
        local.export_version = None
    ns.check_oneof(local, 'converter', ('iris', 'builtin'), 'iris')
    
    # Check data configuration
    if src.datadir:
        data = ns.get_section(config, 'Data', True)
        assert data is not None # stop mypy complaints
        ns.check_oneof(data, 'export', ('embed', 'separate', 'none'), 'embed')

    # Check CSP configuration
    if src.cspdir:
        check_csp(config)
    
        # CSP items appear unsupported in deployments, so must be exported separately
        if local.deployment and config.CSP.export == 'embed':
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
    elif src.type == 'bitbucket':
        ns.check_section(config, 'Bitbucket')
        bb = config.Bitbucket
        ns.check_notempty(bb, 'owner')
        ns.check_notempty(bb, 'repo')
        ns.check_notempty(bb, 'tag')
        ns.check_default(config.Bitbucket, 'token', '')
        ns.check_default(config.Bitbucket, 'user', '')
    else:
        ns.check_section(config, 'GitHub')
        gh = config.GitHub
        ns.check_notempty(gh, 'user')
        ns.check_notempty(gh, 'repo')
        ns.check_notempty(gh, 'tag')
        ns.check_default(config.GitHub, 'token', '')

    # Check server configuration
    if src.srctype == 'udl':
        check_server(config)


def check_server(config):
    """ Check UDL -> XML server configuration """
    
    # Make sure a section is present; it may not be, as every
    # setting here has a default.
    svr = ns.get_section(config, 'Server')
    if svr is None:
        svr = config.Server = ns.Namespace()
    
    # Make sure default values are present
    ns.check_default(svr, 'host', 'localhost')
    ns.check_default(svr, 'port', '52773')
    ns.check_default(svr, 'user', 'SuperUser')
    ns.check_default(svr, 'password', 'SYS')
    ns.check_default(svr, 'namespace', 'USER')
    ns.check_default(svr, 'https', False)
    
    if 'take_from' in svr:
        raise ConfigurationError("Setting take_from no longer supported." \
            " Use augment_from in section Local instead.")


def check_csp(config:ns.Namespace):
    """ Checks the CSP configuration """

    csp = ns.check_section(config, 'CSP')
    ns.check_oneof(csp, 'export', ('embed', 'separate', 'none'), 'embed')
    if not csp.export == 'none':
        # Only check these if we are to export CSP files
        if ns.check_default(csp, 'parsers', []):
            msg = "At least one [[CSP.parsers]] section for CSP items should be present."
            raise ConfigurationError(msg)
        for i, parser in enumerate(csp.parsers):
            if not isinstance(parser, ns.Namespace):
                raise ConfigurationError(f'Parser {i+1} must be a section.')
            ns.check_notempty(parser, 'regex')
            ns.check_notempty(parser, 'app')
            ns.check_notempty(parser, 'item')
            ns.check_oneof(parser, 'nomatch', ('skip', 'error'), 'error')
    
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
        format='%(message)s', force=True)


def setup_logging(config):
    """ Final logging setup: allow log location override in config """

    logdir:str = config.Local.logdir
    loglevel:str = config.Local.loglevel

    # Determine filename (without path)
    base, ext = splitext(basename(config.cfgfile))
    if ext.lower() == '.toml':
        logfile = f'{base}.log'
    else:
        logfile = f'{base}{ext}.log'

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
    now = str(datetime.datetime.now()).split('.')[0] # pylint:disable=use-maxsplit-arg
    logging.info("\n\n===== Starting at %s", now)
    
# =====

def unhandled_exception(exc_type, exc_value, exc_traceback):
    """ Handle otherwise unhandled exceptions by logging them """

    if exc_type == ConfigurationError:
        msg = exc_value.args[0]
        logging.error("\n%s", msg)
    else:
        msg = f"An error occurred; please see the log file for details.\n\n{exc_value}"
        exc_info = exc_type, exc_value, exc_traceback
        logging.exception("\n##### Unhandled exception:", exc_info=exc_info)
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

# Command line overrides for values in the configuration file
ARGS = [
    {
        'name': 'github_tag',
        'path': 'GitHub.tag',
        'argparse': (
            ["--github-tag"],
            {
                'default': '',
                'help': "Override tag/branch to retrieve on GitHub"
            }
        )
    }
]

def parse_args():
    """Parse command line arguments."""

    parser = argparse.ArgumentParser()
    parser.add_argument("config",
       help="The (TOML) configuration file to use")
    parser.add_argument("--no-gui", action='store_true',
       help="Do not display a message box on completion.")
    
    # Add command line overrides
    for arg in ARGS:
        names, kwargs = arg['argparse']
        parser.add_argument(*names, **kwargs)

    # Replace stdout/stderr to capture argparse output
    sys.stdout = StringIO()
    sys.stderr = StringIO()
    
    # Check command line
    try:
        args = parser.parse_args()

    except SystemExit:
        # Get argparse output; either an error message in stderr, or
        # a usage message in stdout.
        msg, err = sys.stderr.getvalue(), True
        if not msg:
            msg = sys.stdout.getvalue()
            err = False
        
        # Show error or usage and exit
        msgbox(msg, err)
        raise

    finally:
        # Restore stdout/stderr
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
    
    cfgfile = args.config
    if not isabs(cfgfile) and not exists(cfgfile):
        cfgfile = join(dirname(__file__), cfgfile)
    
    if not exists(cfgfile) or not isfile(cfgfile):
        msgbox(f"Error: file {args.config} not found.\n\n{parser.format_help()}", True)
        sys.exit(1)
    
    if not isabs(cfgfile):
        cfgfile = abspath(cfgfile)
    
    args.config = cfgfile

    return args
