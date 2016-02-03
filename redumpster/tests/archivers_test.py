from ..archivers import *
from ..data_interfaces import NoOp
from os.path import join, exists
import os

import glob

from pyexpect import expect
import unittest
from testfixtures import tempdir
from unittest.mock import Mock, MagicMock

"""
class ArchiverTest(unittest.TestCase):
    def test_should_know_data_interfaces(self):
        archiver = Archiver.with_data_interfaces(
            '.',
            noop=dict(foo='bar')
        )
        expect(archiver.data_interfaces).has_length(1)
    
    def test_should_dump_all_children(self):
        data_interface = Mock(NoOp)
        archiver = Archiver('.', [data_interface])
        expect(data_interface.dump.called) == False
        expect(data_interface.write_dump_config.called) == False
        archiver.dump_all()
        expect(data_interface.dump.called) == True
        expect(data_interface.write_dump_config.called) == True
    
    @tempdir()
    def test_should_collect_all_directories_to_commit(self, tempdir):
        noop = NoOp(None, dict(), timestamp='bar')
        archiver = Archiver(tempdir.path, [noop])
        committed_noop = join(tempdir.path, 'noop--bar', 'dump.conf')
        expect(exists(committed_noop)) == False
        archiver.dump_all()
        archiver.commit()
        expect(exists(committed_noop)) == True
    
    @tempdir()
    def test_should_follow_symlinks_when_committing(self, tempdir):
        actual_data = join(tempdir.path, 'actual.dir')
        backup = join(tempdir.path, 'backup')
        os.mkdir(actual_data), os.mkdir(backup)
        
        expected = join(backup, 'copydir-*', actual_data[1:])
        archiver = Archiver.with_data_interfaces(backup, copydir=dict(source=actual_data))
        expect(glob.glob(expected)).has_length(0)
        archiver.dump_all()
        archiver.commit()
        expect(glob.glob(expected)).has_length(1)

class AtticArchiverTest(unittest.TestCase):
    @tempdir()
    def test_should_move_files_to_attic(self, tempdir):
        sh = MagicMock()

        actual_data = join(tempdir.path, 'actual.dir')
        backup = join(tempdir.path, 'backup')
        os.mkdir(actual_data), os.mkdir(backup)
        
        archiver = AtticArchiver.with_data_interfaces(backup, sh=sh, copydir=dict(source=actual_data))
        archiver.dump_all()
        expect(sh.attic.called) == False
        archiver.commit()
        expect(sh.attic.called) == True
        args, kwargs = sh.attic.call_args
        expect(args).has_length(4)
        expect(args[0]) == 'create'
        expect(args[1].startswith('%s::copydir--20' % backup)) == True
        expect(args[2]) == actual_data
        expect(args[3]) == 'dump.conf'
    
    @tempdir()
    def test_should_resolve_symlinks_when_creating_an_archive(self, tempdir):
        os.mkdir(join(tempdir.path, 'fnord1'))
        open(join(tempdir.path, 'fnord2'), 'w').close()
        os.symlink('/fnord3', join(tempdir.path, 'fnord4'))
        
        archiver = AtticArchiver(tempdir.path, ())
        expect(archiver._files_to_archive_in_directory(tempdir.path)) == ['/fnord3', 'fnord1', 'fnord2']
    
"""
