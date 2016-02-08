from configobj import ConfigObj
import datetime
from logging import getLogger
import os
from os.path import join, abspath, normpath, basename, isfile, expanduser
from os import path
import sh
import tempfile
from .utils import same_file_system

class UnknownDataInterfaceError(Exception):
    pass

def are_interface_options_tagged_with_tag(options, tag):
    return 'tags' in options and tag in options['tags']

def interfaces_from_config(config, directory, tag=''):
    interfaces = []
    for backup_name, options in config.items():
        interface_name = options['interface_name']
        if tag != '' and not are_interface_options_tagged_with_tag(options, tag):
            continue
        interfaces.append(DataInterface.make_data_interface(
            directory, interface_name, backup_name, options))
    return interfaces

class DataInterface(object):
    INTERFACE_NAME = 'data_interface'
    
    @classmethod
    def make_data_interface(cls, container_directory, data_interface_name, backup_name, options):
        if data_interface_name not in known_data_interfaces:
            raise UnknownDataInterfaceError("Unknown data_interface {0}".format(data_interface_name))
        interface_directory = join(container_directory, backup_name)
        return known_data_interfaces[data_interface_name](interface_directory, options)

    def __init__(self,
            # API options
            directory, options,
            # for mocking
            sh=sh):
        self.log = getLogger(__name__)
        self.directory = directory
        
        # REFACT rename to _options? shouldn't be accessed directly
        self.config = ConfigObj(
            dict(
                interface_name=self.INTERFACE_NAME,
                options=self.default_options(),
            )
        )
        if self.directory is not None:
            self.config.filename = join(self.directory, 'dump.conf')
        
        self.config.merge(dict(options=options or dict()))
        
        self.sh = sh
    
    @property
    def backup_name(self):
        # REFACT consider to save this separately? --mh
        return path.basename(self.directory)
    
    def default_options(self):
        return dict(name="")
    
    def options(self):
        options = dict()
        for key, value in self.config['options'].items():
            if key.startswith(self.INTERFACE_NAME + '_'):
                options[key[len(self.INTERFACE_NAME + '_'):]] = value
        return options
    
    def dump(self):
        if not path.exists(self.directory):
            os.makedirs(self.directory)
    
    def restore(self):
        pass

class NoOp(DataInterface):
    INTERFACE_NAME = 'noop'

class MySQLDump(DataInterface):
    INTERFACE_NAME = 'mysql'
    
    def default_options(self):
        return dict(
            super().default_options(),
            dump_command_prefix='',
            mysql_user='root', mysql_password='',
        )
    
    def options(self):
        options = super().options()
        if not options.get('password', None): # is this intentionally a test for falsyness? --mh
            options['password'] = False
        return options
    
    def dump(self):
        super().dump()
        dumpfile = join(self.directory, "dump.sql")
        
        sh = self.sh
        if self.config['options']['dump_command_prefix']:
            dump_command_prefix = self.config['options']['dump_command_prefix'].split()
            sh = sh.Command(dump_command_prefix[0]).bake(*dump_command_prefix[1:])
        
        sh.mysqldump(
            "--all-databases", "--complete-insert",
            _out=dumpfile,
            **self.options()
        )
    
    def restore(self):
        super().restore()
        dumpfile = join(self.directory, "dump.sql")
        
        self.sh.mysql(
            execute="source {0}".format(dumpfile),
            **self.options()
        )


class PostgreSQLDump(DataInterface):
    INTERFACE_NAME = 'postgres'
    
    def default_options(self):
        return dict(
            super().default_options(),
            username='root',
            dump_command_prefix='',
        )
    
    def dump(self):
        super().dump()
        dumpfile = join(self.directory, "dump.sql")
        
        sh = self.sh
        if self.config['options']['dump_command_prefix']:
            dump_command_prefix = self.config['options']['dump_command_prefix'].split()
            sh = sh.Command(dump_command_prefix[0]).bake(*dump_command_prefix[1:])
        
        sh.pg_dumpall(
            clean=True,
            _out=dumpfile,
            **self.options()
        )
    
    def restore(self):
        super().restore()
        dumpfile = join(self.directory, "dump.sql")
        
        self.sh.psql(
            'postgres',
            file=dumpfile,
            **self.options()
        )
    

class CopyDirectory(DataInterface):
    INTERFACE_NAME = 'copydir'
    
    def default_options(self):
        return dict(
            source=None,
        )
    
    def _default_rsync_args(self):
        return dict(archive=True, acls=True, xattrs=True, numeric_ids=True, delete_after=True)
    
    def dump(self):
        super().dump()
        source = normpath(abspath(self.config['options']['source'])) + '/'
        # path NEEDS to end in a '/' else rsync wouldn't copy the sources content, 
        # but instead work on the sourc directory.
        # also normpath removes any existing trailing slashes
        self.sh.rsync(source, self.directory, 
            link_dest=os.path.dirname(source),
            **self._default_rsync_args()
        )
    
    def should_restore_to_source(self):
        source = self.config['options']['source']
        try:
            os.makedirs(source)
        except FileExistsError:
            if isfile(join(source, '.redumpster_managed')):
                return True
            return False
        return True
    
    def restore(self, home='~'):
        super().restore()
        
        home = expanduser(home)
        if self.should_restore_to_source():
            restore_to = normpath(self.config['options']['source'])
        else:
            prefix = "redumpster_%s_" % (path.basename(self.directory) or 'copydir')
            restore_to = tempfile.mkdtemp(dir=home, prefix=prefix)
        
        self.sh.rsync(
            self.directory + '/', restore_to,
            **self._default_rsync_args()
        )
        self.log.info("Restored backup to %s.", restore_to)
        return restore_to
    

known_data_interfaces = dict(
    noop=NoOp,
    mysql=MySQLDump,
    postgres=PostgreSQLDump,
    copydir=CopyDirectory,
)
