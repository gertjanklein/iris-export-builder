import pytest
import namespace as ns

def test_set_in_path():
    cfg = ns.Namespace()
    ns.set_in_path(cfg, 'Testing.One.Two.Three.name', '42')
    assert cfg.Testing.One.Two.Three.name == '42'

def test_set_in_path_section_is_value():
    cfg = ns.Namespace()
    cfg.Section = ''
    with pytest.raises(ns.ConfigurationError):
        ns.set_in_path(cfg, "Section.name", '42')

def test_set_in_path_section_exists():
    cfg = ns.Namespace()
    cfg.Section = ns.Namespace()
    ns.set_in_path(cfg, "Section.name", '42')
    assert cfg.Section.name == '42'

