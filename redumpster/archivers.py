from logging import getLogger
from os.path import join, abspath, normpath
import os
import sh

from .data_interfaces import DataInterface
from .utils import change_working_directory_to, looks_like_attic_directory, partition

class UnknownAtticArchive(Exception):
    pass

# REFACT: rename DirectoryArchiver
class Archiver(object):
    def __init__(self, directory, data_interfaces, sh=sh):
        self.log = getLogger(__name__)
        self.directory = abspath(normpath(directory))
        self.data_interfaces = data_interfaces
        self.sh = sh
    
    @classmethod
    def with_data_interfaces(cls, directory, sh=sh, **data_interface_spec):
        data_interfaces = []
        
        for name, options in data_interface_spec.items():
            data_interface = DataInterface.make_data_interface(name, options)
            data_interfaces.append(data_interface)
        return cls(directory, data_interfaces, sh=sh)
    
    def dump_all(self):
        for data_interface in self.data_interfaces:
            data_interface.dump()
            data_interface.write_dump_config()
    
    def commit(self):
        for data_interface in self.data_interfaces:
            name = data_interface.dump_name()
            source = data_interface.directory + '/'
            self.commit_data_interface(name, source)
    
    def _files_to_archive_in_directory(self, directory):
        files = os.listdir(directory)
        other, symlinks = partition(lambda f: os.path.islink(join(directory, f)), files)
        symlinks = [os.readlink(join(directory, link)) for link in symlinks]
        files = sorted(symlinks + list(other))
        return files
    
    def commit_data_interface(self, name, source):
        destination = join(self.directory, name)
        files = self._files_to_archive_in_directory(source)
        os.mkdir(destination)
        
        with change_working_directory_to(source):
            files.append(destination)
            self.sh.rsync(
                archive=True, acls=True, xattrs=True, numeric_ids=True, relative=True,
                *files
            )
    

class AtticArchiver(Archiver):
    def commit(self):
        if not looks_like_attic_directory(self.directory):
            self.sh.attic('init', self.directory)
        
        super().commit()
    
    def commit_data_interface(self, name, source):
        archive_name = "{0}::{1}".format(self.directory, name)
        files = self._files_to_archive_in_directory(source)
        
        with change_working_directory_to(source):
            
            self.sh.attic('create', archive_name, *files)
