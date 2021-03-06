from ..data_interfaces import *
from os.path import join, exists
import os

from testfixtures import tempdir, log_capture
from pyexpect import expect
import unittest
from unittest.mock import MagicMock

from redumpster.utils import change_working_directory_to

def touch(a_path):
     open(a_path, 'a').close()

class DataInterfaceFactoryTest(unittest.TestCase):
    
    def test_should_instantiate_multiple_interfaces(self):
        config = dict(
            foo=dict(
                interface_name='noop',
            ),
            bar=dict(
                interface_name='noop',
            )
        )
        interfaces = interfaces_from_config(config, 'fnord')
        expect(interfaces).has_length(2)
        expect(interfaces[0]).isinstance(NoOp)
        directories = sorted(i.directory for i in interfaces)
        expect(directories[0].endswith('fnord/bar')).equals(True)
        expect(directories[1].endswith('fnord/foo')).equals(True)
    
    def test_should_filter_interfaces_by_tags(self):
        from collections import OrderedDict # easier to test if iteration order isn't randomly different…
        config = OrderedDict()
        config['first'] = dict(interface_name='noop', tags=['foo', 'bar'])
        config['second'] = dict(interface_name='noop', tags=['bar'])
        config['third'] = dict(interface_name='noop', tags=['foo'])
        
        interfaces = interfaces_from_config(config, 'unused_directory', tag='foo')
        expect(interfaces).has_length(2)
        expect(interfaces[0].backup_name) == 'first'
        expect(interfaces[1].backup_name) == 'third'
        
        interfaces = interfaces_from_config(config, 'unused_directory', tag='bar')
        expect(interfaces).has_length(2)
        expect(interfaces[0].backup_name) == 'first'
        expect(interfaces[1].backup_name) == 'second'
        
        # ensure other parsing of tags works too
        config = OrderedDict()
        config['first'] = dict(interface_name='noop', tags='foo, bar')
        config['second'] = dict(interface_name='noop', tags='bar')
        config['third'] = dict(interface_name='noop', tags='foo')
        
        interfaces = interfaces_from_config(config, 'unused_directory', tag='foo')
        expect(interfaces).has_length(2)
        expect(interfaces[0].backup_name) == 'first'
        expect(interfaces[1].backup_name) == 'third'
        
        interfaces = interfaces_from_config(config, 'unused_directory', tag='bar')
        expect(interfaces).has_length(2)
        expect(interfaces[0].backup_name) == 'first'
        expect(interfaces[1].backup_name) == 'second'

class DataInterfaceTest(unittest.TestCase):
    
    def test_should_make_data_interfaces(self):
        data_interface = DataInterface.make_data_interface(
            'dir', 'noop', 'fnord', dict(foo='bar'))
        expect(data_interface).isinstance(NoOp)
        expect(data_interface.directory) == 'dir/fnord'
        expect(data_interface.config['options']) == dict(foo='bar', name='')
    
    def test_should_raise_on_missing_data_interfaces(self):
        expect(lambda: DataInterface.make_data_interface(None, None, None, None)).raises(UnknownDataInterfaceError)
    
    @tempdir()
    def test_should_create_its_directory_if_it_does_not_exist(self, tempdir):
        destination = join(tempdir.path, 'foo', 'bar', 'baz')
        data_interface = DataInterface(destination, dict(foo='bar'))
        
        expect(exists(destination)) == False
        data_interface.dump()
        expect(exists(destination)) == True

class MySQLDumpTest(unittest.TestCase):
    
    def setUp(self):
        super().setUp()
        self.sh = MagicMock()
    
    def test_should_call_dump(self):
        dump = MySQLDump(directory='.', options=dict(mysql_user='foo', mysql_password='bar'), sh=self.sh)
        
        expect(self.sh.mysqldump.called) == False
        dump.dump()
        expect(self.sh.mysqldump.called) == True
        
        args, kwargs = self.sh.mysqldump.call_args
        expect(kwargs).has_subdict(
            password='bar',
            user='foo',
        )
    
    def test_should_not_provide_password(self):
        dump = MySQLDump(directory='.', options=dict(mysql_user='foo', mysql_password=''), sh=self.sh)
        
        dump.dump()
        args, kwargs = self.sh.mysqldump.call_args
        expect(kwargs).has_subdict(
            password=False,
        )
    
    def test_should_restore(self):
        dump = MySQLDump(directory='.',
            options=dict(mysql_user='foo', mysql_password='bar'),
            sh=self.sh)
        
        expect(self.sh.mysql.called) == False
        dump.restore()
        expect(self.sh.mysql.called) == True
        
        args, kwargs = self.sh.mysql.call_args
        expect(kwargs).has_subdict(
            execute="source ./dump.sql",
            password='bar',
            user='foo',
        )

    def test_should_provide_command_before_mysqldump(self):
        dump = MySQLDump(directory='/',
            options=dict(
                mysql_user='foo', mysql_password='bar',
                dump_command_prefix='ssh fnord',
            ), sh=self.sh)
        
        expect(self.sh.Command.called) == False
        dump.dump()
        self.sh.Command('ssh').bake('fnord').mysqldump.assert_called_once_with(
            '--all-databases', '--complete-insert',
            user='foo', password='bar',
            _out='/dump.sql',
        )
    

