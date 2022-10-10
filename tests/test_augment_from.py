"""
Tests the [Local] augment_from setting.
"""

import pytest

import namespace as ns


# Base configuration
CFG = """
[Source]
type = "directory"
[Directory]
path = '{path}'
[Local]
outfile = 'out.xml'
augment_from = 'ovr.toml'
"""

# Some overrides to merge-in
OVR = """
[Source]
type = "github"
[GitHub]
user = 'a'
repo = 'b'
tag = 'main'
[Local]
outfile = 'out2.xml'
"""


@pytest.mark.usefixtures("reload_modules")
def test_augment(tmp_path, get_config):
    """ Tests overriding directory settings using augment_from setting """
    
    # Write override toml
    ovr = tmp_path / 'ovr.toml'
    with open(ovr, 'wt', encoding="UTF-8") as f:
        f.write(OVR)
    
    # Get the parsed and augmented configuration settings
    cfg = get_config(CFG, tmp_path)
    
    assert cfg.Source.type == 'github', "Override not applied to Source.type"
    assert cfg.GitHub.user == 'a', "Setting GitHub.user not correct"
    assert cfg.GitHub.repo == 'b', "Setting GitHub.repo not correct"
    assert cfg.GitHub.tag == 'main', "Setting GitHub.tag not correct"
    assert cfg.Local.outfile == 'out2.xml', "Setting Local.outfile not updated"
    

@pytest.mark.usefixtures("reload_modules")
def test_augment_ovr(tmp_path, get_config):
    """ Tests recursive override error """
    
    # Write override toml with another augment_from setting
    ovr = tmp_path / 'ovr.toml'
    with open(ovr, 'wt', encoding="UTF-8") as f:
        f.write(OVR+"augment_from='abcde'")
    
    # Make sure this raises a configuration error
    with pytest.raises(ns.ConfigurationError) as e:
        get_config(CFG, tmp_path)
    
    # Check the error message
    msg:str = e.value.args[0]
    assert msg == "Recursive augment_from not supported", f"Unexpected message {msg}"


@pytest.mark.usefixtures("reload_modules")
def test_take_from_error(tmp_path, get_config):
    """ Tests error message on removed setting """
    
    # Write (empty) override toml
    ovr = tmp_path / 'ovr.toml'
    with open(ovr, 'wt', encoding="UTF-8") as f:
        f.write("")
    
    # Make sure this raises a configuration error
    with pytest.raises(ns.ConfigurationError) as e:
        get_config(CFG+"[Server]\ntake_from='xxx'\n", tmp_path)
    
    # Check the error message
    msg:str = e.value.args[0]
    assert "Setting take_from no longer supported" in msg, f"Unexpected message {msg}"
