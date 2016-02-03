import os
from os.path import join, exists
import re
import sh
import shutil
import tempfile
from logging import getLogger

from .data_interfaces import DataInterface
from .utils import change_working_directory_to, looks_like_attic_directory

class UnknownBackupError(Exception):
    pass

class RestoreFromDirectory(object):
    log = getLogger(__name__)
    
    def __init__(self, backup_directory, backup_name, sh=sh):
        self.backup_directory = backup_directory
        self.backup_name = backup_name
        self.temporary_directory = tempfile.TemporaryDirectory()
        interface_directory = join(self.temporary_directory.name, 'restore_from')
        self.data_interface = self._make_data_interface(interface_directory)
        self.sh = sh
        
    @classmethod
    def _backups_in_directory(cls, backup_directory):
        if looks_like_attic_directory(backup_directory):
            cls.log.error("Looks like you are restoring from an Attic but forgot --attic?")
        return os.listdir(backup_directory)
    
    @classmethod
    def available_backups(cls, backup_directory, filter_prefix, dirlist=None):
        if dirlist is None or backup_directory is not None:
            dirlist = cls._backups_in_directory(backup_directory)
        
        available_backups = sorted(filter(
            lambda dir: dir.startswith(filter_prefix),
            dirlist
        ))
        cls.log.debug("Found available backups: %s", available_backups)
        return available_backups
    
    @classmethod
    def _parse_backup_name(cls, backup_name):
        parser = re.compile('([a-zA-Z0-9]+)-([a-zA-Z0-9-]*)-(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})')
        return parser.match(backup_name)
    
    @classmethod
    def _is_valid_backup_name(cls, backup_name):
        return cls._parse_backup_name(backup_name) is not None
    
    @classmethod
    def best_backup_from_set(cls, backup_names):
        if len(backup_names) == 0:
            raise UnknownBackupError("Did not find backup to determine best from.")
        
        def prefix(name):
            if not cls._is_valid_backup_name(name):
                raise UnknownBackupError("Invalid backup name: %s" % name)
            
            match = cls._parse_backup_name(name)
            return "%s-%s" % (match.group(1), match.group(2))
        
        prefixes = list(map(prefix, backup_names))
        if not all(map(lambda p: p==prefixes[0], prefixes)):
            raise UnknownBackupError("Ambigous backup names, not all match prefix %s" % prefixes[0])
        
        backup_names = sorted(backup_names, reverse=True)
        return backup_names[0]
    
    @classmethod
    def parse_restore_options(cls, options):
        parsed = dict()
        for option in options:
            split = option.split('=', maxsplit=1)
            assert len(split) == 2, "Option %r does not contain = sign" % option
            assert split[0] not in parsed, "Option %r is specified twice" % split[0]
            parsed[split[0]] = split[1]
        return parsed
    
    def _make_data_interface(self, temporary_directory):
        assert self._is_valid_backup_name(self.backup_name)
        interface, name, timestamp = self._parse_backup_name(self.backup_name).groups()
        return DataInterface.make_data_interface(interface, dict(), timestamp, temporary_directory)
    
    def _restore_backup_to_tempdir(self):
        source = join(self.backup_directory, self.backup_name)
        destination = self.data_interface.directory
        shutil.copytree(source, destination)
    
    def restore(self, override_options=dict()):
        self.log.info("Restoring backup at %s tagged %s.", self.backup_directory, self.backup_name)
        self._restore_backup_to_tempdir()
        self.data_interface.load_dump_config(override_options)
        self.data_interface.restore()
    
    def cleanup(self):
        pass

class RestoreFromAttic(RestoreFromDirectory):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mounts = []
    
    @classmethod
    def _backups_in_directory(cls, backup_directory, sh=sh):
        archives = str(sh.attic('list', backup_directory))
        archives = sorted(re.findall('^([^\s]+)', archives, re.MULTILINE))
        return archives
    
    def _should_mount(self):
        try:
            import llfuse
            return True
        except ImportError:
            return False
    
    def _wait_until_mounted(self, directory):
        dump_exists = lambda: exists(join(directory, 'dump.conf'))
        import time
        wait_iterations = 20
        while not dump_exists() and wait_iterations >= 0:
            time.sleep(0.3)
            wait_iterations -= 1
        assert dump_exists()
    
    def _restore_backup_to_tempdir(self, should_mount=None):
        if should_mount is None:
            should_mount = self._should_mount()
        
        backup_directory = os.path.abspath(self.backup_directory)
        source = "{0}::{1}".format(backup_directory, self.backup_name)
        destination = self.data_interface.directory
        
        os.mkdir(destination)
        if should_mount:
            # Unless we background this command, it will be killed in a weird way by sh
            # and then it's not mounted. Go figure...
            command = self.sh.attic('mount', source, destination, _bg=True)
            self.mounts.append(destination)
            self._wait_until_mounted(destination)
            command.wait()
        else:
            self.log.info("Extracting full backup to restore. Consider installing llfuse to improve performance.")
            with change_working_directory_to(destination):
                self.sh.attic('extract', source)
    
    def cleanup(self):
        for mount in self.mounts:
            self.sh.fusermount('-u', mount)
