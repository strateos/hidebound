from importlib import import_module
from pathlib import Path
import json
import os
import shutil
import sys

from hidebound.config import Config
import hidebound.database_tools as db_tools
from hidebound.specification_base import SpecificationBase
import hidebound.tools as tools
# ------------------------------------------------------------------------------


class Database:
    '''
    Generates a DataFrame using the files within a given directory as rows.
    '''
    @staticmethod
    def from_config(config):
        '''
        Constructs a Database instance given a valid config.

        Args:
            config (dict): Dictionary that meets Config class standards.

        Raises:
            DataError: If config is invalid.

        Returns:
            Database: Database instance.
        '''
        Config(config).validate()

        specs = []
        for path in config['specification_files']:
            sys.path.append(path)

            filepath = Path(path)
            filename = filepath.name
            filename, _ = os.path.splitext(filename)
            module = import_module(filename, filepath)

            specs.extend(module.SPECIFICATIONS)

        specs = list(set(specs))
        config['specifications'] = specs

        return Database(
            config['root_directory'],
            config['hidebound_parent_directory'],
            specifications=specs,
            include_regex=config['include_regex'],
            exclude_regex=config['exclude_regex'],
            write_mode=config['write_mode'],
        )

    @staticmethod
    def from_json(filepath):
        '''
        Constructs a Database instance from a given json file.

        Args:
            filepath (str or Path): Filepath of json config file.

        Returns:
            Database: Database instance.
        '''
        with open(filepath) as f:
            config = json.load(f)
        return Database.from_config(config)

    def __init__(
        self,
        root_dir,
        hidebound_parent_dir,
        specifications=[],
        include_regex='',
        exclude_regex=r'\.DS_Store',
        write_mode='copy',
    ):
        r'''
        Creates an instance of Database but does not populate it with data.

        Args:
            root_dir (str or Path): Root directory to recurse.
            hidebound_parent_dir (str or Path): Directory where hidebound
                directory will be created and hidebound data saved.
            specifications (list[SpecificationBase], optional): List of asset
                specifications. Default: [].
            include_regex (str, optional): Include filenames that match this
                regex. Default: None.
            exclude_regex (str, optional): Exclude filenames that match this
                regex. Default: '\.DS_Store'.
            write_mode (str, optional): How assets will be extracted to
                hidebound/data directory. Default: copy.

        Raises:
            TypeError: If specifications contains a non-SpecificationBase
                object.
            ValueError: If write_mode not is not "copy" or "move".
            FileNotFoundError: If root is not a directory or does not exist.
            FileNotFoundError: If hidebound_parent_dir is not directory or
                does not exist.


        Returns:
            Database: Database instance.
        '''
        # validate spec classes
        bad_specs = list(filter(
            lambda x: not issubclass(x, SpecificationBase), specifications
        ))
        if len(bad_specs) > 0:
            msg = f'SpecificationBase may only contain subclasses of '
            msg += f'SpecificationBase. Found: {bad_specs}.'
            raise TypeError(msg)

        # validate root dir
        root = root_dir
        if not isinstance(root, Path):
            root = Path(root)
        if not root.is_dir():
            msg = f'{root} is not a directory or does not exist.'
            raise FileNotFoundError(msg)

        # validate write mode
        modes = ['copy', 'move']
        if write_mode not in modes:
            msg = f'Invalid write mode: {write_mode} not in {modes}.'
            raise ValueError(msg)

        # validate hidebound root dir
        hb_root = hidebound_parent_dir
        if not isinstance(hb_root, Path):
            hb_root = Path(hb_root)
        if not hb_root.is_dir():
            msg = f'{hb_root} is not a directory or does not exist.'
            raise FileNotFoundError(msg)

        # create hidebound root dir
        hb_root = Path(hb_root, 'hidebound')
        os.makedirs(hb_root, exist_ok=True)

        self._root = root
        self._hb_root = hb_root
        self._include_regex = include_regex
        self._exclude_regex = exclude_regex
        self._write_mode = write_mode
        self._specifications = {x.__name__.lower(): x for x in specifications}
        self.data = None

    def update(self):
        '''
        Recurse root directory, populate self.data with its files, locate and
        validate assets.

        Returns:
            Database: self.
        '''
        data = tools.directory_to_dataframe(
            self._root,
            include_regex=self._include_regex,
            exclude_regex=self._exclude_regex
        )
        if len(data) > 0:
            db_tools._add_specification(data, self._specifications)
            db_tools._validate_filepath(data)
            db_tools._add_file_traits(data)
            db_tools._add_asset_name(data)
            db_tools._add_asset_path(data)
            db_tools._add_asset_type(data)
            db_tools._add_asset_traits(data)
            db_tools._validate_assets(data)

        data = db_tools._cleanup(data)
        self.data = data
        return self

    def create(self):
        '''
        Extract valid assets as data and metadata within the hidebound
        directory.

        Writes:

            * file data to hb_parent/hidebound/data - under same directory structure
            * file metadata as json to hb_parent/hidebound/metadata/file
            * asset metadata as json to hb_parent/hidebound/metadata/asset

        Returns:
            Database: self.
        '''
        def write_json(obj, filepath):
            with open(filepath, 'w') as f:
                json.dump(obj, f)

        temp = db_tools._get_data_for_write(
            self.data, self._root, self._hb_root
        )
        if temp is None:
            return self

        file_data, file_meta, asset_meta = temp

        # make directories
        for item in temp:
            item.target.apply(lambda x: os.makedirs(Path(x).parent, exist_ok=True))

        # write file data
        if self._write_mode == 'move':
            file_data.apply(lambda x: shutil.move(x.source, x.target), axis=1)
        else:
            file_data.apply(lambda x: shutil.copy2(x.source, x.target), axis=1)

        # write file metadata
        file_meta.apply(lambda x: write_json(x.metadata, x.target), axis=1)

        # write asset metadata
        asset_meta.apply(lambda x: write_json(x.metadata, x.target), axis=1)

        return self