class PostgreSQLDumpTest(unittest.TestCase):
    
    def setUp(self):
        super().setUp()
        self.sh = MagicMock()
    
    def test_should_dump(self):
        dump = PostgreSQLDump(directory='.', options=dict(postgres_username='foo'), sh=self.sh)
        
        expect(self.sh.pg_dumpall.called) == False
        dump.dump()
        expect(self.sh.pg_dumpall.called) == True
        
        args, kwargs = self.sh.pg_dumpall.call_args
        expect(kwargs).has_subdict(
            clean=True,
            username='foo',
        )
    
    def test_should_restore(self):
        dump = PostgreSQLDump(directory='.', options=dict(postgres_username='foo'), sh=self.sh)
        
        expect(self.sh.psql.called) == False
        dump.restore()
        expect(self.sh.psql.called) == True
        
        args, kwargs = self.sh.psql.call_args
        expect(kwargs).has_subdict(
            file="./dump.sql",
            username='foo',
        )
        expect(args).contains('postgres') # needs to start from the postgres db
    
    def test_should_provide_command_before_postgres_dump(self):
        options = dict(postgres_username='foo', dump_command_prefix='ssh fnord')
        dump = PostgreSQLDump(directory='/', options=options, sh=self.sh)
        
        expect(self.sh.Command.called) == False
        dump.dump()
        self.sh.Command('ssh').bake('fnord').pg_dumpall.assert_called_once_with(
            clean=True,
            username='foo',
            _out='/dump.sql',
        )
    

class DirectoryTest(unittest.TestCase):
    
    def setUp(self):
        super()
        """Lets have a safeguard, that we don't just delete our own home 
        directories when we fuck up something with rsync and run the testsuite."""
        original_default_rsync_args = self.original_default_rsync_args = CopyDirectory._default_rsync_args
        def safer(self):
            return { key: value for key, value 
                in original_default_rsync_args(self).items()
                if 'delete' not in key }
        CopyDirectory._default_rsync_args = safer
    
    def tearDown(self):
        CopyDirectory._default_rsync_args = self.original_default_rsync_args
    
    def test_ensure_default_args_to_rsync_are_safe(self):
        interface = CopyDirectory(directory='/foo', options=dict(source='/bar'))
        default_arguments = interface._default_rsync_args()
        for key in default_arguments.keys():
            expect(key).does_not.contain('delete')
    
    @tempdir()
    def test_should_hard_link_directory_to_copy(self, tempdir):
        production_directory = join(tempdir.path, 'production')
        backup_directory = join(tempdir.path, 'backup')
        
        source_file = join(production_directory, 'important_file')
        os.makedirs(production_directory)
        touch(source_file)
        
        dump = CopyDirectory(directory=backup_directory, options=dict(
            source=production_directory
        ))
        backup_file = join(backup_directory, 'important_file')
        expect(exists(backup_file)) == False
        expect(os.stat(source_file).st_nlink) == 1
        dump.dump()
        expect(exists(backup_file)) == True
        expect(os.stat(source_file).st_nlink) == 2
        expect(os.stat(backup_file).st_nlink) == 2
    
    @tempdir()
    def test_should_restore_copy(self, tempdir):
        production_directory = join(tempdir.path, 'production')
        backup_dir = join(tempdir.path, 'backup')
        restore = CopyDirectory(backup_dir, options=dict(
            source=production_directory
        ))
        
        os.makedirs(join(backup_dir, 'important_file'))
        
        expect(exists(join(production_directory, 'important_file'))) == False
        restore.restore()
        expect(exists(join(production_directory, 'important_file'))) == True
    
    @tempdir()
    def test_ensures_hard_link_path_is_always_absolute(self, tempdir):
        with change_working_directory_to(tempdir.path):
            
            production_directory = 'production'
            backup_directory = 'backup'
            
            os.makedirs(production_directory)
            source_file = join(production_directory, 'important_file')
            touch(source_file)
            
            dump = CopyDirectory(directory=backup_directory, options=dict(
                source=production_directory
            ))
            
            source_file = abspath(source_file)
            backup_file = abspath(join(backup_directory, 'important_file'))
            expect(exists(backup_file)) == False
            expect(os.stat(source_file).st_nlink) == 1
            dump.dump()
            expect(exists(backup_file)) == True
            expect(os.stat(source_file).st_nlink) == 2
            expect(os.stat(backup_file).st_nlink) == 2
    
    @tempdir()
    def test_will_overwrite_existing_data_in_redumpster_managed_directories(self, tempdir):
        with change_working_directory_to(tempdir.path):
            production_directory = 'production'
            backup_directory = 'backup'
            
            os.makedirs(production_directory)
            source_file = join(production_directory, 'important_file')
            touch(source_file)
            touch(join(tempdir.path, production_directory, '.redumpster_managed'))
            
            dump = CopyDirectory(directory=backup_directory, options=dict(
                source=production_directory
            ))
            dump.dump()
            
            os.remove(source_file) # ensure we don't write into the hardlinked file
            with open(source_file, 'w') as f:
                f.write('this is going to be overwritten by restore')
            
            dump.restore()
            
            with open(source_file) as f:
                expect(f.read()) == ''
    
    @tempdir()
    def test_will_remove_files_not_in_backup_in_redumpster_managed_directories(self, tempdir):
        # Dangerous this test is, as it actually deletes files from the disk.
        CopyDirectory._default_rsync_args = self.original_default_rsync_args
        
        with change_working_directory_to(tempdir.path):
            production_directory = 'production'
            backup_directory = 'backup'
            
            os.makedirs(production_directory)
            source_file = join(production_directory, 'important_file')
            touch(join(tempdir.path, production_directory, '.redumpster_managed'))
            
            dump = CopyDirectory(directory=backup_directory, options=dict(
                source=production_directory
            ))
            dump.dump()
            
            touch(source_file)
            dump.restore()
            expect(os.path.exists(source_file)).is_false()
