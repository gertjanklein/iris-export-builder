from __future__ import annotations

import logging

from config import get_config, ConfigurationError, msgbox
from split_export import get_files, ExportFile
from repo import RepositorySourceItem
from convert import setup_session, cleanup, convert
from deployment import add_deployment


def main():
    # Get configuration and handle command line arguments
    config = get_config()
    run(config)
    cleanup()


def run(config):
    # Setup basic auth handler for IRIS, if we need to convert UDL to XML
    if config.Source.srctype == 'udl':
        setup_session(config)

    # Get object representing repo
    repo = get_repo(config)

    # Get list of files to create, with their items
    files = get_files(config, repo)

    # Convert item data from UDL to XML, if needed
    if config.Source.srctype == 'udl':
        convert_udl(config, files)

    # Append export notes to make export usable as a deployment 
    if config.Local.deployment:
        export = files[0]
        # Create the export element
        export.create_export()
        # Add elements with deployment information
        logging.info('Adding deployment items')
        add_deployment(config, repo.name, export.root)
    
    # Export each 1..n files in turn:
    for export_file in files:
        export_file.write()
    
    # Give some feedback
    total = sum(len(f.items) for f in files)
    logmsg= f"\nDone; exported {total} items to {len(files)} files.\n"
    logging.info(logmsg)
    if not config.no_gui:
        msgbox(logmsg)


def convert_udl(config, exports:list[ExportFile]):
    """ Converts all items from UDL to XML, where needed """

    to_convert = []
    for ef in exports:
        for item in ef.items:
            if item.kind != 'src':
                continue
            assert isinstance(item, RepositorySourceItem)
            if not item.is_udl:
                continue
            to_convert.append(item)
    convert(config, to_convert, config.Local.threads)


def get_repo(config):
    """Returns the configured repository."""

    if config.Source.type == 'github':
        from github import get_data
    elif config.Source.type == 'directory':
        from fsrepo import get_data
    else:
        raise ConfigurationError(f"Invalid repository type '{config.Source.type}' in configuration.")
    return get_data(config)


if __name__ == '__main__':
    main()
    
    

