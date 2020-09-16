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
line. It takes no other commandline arguments. For details of what can
be specified in the  configuration file, see file template.toml. The
syntax is [toml](https://toml.io/en/), an ini-like language for use in
configuration files.

The configuration file has the following sections:

### Source

This section configures the specifics of the location to take the
sources from. The type ("github" or "directory") and source type ("xml"
or "udl") determine which of the remaining sections are relevant. Other
configuration settings include the source file encoding, and where in
the checkout to find CSP and source files.

### CSP

This section further configures how CSP items are handled, and is only
consulted when Source.cspdir is nonempty. This main section configures
how the CSP export is to be done: embedded in the main export, or as a
separate file. One or more subsections called CSP.parsers can be specified
that specify how to deal with individual items.

### CSP.parsers

One or more of this subsection can occur. The main goal of these
sections to specify how to split a CSP item into an application and item
part; this is required by the IRIS export format. The parsers specify a
regular expression to match against, and are tried in turn. Parsers can
specify that they must match; if they then don't, a configuration error
is raised.

If no parser matches an item, and none specifies a match is required, the
item will simply be skipped. This will be logged in the logfile.

A default parser is present in the template configuration, that attempts
to guess how to split off the application. An application-specific parser
is probably better.

### GitHub

If the sources to create an export for reside on GitHub, this section
specifies how and where to get them. The GitHub user and repository
name, and what to checkout are the minimum required values. For private
repositories, a security token can be specified.

### Directory

If the sources reside on the local filesystem (e.g., a Subversion
checkout), this section specifies where to find them.

### Server

If the source is in UDL format, it must be converted to XML before it
can become part of an export. A Caché (2017+) or IRIS server is needed
to do this conversion. This section specifies details of the server to
connect to: hostname or IP address, port, credentials, namespace.

### Local

This section specifies details about the export to build. It configures
the name of the export, and whether to make it a deployment or not.

## Usage

The program is a (non-console) python script. It uses the
[toml](https://pypi.org/project/toml/) and
[lxml](https://pypi.org/project/lxml/) libraries.

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
