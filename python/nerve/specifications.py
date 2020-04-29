from schematics.types import IntType, StringType

import nerve.validators as vd
from nerve.specification_base import SequenceSpecificationBase
# ------------------------------------------------------------------------------


'''
The specifications module house all the specifications for all nerve projects.

All specifications used in production should be subclassed from the base classes
found in the specification_base module. All class attributes must have a
"get_[attribute]" function in the traits module and should have one or more
validators related to the value of that trait (especially if required).
'''


class Raw001(SequenceSpecificationBase):
    '''
    Raw 1K x 1K pngs.

    Attributes:
        filename_fields (list[str]): project, specification, descriptor,
            version, frame, extension
        asset_name_fields (list[str]): project, specification, descriptor,
            version,
        height (int): Image height. Must be 1024.
        width (int): Image width. Must be 1024.
        extension (str): File extension. Must be "png".
    '''
    name = 'raw001'
    filename_fields = [
        'project', 'specification', 'descriptor', 'version', 'frame',
        'extension'
    ]
    height = IntType(required=True, validators=[lambda x: vd.is_eq(x, 1024)])
    width = IntType(required=True, validators=[lambda x: vd.is_eq(x, 1024)])
    frame = IntType(required=True, validators=[vd.is_frame])
    extension = StringType(
        required=True,
        validators=[vd.is_extension, lambda x: vd.is_eq(x, 'png')]
    )
