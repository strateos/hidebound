from pathlib import Path
import os
import unittest

from pandas import DataFrame
from schematics.types import ListType, IntType, StringType
import numpy as np
import skimage.io

from hidebound.specification_base import SpecificationBase
import hidebound.traits as tr
import hidebound.validators as vd
# ------------------------------------------------------------------------------


class DatabaseTestBase(unittest.TestCase):
    columns = [
        'project',
        'specification',
        'descriptor',
        'version',
        'coordinate',
        'frame',
        'extension',
        'filename',
        'filepath',
        'file_error',
        'file_traits',
        'asset_name',
        'asset_path',
        'asset_type',
        'asset_traits',
        'asset_error',
        'asset_valid',
        # 'asset_id',
    ]

    def get_data(self, root, nans=False):
        data = [
            [0, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v001', 'p-proj001_s-spec001_d-pizza_v001_c000-001_f0001.png',  None                                ],  # noqa E501 E241
            [0, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v001', 'p-proj001_s-spec001_d-pizza_v001_c000-001_f0002.png',  None                                ],  # noqa E501 E241
            [0, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v001', 'p-proj001_s-spec001_d-pizza_v001_c000-001_f0003.png',  None                                ],  # noqa E501 E241
            [1, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-000_f0001.png',  None                                ],  # noqa E501 E241
            [1, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-000_f0002.png',  None                                ],  # noqa E501 E241
            [1, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-000_f0003.png',  None                                ],  # noqa E501 E241
            [1, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-000_f0004.png',  None                                ],  # noqa E501 E241
            [2, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-001_f0001.png',  None                                ],  # noqa E501 E241
            [2, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-001_f0002.png',  None                                ],  # noqa E501 E241
            [2, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-001_f0003.png',  None                                ],  # noqa E501 E241
            [2, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-001_f0004.png',  None                                ],  # noqa E501 E241
            [3, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec001_d-kiwi_v003_c000-001_f0001.png', ' Inconsistent descriptor field token'],  # noqa E501 E241
            [3, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec001_d-pizza_v003_c000-001_f0002.png',  None                                ],  # noqa E501 E241
            [3, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec001_d-PIZZA_v003_c000-001_f0003.png',  'Illegal descriptor field token'    ],  # noqa E501 E241
            [3, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec001_d-pizza_v003_c000-001_f0004.png',  None                                ],  # noqa E501 E241
            [3, None,      'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec0001_d-pizza_v003_c000-001_f0005.png', 'Illegal specification field token' ],  # noqa E501 E241
            [3, None,      'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'misc.txt',                                             'SpecificationBase not found'       ],  # noqa E501 E241
            [4, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v001',   'p-proj001_s-spec002_d-taco_v001_f0000.jpg',            None                                ],  # noqa E501 E241
            [4, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v001',   'p-proj001_s-spec002_d-taco_v001_f0001.jpg',            None                                ],  # noqa E501 E241
            [4, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v001',   'p-proj001_s-spec002_d-taco_v001_f0002.jpg',            None                                ],  # noqa E501 E241
            [5, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v001_f0000.jpg',            'Invalid asset directory name'      ],  # noqa E501 E241
            [5, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v002_f0001.jpg',            None                                ],  # noqa E501 E241
            [5, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v002',                      'Expected "_"'                      ],  # noqa E501 E241
            [5, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v02_f0003.jpg',             'Illegal version field token'       ],  # noqa E501 E241
            [6, 'vdb001',  'proj002/vdb001',                                         'p-proj002_s-vdb001_d-bagel_v001.vdb',                  'Specification not found'           ],  # noqa E501 E241
            [6, 'vdb001',  'proj002/vdb001',                                         'p-proj002_s-vdb001_d-bagel_v002.vdb',                  'Specification not found'           ],  # noqa E501 E241
            [6, 'vdb001',  'proj002/vdb001',                                         'p-proj002_s-vdb001_d-bagel_v003.vdb',                  'Specification not found'           ],  # noqa E501 E241
        ]

        data = DataFrame(data)
        data.columns = ['asset_id', 'specification', 'asset_path', 'filename', 'file_error']

        data.asset_path = data.asset_path.apply(lambda x: root + '/' + x)
        data['asset_name'] = data.asset_path.apply(lambda x: x.split('/')[-1])

        data['filepath'] = data\
            .apply(lambda x: Path(root, x.asset_path, x.filename), axis=1)

        Spec001, Spec002, BadSpec = self.get_specifications()
        specs = {
            Spec001.name: Spec001,
            Spec002.name: Spec002,
            None: np.nan,
            'vdb001': np.nan,
        }
        data['specification_class'] = data.specification\
            .apply(lambda x: specs[x])

        if nans:
            data = data.applymap(lambda x: np.nan if x is None else x)
        return data

    def create_files(self, root):
        data = self.get_data(root)
        for filepath in data.filepath.tolist():
            os.makedirs(filepath.parent, exist_ok=True)

            ext = os.path.splitext(filepath)[-1][1:]
            if ext in ['png', 'jpg']:
                img = np.zeros((5, 4, 3), dtype=np.uint8)
                skimage.io.imsave(filepath.as_posix(), img)
            else:
                with open(filepath, 'w') as f:
                    f.write('')
        return data

    def get_directory_to_dataframe_data(self, root):
        files = self.get_data(root)
        data = DataFrame()
        data['filename'] = files.filename
        data['filepath'] = files.asset_path
        data.filepath = data\
            .apply(lambda x: Path(x.filepath, x.filename), axis=1)
        data['extension'] = files\
            .filename.apply(lambda x: os.path.splitext(x)[1:])
        return data

    def get_specifications(self):
        class Spec001(SpecificationBase):
            name = 'spec001'
            filename_fields = [
                'project',
                'specification',
                'descriptor',
                'version',
                'coordinate',
                'frame',
                'extension',
            ]
            coordinate = ListType(ListType(IntType()), required=True)
            frame = ListType(IntType(), required=True)
            extension = ListType(
                StringType(),
                required=True,
                validators=[lambda x: vd.is_eq(x, 'png')]
            )

            height = ListType(
                IntType(),
                required=True, validators=[lambda x: vd.is_eq(x, 5)]
            )
            width = ListType(
                IntType(),
                required=True, validators=[lambda x: vd.is_eq(x, 4)]
            )
            channels = ListType(
                IntType(),
                required=True, validators=[lambda x: vd.is_eq(x, 3)]
            )

            file_traits = dict(
                width=tr.get_image_width,
                height=tr.get_image_height,
                channels=tr.get_image_channels,
            )

            def get_asset_path(self, filepath):
                return Path(filepath).parents[0]

        class Spec002(SpecificationBase):
            name = 'spec002'
            filename_fields = [
                'project',
                'specification',
                'descriptor',
                'version',
                'frame',
                'extension',
            ]

            frame = ListType(IntType(), required=True)
            extension = ListType(
                StringType(),
                required=True,
                validators=[lambda x: vd.is_eq(x, 'jpg')]
            )

            height = ListType(
                IntType(),
                required=True, validators=[lambda x: vd.is_eq(x, 5)]
            )
            width = ListType(
                IntType(),
                required=True, validators=[lambda x: vd.is_eq(x, 4)]
            )
            channels = ListType(
                IntType(),
                required=True, validators=[lambda x: vd.is_eq(x, 3)]
            )

            file_traits = dict(
                width=tr.get_image_width,
                height=tr.get_image_height,
                channels=tr.get_image_channels,
            )

            def get_asset_path(self, filepath):
                return Path(filepath).parents[0]

        class BadSpec:
            pass

        return Spec001, Spec002, BadSpec
