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

def test_del():
    cfg = ns.Namespace()
    cfg.attr = ''
    assert 'attr' in cfg
    del cfg.attr
    assert 'attr' not in cfg

def test_get_in_path():
    cfg = ns.Namespace()
    assert ns.get_in_path(cfg, 'Section.value') is None
    assert ns.get_in_path(cfg, 'Section.value', '') == ''
    cfg.Section = ns.Namespace()
    assert ns.get_in_path(cfg, 'Section.value') is None
    assert ns.get_in_path(cfg, 'Section.value', '') == ''
    cfg.Section.value = '42'
    assert ns.get_in_path(cfg, 'Section.value') == '42'
    cfg.Section = ''
    assert ns.get_in_path(cfg, 'Section.value') is None
    
