""" Tests configuration file handling.
"""

from unittest.mock import patch

import pytest

import config
import namespace as ns


CFG = """
[Source]
type = "directory"
cspdir = '{cspdir}'
[Directory]
path = '{path}'
[Local]
outfile = 'out.xml'
"""


@pytest.mark.usefixtures("reload_modules")
def test_missing_config():
    """ Tests error message for missing config file """

    cfgfile = 'missing.toml'
    args = ['builder', cfgfile, '--no-gui']
    seen = False
    
    # Replacement for msgbox that checks the message that would be displayed
    def msgbox(msg, is_error=False):
        nonlocal seen
        seen = True
        msg = msg.split('\n', maxsplit=1)[0]
        assert msg == f"Error: file {cfgfile} not found.", f"Missing config file error message wrong: {msg}"
        assert is_error, "Error mode for msgbox not set."

    # Pass a missing config file name to the configuration parser
    with patch('sys.argv', args), patch('config.msgbox', msgbox):
        with pytest.raises(SystemExit) as e:
            cfg = config.get_config()
        code = e.value.args[0]
        assert code == 1, f"Exit code not 1 but {code}"
        assert seen, "msgbox not called"


@pytest.mark.usefixtures("reload_modules")
def test_logfile_name_toml(tmp_path):
    """ Tests logfile strips toml extension """

    # Create configuration with .toml extension
    toml = CFG.format(path=tmp_path, cspdir='')
    cfgfile = tmp_path / 'cfg.toml'
    with open(cfgfile, 'wt') as f:
        f.write(toml)

    args = ['builder', str(cfgfile), '--no-gui']
    with patch('sys.argv', args):
        cfg = config.get_config()

    log = tmp_path / 'cfg.log'
    assert log.exists(), "Logfile does not exist under expected name"


@pytest.mark.usefixtures("reload_modules")
def test_logfile_name_not_toml(tmp_path):
    """ Tests logfile leaves non-toml extension """

    # Create configuration with .toml extension
    toml = CFG.format(path=tmp_path, cspdir='')
    cfgfile = tmp_path / 'cfg.tml'
    with open(cfgfile, 'wt') as f:
        f.write(toml)

    args = ['builder', str(cfgfile), '--no-gui']
    with patch('sys.argv', args):
        cfg = config.get_config()

    log = tmp_path / 'cfg.tml.log'
    assert log.exists(), "Logfile does not exist under expected name"


@pytest.mark.usefixtures("reload_modules")
def test_CSP_section_check(tmp_path):
    """ Tests missing CSP section check """

    toml = CFG.format(path=tmp_path, cspdir='csp')
    cfgfile = tmp_path / 'cfg.tml'
    with open(cfgfile, 'wt') as f:
        f.write(toml)

    args = ['builder', str(cfgfile), '--no-gui']
    with patch('sys.argv', args):
        with pytest.raises(ns.ConfigurationError) as e:
            cfg = config.get_config()
        msg:str = e.value.args[0]
        assert msg.startswith("Section CSP not found"), f"Unexpected message {msg}"


@pytest.mark.usefixtures("reload_modules")
def test_CSPparsers_section_check(tmp_path):
    """ Tests missing CSP.parsers section check """

    toml = CFG.format(path=tmp_path, cspdir='csp')
    toml += '[CSP]'
    cfgfile = tmp_path / 'cfg.tml'
    with open(cfgfile, 'wt') as f:
        f.write(toml)

    args = ['builder', str(cfgfile), '--no-gui']
    with patch('sys.argv', args):
        with pytest.raises(ns.ConfigurationError) as e:
            cfg = config.get_config()
        msg:str = e.value.args[0]
        assert msg.startswith("At least one [[CSP.parsers]] section"), f"Unexpected message {msg}"


@pytest.mark.usefixtures("reload_modules")
def test_usage_msg():
    """ Tests that a usage message is displayed when no arguments supplied
    
    Not specifying anything on the commandline is an error, so the error
    flag to msgbox should be set, and the exit code should be 2 (this is
    determined by argparse).
    """
 
    args = ['builder']
    seen = False
    
    # Replacement for msgbox that checks the message that would be displayed
    def msgbox(msg, is_error=False):
        nonlocal seen
        seen = True
        msg = msg.split('\n', maxsplit=1)[0]
        assert msg.startswith("usage: builder"), f"Unexpected or missing usage message: {msg}"
        assert is_error, "Error mode for msgbox not set."

    # Pass a missing config file name to the configuration parser
    with patch('sys.argv', args), patch('config.msgbox', msgbox):
        with pytest.raises(SystemExit) as e:
            cfg = config.get_config()
        code = e.value.args[0]
        assert code == 2, f"Exit code not 2 but {code}"
        assert seen, "msgbox not called"
    

@pytest.mark.usefixtures("reload_modules")
def test_help_msg():
    """ Tests that a help message is displayed with argument --help
    
    This situation is not an error, so the error flag to msgbox should
    not be set, and the exit code should be 0.
    """
 
    args = ['builder', '--help']
    seen = False
    
    # Replacement for msgbox that checks the message that would be displayed
    def msgbox(msg, is_error=False):
        nonlocal seen
        seen = True
        msg = msg.split('\n', maxsplit=1)[0]
        assert msg.startswith("usage: builder"), f"Unexpected or missing usage message: {msg}"
        assert not is_error, "Error mode for msgbox set."

    # Pass a missing config file name to the configuration parser
    with patch('sys.argv', args), patch('config.msgbox', msgbox):
        with pytest.raises(SystemExit) as e:
            cfg = config.get_config()
        code = e.value.args[0]
        assert code == 0, f"Exit code not 0 but {code}"
        assert seen, "msgbox not called"
    