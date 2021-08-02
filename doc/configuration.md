# Configuration

Program configuration is done with a configuration file. The file
location must be specified on the command line. To ease specifying new
configurations, a [template file](../template.toml) is provided. The
syntax is [toml](https://github.com/toml-lang/toml), an ini-like
language for use in configuration files.

There are several configuration sections in the file:

* [Source](#section-source): where and how to retrieve source files
* [CSP](#section-csp): how to handle CSP files (if any)
* [Data](#section-data): how to handle data files (if any)
* [GitHub](#section-github): how to handle sources on GitHub
* [Directory](#section-directory): how to handle sources on the
  filesystem
* [Server](#section-server): details about the UDL to XML conversion
  server
* [Local](#section-local): details about the output file, logging, etc.

## Section Source

* **type**: the location of the sources; can be `'github'` (configured
  under [GitHub](#section-github)) or `'directory'` (configured under
  [Directory](#section-directory)).

* **encoding**: the encoding of the sources. Should normally be `'UTF-8'`
  (which is the default). Can be any valid [Python encoding
  specifier](https://docs.python.org/3.9/library/codecs.html#standard-encodings).

* **srctype**: whether the sources are in `'udl'` (the default) or
  `'xml'`.

* **srcdir**: a path relative to the sources root where source files can
  be found, e.g. `'src'`.

* **cspdir**: if CSP files are present, they need to be placed in a
  separate directory, as they are handled differently than normal source
  files. A path relative to the sources root, e.g. `'csp'`. If empty, no
  handling of CSP files is done.

* **datadir**: if data files (e.g., lookup tables) are present, they
  need to be placed in a separate directory, as they are handled
  differently than normal source files. A path relative to the sources
  root, e.g. `'data'`.

* **skip**: a list (enclosed in square brackets) of items to exclude
  from the export. Items are specified as a path (including leading
  slash) from the sources root. Supports asterisk-style wildcards.
  Example: `['/src/tests/*','/data/Test_*.lut']`

## Section CSP

(This section and the CSP.parsers sections are only needed if CSP files
are present, i.e., the `cspdir` setting under [Source](#section-source)
is nonempty.)

Including CSP files in an XML export is somewhat challenging. In the
sources root, a CSP file is just a path and filename. However, in an XML
export, the path to the file is split into two parts: an _application_
and an _item name_. The first part describes the CSP application the
file belongs to, and the second part the path and filename _within that
application_.

The challenge, therefore, is to split a full path and filename from the
sources root, into an application and item. This is what the
[CSP.parsers](#section-cspparsers) subsections are intended for. There can be
one or more of these sections, which is denoted by them being enclosed
in double square brackets (i.e., `[[CSP.parsers]]`).

This general section has only one, general, option:

* **export**: how to export CSP items. There are three possible values:
  * `'embed'` (the default) places the items in the same export file as
    the source items.
  * `'separate'` creates a separate export file for the CSP items. It will
    have the same name as the source items export, with `_csp` appended.
  * `'none'` skips all CSP items.

### Section CSP.parsers

CSP parsers map the path of a CSP item in the source tree to an
application and item within that application. More than one of these
sections can be present; this is denoted by the double brackets that
surround the section in the configuration.

The parsers use a [regular
expression](https://en.wikipedia.org/wiki/Regular_expression) (specified
in **regex**) to determine which part of a CSP path is the application,
and which part the actual item. Note that replacements can be hardcoded
if needed. Some [examples](#examples) can be found below.

The settings for each parser are:

* **regex**: a regular expression to match against the item path.

* **app**: what to use as CSP application when the regex matches. Can be
  a back reference or a literal string. The application should start
  with a slash, and may not end with it.

* **item**: what to use as the item name within the application. Can be
  a back reference or a literal string. The item may not start with a
  slash.

* **nomatch**: what to do if this parser does not match the item. One of
  `'error'` to stop processing with an error message, or `'skip'` to
  continue with the next parser (if any). If the last parser doesn't
  match and specifies `'skip'`, the item in question will not be
  included in the export.

#### Examples

The default parser specified in the template configuration is this:

```toml
[[CSP.parsers]]
regex = '((/csp)?/[^/]+)/(.+)'
app = '\1'
item = '\3'
nomatch = 'error'
```

This splits:

* `/app/page.csp` in `/app` and `page.csp`
* `/app/sub/dir/page.csp` in `/app` and `sub/dir/page.csp`
* `/csp/app/dir/page.csp` in `/csp/app` and `dir/page.csp`

That is, it assumes the first part is the application, unless that part
is `csp`, in which case it uses the first two parts as application. In
both cases, anything left is used as the item name.

The parser above tries to be as universal as possible. In most cases,
there is only a single CSP application in a given configuration, with a
known path. In this case, assuming that CSP application is called
`/app`, the following configuration could be used:

```toml
[[CSP.parsers]]
regex = '/app/(.+)'
app = '/app'
item = '\1'
nomatch = 'error'
```

## Section Data

This section describes how data exports are handled. The is one setting:

* **export**: how to export data items. There are three possible values:
  * `'embed'` (the default) places the items in the same export file as
    the source items.
  * `'separate'` creates a separate export file for the data items. It
    will have the same name as the source items export, with `_data`
    appended.
  * `'none'` skips all data items.

## Section GitHub

This section describes where to find sources located on GitHub. They
will be downloaded automatically.

* **user**: the GitHub username, i.e. the repository owner

* **repo**: the GitHub repository name, i.e. the actual repository

* **tag**: the tag to get the sources for. This may be anything that
  GitHub supports, i.e. a tag, branch name, commit id, etc.

* **token**: if the GitHub repository is private, and a token is needed
  to access it, it can be placed here. Information about creating a
  GitHub access token can be found
  [here](https://docs.github.com/en/github/authenticating-to-github/keeping-your-account-and-data-secure/creating-a-personal-access-token).
  The token needs only `repo` permissions.
  
  If the value starts with an at-sign, it is interpreted as a path to a
  file containing the token. This can be useful to share the
  configuration file with others, without accidentally sharing a
  personal GitHub token. The path may be specified absolute, or relative
  to the configuration file.

## Section Directory

If sources are to be found in a filesystem directory, this section
specifies where exactly to find them. It has only one option:

* **path**: the path to the source files. If not an absolute path, it
  will be interpreted as relative to the configuration file.

## Section Server

The Server section is only needed if the sources are stored in UDL.
Exports are always XML, so these sources need to be converted. This is
done by calling an API on a Cache/IRIS server, in web application
`/api/atelier`. The credentials supplied (see below) should therefore be
sufficient to access that application.

Configuration options are:

* **host**: the hostname of the server; default is `'localhost'`.

* **port**: the webserver port of the server; default is `'52773'`.

* **namespace**: the namespace to perform the conversion in. Only
  matters if some namespaces are locked down; default is `'USER'`.

* **user**: username to use accessing the API; default is `'SuperUser'`.

* **password**: password to use accessing the API; default is `'SYS'`.

* **https**: whether to use HTTPS to access the server; boolean, default
  is `false`.

* **take_from**: file path (absolute or relative to the configuration
  file) containing (part of) the server details. Anything in this file
  will override the settings specified above. Not all settings need be
  present; the `[Server]` section header is not needed but allowed.

## Section Local

This section specifies where to create the export file, and what and
where to log.

* **outfile**: the name of the output file to create. This is a string
  supporting a few replacements:

  * `{name}`: will be replaced with the top-level directory in the
    filesystem or GitHub zip.
  * `{cfgname}`: will be replaced with the name (without extension) of the
    configuration file.
  * `{timestamp}`: will be replaced with the current date/time in format
    `YYYY-MM-DDThh-mm`.

* **deployment**: a boolean (default `false`) indicating whether the
  export should be created as an Ensemble deployment. This adds a Studio
  project, and a `ProjectTextDocument` XML element that Ensemble uses
  when processing a deployment. Importing a deployment has the advantage
  that an import log is maintained, and rollback functionality provided.
  Support for deployments here is minimal, though, as there is no
  documentation. Additionally, deployments do not support CSP items.

* **logdir**: the directory to place the log file in. Can be specified
  absolute or relative to the configuration file. The logfile itself has
  the same name as the configuration file, with a `.log` extension. If
  no directory is specified, the log file is placed adjacent to the
  configuration file.

* **loglevel**: the level of logging. Possible values are `'debug'`,
  `'info'`, `'warning'`, `'error'`, and `'critical'`. Note that most
  logging is done as `'info'` or `'debug'`.
