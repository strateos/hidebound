import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import flasgger as swg
import flask
import lunchbox.tools as lbt
import numpy as np

from hidebound.core.database_test_base import DatabaseTestBase
from hidebound.exporters.mock_girder import MockGirderExporter
import hidebound.server.api as api
# ------------------------------------------------------------------------------


class ApiTests(DatabaseTestBase):
    def setUp(self):
        # setup files and dirs
        self.tempdir = TemporaryDirectory()
        temp = self.tempdir.name
        self.hb_root = Path(temp, 'hidebound').as_posix()
        os.makedirs(self.hb_root)

        self.root = Path(temp, 'projects').as_posix()
        os.makedirs(self.root)

        self.create_files(self.root)

        # setup app
        app = flask.Flask(__name__)
        swg.Swagger(app)
        app.register_blueprint(api.API)
        self.context = app.app_context()
        self.context.push()

        self.app = self.context.app
        api.DATABASE = None
        api.CONFIG = None

        self.api = api
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True

        self.specs = lbt.relative_path(
            __file__,
            '../core/test_specifications.py'
        ).absolute().as_posix()

    def tearDown(self):
        self.context.pop()
        self.tempdir.cleanup()

    # INITIALIZE----------------------------------------------------------------
    def test_initialize(self):
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        result = self.client.post('/api/initialize', json=config)
        result = result.json['message']
        expected = 'Database initialized.'
        self.assertEqual(result, expected)

    def test_initialize_no_config(self):
        result = self.client.post('/api/initialize').json['message']
        expected = 'Please supply a config dictionary.'
        self.assertRegex(result, expected)

    def test_initialize_bad_config_type(self):
        bad_config = '["a", "b"]'
        result = self.client.post('/api/initialize', json=bad_config)
        result = result.json['message']
        expected = 'Please supply a config dictionary.'
        self.assertRegex(result, expected)

    def test_initialize_bad_config(self):
        config = dict(
            root_directory='/foo/bar',
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        result = self.client.post('/api/initialize', json=config)
        result = result.json['message']
        expected = '/foo/bar is not a directory or does not exist.'
        self.assertRegex(result, expected)

    # CREATE--------------------------------------------------------------------
    def test_create(self):
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)
        self.client.post('/api/update')

        data = Path(self.hb_root, 'data')
        meta = Path(self.hb_root, 'metadata')
        self.assertFalse(os.path.exists(data))
        self.assertFalse(os.path.exists(meta))

        result = self.client.post('/api/create').json['message']
        expected = 'Hidebound data created.'
        self.assertEqual(result, expected)
        self.assertTrue(os.path.exists(data))
        self.assertTrue(os.path.exists(meta))

    def test_create_no_update(self):
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)

        result = self.client.post('/api/create').json['message']
        expected = 'Database not updated. Please call update.'
        self.assertRegex(result, expected)

    def test_create_no_init(self):
        result = self.client.post('/api/create').json['message']
        expected = 'Database not initialized. Please call initialize.'
        self.assertRegex(result, expected)

    # READ----------------------------------------------------------------------
    def test_read(self):
        # init database
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)
        self.client.post('/api/update')

        # call read
        result = self.client.post('/api/read').json['response']
        expected = api.DATABASE.read()\
            .replace({np.nan: None})\
            .to_dict(orient='records')
        self.assertEqual(result, expected)

        # test general exceptions
        api.DATABASE = 'foo'
        result = self.client.post('/api/read').json['error']
        self.assertEqual(result, 'AttributeError')

    def test_read_group_by_asset(self):
        # init database
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)
        self.client.post('/api/update')

        # good params
        params = json.dumps({'group_by_asset': True})
        result = self.client.post('/api/read', json=params).json['response']
        expected = api.DATABASE.read(group_by_asset=True)\
            .replace({np.nan: None})\
            .to_dict(orient='records')
        self.assertEqual(result, expected)

        # bad params
        params = json.dumps({'foo': True})
        result = self.client.post('/api/read', json=params).json['message']
        expected = 'Please supply valid read params in the form '
        expected += r'\{"group_by_asset": BOOL\}\.'
        self.assertRegex(result, expected)

        params = json.dumps({'group_by_asset': 'foo'})
        result = self.client.post('/api/read', json=params).json['message']
        expected = 'Please supply valid read params in the form '
        expected += r'\{"group_by_asset": BOOL\}\.'
        self.assertRegex(result, expected)

    def test_read_no_init(self):
        result = self.client.post('/api/read').json['message']
        expected = 'Database not initialized. Please call initialize.'
        self.assertRegex(result, expected)

    def test_read_no_update(self):
        # init database
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)

        # call read
        result = self.client.post('/api/read').json['message']
        expected = 'Database not updated. Please call update.'
        self.assertRegex(result, expected)

    # UPDATE--------------------------------------------------------------------
    def test_update(self):
        # init database
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)

        # call update
        result = self.client.post('/api/update').json['message']
        expected = 'Database updated.'
        self.assertEqual(result, expected)

    def test_update_no_init(self):
        result = self.client.post('/api/update').json['message']
        expected = 'Database not initialized. Please call initialize.'
        self.assertRegex(result, expected)

    # DELETE--------------------------------------------------------------------
    def test_delete(self):
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)
        self.client.post('/api/update')
        self.client.post('/api/create')

        data = Path(self.hb_root, 'data')
        meta = Path(self.hb_root, 'metadata')
        self.assertTrue(os.path.exists(data))
        self.assertTrue(os.path.exists(meta))

        result = self.client.post('/api/delete').json['message']
        expected = 'Hidebound data deleted.'
        self.assertEqual(result, expected)
        self.assertFalse(os.path.exists(data))
        self.assertFalse(os.path.exists(meta))

    def test_delete_no_create(self):
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)

        result = self.client.post('/api/delete').json['message']
        expected = 'Hidebound data deleted.'
        self.assertEqual(result, expected)

        data = Path(self.hb_root, 'data')
        meta = Path(self.hb_root, 'metadata')
        self.assertFalse(os.path.exists(data))
        self.assertFalse(os.path.exists(meta))

    def test_delete_no_init(self):
        result = self.client.post('/api/delete').json['message']
        expected = 'Database not initialized. Please call initialize.'
        self.assertRegex(result, expected)

    # EXPORT--------------------------------------------------------------------
    def test_export(self):
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
            exporters=dict(girder=dict(api_key='api_key', root_id='root_id'))
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)
        self.api.DATABASE._Database__exporter_lut = dict(
            girder=MockGirderExporter
        )
        self.client.post('/api/update')
        self.client.post('/api/create')
        self.client.post('/api/export')

        client = self.api.DATABASE._Database__exporter_lut['girder']._client
        result = list(client.folders.keys())
        asset_paths = [
            'p-proj001_s-spec001_d-pizza_v001',
            'p-proj001_s-spec001_d-pizza_v002',
        ]
        for expected in asset_paths:
            self.assertIn(expected, result)

    def test_export_no_init(self):
        result = self.client.post('/api/export').json['message']
        expected = 'Database not initialized. Please call initialize.'
        self.assertRegex(result, expected)

    def test_export_error(self):
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
            exporters=dict(girder=dict(api_key='api_key', root_id='root_id'))
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)
        self.api.DATABASE._Database__exporter_lut = dict(
            girder=MockGirderExporter
        )
        self.client.post('/api/update')
        result = self.client.post('/api/export').json['message']
        expected = 'hidebound/data directory does not exist'
        self.assertRegex(result, expected)

    # SEARCH--------------------------------------------------------------------
    def test_search(self):
        # init database
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)
        self.client.post('/api/update')

        # call search
        query = 'SELECT * FROM data WHERE specification == "spec001"'
        temp = {'query': query}
        temp = json.dumps(temp)
        result = self.client.post('/api/search', json=temp).json['response']
        expected = api.DATABASE.search(query)\
            .replace({np.nan: None})\
            .to_dict(orient='records')
        self.assertEqual(result, expected)

    def test_search_group_by_asset(self):
        # init database
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)
        self.client.post('/api/update')

        # call search
        query = 'SELECT * FROM data WHERE asset_type == "sequence"'
        temp = {'query': query, 'group_by_asset': True}
        temp = json.dumps(temp)
        result = self.client.post('/api/search', json=temp).json['response']
        expected = api.DATABASE.search(query, group_by_asset=True)\
            .replace({np.nan: None})\
            .to_dict(orient='records')
        self.assertEqual(result, expected)

    def test_search_no_query(self):
        result = self.client.post('/api/search').json['message']
        expected = 'Please supply valid search params in the form '
        expected += r'\{"query": SQL query, "group_by_asset": BOOL\}\.'
        self.assertRegex(result, expected)

    def test_search_bad_json(self):
        query = {'foo': 'bar'}
        query = json.dumps(query)
        result = self.client.post('/api/search', json=query).json['message']
        expected = 'Please supply valid search params in the form '
        expected += r'\{"query": SQL query, "group_by_asset": BOOL\}\.'
        self.assertRegex(result, expected)

    def test_search_bad_group_by_asset(self):
        params = dict(
            query='SELECT * FROM data WHERE asset_type == "sequence"',
            group_by_asset='foo'
        )
        params = json.dumps(params)
        result = self.client.post('/api/search', json=params).json['message']
        expected = 'Please supply valid search params in the form '
        expected += r'\{"query": SQL query, "group_by_asset": BOOL\}\.'
        self.assertRegex(result, expected)

    def test_search_bad_query(self):
        # init database
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)
        self.client.post('/api/update')

        # call search
        query = {'query': 'SELECT * FROM data WHERE foo == "bar"'}
        query = json.dumps(query)
        result = self.client.post('/api/search', json=query).json['error']
        expected = 'PandaSQLException'
        self.assertEqual(result, expected)

    def test_search_no_init(self):
        query = {'query': 'SELECT * FROM data WHERE specification == "spec001"'}
        query = json.dumps(query)
        result = self.client.post('/api/search', json=query).json['message']
        expected = 'Database not initialized. Please call initialize.'
        self.assertRegex(result, expected)

    def test_search_no_update(self):
        # init database
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)

        # call search
        query = {'query': 'SELECT * FROM data WHERE specification == "spec001"'}
        query = json.dumps(query)
        result = self.client.post('/api/search', json=query).json['message']
        expected = 'Database not updated. Please call update.'
        self.assertRegex(result, expected)
