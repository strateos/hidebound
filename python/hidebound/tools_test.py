from pathlib import Path
import os
from tempfile import TemporaryDirectory
import time
import unittest

from pandas import DataFrame
from schematics.exceptions import DataError, ValidationError
from schematics.models import Model
from schematics.types import StringType

import hidebound.tools as tools
# ------------------------------------------------------------------------------


class ToolsTests(unittest.TestCase):
    def create_files(self, root):
        filepaths = [
            'a/1.foo',
            'a/b/2.json',
            'a/b/3.txt',
            'a/b/c/4.json',
            'a/b/c/5.txt'
        ]
        filepaths = [Path(root, x) for x in filepaths]
        for filepath in filepaths:
            os.makedirs(filepath.parent, exist_ok=True)
            with open(filepath, 'w') as f:
                f.write('')
        return filepaths

    def test_try_(self):
        result = tools.try_(lambda x: int(x), 1.0, return_item='item')
        self.assertEqual(result, 1)

        result = tools.try_(lambda x: int(x), 'foo', return_item='bar')
        self.assertEqual(result, 'bar')

        result = tools.try_(lambda x: int(x), 'foo')
        self.assertEqual(result, 'foo')

        result = tools.try_(lambda x: int(x), 'foo', return_item='error')
        self.assertIsInstance(result, ValueError)

    def test_relative_path(self):
        result = tools.relative_path(__file__, '../../resources/foo.txt')
        self.assertTrue(os.path.exists(result))

    def test_error_to_string(self):
        error = KeyError('Foo')
        expected = 'KeyError( Foo )'
        result = tools.error_to_string(error)
        self.assertEqual(result, expected)

        error = ValidationError(['foo', 'bar'])
        expected = 'ValidationError(\nfoo\nbar\n)'
        result = tools.error_to_string(error)
        self.assertEqual(result, expected)

        class Foo(Model):
            bar = StringType(required=True)
            baz = StringType(required=True)

        try:
            Foo({}).validate()
        except DataError as e:
            result = tools.error_to_string(e)
        expected = r'DataError\(\n.*(bar|baz).*\n.*(bar|baz).*\n\)'
        self.assertRegex(result, expected)

    def test_to_prototype(self):
        dicts = [
            dict(a=1, b=2, c=3),
            dict(a=1, b=2, d=3),
            dict(a=1, b=2, e=3),
        ]
        expected = dict(a=[1, 1, 1], b=[2, 2, 2], c=[3], d=[3], e=[3])
        result = tools.to_prototype(dicts)
        self.assertEqual(result, expected)

    def test_stopwatch(self):
        stopwatch = tools.StopWatch()
        stopwatch.start()
        time.sleep(0.01)
        stopwatch.stop()

        self.assertAlmostEqual(stopwatch.delta.microseconds, 10000, delta=10000)
        self.assertEqual(stopwatch.human_readable_delta, '0.01 seconds')

        stopwatch.start()
        time.sleep(0.02)
        stopwatch.stop()

        self.assertAlmostEqual(stopwatch.delta.microseconds, 20000, delta=10000)
        self.assertEqual(stopwatch.human_readable_delta, '0.02 seconds')

    def test_list_all_files(self):
        expected = '/foo/bar is not a directory or does not exist.'
        with self.assertRaisesRegexp(FileNotFoundError, expected):
            next(tools.list_all_files('/foo/bar'))

        expected = '/foo.bar is not a directory or does not exist.'
        with self.assertRaisesRegexp(FileNotFoundError, expected):
            next(tools.list_all_files('/foo.bar'))

        with TemporaryDirectory() as root:
            expected = sorted(self.create_files(root))
            result = sorted(list(tools.list_all_files(root)))
            self.assertEqual(result, expected)

    def test_list_all_files_include(self):
        with TemporaryDirectory() as root:
            regex = r'\.txt'

            self.create_files(root)
            expected = [
                Path(root, 'a/b/3.txt'),
                Path(root, 'a/b/c/5.txt'),
            ]

            result = tools.list_all_files(root, include_regex=regex)
            result = sorted(list(result))
            self.assertEqual(result, expected)

    def test_list_all_files_exclude(self):
        with TemporaryDirectory() as root:
            regex = r'\.txt'

            self.create_files(root)
            expected = [
                Path(root, 'a/1.foo'),
                Path(root, 'a/b/2.json'),
                Path(root, 'a/b/c/4.json'),
            ]

            result = tools.list_all_files(root, exclude_regex=regex)
            result = sorted(list(result))
            self.assertEqual(result, expected)

    def test_list_all_files_include_exclude(self):
        with TemporaryDirectory() as root:
            i_regex = r'/a/b'
            e_regex = r'\.json'

            self.create_files(root)
            expected = [
                Path(root, 'a/b/3.txt'),
                Path(root, 'a/b/c/5.txt'),
            ]

            result = tools.list_all_files(
                root,
                include_regex=i_regex,
                exclude_regex=e_regex
            )
            result = sorted(list(result))
            self.assertEqual(result, expected)

    def test_directory_to_dataframe(self):
        with TemporaryDirectory() as root:
            self.create_files(root)
            filepaths = [
                Path(root, 'a/b/3.txt'),
                Path(root, 'a/b/c/5.txt'),
            ]
            expected = DataFrame()
            expected['filepath'] = filepaths
            expected['filename'] = expected.filepath.apply(lambda x: x.name)
            expected['extension'] = 'txt'
            expected.filepath = expected.filepath.apply(lambda x: x.as_posix())

            result = tools.directory_to_dataframe(
                root,
                include_regex=r'/a/b',
                exclude_regex=r'\.json'
            )
            cols = ['filepath', 'filename', 'extension']
            for col in cols:
                self.assertEqual(result[col].tolist(), expected[col].tolist())