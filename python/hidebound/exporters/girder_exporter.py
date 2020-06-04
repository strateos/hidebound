from pathlib import Path

from girder_client import HttpError
import girder_client

from hidebound.exporters.exporter_base import ExporterBase
# ------------------------------------------------------------------------------


class GirderExporter(ExporterBase):
    '''
    Export for Girder asset framework.
    '''
    def __init__(
        self,
        api_key,
        root_id,
        root_type='collection',
        host='0.0.0.0',
        port=8080,
        client=None,
    ):
        '''
        Constructs a GirderExporter instances and creates a Girder client.

        Args:
            api_key (str): Girder API key.
            root_id (str): ID of folder or collection under which all data will
                be exported.
            root_type (str, optional): Root entity type. Default: collection.
                Options: folder, collection
            host (str, optional): Docker host IP address. Default: 0.0.0.0.
            port (int, optional): Docker host port. Default: 8080.
            client (object, optional): Client instance, for testing.
                Default: None.

        Raises:
            ValueError: If invalid root_type given.
        '''
        # sudo ip addr show docker0 | grep inet | grep docker0 | awk '{print $2}' | sed 's/\/.*//'
        # will give you the ip address of the docker network which binds to
        # localhost
        if root_type not in ['folder', 'collection']:
            msg = f'Invalid root_type. {root_type} is not folder or collection.'
            raise ValueError(msg)

        self._url = f'http://{host}:{port}/api/v1'

        if client is None:
            client = girder_client.GirderClient(apiUrl=self._url)
            client.authenticate(apiKey=api_key)
        self._client = client

        self._root_id = root_id
        self._root_type = root_type

    def _export_dirs(self, dirpath, metadata={}, exists_ok=False):
        '''
        Recursively export all the dirtectories found in given path.

        Args:
            dirpath (Path or str): Directory paht to be exported.
            metadata (dict, optional): Metadata to be appended to final
                directory. Default: {}.

        Returns:
            dict: Response (contains _id key).
        '''
        dirs = Path(dirpath).parts
        dirs = list(filter(lambda x: x != '/', dirs))

        # if dirpath has no parents then export to root with metadata
        if len(dirs) == 1:
            return self._client.createFolder(
                self._root_id,
                dirs[0],
                metadata=metadata,
                reuseExisting=exists_ok,
                parentType=self._root_type,
            )

        # if dirpath has parents then export all parent directories
        response = dict(_id=self._root_id)
        parent_type = self._root_type
        for dir_ in dirs[:-1]:
            response = self._client.createFolder(
                response['_id'],
                dir_,
                reuseExisting=True,
                parentType=parent_type
            )
            parent_type = 'folder'

        # then export last directory with metadata
        return self._client.createFolder(
            response['_id'],
            dirs[-1],
            metadata=metadata,
            reuseExisting=exists_ok,
            parentType='folder',
        )

    def _export_asset(self, metadata):
        '''
        Export asset metadata to Girder.
        Metadata must contain these fields:
            * asset_type
            * asset_path_relative

        Args:
            metadata (dict): Asset metadata.

        Raises:
            HttpError: If final asset directory already exists.
        '''
        if metadata['asset_type'] != 'file':
            try:
                self._export_dirs(
                    metadata['asset_path_relative'],
                    metadata=metadata
                )
            except HttpError as e:
                msg = f"{metadata['asset_path_relative']} directory already "
                msg += 'exists. ' + e.responseText
                e.responseText = msg
                raise e

    def _export_file(self, metadata):
        '''
        Export file metadata to Girder.
        Metadata must contain these fields:
            * filepath_relative
            * filename
            * filepath

        Args:
            metadata (dict): File metadata.
        '''
        filepath = metadata['filepath_relative']
        filename = metadata['filename']
        parent_dir = Path(filepath).parent
        response = self._export_dirs(parent_dir, exists_ok=True)

        # folder error will always be raised before duplicate file conflict is
        # encountered, so don't test for duplicate files within directory

        response = self._client.createItem(
            response['_id'],
            filename,
            metadata=metadata,
            reuseExisting=True,
        )
        response = self._client\
            .uploadFileToItem(response['_id'], metadata['filepath'])
        return response