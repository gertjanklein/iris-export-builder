![Tests](https://github.com/gertjanklein/iris-export-builder/actions/workflows/run-pytest.yml/badge.svg)

# iris-export-builder

Creates a single Caché/IRIS export file from separate source files.

## Motivation

When rolling out a release to testing/acceptance/production, it is most
convenient to have a single file to deploy. For repeatability and
traceability, creating such a deployment directly from source control is
desirable. This tool is written to combine the separate sources in the
source control system into a single XML export file to be used for
deployment.

## Description

The tool can currently use two types of input: a local directory, and
GitHub. The local directory can be a checkout from any source control
system. Alternatively, releases can be downloaded and created directly
from a tag in a GitHub repository.

UDL sources can be converted to XML; this needs a Caché/IRIS server to
do the actual conversion.

Rudimentary support for converting the export into an Ensemble
production
[deployment](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=EGDV_deploying)
is present.

## Basic configuration

The program requires a configuration file to be specified on its command
line. The syntax is [toml](https://toml.io/en/), an ini-like language
for use in configuration files. A detailed description of the
configuration options can be found in
[doc/configuration.md](doc/configuration.md). A [template configuration
file](template.toml) is provided.

Currently, two commandline overrides are supported, that take precedence
over the values in the configuration file:

* **no-gui**: normally, a confirmation messagebox is displayed when the
  program has run successfully. This option disables this. This can be
  useful in automated pipelines.
* **--github-tag**: which tag/release to download from GitHub.

## Usage

The program is a (non-console) python script. It uses the
[toml](https://pypi.org/project/toml/),
[lxml](https://pypi.org/project/lxml/) and
[requests](https://pypi.org/project/requests/) libraries.

Releases, containing pre-built single file executables, can be found
[here](https://github.com/gertjanklein/iris-export-builder/releases).

It is easiest to create a shortcut to the program (either script or
binary) next to the configuration file, and drag and drop that on the
shortcut when you want to run the program with it.

When the program is done, a simple popup shows the number of items that
were added to the export, and the name of the export file. Creating the
export may take a while for large projects, especially if the sources
are in UDL format, as they then have to be converted to XML
individually. A log file is maintained, and each synchronized item is
listed there.

If an error occurs, a popup shows a simple description. The log file
usually has more details. Most likely errors are configuration file
syntax errors, wrong credentials, or connection errors.
