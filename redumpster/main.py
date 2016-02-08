#!/usr/bin/env python
#    <BACKUP_NAME> [<restore_options>...]

"""
Import, export, backup and update data.

Usage:
  redumpster [options] dump --config=<CONFIG> --to=<DUMP_DIR> --tagged=<TAG>
  redumpster [options] restore --config=<CONFIG> --from=<DUMP_DIR> --tagged=<TAG>
  redumpster -h | --help

Global Options:
     --tagged=<TAG>        Which tagged data interfaces to select for restoration or dumping. Default: ''
     --config=<CONFIG>     Configuration file that specifies what should be backed up.
                           
  -h --help                Show this screen.
  -v --verbose             Increase amount of output.
     --debug               Increase amount of output even more.

Dump Options:
     --to=<DUMP_DIR>       Directory to create backup in. Must be empty or non-existant.

Restore Options:
     --from=<RESTORE_DIR>  Backup directory to restore from.
     <restore_options>     Override options that were stored at backup time when restoring,
                           for example to change restore location or mysql credentials.
"""


import logging
import shutil
from os import path
from docopt import docopt
from configobj import ConfigObj
from .data_interfaces import interfaces_from_config

def main():
    arguments = docopt(__doc__, argv=None)
    
    level = logging.WARN
    if arguments['--verbose']:
        level = logging.INFO
    if arguments['--debug']:
        level = logging.DEBUG
        logging.getLogger('sh').setLevel(logging.INFO)
    else:
        logging.getLogger('sh').setLevel(logging.WARN)
    logging.basicConfig(level=level)
    
    
    assert path.exists(arguments['--config']), "No config file found"
    config = ConfigObj(arguments['--config'])
    if arguments['dump']:
        for interface in interfaces_from_config(config, arguments['--to'], tag=arguments['--tag']):
            interface.dump()
        shutil.copy2(arguments['--config'], path.join(arguments['--to']))
    
    if arguments['restore']:
        for interface in interfaces_from_config(config, arguments['--from'], tag=arguments['--tag']):
            interface.restore()
