# Release notes

## Version 0.8

Version 0.8 switches to a different way of distributing the program.
Previous versions used a
[PyInstaller](https://pyinstaller.org/en/stable/index.html) [single file
executable](https://pyinstaller.org/en/stable/operating-mode.html#bundling-to-one-file).
This mode of operation is slightly slower than the alternative, with the
program and supporting files placed in a directory. Version 0.8 starts
using the latter way of distributing.

Further changes in this release:

- Add an option to use a built-in UDL to XML converter, using
  [iris-udl-to-xml](https://github.com/gertjanklein/iris-udl-to-xml).
  This can be especially useful in CI/CD pipelines, as an IRIS server is
  no longer required.
- Add a [sort](../doc/configuration.md#section-local) setting, allowing
  to sort items in the export file.
- Bugfix: actually use https if so configured.
- The embedded Python is upgraded to version 3.12.

## Version 0.7.1

This version adds support for loading sources from Bitbucket.

## Version 0.6

This version adds:

- The [augment_from](../doc/configuration.md#section-local) setting,
  allowing common system-specific settings to be maintained in a shared
  configuration file. This option replaces the `take_from` setting.
- The [export_version](../doc/configuration.md#section-local) (expert)
  setting, allowing to override the version number in the export file.
