import os
from contextlib import contextmanager
from os.path import join, exists
from itertools import tee, filterfalse

# from https://docs.python.org/3/library/itertools.html#itertools-recipes
def partition(pred, iterable):
    'Use a predicate to partition entries into false entries and true entries'
    # partition(is_odd, range(10)) --> 0 2 4 6 8   and  1 3 5 7 9
    t1, t2 = tee(iterable)
    return filterfalse(pred, t1), filter(pred, t2)


# REFACT: rename changeD_work*
@contextmanager
def change_working_directory_to(directory):
    old_cwd = os.getcwd()
    os.chdir(directory)
    yield
    os.chdir(old_cwd)

def looks_like_attic_directory(directory):
    return exists(join(directory, 'README')) and exists(join(directory, 'config'))

def same_file_system(path1, path2):
    dev1 = os.stat(path1).st_dev
    dev2 = os.stat(path2).st_dev
    return dev1 == dev2
