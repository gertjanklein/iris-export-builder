from __future__ import annotations

import logging

from config import get_config, ConfigurationError, msgbox
from split_export import get_files, ExportFile
from repo import RepositorySourceItem
from convert import setup_session, cleanup as cleanup_convert, convert
from deployment import add_deployment


def main():
    """ Get configuration and handle command line arguments """
    
    config = get_config()
    # Get object representing repo
    repo = get_repo(config)
    # Create the export file(s)
    run(config, repo)


def run(config, repo):
    """ Main entry point for code and tests """
    
    # Setup basic auth handler for IRIS, if we need to convert UDL to XML
    if config.Source.srctype == 'udl':
        setup_session(config)

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
    cleanup()
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
    elif config.Source.type == 'bitbucket':
        from bitbucket import get_data
    elif config.Source.type == 'directory':
        from fsrepo import get_data
    else:
        msg = f"Invalid repository type '{config.Source.type}' in configuration."
        raise ConfigurationError(msg)
    return get_data(config)


def cleanup():
    """ Cleanup for subsequent runs """
    
    cleanup_convert()
    cleanup_logging()


def cleanup_logging():
    """ Closes all resources taken by the loggers' handlers """

    # Get root logger
    loggers = [logging.getLogger()]
    # Get all other loggers, if any
    logger_names = logging.root.manager.loggerDict # pylint: disable=no-member
    loggers = loggers + [logging.getLogger(name) for name in logger_names]

    # Call close() on each handler in each logger
    for logger in loggers:
        for handler in logger.handlers:
            handler.close()
        logger.handlers.clear()


if __name__ == '__main__':
    main()
    
    

