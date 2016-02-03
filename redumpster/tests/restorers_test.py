from ..restorers import *
from ..data_interfaces import NoOp, UnknownDataInterfaceError

from textwrap import dedent

from pyexpect import expect
import unittest
from testfixtures import tempdir
from unittest.mock import MagicMock


'''
class RestoreFromDirectoryTest(unittest.TestCase):
    def test_should_identify_multiple_backups(self):
        expect(RestoreFromDirectory.available_backups(None, 'fnord', ['a', 'fnord-23', 'foobar-blub', 'fnord-42'])) == ['fnord-23', 'fnord-42']
        expect(RestoreFromDirectory.available_backups(None, 'fnord', [])) == []
    
    def test_should_determine_valid_backup_names(self):
        expect(RestoreFromDirectory._is_valid_backup_name('fnord-lala-2015-01-20_14-24-29')) == True
        expect(RestoreFromDirectory._is_valid_backup_name('a--2015-01-20_14-24-29')) == True
        
        expect(RestoreFromDirectory._is_valid_backup_name('a-2015-01-20_14-24-29')) == False
        expect(RestoreFromDirectory._is_valid_backup_name('-2015-01-20_14-24-29')) == False
        expect(RestoreFromDirectory._is_valid_backup_name('a2015-01-20_14-24-29')) == False
        expect(RestoreFromDirectory._is_valid_backup_name('2015-01-20_14-24-29')) == False
        expect(RestoreFromDirectory._is_valid_backup_name('fnord-20a5-01-20_14-24-29')) == False
        expect(RestoreFromDirectory._is_valid_backup_name('fnord-205-01-20_14-24-29')) == False
        expect(RestoreFromDirectory._is_valid_backup_name('fnord-205-01-20_14-24-29a')) == False
        expect(RestoreFromDirectory._is_valid_backup_name('')) == False
    
    def test_should_choose_best_backup(self):
        expect(RestoreFromDirectory.best_backup_from_set(['fnord-lala-2015-01-20_14-24-29', 'fnord-lala-2015-01-20_16-24-29'])) == 'fnord-lala-2015-01-20_16-24-29'
        expect(RestoreFromDirectory.best_backup_from_set(['fnord-lala-2015-01-20_16-24-29'])) == 'fnord-lala-2015-01-20_16-24-29'
        expect(lambda: RestoreFromDirectory.best_backup_from_set(['fnord-moo-2015-01-20_14-24-29', 'fnord-lala-2015-01-20_16-24-29'])
            ).raises(UnknownBackupError)
        expect(lambda: RestoreFromDirectory.best_backup_from_set(['a2015-01-20_16-24-29'])
            ).raises(UnknownBackupError)
        expect(lambda: RestoreFromDirectory.best_backup_from_set([])).raises(UnknownBackupError)
    
    def test_should_instantiate_data_interface(self):
        restorer = RestoreFromDirectory('.', 'noop--2015-01-20_16-24-29')
        expect(restorer.data_interface).isinstance(NoOp)
        expect(restorer.data_interface.timestamp) == '2015-01-20_16-24-29'
        
        expect(lambda: RestoreFromDirectory('.', 'fnord--2015-01-20_16-24-29')).raises(UnknownDataInterfaceError)
    
    @tempdir()
    def test_should_copy_dump_config_to_data_interface(self, tempdir):
        backup_dir = os.path.join(tempdir.path, 'noop--2015-01-20_16-24-29')
        os.mkdir(backup_dir)
        dump_conf = open(os.path.join(backup_dir, 'dump.conf'), 'w')
        dump_conf.write('[options]\n  foo=bar')
        dump_conf.close()
        
        restorer = RestoreFromDirectory(tempdir.path, 'noop--2015-01-20_16-24-29')
        restorer.restore()
        expect(restorer.data_interface.config['options']['foo']) == 'bar'
        
        # cleanup
        os.unlink(join(restorer.data_interface.directory, 'dump.conf'))
        os.rmdir(restorer.data_interface.directory)
        
        # should allow overriding options
        restorer.restore(override_options=dict(foo='otherfoo'))
        expect(restorer.data_interface.config['options']['foo']) == 'otherfoo'
    
    def test_should_parse_additional_restore_options(self):
        expect(RestoreFromDirectory.parse_restore_options([])) == dict()
        expect(RestoreFromDirectory.parse_restore_options(['a=b'])) == dict(a='b')
        expect(RestoreFromDirectory.parse_restore_options(['a=b', 'b=f'])) == dict(a='b', b='f')
        expect(RestoreFromDirectory.parse_restore_options(['c=d=f==g'])) == {'c': 'd=f==g'}
        expect(lambda: RestoreFromDirectory.parse_restore_options(['a'])).raises(AssertionError)
        expect(lambda: RestoreFromDirectory.parse_restore_options(['a=b', 'a=f'])).raises(AssertionError)

class RestoreFromAtticTest(unittest.TestCase):
    def test_should_list_archives(self):
        sh = MagicMock()
        sh.attic.return_value = dedent("""\
            fnord-2015-01-20_14-24-29                  Tue Jan 20 15:24:49 2015
            blala-2015-01-20_16-24-29                  Tue Jan 20 15:24:49 2015
            grumpf-2015-01-20_13-24-29                  Tue Jan 20 15:24:49 2015
        """)
        expect(RestoreFromAttic._backups_in_directory('ignored', sh=sh)) == [
            'blala-2015-01-20_16-24-29', 'fnord-2015-01-20_14-24-29', 'grumpf-2015-01-20_13-24-29']
    
    def test_should_list_no_archive(self):
        sh = MagicMock()
        sh.attic.return_value = dedent("\n")
        expect(RestoreFromAttic._backups_in_directory('ignored', sh=sh)) == []
    
    def test_should_mount_attic_to_restore(self):
        sh = MagicMock()
        attic = RestoreFromAttic('/backup_dir', 'noop--2015-01-20_13-24-29', sh=sh)
        attic._wait_until_mounted = lambda *args: True
        expect(sh.attic.called) == False
        attic._restore_backup_to_tempdir(should_mount=True)
        
        expect(sh.attic.called) == True
        args, kwargs = sh.attic.call_args
        expect(args).has_length(3)
        expect(args[0]) == 'mount'
        expect(args[1]) == '/backup_dir::noop--2015-01-20_13-24-29'
        expect(args[2].endswith('/restore_from')) == True
    
    def test_should_extract_to_restore(self):
        sh = MagicMock()
        attic = RestoreFromAttic('/backup_dir', 'noop--2015-01-20_13-24-29', sh=sh)
        expect(sh.attic.called) == False
        attic._restore_backup_to_tempdir(should_mount=False)
        
        expect(sh.attic.called) == True
        args, kwargs = sh.attic.call_args
        expect(args).has_length(2)
        expect(args[0]) == 'extract'
        expect(args[1]) == '/backup_dir::noop--2015-01-20_13-24-29'
    
    def test_should_unmount_on_clean_up(self):
        sh = MagicMock()
        attic = RestoreFromAttic('/backup_dir', 'noop--2015-01-20_13-24-29', sh=sh)
        attic._wait_until_mounted = lambda *args: True
        attic._restore_backup_to_tempdir(should_mount=True)
        
        expect(sh.fusermount.called) == False
        attic.cleanup()
        expect(sh.fusermount.called) == True
        args, kwargs = sh.fusermount.call_args
        expect(args).has_length(2)
        expect(args[0]) == '-u'
        expect(args[1].endswith('/restore_from')) == True
    

from ..archivers import Archiver, AtticArchiver
from nose.plugins.attrib import attr

@attr('slow')
class RoundTripIntegrationTest(unittest.TestCase):
    
    def _assert_can_restore_file_with(self, archiver, restorer, tempdir):
        backup_dir = os.path.join(tempdir.path, 'backup_dir')
        actual_data = join(tempdir.path, 'actual_dir')
        os.mkdir(actual_data), os.mkdir(backup_dir)
        
        important_file = join(actual_data, 'data.txt')
        open(important_file, 'w').write('hello world')
        
        archiver = archiver.with_data_interfaces(backup_dir,
            copydir=dict(source=actual_data, name='test'))

        archiver.dump_all()
        archiver.commit()
        
        os.unlink(important_file)
        os.rmdir(actual_data)
        
        available_backups = restorer.available_backups(backup_dir, 'copydir-test')
        expect(available_backups).has_length(1)
        best_backup = restorer.best_backup_from_set(available_backups)
        
        expect(os.path.exists(important_file)) == False
        
        backup = restorer(backup_dir, best_backup)
        try:
            backup.restore()
        finally:
            backup.cleanup()
        
        expect(os.path.exists(important_file)) == True
        expect(open(important_file).read()) == 'hello world'

    @tempdir()
    def test_should_round_trip_on_directory(self, tempdir):
        self._assert_can_restore_file_with(
            archiver=Archiver,
            restorer=RestoreFromDirectory,
            tempdir=tempdir,
        )
    
    @tempdir()
    def test_should_round_trip_on_attic(self, tempdir):
        self._assert_can_restore_file_with(
            archiver=AtticArchiver,
            restorer=RestoreFromAttic,
            tempdir=tempdir,
        )
'''
